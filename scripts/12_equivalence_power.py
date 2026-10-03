"""Equivalence-test sensitivity, kept separate from difference-test power.

07_power_analysis.py reports the power to reject a ZERO relative improvement.
That is the power of a difference test. It says nothing about the probability
of certifying practical equivalence, which is a different test: two one-sided
tests (TOST) that reject both |effect| >= margin hypotheses, equivalently an
interval that lies entirely inside (-margin, +margin).

This script computes, from the same bootstrap standard errors, the power of
the equivalence diagnostic actually used in the manuscript (a 90% interval for
a single comparator, a 97.5% interval for the four-comparator family), the
smallest margin that the design could certify with 80% probability, and the
interval-based decision that the observed data support. Decisions rest on the
observed intervals; power quantities describe design sensitivity only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import common

CONFIG = common.CONFIG
FAMILY_SIZE = 4
ALPHA = 0.05                        # two-sided difference test; 90% interval for TOST
# 03_inference_and_report.py builds the family interval as interval(rel, 0.10 / 4): a two-sided
# 97.5% interval, so each bound is a one-sided test at 0.0125.
FAMILY_ALPHA = 0.10 / FAMILY_SIZE / 2
MARGINS = [0.01, 0.02, 0.05]
TARGET_POWER = 0.80
MARGIN_GRID = np.round(np.arange(0.001, 0.1201, 0.001), 4)
DATASETS = ['purged_pilot', 'historical_p2c']


def difference_power(effect: float, se: float, alpha: float = ALPHA) -> float:
    """Two-sided power to reject a zero effect when the true effect is ``effect``."""
    critical = stats.norm.ppf(1 - alpha / 2)
    standardized = abs(effect) / se
    return float(stats.norm.sf(critical - standardized) + stats.norm.cdf(-critical - standardized))


def equivalence_power(margin: float, se: float, alpha: float, theta: float = 0.0) -> float:
    """Probability that the (1 - 2 alpha) interval lies inside (-margin, margin).

    Under a normal approximation, TOST at one-sided level alpha declares
    equivalence when -margin + z se < estimate < margin - z se. The acceptance
    region is empty, and the power is exactly zero, whenever margin <= z se.
    """
    z = stats.norm.ppf(1 - alpha)
    upper = (margin - theta) / se - z
    lower = (-margin - theta) / se + z
    if upper <= lower:
        return 0.0
    return float(stats.norm.cdf(upper) - stats.norm.cdf(lower))


def equivalence_margin(se: float, alpha: float, power: float = TARGET_POWER) -> float:
    """Smallest margin certified with probability ``power`` when the true effect is zero."""
    return float((stats.norm.ppf(1 - alpha) + stats.norm.ppf((1 + power) / 2)) * se)


def decision(holm_p: float, low: float, high: float, margin: float) -> str:
    """Interval-based reading of one comparison at a given margin."""
    if high < -margin:
        return 'RDFL_WORSE_BEYOND_MARGIN'
    if low > margin:
        return 'RDFL_BETTER_BEYOND_MARGIN'
    if -margin < low and high < margin:
        return 'EQUIVALENT_WITHIN_MARGIN'
    if holm_p < ALPHA:
        return 'DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN'
    return 'INCONCLUSIVE'


def main() -> None:
    out = common.start_run('equivalence_power')
    power = pd.read_csv(common.ROOT / 'results' / 'power' / 'power_summary.csv')
    rows, curve = [], []
    for dataset in DATASETS:
        inference = pd.read_csv(common.ROOT / 'results' / 'report' / f'{dataset}_paired_inference.csv')
        merged = inference.merge(power[power['dataset'] == dataset],
                                 on=['dataset', 'competitor', 'block_length'], validate='one_to_one',
                                 suffixes=('', '_power'))
        if len(merged) != len(inference):
            raise ValueError(f'{dataset}: power and inference tables do not align')
        if not np.allclose(merged['relative_improvement'], merged['observed_relative_improvement']):
            raise ValueError(f'{dataset}: power and inference analysed different estimates')
        for record in merged.itertuples(index=False):
            se = float(record.bootstrap_se)
            row = {
                'dataset': dataset, 'competitor': record.competitor,
                'block_length': int(record.block_length), 'n_dates': int(record.n_dates),
                'relative_improvement': float(record.relative_improvement),
                'bootstrap_se': se,
                'relative_ci95_low': float(record.relative_ci95_low),
                'relative_ci95_high': float(record.relative_ci95_high),
                'relative_ci90_low': float(record.relative_ci90_low),
                'relative_ci90_high': float(record.relative_ci90_high),
                'family_ci_low': float(record.relative_family_equivalence_ci_low),
                'family_ci_high': float(record.relative_family_equivalence_ci_high),
                'holm_p': float(record.holm_p),
                'mde80_difference': float(record.mde_power_80),
                'equivalence_margin80_comparator': equivalence_margin(se, ALPHA),
                'equivalence_margin80_family': equivalence_margin(se, FAMILY_ALPHA),
                'observed_bound_ci90': max(abs(record.relative_ci90_low), abs(record.relative_ci90_high)),
                'observed_bound_family': max(abs(record.relative_family_equivalence_ci_low),
                                             abs(record.relative_family_equivalence_ci_high)),
            }
            for margin in MARGINS:
                tag = f'{int(round(margin * 100))}pct'
                row[f'difference_power_{tag}'] = difference_power(margin, se)
                row[f'equivalence_power_{tag}_comparator'] = equivalence_power(margin, se, ALPHA)
                row[f'equivalence_power_{tag}_family'] = equivalence_power(margin, se, FAMILY_ALPHA)
                row[f'decision_{tag}_family'] = decision(record.holm_p,
                                                        record.relative_family_equivalence_ci_low,
                                                        record.relative_family_equivalence_ci_high, margin)
            # The published family-level flag must agree with the interval decision.
            flagged = bool(record.family_equivalent_2pct)
            if flagged != (row['decision_2pct_family'] == 'EQUIVALENT_WITHIN_MARGIN'):
                raise ValueError('Equivalence decision disagrees with the published inference table')
            rows.append(row)
            if int(record.block_length) == CONFIG['inference']['primary_block_length']:
                for margin in MARGIN_GRID:
                    curve.append({'dataset': dataset, 'competitor': record.competitor,
                                  'margin': float(margin),
                                  'equivalence_power_family': equivalence_power(float(margin), se, FAMILY_ALPHA),
                                  'equivalence_power_comparator': equivalence_power(float(margin), se, ALPHA)})
    summary = pd.DataFrame(rows)
    summary.to_csv(out / 'equivalence_summary.csv', index=False)
    pd.DataFrame(curve).to_csv(out / 'equivalence_curve.csv', index=False)

    primary = summary[summary['block_length'] == CONFIG['inference']['primary_block_length']]
    columns = ['dataset', 'competitor', 'relative_improvement', 'family_ci_low', 'family_ci_high',
               'holm_p', 'decision_2pct_family', 'bootstrap_se', 'mde80_difference',
               'difference_power_2pct', 'equivalence_power_2pct_family', 'equivalence_margin80_family']
    lines = [
        '# Equivalence Sensitivity Separated from Difference-Test Power',
        '',
        'Status: **DESIGN DIAGNOSTIC — NORMAL APPROXIMATION TO THE BOOTSTRAP**',
        '',
        '`difference_power_2pct` is the power of the test of a zero effect when the true effect is 2%.',
        '`equivalence_power_2pct_family` is the probability that the 97.5% family interval lies inside',
        '(-2%, +2%) when the true effect is zero. They are different tests and are not interchangeable.',
        'Decisions are read from the observed intervals, not from either power quantity.',
        '',
        common.markdown(primary[columns]),
        '',
    ]
    for dataset in DATASETS:
        block = primary[primary['dataset'] == dataset]
        counts = block['decision_2pct_family'].value_counts().to_dict()
        lines.append(f'- {dataset}: decisions at +/-2% = {counts}')
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    common.complete(out, datasets=DATASETS, margins=MARGINS, alpha=ALPHA, family_alpha=FAMILY_ALPHA,
                    target_power=TARGET_POWER, theta_for_equivalence_power=0.0)
    print((out / 'REPORT.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
