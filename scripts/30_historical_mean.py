"""Historical-mean baselines (revision analysis, research/PREREGISTRATION_DEVIATIONS.md entry 7).

Two questions from the 2026-10-05 review, answered from saved predictions and the training history
that the pilot and the replication already used:

1. Uncalibrated pipelines. For each test block, an expanding historical mean of the target uses only
   valid stock-days before the block's purge boundary, the same rows from which the stock's training
   scale of (5) is computed. HIST_MEAN_STOCK is the mean per stock; HIST_MEAN_POOLED pools the eight
   stocks. Both are compared with ZERO and with the RDFL soft learner on the evaluated stock-days.
2. Calibrated pipelines. An intercept-only calibrator fitted on the same calibration history as the
   archived forward calibrator (all completed earlier out-of-sample blocks) forecasts the mean
   realized return of that history. Calibrated RDFL is compared with it on the same stock-days.

Inference follows the primary analysis: date-level losses on the scale of (5), dates weighted
equally, paired circular moving-block bootstrap (block 20, 10,000 draws), 95% and family-adjusted
intervals with the family size stated in the output, Holm adjustment within each family, and the
±2% decision rule of 12_equivalence_power.py. The analysis is descriptive and was run after every
locked result was known.
"""
import importlib.util

import numpy as np
import pandas as pd

import common

CONFIG = common.CONFIG
BLOCK = int(CONFIG['inference']['primary_block_length'])
SEED = int(CONFIG['inference']['seed']) + 3000
PURGE = int(CONFIG['real_data']['purge_observed_sessions'])
RESULTS = common.ROOT / 'results'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ABLATION = load_module(common.ROOT / 'scripts/13_factorial_ablation.py', 'ablation')
EQUIVALENCE = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')


def history_means(panel, predictions):
    """Per-stock and pooled target means before each block's purge boundary; checks the scales."""
    valid = panel[panel.outcome_data_valid].copy()
    dates = np.sort(valid.Date.unique())
    rows = []
    for block, test in predictions.groupby('block'):
        start = pd.Timestamp(block)
        boundary = pd.Timestamp(dates[dates < start.to_datetime64()][-PURGE])
        history = valid[valid.Date < boundary]
        scale = history.groupby('Symbol').target_open_close.std(ddof=1).clip(lower=1e-6)
        check = test.drop_duplicates('Symbol').set_index('Symbol').stock_training_scale
        gap = float(np.max(np.abs(scale.reindex(check.index).to_numpy() - check.to_numpy())))
        if gap > 1e-12:
            raise ValueError(f'{block}: training history does not reproduce the saved scales ({gap})')
        stock_mean = history.groupby('Symbol').target_open_close.mean()
        for symbol in test.Symbol.unique():
            rows.append({'block': block, 'Symbol': symbol, 'boundary': str(boundary.date()),
                         'history_stock_days': int((history.Symbol == symbol).sum()),
                         'stock_mean': float(stock_mean[symbol]),
                         'pooled_mean': float(history.target_open_close.mean())})
    return pd.DataFrame(rows)


def add_baselines(predictions, means):
    base = predictions[predictions.method == 'ZERO'].drop(columns=['method', 'prediction']).merge(
        means[['block', 'Symbol', 'stock_mean', 'pooled_mean']], on=['block', 'Symbol'], validate='many_to_one')
    extra = []
    for name, column in [('HIST_MEAN_STOCK', 'stock_mean'), ('HIST_MEAN_POOLED', 'pooled_mean')]:
        frame = base.copy()
        frame['prediction'] = frame[column]
        frame['method'] = name
        extra.append(frame.drop(columns=['stock_mean', 'pooled_mean']))
    keep = ['Date', 'Symbol', 'actual', 'prediction', 'method', 'block', 'stock_training_scale']
    return pd.concat([predictions[keep]] + [e[keep] for e in extra], ignore_index=True)


def daily(frame, value='prediction', key='method'):
    frame = frame.copy()
    frame['loss'] = ((frame.actual - frame[value]) / frame.stock_training_scale) ** 2
    table = frame.pivot_table(index='Date', columns=key, values='loss', aggfunc='mean').sort_index()
    if table.isna().any().any():
        raise ValueError('methods are not evaluated on identical dates')
    return table


def family(losses, pairs, label, offset):
    """pairs: (baseline, variant); relative improvement of the variant over the baseline."""
    rows = []
    for k, (base, variant) in enumerate(pairs):
        rng = np.random.default_rng(SEED + offset + k)
        row = ABLATION.paired(losses[base].to_numpy(), losses[variant].to_numpy(), rng, BLOCK, len(pairs))
        row.update(analysis=label, baseline=base, variant=variant, family_size=len(pairs),
                   n_dates=len(losses), block_length=BLOCK)
        rows.append(row)
    for row, p in zip(rows, common.holm([r['raw_p'] for r in rows])):
        row['holm_p'] = float(p)
        row['decision_2pct_family'] = EQUIVALENCE.decision(p, row['family_ci_low'], row['family_ci_high'], .02)
    return rows


