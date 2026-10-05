"""Decomposition of each method's loss relative to the zero forecast (revision analysis).

On the evaluation scale of (5), with losses averaged within dates and dates weighted equally,

    L_m - L_ZERO = E[yhat^2] - 2 E[y yhat],

where y and yhat are divided by the stock's training scale. Dividing by L_ZERO splits the relative
improvement over the zero forecast, 1 - L_m / L_ZERO, into a signal term 2 E[y yhat] / L_ZERO and a
variance term E[yhat^2] / L_ZERO: improvement = signal - variance. The identity is checked for every
row. Intervals resample dates with the circular moving-block bootstrap of the primary inference
(block length 20, 10,000 draws); every row of a dataset uses the same resampled dates, so no
result depends on the order in which methods are processed.

Run after all locked and published results were known, in response to reviewers; it reads saved
predictions only and is descriptive (research/PREREGISTRATION_DEVIATIONS.md, entry 6).
"""
import numpy as np
import pandas as pd

import common

CONFIG = common.CONFIG
BLOCK = int(CONFIG['inference']['primary_block_length'])
ITERATIONS = int(CONFIG['inference']['bootstrap_iterations'])
SEED = int(CONFIG['inference']['seed']) + 2600


def block_indices(n, rng):
    """Circular moving-block resamples of n dates, as in common.bootstrap_paired."""
    starts = rng.integers(0, n, size=(ITERATIONS, int(np.ceil(n / BLOCK))))
    return ((starts[..., None] + np.arange(BLOCK)) % n).reshape(ITERATIONS, -1)[:, :n]


def daily_terms(frame, value):
    """Date-level means of the loss, the zero-forecast loss, yhat^2, and y yhat on the scale of (5)."""
    y = frame.actual / frame.stock_training_scale
    yhat = frame[value] / frame.stock_training_scale
    terms = pd.DataFrame({'Date': frame.Date, 'loss': (y - yhat) ** 2, 'zero_loss': y ** 2,
                          'variance': yhat ** 2, 'covariance': y * yhat, 'y': y, 'yhat': yhat})
    return terms.groupby('Date').mean().sort_index()


def decompose(frame, key, value, label):
    keys = frame[key].drop_duplicates().tolist()
    daily = {k: daily_terms(frame[frame[key] == k], value) for k in keys}
    dates = daily[keys[0]].index
    for k in keys:
        if not daily[k].index.equals(dates):
            raise ValueError(f'{label}: {k} is not evaluated on the same dates')
    index = block_indices(len(dates), np.random.default_rng(SEED))
    rows = []
    for k in keys:
        d = daily[k]
        loss, zero, variance, covariance = (float(d[c].mean()) for c in ['loss', 'zero_loss', 'variance', 'covariance'])
        gap = (loss - zero) - (variance - 2 * covariance)
        if abs(gap) > 1e-10:
            raise ValueError(f'{label}: identity fails for {k} by {gap}')
        z, v, c = (d[col].to_numpy()[index].mean(axis=1) for col in ['zero_loss', 'variance', 'covariance'])
        signal_boot, variance_boot = 2 * c / z, v / z
        stock_days = frame[frame[key] == k]
        rows.append({
            'dataset': label, key: k, 'dates': len(d), 'stock_days': len(stock_days),
            'mean_loss': loss, 'zero_loss': zero, 'identity_gap': gap,
            'relative_improvement_vs_zero': 1 - loss / zero,
            'signal_term': 2 * covariance / zero,
            'signal_term_ci95_low': common.interval(signal_boot)[0],
            'signal_term_ci95_high': common.interval(signal_boot)[1],
            'variance_term': variance / zero,
            'variance_term_ci95_low': common.interval(variance_boot)[0],
            'variance_term_ci95_high': common.interval(variance_boot)[1],
            'signal_to_variance': (2 * covariance) / variance if variance > 0 else np.nan,
            'mean_scaled_prediction': float(d['yhat'].mean()),
            'mean_scaled_outcome': float(d['y'].mean()),
            'prediction_outcome_correlation': (float(np.corrcoef(stock_days.actual / stock_days.stock_training_scale,
                                                                 stock_days[value] / stock_days.stock_training_scale)[0, 1])
                                               if stock_days[value].std() > 0 else np.nan),
            'prediction_sd': float(stock_days[value].std(ddof=1)),
        })
    return pd.DataFrame(rows)


def main():
    out = common.start_run('loss_decomposition')
    results = common.ROOT / 'results'
    tables = {}

    pilot = pd.read_csv(results / 'purged_pilot/predictions.csv')
    tables['thai_pilot'] = decompose(pilot, 'method', 'prediction', 'thai_pilot')
    components = pd.read_csv(results / 'rdfl_component_ablation/predictions.csv')
    tables['thai_components'] = decompose(components, 'cell', 'prediction', 'thai_components')
    factorial = pd.read_csv(results / 'factorial_ablation/predictions.csv')
    factorial = factorial[(factorial.purge > 0) & factorial.exact_overlap_exclusion.astype(bool)].copy()
    factorial['method_calibration'] = factorial.method + np.where(factorial.calibration.astype(bool),
                                                                 ' calibrated', ' uncalibrated')
    tables['thai_calibration'] = decompose(factorial, 'method_calibration', 'prediction', 'thai_calibration')

    external = pd.read_csv(results / 'fnspid_replication/predictions.csv')
    tables['fnspid_pilot'] = decompose(external, 'method', 'prediction', 'fnspid_pilot')
    calibrated = pd.read_csv(results / 'fnspid_replication/calibrated_predictions.csv')
    tables['fnspid_calibrated'] = decompose(calibrated, 'method', 'calibrated_prediction', 'fnspid_calibrated')
    external_components = pd.read_csv(results / 'fnspid_replication/component_predictions.csv')
    tables['fnspid_components'] = decompose(external_components, 'cell', 'prediction', 'fnspid_components')

    summary = {}
    lines = ['# Loss Decomposition Relative to the Zero Forecast', '',
             'Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**', '',
             'relative improvement vs zero = signal term - variance term, with signal = 2E[y yhat]/E[y^2] and '
             'variance = E[yhat^2]/E[y^2] on the scale of (5), dates weighted equally. Intervals: circular '
             f'moving-block bootstrap of dates, block {BLOCK}, {ITERATIONS} draws.', '']
    for name, table in tables.items():
        table.to_csv(out / f'{name}.csv', index=False)
        key = table.columns[1]
        summary[name] = {'rows': len(table), 'dates': int(table.dates.iloc[0]),
                         'stock_days': int(table.stock_days.iloc[0]),
                         'max_identity_gap': float(table.identity_gap.abs().max())}
        shown = table[[key, 'relative_improvement_vs_zero', 'signal_term', 'signal_term_ci95_low',
                       'signal_term_ci95_high', 'variance_term', 'prediction_outcome_correlation']]
        lines += [f'## {name}', '', common.markdown(shown), '']
    common.dump(out / 'summary.json', summary)
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, block_length=BLOCK, iterations=ITERATIONS, seed=SEED,
                    datasets={k: v['rows'] for k, v in summary.items()})
    print('\n'.join(lines).encode('ascii', 'replace').decode(), flush=True)


if __name__ == '__main__':
    main()
