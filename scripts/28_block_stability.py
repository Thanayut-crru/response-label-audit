"""Stability of the main comparisons over time (revision analysis, research/PREREGISTRATION_DEVIATIONS.md entry 7).

The 2026-10-05 review asked whether the moving-block bootstrap hides instability in the loss process.
From saved predictions only, for the four primary comparisons of the RDFL soft learner in the Thai
pilot and the U.S. replication, uncalibrated and forward-calibrated:

1. Leave-one-block-out: each test block is dropped in turn and the paired inference of the primary
   analysis is repeated on the remaining dates (circular moving-block bootstrap, block 20,
   10,000 draws, family of four, Holm, ±2% decision rule). Every change of decision from the full
   sample is flagged.
2. U.S. before and during the 2020 crisis: the same inference on dates before 20 February 2020 and
   from that date on.
3. The date-level loss difference between the RDFL soft learner and the zero forecast on the scale
   of (5), saved as a series and drawn with its 20-date moving average and the block boundaries.

The intervals are conditional on the fitted predictions: models are not retrained. The analysis is
descriptive and was run after every locked result was known.
"""
import importlib.util

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import common

CONFIG = common.CONFIG
BLOCK = int(CONFIG['inference']['primary_block_length'])
SEED = int(CONFIG['inference']['seed']) + 2800
RESULTS = common.ROOT / 'results'
COMPARATORS = ['ZERO', 'DIRECT_HUBER', 'ORDINARY_SOFT', 'HARD_RDFL']
CRISIS_START = pd.Timestamp('2020-02-20')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ABLATION = load_module(common.ROOT / 'scripts/13_factorial_ablation.py', 'ablation')
EQUIVALENCE = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')


def daily(frame, value):
    frame = frame.copy()
    frame['Date'] = pd.to_datetime(frame.Date)
    frame['loss'] = ((frame.actual - frame[value]) / frame.stock_training_scale) ** 2
    table = frame.pivot_table(index='Date', columns='method', values='loss', aggfunc='mean').sort_index()
    if table.isna().any().any():
        raise ValueError('methods are not evaluated on identical dates')
    blocks = frame.drop_duplicates('Date').set_index('Date').block.reindex(table.index)
    return table, blocks


def inference(losses, offset):
    rows = []
    for k, comparator in enumerate(COMPARATORS):
        rng = np.random.default_rng(SEED + offset + k)
        row = ABLATION.paired(losses[comparator].to_numpy(), losses['RDFL_SOFT'].to_numpy(), rng, BLOCK, len(COMPARATORS))
        row.update(competitor=comparator, n_dates=len(losses))
        rows.append(row)
    for row, p in zip(rows, common.holm([r['raw_p'] for r in rows])):
        row['holm_p'] = float(p)
        row['decision_2pct_family'] = EQUIVALENCE.decision(p, row['family_ci_low'], row['family_ci_high'], .02)
    return rows