def intercept_only(raw, calibrated, value='calibrated_prediction'):
    """Intercept-only forecasts from the calibration history of each block; calibrated RDFL alongside."""
    raw = raw.copy()
    raw['Date'] = pd.to_datetime(raw.Date)
    cal = calibrated.copy()
    cal['Date'] = pd.to_datetime(cal.Date)
    rdfl = cal[cal.method == 'RDFL_SOFT']
    parts = []
    for block, current in rdfl.groupby('block'):
        start = current.Date.min()
        history = raw[(raw.Date < start) & (raw.method == 'RDFL_SOFT')]
        frame = current[['Date', 'Symbol', 'actual', 'block', 'stock_training_scale']].copy()
        for name, forecast in [('ZERO', 0.0), ('INTERCEPT_ONLY', float(history.actual.mean()))]:
            parts.append(frame.assign(method=name, prediction=forecast, history_stock_days=len(history)))
        parts.append(frame.assign(method='RDFL_SOFT_CALIBRATED', prediction=current[value].to_numpy(),
                                  history_stock_days=len(history)))
    return pd.concat(parts, ignore_index=True)


def main():
    out = common.start_run('historical_mean')
    m = common.load_legacy('04_run_tfidf_label_methods.py')
    rows, means_all, sizes = [], [], {}

    datasets = {
        'thai_pilot': (common.ROOT / 'provenance/historical/p1_pilot_labels', RESULTS / 'purged_pilot/predictions.csv'),
        'fnspid_pilot': (RESULTS / 'fnspid_prepared/p1_labels', RESULTS / 'fnspid_replication/predictions.csv'),
    }
    for k, (label, (labels_dir, path)) in enumerate(datasets.items()):
        m.P1 = labels_dir
        panel, _ = m.load_bags()
        predictions = pd.read_csv(path)
        predictions['Date'] = pd.to_datetime(predictions.Date)
        means = history_means(panel, predictions)
        means.insert(0, 'dataset', label)
        means_all.append(means)
        losses = daily(add_baselines(predictions, means))
        pairs = [('ZERO', 'HIST_MEAN_STOCK'), ('ZERO', 'HIST_MEAN_POOLED'),
                 ('HIST_MEAN_STOCK', 'RDFL_SOFT'), ('HIST_MEAN_POOLED', 'RDFL_SOFT')]
        rows += family(losses, pairs, f'{label}_uncalibrated', 100 * k)
        sizes[label] = {'dates': len(losses), 'stock_days': int((predictions.method == 'ZERO').sum())}

    thai_factorial = pd.read_csv(RESULTS / 'factorial_ablation/predictions.csv')
    fresh = thai_factorial[(thai_factorial.purge > 0) & thai_factorial.exact_overlap_exclusion.astype(bool)]
    # The saved factorial cells start after the warm-up block; this cell reproduces the fresh pilot exactly
    # (13_factorial_ablation.py gate), so the pilot's predictions supply the calibration history.
    thai_raw = pd.read_csv(RESULTS / 'purged_pilot/predictions.csv')
    thai_cal = fresh[fresh.calibration.astype(bool)].rename(columns={'prediction': 'calibrated_prediction'})
    us_raw = pd.read_csv(RESULTS / 'fnspid_replication/predictions.csv')
    us_cal = pd.read_csv(RESULTS / 'fnspid_replication/calibrated_predictions.csv')
    intercepts = []
    for k, (label, raw, cal) in enumerate([('thai_calibrated', thai_raw, thai_cal), ('fnspid_calibrated', us_raw, us_cal)]):
        frame = intercept_only(raw, cal)
        intercepts.append(frame.groupby(['block', 'method']).agg(prediction=('prediction', 'mean'),
                                                                history_stock_days=('history_stock_days', 'first'))
                          .reset_index().assign(dataset=label))
        losses = daily(frame)
        pairs = [('ZERO', 'INTERCEPT_ONLY'), ('INTERCEPT_ONLY', 'RDFL_SOFT_CALIBRATED')]
        rows += family(losses, pairs, label, 500 + 100 * k)
        sizes[label] = {'dates': len(losses), 'stock_days': int(len(frame) / 3)}

    result = pd.DataFrame(rows)
    result.to_csv(out / 'comparisons.csv', index=False)
    pd.concat(means_all, ignore_index=True).to_csv(out / 'history_means.csv', index=False)
    pd.concat(intercepts, ignore_index=True).to_csv(out / 'intercept_only_by_block.csv', index=False)
    common.dump(out / 'summary.json', sizes)
    shown = result[['analysis', 'baseline', 'variant', 'relative_improvement', 'family_ci_low', 'family_ci_high',
                    'holm_p', 'decision_2pct_family']]
    lines = ['# Historical-Mean Baselines', '',
             'Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**', '',
             'Relative improvement of the variant over the baseline, 1 - L_variant / L_baseline, on the scale of (5); '
             f'paired circular moving-block bootstrap, block {BLOCK}; family-adjusted intervals at 1 - 0.10/family size.',
             '', common.markdown(shown), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, block_length=BLOCK, seed=SEED, comparisons=len(result), datasets=sizes)
    print('\n'.join(lines).encode('ascii', 'replace').decode(), flush=True)


if __name__ == '__main__':
    main()
