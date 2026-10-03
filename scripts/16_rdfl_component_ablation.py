"""Which component of RDFL makes it lose? One-factor-at-a-time ablation.

RDFL_SOFT differs from ORDINARY_SOFT in three ways at once: the label rule
(fuzzy memberships versus a softmax of the same response and volume signals),
the selection (only examples with membership confidence >= 0.70), and the
confidence weights. This script holds the fresh-pilot folds, purge, exact-overlap
exclusion, vectorizer, learner (`fit_soft_ensemble` with class-centre mapping),
seeds, and the 2,197 evaluation stock-days fixed, and changes one component at a
time:

- label rule: RDFL or ordinary;
- selection: retained examples, or every example for which the RDFL label is defined;
- weights: RDFL confidence, or uniform;
- abstention (StockNet-style): retained examples whose RDFL hard label is
  LOW_RESPONSE are dropped instead of taught as a class;
- random size-matched selection (Zadrozny 2004): five random subsets of the
  eligible examples with the same size as the retained set, averaged.

Two cells must reproduce archived predictions before anything is reported:
(RDFL, retained, confidence) is RDFL_SOFT and (ordinary, ordinary-eligible,
uniform) is ORDINARY_SOFT of the fresh pilot.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG
PURGE = 5
RANDOM_DRAWS = 5
RDFL_COLUMNS = ['p_negative', 'p_low_response', 'p_positive']
REFERENCE = 'RDFL|retained|confidence'
FACTORIAL = [f'{rule}|{selection}|{weights}' for rule in ('RDFL', 'ORD')
             for selection in ('retained', 'eligible') for weights in ('confidence', 'uniform')]
EXTRA = ['RDFL|retained_without_low|confidence', 'RDFL|random_size_matched|confidence', 'ORD|ordinary_eligible|uniform']
CELLS = FACTORIAL + EXTRA
CONTRASTS = {   # name: (baseline cell, variant cell); positive favours the variant
    'label_rule_ordinary': (REFERENCE, 'ORD|retained|confidence'),
    'selection_all_eligible': (REFERENCE, 'RDFL|eligible|confidence'),
    'weights_uniform': (REFERENCE, 'RDFL|retained|uniform'),
    'abstain_on_low_response': (REFERENCE, 'RDFL|retained_without_low|confidence'),
    'random_selection_same_size': (REFERENCE, 'RDFL|random_size_matched|confidence'),
    'size_given_random_selection': ('RDFL|random_size_matched|confidence', 'RDFL|eligible|confidence'),
}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprint(text):
    normalized = re.sub(r'\s+', ' ', str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def run(m, panel, bags):
    valid = panel[panel.outcome_data_valid.astype(str).str.lower().eq('true')]
    dates = np.sort(valid.Date.unique())
    parts, sizes = [], []
    for fold, (start, stop) in enumerate(zip(m.OUTER_STARTS[:-1], m.OUTER_STARTS[1:])):
        prior = dates[dates < start.to_datetime64()]
        if len(prior) <= PURGE:
            continue
        boundary = pd.Timestamp(prior[-PURGE])
        train = bags[bags.Date < boundary].copy()
        test = bags[(bags.Date >= start) & (bags.Date < stop)].copy()
        if test.empty:
            continue
        test_hashes = set().union(*test.text_hashes)
        overlap = train.text_hashes.map(lambda s: bool(s & test_hashes))
        train = train.loc[~overlap].reset_index(drop=True)
        vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=3, max_df=.98,
                              max_features=20000, sublinear_tf=True, norm='l2', dtype=np.float32)
        x = vec.fit_transform(train.bag_text)
        xt = vec.transform(test.bag_text)
        target = train.target_open_close.to_numpy(float)

        ordinary_mask = np.isfinite(train[['residual_z', 'volume_deviation']].to_numpy(float)).all(axis=1)
        eligible = ordinary_mask & np.isfinite(train[RDFL_COLUMNS].to_numpy(float)).all(axis=1)
        retained = train.retain_for_text_training.to_numpy(bool)
        if not (retained <= eligible).all():
            raise ValueError('Retained examples must have defined RDFL labels')
        without_low = retained & train.weak_label.ne('LOW_RESPONSE').to_numpy()
        q_rdfl = np.full((len(train), 3), np.nan)
        q_rdfl[eligible] = train.loc[eligible, RDFL_COLUMNS].to_numpy(float)
        q_ord = np.full((len(train), 3), np.nan)
        q_ord[ordinary_mask] = m.ordinary_probabilities(train.loc[ordinary_mask])
        confidence = train.label_confidence.to_numpy(float)

        def fit(mask, rule, weighted):
            index = np.flatnonzero(mask)
            q = (q_rdfl if rule == 'RDFL' else q_ord)[index]
            w = confidence[index] if weighted else np.ones(len(index))
            probabilities = m.fit_soft_ensemble(x[index], q, w, xt)
            return probabilities @ m.class_centers(target[index], q, w if weighted else None)

        selections = {'retained': retained, 'eligible': eligible, 'retained_without_low': without_low,
                      'ordinary_eligible': ordinary_mask}
        predictions = {}
        for cell in CELLS:
            rule, selection, weights = cell.split('|')
            if selection == 'random_size_matched':
                draws = []
                pool = np.flatnonzero(eligible)
                for draw in range(RANDOM_DRAWS):
                    rng = np.random.default_rng(CONFIG['inference']['seed'] + 100 * fold + draw)
                    mask = np.zeros(len(train), bool)
                    mask[rng.choice(pool, size=int(retained.sum()), replace=False)] = True
                    draws.append(fit(mask, rule, weights == 'confidence'))
                predictions[cell] = np.mean(draws, axis=0)
                size = int(retained.sum())
            else:
                predictions[cell] = fit(selections[selection], rule, weights == 'confidence')
                size = int(selections[selection].sum())
            sizes.append({'test_start': str(start.date()), 'cell': cell, 'training_examples': size})
        scales = valid[valid.Date < boundary].groupby('Symbol').target_open_close.std(ddof=1).clip(lower=1e-6)
        for cell, pred in predictions.items():
            frame = test[['Date', 'Symbol', 'target_open_close']].rename(columns={'target_open_close': 'actual'}).copy()
            frame['prediction'] = pred
            frame['cell'] = cell
            frame['block'] = str(start.date())
            frame['stock_training_scale'] = frame.Symbol.map(scales)
            parts.append(frame)
        print(f'{start.date()}: train={len(train)}, eligible={int(eligible.sum())}, retained={int(retained.sum())}',
              flush=True)
    return pd.concat(parts, ignore_index=True), pd.DataFrame(sizes)


def paired(a, b, rng, block, family_size):
    """Relative improvement 1 - mean(b)/mean(a), as in 13_factorial_ablation.py."""
    iterations = int(CONFIG['inference']['bootstrap_iterations'])
    diff, rel = common.bootstrap_paired(a, b, iterations, rng, block)
    observed = float(np.mean(a) - np.mean(b))
    ci95 = common.interval(rel)
    family = common.interval(rel, .1 / family_size)
    return {'relative_improvement': observed / float(np.mean(a)),
            'bootstrap_se': float(rel[np.isfinite(rel)].std(ddof=1)),
            'ci95_low': ci95[0], 'ci95_high': ci95[1], 'family_ci_low': family[0], 'family_ci_high': family[1],
            'raw_p': float((1 + np.sum(np.abs(diff - observed) >= abs(observed))) / (iterations + 1))}


def main():
    out = common.start_run('rdfl_component_ablation')
    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = common.ROOT / 'provenance/historical/p1_pilot_labels'
    m.SEEDS = CONFIG['real_data']['seeds']
    equivalence = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')

    panel, bags = m.load_bags()
    articles = pd.read_csv(m.P1 / 'article_to_stock_day_pilot.csv')
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    articles['text_hash'] = articles['model_text'].fillna('').map(fingerprint)
    groups = articles.groupby(['Date', 'Symbol'])['text_hash'].agg(set).to_dict()
    bags['text_hashes'] = [groups.get((r.Date, r.Symbol), set()) for r in bags.itertuples()]

    with threadpool_limits(limits=1):
        predictions, sizes = run(m, panel, bags)

    fresh = pd.read_csv(common.ROOT / 'results/purged_pilot/predictions.csv')
    fresh['Date'] = pd.to_datetime(fresh['Date'])
    gaps = {}
    for cell, method in [(REFERENCE, 'RDFL_SOFT'), ('ORD|ordinary_eligible|uniform', 'ORDINARY_SOFT')]:
        a = predictions[predictions.cell == cell].set_index(['Date', 'Symbol']).prediction.sort_index()
        b = fresh[fresh.method == method].set_index(['Date', 'Symbol']).prediction.sort_index()
        if not a.index.equals(b.index):
            raise ValueError(f'{cell}: evaluation units differ from the fresh pilot')
        gaps[cell] = float(np.max(np.abs(a.to_numpy() - b.to_numpy())))
        if gaps[cell] > 1e-12:
            raise ValueError(f'{cell} does not reproduce {method} (max gap {gaps[cell]:.3g})')
    print('Reproduction gates passed:', gaps, flush=True)

    predictions['loss'] = ((predictions.actual - predictions.prediction) / predictions.stock_training_scale) ** 2
    zero = predictions[predictions.cell == REFERENCE].assign(cell='ZERO', prediction=0.0)
    zero['loss'] = (zero.actual / zero.stock_training_scale) ** 2
    frame = pd.concat([predictions, zero], ignore_index=True)
    predictions.to_csv(out / 'predictions.csv', index=False)
    sizes.to_csv(out / 'training_sizes.csv', index=False)
    daily = frame.pivot_table(index='Date', columns='cell', values='loss', aggfunc='mean').sort_index()

    rows, contrasts = [], []
    for block in CONFIG['inference']['block_lengths']:
        group = []
        for k, cell in enumerate(CELLS):
            rng = np.random.default_rng(CONFIG['inference']['seed'] + 60000 + 17 * block + k)
            row = paired(daily['ZERO'].to_numpy(), daily[cell].to_numpy(), rng, block, len(CELLS))
            row.update(cell=cell, comparison='cell_vs_ZERO', block_length=block, n_dates=len(daily))
            group.append(row)
        for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
            row['holm_p'] = float(p)
            row['decision_2pct_family'] = equivalence.decision(p, row['family_ci_low'], row['family_ci_high'], .02)
        rows += group
        group = []
        for k, (name, (base, variant)) in enumerate(CONTRASTS.items()):
            rng = np.random.default_rng(CONFIG['inference']['seed'] + 70000 + 17 * block + k)
            row = paired(daily[base].to_numpy(), daily[variant].to_numpy(), rng, block, len(CONTRASTS))
            row.update(contrast=name, baseline=base, variant=variant, block_length=block, n_dates=len(daily))
            group.append(row)
        for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
            row['holm_p'] = float(p)
        contrasts += group
    cells = pd.DataFrame(rows)
    contrasts = pd.DataFrame(contrasts)
    cells.to_csv(out / 'cells_vs_zero.csv', index=False)
    contrasts.to_csv(out / 'contrasts.csv', index=False)

    primary = cells[cells.block_length == CONFIG['inference']['primary_block_length']].set_index('cell')
    effects = []
    for position, factor in enumerate(['rule', 'selection', 'weights']):
        levels = {'rule': ('RDFL', 'ORD'), 'selection': ('retained', 'eligible'), 'weights': ('confidence', 'uniform')}
        shifts = []
        for cell in FACTORIAL:
            parts = cell.split('|')
            if parts[position] != levels[factor][0]:
                continue
            other = parts.copy()
            other[position] = levels[factor][1]
            shifts.append(primary.loc['|'.join(other), 'relative_improvement'] - primary.loc[cell, 'relative_improvement'])
        effects.append({'factor': factor, 'from': levels[factor][0], 'to': levels[factor][1],
                        'mean_shift_in_improvement_vs_zero': float(np.mean(shifts)),
                        'shift_min': float(np.min(shifts)), 'shift_max': float(np.max(shifts))})
    effects = pd.DataFrame(effects)
    effects.to_csv(out / 'factor_effects.csv', index=False)

    primary_contrasts = contrasts[contrasts.block_length == CONFIG['inference']['primary_block_length']]
    lines = [
        '# RDFL Component Ablation',
        '',
        'Status: **EXPLORATORY — RETROSPECTIVE; SAME PROVENANCE GATES AS THE PILOT**',
        '',
        f'Fresh-pilot folds, {primary.n_dates.iloc[0]} dates. Reproduction gaps: {gaps}',
        '',
        '## Cells versus ZERO (block length 20; positive favours the cell)',
        '',
        common.markdown(primary.reset_index()[['cell', 'relative_improvement', 'bootstrap_se', 'family_ci_low',
                                                'family_ci_high', 'holm_p', 'decision_2pct_family']]),
        '',
        '## One-factor contrasts from RDFL_SOFT (positive favours the variant)',
        '',
        common.markdown(primary_contrasts[['contrast', 'relative_improvement', 'ci95_low', 'ci95_high',
                                           'family_ci_low', 'family_ci_high', 'holm_p']]),
        '',
        '## Factorial main effects on improvement versus ZERO',
        '',
        common.markdown(effects),
        '',
    ]
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, cells=len(CELLS), contrasts=len(CONTRASTS), random_draws=RANDOM_DRAWS,
                    reproduction_max_abs_gap=gaps, evaluation_dates=int(primary.n_dates.iloc[0]))
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
