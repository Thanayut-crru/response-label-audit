"""Does the RDFL result depend on two fixed settings of its label rule?

The label rule (called RDFL in the code) keeps a stock-day for training only when its largest
fuzzy membership is at least 0.70, and it places the response band between the 30th and 70th
percentiles of past |z|. Both values were fixed when the procedure was designed and never varied.
This run varies them on the Thai pilot and on the FNSPID replication data, with everything else of
RDFL_SOFT held fixed (folds, purge, exact-overlap exclusion, vectorizer, learner, seeds, weights):

- retention threshold: none (every eligible example), 0.50, 0.60, 0.70, 0.80, 0.90;
- response band: 20th-80th and 40th-60th percentiles, at threshold 0.70.

Status: EXPLORATORY AND POST HOC. It was run after every locked result was known and is outside
the locked FNSPID protocol. It changes no locked file or earlier result, every setting in the grid
is reported, and none is selected. Labels are recomputed in memory by the legacy builder's own
function (01_build_pilot_labels.add_fuzzy_labels) with only the band percentiles substituted. Two
gates must pass before anything is reported: the original band reproduces the stored labels, and
the original setting reproduces the published RDFL_SOFT predictions.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG
PURGE = 5
TOLERANCE = 1e-12
BUILDER = common.ROOT / 'provenance/source_code/01_build_pilot_labels.py'
BAND_LITERAL = 'np.quantile(past_abs_z, [0.30, 0.70])'
ORIGINAL_BAND = (0.30, 0.70)
RDFL_COLUMNS = ['p_negative', 'p_low_response', 'p_positive']
NUMERIC_LABELS = RDFL_COLUMNS + ['label_confidence']
LABEL_COLUMNS = NUMERIC_LABELS + ['weak_label', 'retain_for_text_training']
CELLS = {   # cell: (response band percentiles, retention threshold; None keeps every eligible example)
    'threshold_none': (ORIGINAL_BAND, None),
    'threshold_0.50': (ORIGINAL_BAND, 0.50),
    'threshold_0.60': (ORIGINAL_BAND, 0.60),
    'threshold_0.70': (ORIGINAL_BAND, 0.70),
    'threshold_0.80': (ORIGINAL_BAND, 0.80),
    'threshold_0.90': (ORIGINAL_BAND, 0.90),
    'band_0.20_0.80': ((0.20, 0.80), 0.70),
    'band_0.40_0.60': ((0.40, 0.60), 0.70),
}
REFERENCE = 'threshold_0.70'
DATASETS = {
    'thai': {'labels': common.ROOT / 'provenance/historical/p1_pilot_labels',
             'published': common.ROOT / 'results/purged_pilot/predictions.csv'},
    'fnspid': {'labels': common.ROOT / 'results/fnspid_prepared/p1_labels',
               'published': common.ROOT / 'results/fnspid_replication/predictions.csv'},
}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprint(text):
    normalized = re.sub(r'\s+', ' ', str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def setup(name):
    """The same data, folds, and text hashes as 16 (Thai) and 21 (FNSPID)."""
    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = DATASETS[name]['labels']
    m.SEEDS = CONFIG['real_data']['seeds']
    if name == 'fnspid':
        replication = load_module(common.ROOT / 'scripts/21_fnspid_replication.py', 'replication')
        prepared = json.loads((common.ROOT / 'results/fnspid_prepared/COMPLETE.json').read_text(encoding='utf-8'))
        descriptives = json.loads((common.ROOT / 'results/fnspid_replication/descriptives.json')
                                  .read_text(encoding='utf-8'))
        starts = replication.block_starts(prepared['window_start'], prepared['window_end'])
        m.OUTER_STARTS = starts[descriptives['blocks_dropped_by_rule']:]
    panel, bags = m.load_bags()
    articles = pd.read_csv(m.P1 / 'article_to_stock_day_pilot.csv', low_memory=False)
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    articles['text_hash'] = articles['model_text'].fillna('').map(fingerprint)
    groups = articles.groupby(['Date', 'Symbol'])['text_hash'].agg(set).to_dict()
    bags['text_hashes'] = [groups.get((r.Date, r.Symbol), set()) for r in bags.itertuples()]
    return m, panel, bags


def labeler(band):
    """The legacy add_fuzzy_labels with only its band percentiles substituted; the file is not changed."""
    source = BUILDER.read_text(encoding='utf-8')
    if source.count(BAND_LITERAL) != 1:
        raise ValueError('Band percentiles not found exactly once in the label builder')
    source = source.replace(BAND_LITERAL, f'np.quantile(past_abs_z, [{band[0]!r}, {band[1]!r}])')
    namespace = {'__name__': f'builder_{band[0]}_{band[1]}', '__file__': str(BUILDER)}
    exec(compile(source, str(BUILDER), 'exec'), namespace)
    return namespace['add_fuzzy_labels']


def relabel(panel, band):
    add = labeler(band)
    frame = panel.copy()
    frame['has_news'] = frame['has_news'].astype(str).str.lower().eq('true')
    parts = []
    for symbol, group in frame.groupby('Symbol', sort=False):
        part = add(group)
        part['Symbol'] = symbol
        parts.append(part)
    return pd.concat(parts, ignore_index=True)[['Date', 'Symbol'] + LABEL_COLUMNS]


def label_gap(panel, labels):
    """Gate: the original band must reproduce the stored labels."""
    merged = panel[['Date', 'Symbol'] + LABEL_COLUMNS].merge(
        labels, on=['Date', 'Symbol'], how='outer', validate='one_to_one', suffixes=('_stored', '_new'),
        indicator=True)
    if not merged['_merge'].eq('both').all():
        raise ValueError('Relabeled panel does not match the stored panel')
    gap = 0.0
    for column in NUMERIC_LABELS:
        a, b = merged[f'{column}_stored'].to_numpy(float), merged[f'{column}_new'].to_numpy(float)
        if not np.array_equal(np.isnan(a), np.isnan(b)):
            raise ValueError(f'{column}: defined cases differ from the stored labels')
        finite = np.isfinite(a)
        gap = max(gap, float(np.max(np.abs(a[finite] - b[finite]), initial=0.0)))
    same_labels = merged['weak_label_stored'].astype(str).eq(merged['weak_label_new'].astype(str)).all()
    same_retained = (merged['retain_for_text_training_stored'].astype(bool)
                     == merged['retain_for_text_training_new'].astype(bool)).all()
    if gap > TOLERANCE or not same_labels or not same_retained:
        raise ValueError(f'Original band does not reproduce the stored labels (gap {gap:.3g})')
    return gap


def with_labels(bags, labels):
    merged = bags[['Date', 'Symbol']].merge(labels, on=['Date', 'Symbol'], how='left', validate='one_to_one')
    variant = bags.copy()
    for column in LABEL_COLUMNS:
        variant[column] = merged[column].to_numpy()
    return variant


def run(m, panel, bags, variants):
    """The fold loop of 16_rdfl_component_ablation.run with the selection varied."""
    valid = panel[panel.outcome_data_valid.astype(str).str.lower().eq('true')]
    dates = np.sort(valid.Date.unique())
    parts, sizes = [], []
    for start, stop in zip(m.OUTER_STARTS[:-1], m.OUTER_STARTS[1:]):
        prior = dates[dates < start.to_datetime64()]
        if len(prior) <= PURGE:
            continue
        boundary = pd.Timestamp(prior[-PURGE])
        in_test = ((bags.Date >= start) & (bags.Date < stop)).to_numpy()
        if not in_test.any():
            continue
        test = bags[in_test]
        test_hashes = set().union(*test.text_hashes)
        rows = np.flatnonzero((bags.Date < boundary).to_numpy())
        overlap = bags.text_hashes.iloc[rows].map(lambda s: bool(s & test_hashes)).to_numpy(bool)
        rows = rows[~overlap]
        train = bags.iloc[rows].reset_index(drop=True)
        vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=3, max_df=.98,
                              max_features=20000, sublinear_tf=True, norm='l2', dtype=np.float32)
        x = vec.fit_transform(train.bag_text)
        xt = vec.transform(test.bag_text)
        target = train.target_open_close.to_numpy(float)
        ordinary_mask = np.isfinite(train[['residual_z', 'volume_deviation']].to_numpy(float)).all(axis=1)
        scales = valid[valid.Date < boundary].groupby('Symbol').target_open_close.std(ddof=1).clip(lower=1e-6)
        for cell, (band, threshold) in CELLS.items():
            labels = variants[band].iloc[rows].reset_index(drop=True)
            probabilities_all = labels[RDFL_COLUMNS].to_numpy(float)
            eligible = ordinary_mask & np.isfinite(probabilities_all).all(axis=1)
            confidence = labels.label_confidence.to_numpy(float)
            mask = eligible.copy() if threshold is None else eligible & (confidence >= threshold)
            if cell == REFERENCE and not np.array_equal(mask, labels.retain_for_text_training.to_numpy(bool)):
                raise ValueError(f'{start.date()}: threshold 0.70 does not reproduce the retained set')
            index = np.flatnonzero(mask)
            q, w = probabilities_all[index], confidence[index]
            probabilities = m.fit_soft_ensemble(x[index], q, w, xt)
            prediction = probabilities @ m.class_centers(target[index], q, w)
            frame = test[['Date', 'Symbol', 'target_open_close']].rename(columns={'target_open_close': 'actual'})
            frame = frame.assign(prediction=prediction, cell=cell, block=str(start.date()),
                                 stock_training_scale=frame.Symbol.map(scales))
            parts.append(frame)
            hard = labels.weak_label.to_numpy(str)[index] if threshold is not None else np.array([])
            sizes.append({'test_start': str(start.date()), 'cell': cell, 'training_examples': int(len(index)),
                          'mean_low_response_probability': float(q[:, 1].mean()) if len(index) else np.nan,
                          'hard_low_response_share': float(np.mean(hard == 'LOW_RESPONSE')) if len(hard) else np.nan})
        print(f'{start.date()}: train={len(train)}, retained at 0.70={int(train.retain_for_text_training.sum())}',
              flush=True)
    return pd.concat(parts, ignore_index=True), pd.DataFrame(sizes)


def prediction_gap(predictions, published_path):
    """Gate: the original setting must reproduce the published RDFL_SOFT predictions."""
    published = pd.read_csv(published_path)
    published['Date'] = pd.to_datetime(published['Date'])
    b = published[published.method == 'RDFL_SOFT'].set_index(['Date', 'Symbol']).prediction.sort_index()
    a = predictions[predictions.cell == REFERENCE].set_index(['Date', 'Symbol']).prediction.sort_index()
    if not a.index.equals(b.index):
        raise ValueError('Evaluation units differ from the published run')
    gap = float(np.max(np.abs(a.to_numpy() - b.to_numpy())))
    if gap > TOLERANCE:
        raise ValueError(f'Original setting does not reproduce RDFL_SOFT (max gap {gap:.3g})')
    return gap


def main():
    out = common.start_run('threshold_sensitivity')
    equivalence = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')
    components = load_module(common.ROOT / 'scripts/16_rdfl_component_ablation.py', 'components')
    bands = sorted({band for band, _ in CELLS.values()})
    predictions_all, sizes_all, rows, dispersion, gates = [], [], [], [], {}
    for d, name in enumerate(DATASETS):
        m, panel, bags = setup(name)
        variants = {}
        for band in bands:
            labels = relabel(panel, band)
            if band == ORIGINAL_BAND:
                gates[f'{name}_labels_max_gap'] = label_gap(panel, labels)
            variants[band] = with_labels(bags, labels)
        with threadpool_limits(limits=1):
            predictions, sizes = run(m, panel, bags, variants)
        gates[f'{name}_rdfl_soft_max_gap'] = prediction_gap(predictions, DATASETS[name]['published'])
        print(f'{name}: reproduction gates passed {gates}', flush=True)

        predictions['loss'] = ((predictions.actual - predictions.prediction) / predictions.stock_training_scale) ** 2
        zero = predictions[predictions.cell == REFERENCE].assign(cell='ZERO', prediction=0.0)
        zero['loss'] = (zero.actual / zero.stock_training_scale) ** 2
        daily = pd.concat([predictions, zero]).pivot_table(index='Date', columns='cell', values='loss',
                                                            aggfunc='mean').sort_index()
        for block in CONFIG['inference']['block_lengths']:
            group = []
            for k, (cell, (band, threshold)) in enumerate(CELLS.items()):
                rng = np.random.default_rng(CONFIG['inference']['seed'] + 90000 + 1000 * d + 17 * block + k)
                row = components.paired(daily['ZERO'].to_numpy(), daily[cell].to_numpy(), rng, block, len(CELLS))
                row.update(dataset=name, cell=cell, band=f'{band[0]:.2f}-{band[1]:.2f}',
                           threshold='none' if threshold is None else f'{threshold:.2f}',
                           block_length=block, n_dates=len(daily))
                group.append(row)
            for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
                row['holm_p'] = float(p)
                row['decision_2pct_family'] = equivalence.decision(p, row['family_ci_low'], row['family_ci_high'], .02)
            rows += group
        outcome_sd = float(predictions[predictions.cell == REFERENCE].actual.std(ddof=1))
        for cell, group in predictions.groupby('cell', sort=False):
            dispersion.append({'dataset': name, 'cell': cell, 'prediction_sd': float(group.prediction.std(ddof=1)),
                               'outcome_sd': outcome_sd})
        predictions_all.append(predictions.assign(dataset=name))
        sizes_all.append(sizes.assign(dataset=name))

    cells = pd.DataFrame(rows)
    dispersion = pd.DataFrame(dispersion)
    sizes = pd.concat(sizes_all, ignore_index=True)
    pd.concat(predictions_all, ignore_index=True).to_csv(out / 'predictions.csv', index=False)
    cells.to_csv(out / 'cells_vs_zero.csv', index=False)
    dispersion.to_csv(out / 'prediction_dispersion.csv', index=False)
    sizes.to_csv(out / 'training_sizes.csv', index=False)

    primary = cells[cells.block_length == CONFIG['inference']['primary_block_length']]
    mean_sizes = sizes.groupby(['dataset', 'cell']).training_examples.mean().rename('mean_training_examples')
    table = (primary.merge(mean_sizes.reset_index(), on=['dataset', 'cell'])
             .merge(dispersion, on=['dataset', 'cell']))
    stable = {name: bool(group.decision_2pct_family.eq('RDFL_WORSE_BEYOND_MARGIN').all())
              for name, group in cells.groupby('dataset')}
    lines = ['# Sensitivity of RDFL (RDFL in the code) to its fixed settings', '',
             'Status: **EXPLORATORY AND POST HOC — outside the locked FNSPID protocol; no setting is selected**', '',
             f'Reproduction gates: {gates}', '',
             f'Every cell worse than ZERO beyond the ±2% margin at all block lengths: {stable}', '',
             '## Cells versus ZERO (block length 20; positive favours the cell)', '',
             common.markdown(table[['dataset', 'cell', 'band', 'threshold', 'relative_improvement', 'family_ci_low',
                                    'family_ci_high', 'holm_p', 'decision_2pct_family', 'mean_training_examples',
                                    'prediction_sd', 'outcome_sd']]), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, status='EXPLORATORY_POST_HOC', cells=len(CELLS), datasets=list(DATASETS),
                    reproduction_gates=gates, all_cells_worse_beyond_margin=stable)
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