def main():
    out = common.start_run('block_stability')
    thai_factorial = pd.read_csv(RESULTS / 'factorial_ablation/predictions.csv')
    fresh = thai_factorial[(thai_factorial.purge > 0) & thai_factorial.exact_overlap_exclusion.astype(bool)
                           & thai_factorial.calibration.astype(bool)]
    datasets = {
        'thai_uncalibrated': daily(pd.read_csv(RESULTS / 'purged_pilot/predictions.csv'), 'prediction'),
        'thai_calibrated': daily(fresh, 'prediction'),
        'fnspid_uncalibrated': daily(pd.read_csv(RESULTS / 'fnspid_replication/predictions.csv'), 'prediction'),
        'fnspid_calibrated': daily(pd.read_csv(RESULTS / 'fnspid_replication/calibrated_predictions.csv'),
                                   'calibrated_prediction'),
    }
    rows, series = [], []
    for d, (label, (losses, blocks)) in enumerate(datasets.items()):
        full = {r['competitor']: r for r in inference(losses, 1000 * d)}
        for r in full.values():
            rows.append({**r, 'dataset': label, 'subset': 'all blocks', 'decision_changed': False})
        for b, block in enumerate(sorted(blocks.unique())):
            kept = losses[blocks != block]
            for r in inference(kept, 1000 * d + 50 * (b + 1)):
                changed = r['decision_2pct_family'] != full[r['competitor']]['decision_2pct_family']
                rows.append({**r, 'dataset': label, 'subset': f'without {block}', 'decision_changed': changed})
        if label.startswith('fnspid'):
            for s, (name, mask) in enumerate([('before 2020-02-20', losses.index < CRISIS_START),
                                              ('from 2020-02-20', losses.index >= CRISIS_START)]):
                for r in inference(losses[mask], 1000 * d + 700 + 50 * s):
                    changed = r['decision_2pct_family'] != full[r['competitor']]['decision_2pct_family']
                    rows.append({**r, 'dataset': label, 'subset': name, 'decision_changed': changed})
        difference = (losses['RDFL_SOFT'] - losses['ZERO']).rename('loss_difference_rdfl_minus_zero')
        series.append(pd.DataFrame({'dataset': label, 'Date': losses.index, 'block': blocks.to_numpy(),
                                    'loss_difference_rdfl_minus_zero': difference.to_numpy(),
                                    'zero_loss': losses['ZERO'].to_numpy()}))
    result = pd.DataFrame(rows)
    result.to_csv(out / 'leave_one_block_out.csv', index=False)
    series = pd.concat(series, ignore_index=True)
    series.to_csv(out / 'daily_loss_difference.csv', index=False)

    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 8,
                         'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': 0.6,
                         'savefig.dpi': 400, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02})
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 4.2))
    for ax, (label, title) in zip(axes, [('thai_uncalibrated', '(a) Thai pilot, uncalibrated'),
                                         ('fnspid_uncalibrated', '(b) U.S. replication, uncalibrated')]):
        s = series[series.dataset == label].set_index('Date')
        y = s.loss_difference_rdfl_minus_zero
        ax.bar(s.index, y, width=1.0, color='#9E9E9E', linewidth=0, label='Daily difference')
        ax.plot(s.index, y.rolling(20, min_periods=10).mean(), color='#D55E00', lw=1.2, label='20-date moving average')
        ax.axhline(0, color='#4D4D4D', lw=0.6)
        for start in s.groupby('block').apply(lambda g: g.index.min()).iloc[1:]:
            ax.axvline(start, color='#4D4D4D', lw=0.5, ls=':')
        if label.startswith('fnspid'):
            ax.axvline(CRISIS_START, color='#0072B2', lw=0.8, ls='--', label='20 February 2020')
        ax.set_title(title, loc='left')
        ax.set_ylabel('RDFL minus zero-forecast loss\n(normalized-loss units)')
        ax.set_ylim(np.quantile(y, 0.005) * 1.1, np.quantile(y, 0.995) * 1.1)
        ax.legend(frameon=False, ncol=3, loc='upper left')
    fig.tight_layout()
    for ext in ('pdf', 'png'):
        fig.savefig(out / f'block_stability.{ext}')
    plt.close(fig)

    changes = result[result.decision_changed]
    lines = ['# Stability of the Main Comparisons over Time', '',
             'Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**', '',
             f'Paired circular moving-block bootstrap, block {BLOCK}, family of four, Holm; intervals conditional on '
             'the fitted predictions. Relative improvement of RDFL over each comparator.', '',
             f'Decision changes from the full sample: {len(changes)}', '',
             common.markdown(result[['dataset', 'subset', 'competitor', 'relative_improvement', 'family_ci_low',
                                     'family_ci_high', 'holm_p', 'decision_2pct_family', 'decision_changed']]), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, block_length=BLOCK, seed=SEED, rows=len(result), decision_changes=len(changes),
                    crisis_start=str(CRISIS_START.date()))
    print('\n'.join(lines[:7]).encode('ascii', 'replace').decode(), flush=True)
    print(changes[['dataset', 'subset', 'competitor', 'relative_improvement', 'family_ci_low', 'family_ci_high',
                   'decision_2pct_family']].to_string(), flush=True)


if __name__ == '__main__':
    main()
