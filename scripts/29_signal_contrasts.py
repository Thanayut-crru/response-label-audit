"""Paired signal contrasts and calibration coefficients (revision analysis, research/PREREGISTRATION_DEVIATIONS.md entry 7).

Two follow-ups to 26_loss_decomposition.py requested in the 2026-10-05 review.

1. Signal contrasts. With improvement over the zero forecast = 2E[y yhat]/E[y^2] - E[yhat^2]/E[y^2]
   on the scale of (5) (dates weighted equally), the signal term of every method or cell is compared
   with that of the RDFL soft learner (reference cell for the component ablations) on the same
   resampled dates: paired circular moving-block bootstrap, block 20, 10,000 draws, 95% intervals,
   centered bootstrap p-values with Holm adjustment within each dataset. The prediction second
   moment E[yhat^2]/E[y^2] is split into a variance part and a squared-mean part,
   E[yhat^2] = Var(yhat) + (E[yhat])^2, with the same date weighting.
2. Calibration coefficients. For every block after the warm-up, the archived forward calibrator is
   refitted on the same history as in 13_factorial_ablation.py and its map is written as
   intercept + slope x prediction in return units; the map is checked against the saved calibrated
   predictions.

The analysis reads saved predictions only, is descriptive, and was run after every locked result
was known.
"""
import importlib.util

import numpy as np
import pandas as pd

import common

CONFIG = common.CONFIG
BLOCK = int(CONFIG['inference']['primary_block_length'])
ITERATIONS = int(CONFIG['inference']['bootstrap_iterations'])
SEED = int(CONFIG['inference']['seed']) + 2900
RESULTS = common.ROOT / 'results'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPONENTS = load_module(common.ROOT / 'scripts/16_rdfl_component_ablation.py', 'components')
CALIBRATION = load_module(common.ROOT / 'provenance/supplement/source_code/05_calibrate_text_predictions.py',
                          'p2c_calibration')


def block_indices(n, rng):
    starts = rng.integers(0, n, size=(ITERATIONS, int(np.ceil(n / BLOCK))))
    return ((starts[..., None] + np.arange(BLOCK)) % n).reshape(ITERATIONS, -1)[:, :n]


def date_terms(frame, key, value):
    y = frame.actual / frame.stock_training_scale
    yhat = frame[value] / frame.stock_training_scale
    terms = pd.DataFrame({'Date': frame.Date, key: frame[key], 'zero': y ** 2, 'second': yhat ** 2,
                          'cross': y * yhat, 'yhat': yhat})
    return {k: g.groupby('Date')[['zero', 'second', 'cross', 'yhat']].mean().sort_index()
            for k, g in terms.groupby(key)}


def contrasts(frame, key, value, reference, label):
    daily = date_terms(frame, key, value)
    dates = daily[reference].index
    if any(not d.index.equals(dates) for d in daily.values()):
        raise ValueError(f'{label}: not evaluated on identical dates')
    index = block_indices(len(dates), np.random.default_rng(SEED))
    zero = daily[reference]['zero'].to_numpy()
    zero_boot = zero[index].mean(axis=1)
    ref_cross = daily[reference]['cross'].to_numpy()
    ref_signal = 2 * ref_cross.mean() / zero.mean()
    ref_boot = 2 * ref_cross[index].mean(axis=1) / zero_boot
    rows = []
    for k, d in daily.items():
        second, cross, mean_pred = d['second'].to_numpy(), d['cross'].to_numpy(), d['yhat'].to_numpy()
        signal = 2 * cross.mean() / zero.mean()
        boot = 2 * cross[index].mean(axis=1) / zero_boot
        diff, diff_boot = signal - ref_signal, boot - ref_boot
        square_mean = mean_pred.mean() ** 2
        rows.append({
            'dataset': label, key: k, 'reference': reference, 'dates': len(dates),
            'signal_term': signal, 'signal_ci95_low': common.interval(boot)[0], 'signal_ci95_high': common.interval(boot)[1],
            'signal_minus_reference': diff,
            'signal_minus_reference_ci95_low': common.interval(diff_boot)[0] if k != reference else 0.0,
            'signal_minus_reference_ci95_high': common.interval(diff_boot)[1] if k != reference else 0.0,
            'raw_p': (float((1 + np.sum(np.abs(diff_boot - diff) >= abs(diff))) / (ITERATIONS + 1))
                      if k != reference else np.nan),
            'second_moment_term': second.mean() / zero.mean(),
            'variance_part': (second.mean() - square_mean) / zero.mean(),
            'squared_mean_part': square_mean / zero.mean(),
            'relative_improvement_vs_zero': (signal - second.mean() / zero.mean()),
        })
    table = pd.DataFrame(rows)
    tested = table[key] != reference
    table.loc[tested, 'holm_p'] = common.holm(table.loc[tested, 'raw_p'].to_numpy())
    table['family_size'] = int(tested.sum())
    return table


