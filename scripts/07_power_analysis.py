"""Minimum detectable effect and retrospective power for the purged pilot.

A negative result requires evidence that the design could have detected an
effect of practical size. This script derives the sampling variability of the
paired relative-loss statistic from the same circular moving-block bootstrap
used for the primary inference, then reports the minimum detectable effect and
the power curve implied by that variability.

Power is computed under a normal approximation to the bootstrap sampling
distribution of the relative-improvement statistic. It is a retrospective
design diagnostic, not an observed-effect post hoc power calculation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import common

CONFIG = common.CONFIG
RDFL = 'RDFL_SOFT'
COMPARATORS = ['ZERO', 'DIRECT_HUBER', 'ORDINARY_SOFT', 'HARD_RDFL']
ALPHA = 0.05
POWER_TARGETS = [0.80, 0.90]
EFFECT_GRID = np.round(np.arange(0.001, 0.1001, 0.001), 4)

DATASETS = {
    'purged_pilot': {
        'path': ('results', 'purged_pilot', 'predictions.csv'),
        'loss_column': 'normalized_squared_error',
        'warmup_block': None,
    },
    'historical_p2c': {
        'path': ('provenance', 'historical', 'p2c_forward_calibration',
                 'calibrated_predictions.csv'),
        'loss_column': 'calibrated_normalized_squared_error',
        'warmup_block': '2024-08-01_2024-10-31',
    },
}


def date_loss_matrix(predictions: pd.DataFrame, loss_column: str) -> pd.DataFrame:
    """Mean normalized squared loss per evaluation date, one column per method.

    Stocks are averaged within a date so that every date carries equal weight,
    matching the primary inference.
    """
    per_date = (predictions
                .groupby(['method', 'Date'])[loss_column]
                .mean()
                .unstack('method'))
    if per_date.isna().any().any():
        raise ValueError('Methods are not evaluated on an identical set of dates')
    return per_date.sort_index()


def relative_se(comparator: np.ndarray, rdfl: np.ndarray, block: int,
                iterations: int, rng: np.random.Generator) -> tuple[float, float]:
    """Point estimate and bootstrap standard error of relative improvement."""
    _, ratios = common.bootstrap_paired(comparator, rdfl, iterations, rng, block=block)
    ratios = ratios[np.isfinite(ratios)]
    point = 1.0 - rdfl.mean() / comparator.mean()
    return float(point), float(ratios.std(ddof=1))


def mde(se: float, power: float, alpha: float = ALPHA) -> float:
    """Two-sided minimum detectable effect under a normal approximation."""
    return float((stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) * se)


def power_at(effect: float, se: float, alpha: float = ALPHA) -> float:
    """Two-sided power to reject a zero relative improvement."""
    critical = stats.norm.ppf(1 - alpha / 2)
    standardized = abs(effect) / se
    return float(stats.norm.sf(critical - standardized) + stats.norm.cdf(-critical - standardized))


def analyse(name: str, spec: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    predictions = pd.read_csv(common.ROOT.joinpath(*spec['path']))
    if spec['warmup_block'] is not None:
        predictions = predictions[predictions['block'] != spec['warmup_block']]
    losses = date_loss_matrix(predictions, spec['loss_column'])

    missing = [m for m in [RDFL, *COMPARATORS] if m not in losses.columns]
    if missing:
        raise ValueError(f'{name}: missing methods in prediction table: {missing}')

    n_dates = len(losses)
    n_stock_days = int(predictions.loc[predictions['method'] == RDFL].shape[0])
    iterations = int(CONFIG['inference']['bootstrap_iterations'])
    margin = float(CONFIG['inference']['relative_equivalence_margin'])
    rdfl_losses = losses[RDFL].to_numpy()

    summary_rows, curve_rows = [], []
    for block in CONFIG['inference']['block_lengths']:
        for comparator in COMPARATORS:
            rng = np.random.default_rng(CONFIG['inference']['seed'] + block * 17
                                        + len(comparator) - comparator.count('RDFL') + len(name))  # seed uses the pre-rename name length
            point, se = relative_se(losses[comparator].to_numpy(), rdfl_losses,
                                    block, iterations, rng)
            row = {
                'dataset': name,
                'competitor': comparator,
                'block_length': block,
                'n_dates': n_dates,
                'n_stock_days': n_stock_days,
                'observed_relative_improvement': point,
                'bootstrap_se': se,
                'power_at_2pct_margin': power_at(margin, se),
                'observed_exceeds_mde80': bool(abs(point) >= mde(se, 0.80)),
            }
            for target in POWER_TARGETS:
                row[f'mde_power_{int(target * 100)}'] = mde(se, target)
            summary_rows.append(row)

            if block == CONFIG['inference']['primary_block_length']:
                for effect in EFFECT_GRID:
                    curve_rows.append({'dataset': name, 'competitor': comparator,
                                       'block_length': block,
                                       'true_relative_effect': float(effect),
                                       'power': power_at(float(effect), se)})

    meta = {'n_dates': n_dates, 'n_stock_days': n_stock_days, 'iterations': iterations}
    return pd.DataFrame(summary_rows), pd.DataFrame(curve_rows), meta


def main() -> None:
    out = common.start_run('power')
    margin = float(CONFIG['inference']['relative_equivalence_margin'])
    primary_block = CONFIG['inference']['primary_block_length']

    summaries, curves, metas = [], [], {}
    for name, spec in DATASETS.items():
        summary, curve, meta = analyse(name, spec)
        summaries.append(summary)
        curves.append(curve)
        metas[name] = meta

    summary = pd.concat(summaries, ignore_index=True)
    curve = pd.concat(curves, ignore_index=True)
    summary.to_csv(out / 'power_summary.csv', index=False)
    curve.to_csv(out / 'power_curve.csv', index=False)

    lines = [
        '# Retrospective Power and Minimum Detectable Effect',
        '',
        'Status: **DESIGN DIAGNOSTIC — NORMAL APPROXIMATION TO THE BOOTSTRAP**',
        '',
        'Power is the probability of rejecting a zero relative improvement at a',
        f'two-sided {ALPHA:.2f} level, given the bootstrap standard error of the paired',
        'relative-loss statistic. It is a design diagnostic, not an observed-effect',
        'post hoc calculation.',
        '',
    ]
    for name in DATASETS:
        block = summary[(summary['dataset'] == name) & (summary['block_length'] == primary_block)]
        meta = metas[name]
        lines += [
            f'## {name}',
            '',
            f'Evaluation dates: {meta["n_dates"]}; matched stock-days: {meta["n_stock_days"]}; '
            f'bootstrap draws: {meta["iterations"]:,}.',
            '',
            common.markdown(block[['competitor', 'observed_relative_improvement', 'bootstrap_se',
                                   'mde_power_80', 'mde_power_90', 'power_at_2pct_margin',
                                   'observed_exceeds_mde80']]),
            '',
            f'Power at the disclosed {margin * 100:.0f}% margin ranges from '
            f'{block["power_at_2pct_margin"].min():.2f} to '
            f'{block["power_at_2pct_margin"].max():.2f}. '
            f'{int(block["observed_exceeds_mde80"].sum())} of {len(block)} observed effects '
            f'exceed their own 80% minimum detectable effect.',
            '',
        ]
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')

    common.complete(out, datasets=metas, comparators=COMPARATORS,
                    block_lengths=CONFIG['inference']['block_lengths'],
                    alpha=ALPHA, power_targets=POWER_TARGETS)
    print((out / 'REPORT.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
