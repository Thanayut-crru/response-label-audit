"""Controlled factorial ablation: purge x exact-overlap exclusion x calibration.

The fresh purged pilot and the archived P2c pipeline differ in three procedural
factors at once. This script crosses them on identical evaluation units so that
differences in point estimates and precision can be attributed to a factor:

- purge: 0 or 5 observed sessions removed before each test block;
- exact-overlap exclusion: off or on (training bags sharing a normalized text
  hash with the test block are removed);
- calibration: none, or the P2c forward-only ridge calibrator fitted on
  completed earlier out-of-sample blocks.

Everything else is held fixed: labels, vectorizer, learners, seeds, folds,
evaluation stock-days, and the loss scale. Two cells must reproduce archived
artifacts exactly, which is checked before any inference is reported:
(purge 5, exclusion on) reproduces the fresh pilot predictions, and
(purge 0, exclusion off) reproduces the archived P2b predictions; applying the
imported P2c calibrator to P2b reproduces the archived calibrated predictions.

The first outer block has no earlier out-of-sample history and serves as the
calibration warm-up, so every cell is evaluated on blocks 2-7.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import time

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG
PURGES = [0, 5]
EXCLUSIONS = [False, True]
CALIBRATIONS = [False, True]
RDFL = 'RDFL_SOFT'
COMPARATORS = ['ZERO', 'DIRECT_HUBER', 'ORDINARY_SOFT', 'HARD_RDFL']
METHODS = ['ZERO', 'DIRECT_HUBER', 'HARD_RDFL', 'ORDINARY_SOFT', RDFL]
SCALE_PURGE = 5   # one loss scale for every cell: training-history SD before the purged boundary


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprint(text):
    normalized = re.sub(r'\s+', ' ', str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def cell_name(purge, exclude, calibrate):
    return f'purge{purge}_{"excl" if exclude else "noexcl"}_{"cal" if calibrate else "raw"}'


def train_config(m, panel, bags, purge, exclude):
    """One training configuration across all outer folds; mirrors 02_purged_pilot.py."""
    valid = panel[panel.outcome_data_valid.astype(str).str.lower().eq('true')]
    dates = np.sort(valid.Date.unique())
    parts, folds = [], []
    for start, stop in zip(m.OUTER_STARTS[:-1], m.OUTER_STARTS[1:]):
        prior = dates[dates < start.to_datetime64()]
        if len(prior) <= max(purge, SCALE_PURGE):
            continue
        boundary = pd.Timestamp(prior[-purge]) if purge else pd.Timestamp(start)
        scale_boundary = pd.Timestamp(prior[-SCALE_PURGE])
        train = bags[bags.Date < boundary].copy()
        test = bags[(bags.Date >= start) & (bags.Date < stop)].copy()
        if test.empty:
            continue
        excluded = 0
        if exclude:
            test_hashes = set().union(*test.text_hashes)
            overlap = train.text_hashes.map(lambda s: bool(s & test_hashes))
            excluded = int(overlap.sum())
            train = train.loc[~overlap]
        train = train.reset_index(drop=True)
        retained = train[train.retain_for_text_training]
        ordinary = train[np.isfinite(train[['residual_z', 'volume_deviation']].to_numpy(float)).all(axis=1)]
        if len(retained) < 100 or len(ordinary) < 100:
            raise RuntimeError('Insufficient fold data; do not silently omit the fold')
        vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=3, max_df=.98,
                              max_features=20000, sublinear_tf=True, norm='l2', dtype=np.float32)
        x = vec.fit_transform(train.bag_text)
        xt = vec.transform(test.bag_text)
        q = retained[['p_negative', 'p_low_response', 'p_positive']].to_numpy(float)
        w = retained.label_confidence.to_numpy(float)
        p = m.fit_soft_ensemble(x[retained.index], q, w, xt)
        rdfl = p @ m.class_centers(retained.target_open_close.to_numpy(float), q, w)
        hard = retained.weak_label.map(m.LABEL_TO_INT).to_numpy(int)
        hp = m.fit_hard_ensemble(x[retained.index], hard, xt)
        hpred = hp @ m.class_centers(retained.target_open_close.to_numpy(float), np.eye(3)[hard])
        oq = m.ordinary_probabilities(ordinary)
        op = m.fit_soft_ensemble(x[ordinary.index], oq, np.ones(len(ordinary)), xt)
        opred = op @ m.class_centers(ordinary.target_open_close.to_numpy(float), oq)
        predictions = {'ZERO': np.zeros(len(test)),
                       'DIRECT_HUBER': m.fit_direct_ensemble(x, train.target_open_close.to_numpy(float), xt),
                       'HARD_RDFL': hpred, 'ORDINARY_SOFT': opred, RDFL: rdfl}
        scales = valid[valid.Date < scale_boundary].groupby('Symbol').target_open_close.std(ddof=1).clip(lower=1e-6)
        for method, pred in predictions.items():
            frame = test[['Date', 'Symbol', 'target_open_close']].rename(columns={'target_open_close': 'actual'}).copy()
            frame['prediction'] = pred
            frame['method'] = method
            frame['block'] = str(start.date())
            frame['stock_training_scale'] = frame.Symbol.map(scales)
            parts.append(frame)
        folds.append({'purge': purge, 'exact_overlap_exclusion': exclude, 'test_start': str(start.date()),
                      'train_end': str(train.Date.max().date()), 'train_bags': len(train),
                      'test_bags': len(test), 'exact_overlap_train_bags_removed': excluded})
    return pd.concat(parts, ignore_index=True), folds


def forward_calibrate(calibration, raw):
    """Apply the imported P2c calibrator exactly as its main() does."""
    raw = raw.copy()
    raw['Date'] = pd.to_datetime(raw['Date'])
    order = raw.groupby('block')['Date'].min().sort_values().index.tolist()
    parts = []
    for block in order[1:]:
        start = raw.loc[raw['block'] == block, 'Date'].min()
        for method in METHODS:
            current = raw[(raw['block'] == block) & (raw['method'] == method)].copy()
            if method == 'ZERO':
                current['calibrated_prediction'] = 0.0
            else:
                history = raw[(raw['Date'] < start) & (raw['method'] == method)].copy()
                calibrator = calibration.fit_calibrator(history)
                current['calibrated_prediction'] = calibration.apply_calibrator(
                    calibrator, current['prediction'].to_numpy(dtype=float))
            parts.append(current)
    return pd.concat(parts, ignore_index=True), order[0]


def keyed(frame, column):
    frame = frame.copy()
    frame['Date'] = pd.to_datetime(frame['Date'])
    return frame.set_index(['Date', 'Symbol', 'method'])[column].sort_index()


def assert_reproduces(label, produced, archived, column_produced, column_archived):
    """Predictions are daily log returns of order 1e-2. A gap below 1e-8 in return units is
    floating-point noise across environments (P2b was produced outside this workspace), four
    orders of magnitude below any reported loss difference; the observed gap is recorded."""
    a = keyed(produced, column_produced)
    b = keyed(archived, column_archived)
    if not a.index.equals(b.index):
        raise ValueError(f'{label}: evaluation units differ from the archived artifact')
    gap = float(np.max(np.abs(a.to_numpy() - b.to_numpy())))
    if not np.allclose(a.to_numpy(), b.to_numpy(), rtol=0, atol=1e-8):
        raise ValueError(f'{label}: does not reproduce the archived artifact (max abs gap {gap:.3g})')
    return gap


def paired(a, b, rng, block, family_size):
    """Same estimands as 03_inference_and_report.py and 07_power_analysis.py."""
    iterations = int(CONFIG['inference']['bootstrap_iterations'])
    diff, rel = common.bootstrap_paired(a, b, iterations, rng, block)
    observed = float(np.mean(a) - np.mean(b))
    finite = rel[np.isfinite(rel)]
    ci95 = common.interval(rel)
    family = common.interval(rel, .1 / family_size)
    return {'relative_improvement': observed / float(np.mean(a)),
            'bootstrap_se': float(finite.std(ddof=1)),
            'relative_ci95_low': ci95[0], 'relative_ci95_high': ci95[1],
            'family_ci_low': family[0], 'family_ci_high': family[1],
            'raw_p': float((1 + np.sum(np.abs(diff - observed) >= abs(observed))) / (iterations + 1))}


def main():
    out = common.start_run('factorial_ablation')
    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = common.ROOT / 'provenance/historical/p1_pilot_labels'
    m.SEEDS = CONFIG['real_data']['seeds']
    calibration = load_module(common.ROOT / 'provenance/supplement/source_code/05_calibrate_text_predictions.py',
                              'p2c_calibration')
    equivalence = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')

    panel, bags = m.load_bags()
    articles = pd.read_csv(m.P1 / 'article_to_stock_day_pilot.csv')
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    articles['text_hash'] = articles['model_text'].fillna('').map(fingerprint)
    groups = articles.groupby(['Date', 'Symbol'])['text_hash'].agg(set).to_dict()
    bags['text_hashes'] = [groups.get((r.Date, r.Symbol), set()) for r in bags.itertuples()]

    raw, folds = {}, []
    with threadpool_limits(limits=1):
        for purge in PURGES:
            for exclude in EXCLUSIONS:
                began = time.time()
                raw[(purge, exclude)], manifest = train_config(m, panel, bags, purge, exclude)
                folds += manifest
                print(f'purge={purge} exclusion={exclude}: {len(manifest)} folds in {time.time() - began:.0f}s',
                      flush=True)

    # Reproduction gates: two training cells and the calibrator must match archived artifacts.
    fresh = pd.read_csv(common.ROOT / 'results/purged_pilot/predictions.csv')
    p2b = pd.read_csv(common.ROOT / 'provenance/supplement/historical/p2b_tfidf_label_methods/predictions.csv')
    p2c = pd.read_csv(common.ROOT / 'provenance/historical/p2c_forward_calibration/calibrated_predictions.csv')
    gaps = {
        'purge5_excl_vs_fresh_pilot': assert_reproduces('fresh pilot', raw[(5, True)], fresh,
                                                        'prediction', 'prediction'),
        'purge0_noexcl_vs_p2b': assert_reproduces('P2b', raw[(0, False)], p2b, 'prediction', 'prediction'),
    }
    p2b_calibrated, _ = forward_calibrate(calibration, p2b)
    gaps['imported_calibrator_vs_p2c'] = assert_reproduces('P2c calibrator', p2b_calibrated, p2c,
                                                           'calibrated_prediction', 'calibrated_prediction')
    print('Reproduction gates passed:', gaps, flush=True)

    # Eight cells on identical evaluation units (blocks 2-7), one common loss scale.
    cells = []
    for (purge, exclude), frame in raw.items():
        calibrated, warmup = forward_calibrate(calibration, frame)
        evaluated = calibrated.rename(columns={'prediction': 'raw_prediction'})
        for calibrate in CALIBRATIONS:
            cell = evaluated.copy()
            cell['prediction'] = cell['calibrated_prediction'] if calibrate else cell['raw_prediction']
            cell['loss'] = ((cell.actual - cell.prediction) / cell.stock_training_scale) ** 2
            cell['cell'] = cell_name(purge, exclude, calibrate)
            cell['purge'], cell['exact_overlap_exclusion'], cell['calibration'] = purge, exclude, calibrate
            cells.append(cell[['cell', 'purge', 'exact_overlap_exclusion', 'calibration', 'Date', 'Symbol',
                               'block', 'method', 'actual', 'prediction', 'stock_training_scale', 'loss']])
    long = pd.concat(cells, ignore_index=True)
    units = long.groupby('cell').apply(lambda g: frozenset(zip(g.Date, g.Symbol, g.method)))
    if units.nunique() != 1:
        raise ValueError('Cells are not evaluated on identical stock-day units')
    if long.groupby(['Date', 'Symbol']).actual.nunique().max() != 1:
        raise ValueError('Cells disagree on the realized outcome')
    if not np.isfinite(long.loss).all():
        raise ValueError('Non-finite loss')
    long.to_csv(out / 'predictions.csv', index=False)
    pd.DataFrame(folds).to_csv(out / 'fold_manifest.csv', index=False)

    rows = []
    names = list(dict.fromkeys(long.cell))
    for index, name in enumerate(names):
        frame = long[long.cell == name]
        daily = frame.pivot_table(index='Date', columns='method', values='loss', aggfunc='mean').sort_index()
        for block in CONFIG['inference']['block_lengths']:
            group = []
            for k, comparator in enumerate(COMPARATORS):
                rng = np.random.default_rng(CONFIG['inference']['seed'] + 1000 * index + 17 * block + k)
                row = paired(daily[comparator].to_numpy(), daily[RDFL].to_numpy(), rng, block, len(COMPARATORS))
                row.update(cell=name, purge=int(frame.purge.iloc[0]),
                           exact_overlap_exclusion=bool(frame.exact_overlap_exclusion.iloc[0]),
                           calibration=bool(frame.calibration.iloc[0]), competitor=comparator,
                           block_length=block, n_dates=len(daily), n_stock_days=len(frame) // len(METHODS))
                group.append(row)
            for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
                row['holm_p'] = float(p)
                row['decision_2pct_family'] = equivalence.decision(p, row['family_ci_low'], row['family_ci_high'], .02)
                row['equivalence_power_2pct_family'] = equivalence.equivalence_power(
                    .02, row['bootstrap_se'], equivalence.FAMILY_ALPHA)
            rows += group
    result = pd.DataFrame(rows)
    result.to_csv(out / 'cell_inference.csv', index=False)

    # Main effect of each factor on log standard error and on the point estimate, per comparator.
    primary = result[result.block_length == CONFIG['inference']['primary_block_length']]
    effects = []
    for comparator, group in primary.groupby('competitor'):
        for factor in ['purge', 'exact_overlap_exclusion', 'calibration']:
            levels = sorted(group[factor].unique())
            off = group[group[factor] == levels[0]].set_index([f for f in ['purge', 'exact_overlap_exclusion', 'calibration'] if f != factor])
            on = group[group[factor] == levels[1]].set_index(off.index.names)
            on = on.reindex(off.index)
            effects.append({
                'competitor': comparator, 'factor': factor,
                'se_ratio_on_over_off_geometric_mean': float(np.exp(np.mean(np.log(on.bootstrap_se / off.bootstrap_se)))),
                'se_ratio_min': float((on.bootstrap_se / off.bootstrap_se).min()),
                'se_ratio_max': float((on.bootstrap_se / off.bootstrap_se).max()),
                'mean_shift_in_relative_improvement': float((on.relative_improvement - off.relative_improvement).mean()),
                'shift_min': float((on.relative_improvement - off.relative_improvement).min()),
                'shift_max': float((on.relative_improvement - off.relative_improvement).max()),
            })
    effects = pd.DataFrame(effects)
    effects.to_csv(out / 'factor_effects.csv', index=False)

    table = primary.pivot_table(index=['purge', 'exact_overlap_exclusion', 'calibration'], columns='competitor',
                                values=['relative_improvement', 'bootstrap_se'])
    lines = [
        '# Controlled Factorial Ablation',
        '',
        'Status: **EXPLORATORY — RETROSPECTIVE; SAME PROVENANCE GATES AS THE PILOT**',
        '',
        f'Evaluation: blocks 2-7, {primary.n_dates.iloc[0]} dates, {primary.n_stock_days.iloc[0]} stock-days per cell; '
        f'first block {warmup} is the calibration warm-up. One loss scale for all cells.',
        '',
        f'Reproduction gates (max abs prediction gap): {gaps}',
        '',
        '## Cells at block length 20',
        '',
        common.markdown(primary[['cell', 'competitor', 'relative_improvement', 'bootstrap_se', 'family_ci_low',
                                 'family_ci_high', 'holm_p', 'decision_2pct_family']]),
        '',
        '## Factor effects at block length 20',
        '',
        common.markdown(effects),
        '',
    ]
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, cells=len(names), evaluation_dates=int(primary.n_dates.iloc[0]),
                    evaluation_stock_days=int(primary.n_stock_days.iloc[0]), warmup_block=warmup,
                    reproduction_max_abs_gap=gaps, scale='training SD before the 5-session purged boundary')
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