def calibration_coefficients(raw, calibrated, label):
    """Refit the archived calibrator per block and express it as intercept + slope x prediction."""
    raw = raw.copy()
    raw['Date'] = pd.to_datetime(raw.Date)
    calibrated = calibrated.copy()
    calibrated['Date'] = pd.to_datetime(calibrated.Date)
    rows = []
    for (block, method), current in calibrated.groupby(['block', 'method']):
        if method == 'ZERO':
            continue
        start = current.Date.min()
        history = raw[(raw.Date < start) & (raw.method == method)]
        c = CALIBRATION.fit_calibrator(history)
        if c['constant']:
            intercept, slope = c['prediction'], 0.0
        else:
            coef, b0 = float(c['model'].coef_[0]), float(c['model'].intercept_)
            slope = coef * c['y_scale'] / c['x_scale']
            intercept = c['y_mean'] + c['y_scale'] * (b0 - coef * c['x_mean'] / c['x_scale'])
        x = current.prediction.to_numpy(float)
        gap = float(np.max(np.abs(intercept + slope * x - current.calibrated_prediction.to_numpy(float))))
        if gap > 1e-12:
            raise ValueError(f'{label} {block} {method}: refitted calibrator differs from saved output by {gap}')
        rows.append({'dataset': label, 'block': block, 'method': method, 'history_stock_days': len(history),
                     'ridge_alpha': c['alpha'], 'intercept': intercept, 'slope': slope,
                     'raw_prediction_sd': float(np.std(x, ddof=1)),
                     'calibrated_prediction_sd': float(np.std(current.calibrated_prediction, ddof=1)),
                     'max_reproduction_gap': gap})
    return pd.DataFrame(rows)


def main():
    out = common.start_run('signal_contrasts')
    pilot = pd.read_csv(RESULTS / 'purged_pilot/predictions.csv')
    components = pd.read_csv(RESULTS / 'rdfl_component_ablation/predictions.csv')
    us_pilot = pd.read_csv(RESULTS / 'fnspid_replication/predictions.csv')
    us_components = pd.read_csv(RESULTS / 'fnspid_replication/component_predictions.csv')
    tables = [contrasts(pilot, 'method', 'prediction', 'RDFL_SOFT', 'thai_pilot'),
              contrasts(components, 'cell', 'prediction', COMPONENTS.REFERENCE, 'thai_components'),
              contrasts(us_pilot, 'method', 'prediction', 'RDFL_SOFT', 'fnspid_pilot'),
              contrasts(us_components, 'cell', 'prediction', COMPONENTS.REFERENCE, 'fnspid_components')]
    for t in tables:
        t.to_csv(out / f'{t.dataset.iloc[0]}_signal_contrasts.csv', index=False)

    factorial = pd.read_csv(RESULTS / 'factorial_ablation/predictions.csv')
    fresh = factorial[(factorial.purge > 0) & factorial.exact_overlap_exclusion.astype(bool)
                      & factorial.calibration.astype(bool)]
    raw_fresh = factorial[(factorial.purge > 0) & factorial.exact_overlap_exclusion.astype(bool)
                          & ~factorial.calibration.astype(bool)]
    thai_cal = fresh.merge(raw_fresh[['Date', 'Symbol', 'method', 'prediction']], on=['Date', 'Symbol', 'method'],
                           suffixes=('_calibrated', ''), validate='one_to_one')
    thai_cal = thai_cal.rename(columns={'prediction_calibrated': 'calibrated_prediction'})
    coefficients = pd.concat([
        calibration_coefficients(pilot, thai_cal, 'thai_calibrated'),   # pilot rows give the warm-up block
        calibration_coefficients(us_pilot, pd.read_csv(RESULTS / 'fnspid_replication/calibrated_predictions.csv'),
                                 'fnspid_calibrated')], ignore_index=True)
    coefficients.to_csv(out / 'calibration_coefficients.csv', index=False)

    lines = ['# Signal Contrasts and Calibration Coefficients', '',
             'Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**', '',
             f'Signal term 2E[y yhat]/E[y^2]; contrasts against the reference on the same resampled dates (block {BLOCK}, '
             f'{ITERATIONS} draws), Holm within each dataset. Second moment = variance part + squared-mean part.', '']
    for t in tables:
        key = t.columns[1]
        lines += [f'## {t.dataset.iloc[0]}', '', common.markdown(t[[key, 'signal_term', 'signal_minus_reference',
                  'signal_minus_reference_ci95_low', 'signal_minus_reference_ci95_high', 'holm_p',
                  'second_moment_term', 'variance_part', 'squared_mean_part']]), '']
    rdfl = coefficients[coefficients.method == 'RDFL_SOFT']
    lines += ['## Calibration of the RDFL soft learner', '',
              common.markdown(rdfl[['dataset', 'block', 'history_stock_days', 'ridge_alpha', 'intercept', 'slope',
                                    'raw_prediction_sd', 'calibrated_prediction_sd']]), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, block_length=BLOCK, iterations=ITERATIONS, seed=SEED,
                    max_calibration_reproduction_gap=float(coefficients.max_reproduction_gap.max()))
    print('\n'.join(lines).encode('ascii', 'replace').decode(), flush=True)


if __name__ == '__main__':
    main()
