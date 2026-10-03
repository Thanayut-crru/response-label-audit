"""Manuscript figure set for the IEEE Access submission.

Every figure must carry information that its companion table cannot. The two
legacy figures reproduced Table I and Table III value for value, so they are
replaced here by a conceptual panel, a protocol timeline, a gap plot, a
redesigned interval plot, and a power curve.

Figures are written as vector PDF for submission and PNG for review copies,
sized for the IEEE two-column layout.
"""
from __future__ import annotations

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import common

OUT = common.ROOT / 'results' / 'figures'
REPORT = common.ROOT / 'results' / 'report'

COL_SINGLE = 3.5   # inches, IEEE single column
COL_DOUBLE = 7.16  # inches, IEEE double column

BLUE, ORANGE, GREEN = '#0072B2', '#E69F00', '#009E73'
VERMILLION, PURPLE, GREY = '#D55E00', '#CC79A7', '#4D4D4D'

SCENARIO_LABELS = {
    'anticipation': 'Anticipation',
    'cancellation_050': 'Cancellation\n$c=0.50$',
    'cancellation_085': 'Cancellation\n$c=0.85$',
    'cancellation_100': 'Cancellation\n$c=1.00$',
    'high_noise': 'High noise',
    'informative_missing': 'Informative\nmissingness',
    'null_effect': 'Null effect',
    'regime_shift': 'Regime shift',
    'stale_price': 'Stale price',
    'strong_signal': 'Strong signal',
}

METHOD_LABELS = {
    'ZERO': 'Zero forecast',
    'DIRECT_HUBER': 'Direct (Huber)',
    'ORDINARY_SOFT': 'Ordinary soft',
    'HARD_RDFL': 'Hard RDFL',
}


def style() -> None:
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'font.size': 8,
        'axes.labelsize': 8,
        'axes.titlesize': 8.5,
        'xtick.labelsize': 7,
        'ytick.labelsize': 7,
        'legend.fontsize': 7,
        'axes.linewidth': 0.6,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'xtick.major.width': 0.6,
        'ytick.major.width': 0.6,
        'lines.linewidth': 1.1,
        'figure.dpi': 200,
        'savefig.dpi': 400,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.02,
    })


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ('pdf', 'png'):
        fig.savefig(OUT / f'{name}.{ext}')
    plt.close(fig)
    print(f'wrote {name}.pdf / {name}.png')


# ---------------------------------------------------------------- figure 1
def figure_observational_equivalence() -> None:
    """The paper's central claim, drawn rather than left in symbols."""
    fig, axes = plt.subplots(1, 2, figsize=(COL_DOUBLE, 2.45))

    worlds = [
        ('World 0: no component acts', ['$A = 0$', '$B = 0$'], [0.0, 0.0],
         r'$Z_{\mathrm{component}} = 1$', GREEN),
        ('World 1: two components cancel', ['$A = g(X)$', '$B = -g(X)$'], [0.62, -0.62],
         r'$Z_{\mathrm{component}} = 0$', VERMILLION),
    ]

    for ax, (title, labels, values, verdict, colour) in zip(axes, worlds):
        ax.set_title(title, pad=6)
        ax.set_xlim(0, 1)
        ax.set_ylim(-1.15, 1.35)
        ax.axis('off')
        ax.axhline(0, xmin=0.06, xmax=0.52, color=GREY, lw=0.6, ls=':')

        # latent components as signed bars
        for x, (label, value) in zip((0.13, 0.38), zip(labels, values)):
            ax.add_patch(FancyBboxPatch((x - 0.055, min(0, value)), 0.11, abs(value) or 0.012,
                                        boxstyle='square,pad=0', linewidth=0.7,
                                        facecolor=colour if value else '#FFFFFF',
                                        edgecolor=colour, alpha=0.85 if value else 1.0))
            ax.text(x, 1.15, label, ha='center', va='center', fontsize=7.5)
        ax.text(0.255, -1.02, 'latent components', ha='center', va='center',
                fontsize=7, color=GREY, style='italic')

        ax.add_patch(FancyArrowPatch((0.47, 0.0), (0.60, 0.0), arrowstyle='-|>',
                                     mutation_scale=9, lw=0.8, color=GREY))
        ax.text(0.535, 0.16, 'sum', ha='center', fontsize=6.5, color=GREY)

        ax.add_patch(FancyBboxPatch((0.63, -0.30), 0.32, 0.60,
                                    boxstyle='round,pad=0.02,rounding_size=0.04',
                                    linewidth=0.8, facecolor='#F2F2F2', edgecolor=GREY))
        ax.text(0.79, 0.10, r'$Y = A + B + \varepsilon$', ha='center', va='center', fontsize=7.5)
        ax.text(0.79, -0.13, r'$V = h(|A + B|) + \eta$', ha='center', va='center', fontsize=7.5)
        ax.text(0.79, -0.47, 'identical observables\n$(X,\\,Y,\\,V)$', ha='center', va='top',
                fontsize=7, color=GREY, style='italic')
        ax.text(0.79, -0.93, verdict, ha='center', va='center', fontsize=8, color=colour)

    fig.text(0.5, -0.055,
             'Any rule reading only $(X,\\,Y,\\,V)$ returns the same label in both worlds, '
             'yet component absence differs wherever $|g(X)| > \\delta$.',
             ha='center', fontsize=7.5, color=GREY)
    save(fig, 'fig1_observational_equivalence')


# ---------------------------------------------------------------- figure 2
def figure_protocol_timeline() -> None:
    """Reviewers checking leakage want to see the fold geometry, not read it."""
    folds = pd.read_csv(common.ROOT / 'results' / 'purged_pilot' / 'fold_manifest.csv')
    for col in ('test_start', 'test_stop_exclusive', 'train_end', 'purge_start'):
        folds[col] = pd.to_datetime(folds[col])
    origin = folds['train_end'].min() - pd.Timedelta(days=380)

    fig, ax = plt.subplots(figsize=(COL_DOUBLE, 2.9))
    for i, row in folds.iterrows():
        y = len(folds) - i
        ax.barh(y, (row['train_end'] - origin).days, left=origin, height=0.52,
                color=BLUE, alpha=0.30, edgecolor=BLUE, linewidth=0.5)
        ax.barh(y, (row['test_start'] - row['purge_start']).days, left=row['purge_start'],
                height=0.52, color=GREY, alpha=0.55, hatch='////', edgecolor='white', linewidth=0.0)
        ax.barh(y, (row['test_stop_exclusive'] - row['test_start']).days, left=row['test_start'],
                height=0.52, color=ORANGE, edgecolor=ORANGE, linewidth=0.5)
        ax.text(row['test_stop_exclusive'] + pd.Timedelta(days=12), y,
                f'{int(row["test_bags"])} bags\n$-${int(row["exact_text_overlap_train_bags_removed"])} overlap',
                va='center', fontsize=6.2, color=GREY)

    ax.set_yticks(range(1, len(folds) + 1))
    ax.set_yticklabels([f'Fold {i}' for i in range(len(folds), 0, -1)])
    ax.set_xlim(origin, folds['test_stop_exclusive'].max() + pd.Timedelta(days=150))
    ax.set_ylim(0.3, len(folds) + 0.9)
    ax.set_xlabel('Evaluation calendar')

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=BLUE, alpha=0.30, edgecolor=BLUE, lw=0.5),
        plt.Rectangle((0, 0), 1, 1, facecolor=GREY, alpha=0.55, hatch='////', edgecolor='white'),
        plt.Rectangle((0, 0), 1, 1, facecolor=ORANGE, edgecolor=ORANGE, lw=0.5),
    ]
    ax.legend(handles, ['Expanding training window', 'Five-session purge', 'Quarterly test block'],
              loc='lower left', bbox_to_anchor=(0.0, -0.40), ncol=3, frameon=False,
              handlelength=1.4, columnspacing=1.2)
    save(fig, 'fig2_protocol_timeline')


# ---------------------------------------------------------------- figure 3
def figure_absence_gap() -> None:
    """Error minus prevalence is the quantity the legacy figure never showed."""
    data = pd.read_csv(REPORT / 'absence_summary.csv')
    data = data[data['threshold'].str.startswith('fixed_')].copy()
    data['gap'] = data['component_error'] - data['component_prevalence']
    data['delta'] = data['threshold'].str.replace('fixed_', '', regex=False).astype(float)

    order = [s for s in SCENARIO_LABELS if s in set(data['scenario'])]
    deltas = sorted(data['delta'].unique())
    colours = {0.2: BLUE, 0.35: ORANGE, 0.5: GREEN}
    width = 0.26

    fig, ax = plt.subplots(figsize=(COL_DOUBLE, 2.8))
    positions = np.arange(len(order))
    for k, delta in enumerate(deltas):
        subset = data[data['delta'] == delta].set_index('scenario').reindex(order)
        offset = (k - (len(deltas) - 1) / 2) * width
        ax.bar(positions + offset, subset['gap'], width=width,
               color=colours.get(delta, GREY), edgecolor='white', linewidth=0.4,
               label=f'$\\delta = {delta:g}$')

    ax.axhline(0, color=GREY, lw=0.7)
    ax.set_xticks(positions)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in order], fontsize=6.3)
    ax.set_ylabel('Component-absence error\nminus population prevalence')
    ax.set_ylim(min(data['gap'].min() * 1.30, -0.05), 0.012)
    ax.legend(loc='lower left', frameon=False, ncol=3, handlelength=1.2, columnspacing=1.2)
    ax.text(0.42, 0.10, 'bars near zero mean the retained label\nbarely improves on the base rate',
            transform=ax.transAxes, ha='left', va='bottom', fontsize=6.5,
            color=GREY, style='italic')
    save(fig, 'fig3_absence_gap')


# ---------------------------------------------------------------- figure 4
def figure_paired_intervals() -> None:
    """Interval geometry that a table of four rows cannot convey."""
    inference = pd.read_csv(REPORT / 'purged_pilot_paired_inference.csv')
    primary = common.CONFIG['inference']['primary_block_length']
    inference = inference[inference['block_length'] == primary].set_index('competitor')
    inference = inference.reindex([c for c in METHOD_LABELS if c in inference.index])
    margin = float(common.CONFIG['inference']['relative_equivalence_margin']) * 100

    fig, ax = plt.subplots(figsize=(COL_DOUBLE, 2.25))
    ax.axvspan(-margin, margin, color=GREY, alpha=0.12, lw=0)
    ax.axvline(0, color=GREY, lw=0.8)

    y = np.arange(len(inference))[::-1]
    for yi, (name, row) in zip(y, inference.iterrows()):
        point = row['relative_improvement'] * 100
        lo, hi = row['relative_ci95_low'] * 100, row['relative_ci95_high'] * 100
        flo, fhi = row['relative_family_equivalence_ci_low'] * 100, row['relative_family_equivalence_ci_high'] * 100
        colour = GREEN if point > 0 else VERMILLION
        ax.plot([flo, fhi], [yi, yi], color=colour, lw=0.8, alpha=0.45,
                solid_capstyle='butt', zorder=2)
        ax.plot([lo, hi], [yi, yi], color=colour, lw=2.2, solid_capstyle='butt', zorder=3)
        ax.plot([point], [yi], 'o', color=colour, ms=4.2, zorder=4,
                markeredgecolor='white', markeredgewidth=0.6)
        ax.text(hi + 1.0, yi, f'{point:+.2f}%'.replace('-', '−'),
                va='center', fontsize=6.8, color=colour)

    ax.set_yticks(y)
    ax.set_yticklabels([METHOD_LABELS[i] for i in inference.index])
    ax.set_xlabel('RDFL relative loss improvement (%). Negative favours the comparator.')
    ax.set_ylim(-0.7, len(inference) - 0.3)
    ax.text(0, 1.04, f'shaded band: disclosed $\\pm${margin:g}% practical margin',
            transform=ax.transAxes, fontsize=6.6, color=GREY, style='italic')
    ax.text(0.995, 1.04, 'thick: paired 95% CI    thin: family-adjusted',
            transform=ax.transAxes, ha='right', fontsize=6.6, color=GREY, style='italic')
    save(fig, 'fig4_paired_intervals')


# ---------------------------------------------------------------- figure 5
def figure_power_curve() -> None:
    """Difference-test power and equivalence-test power are different quantities.

    The top row answers "could the design detect a nonzero effect of this size?",
    the bottom row "could the design certify equivalence at this margin if the
    true effect were zero?". Reading the top row as evidence for equivalence was
    the error corrected in revision r5, so the two are drawn on separate axes.
    """
    curve = pd.read_csv(common.ROOT / 'results' / 'power' / 'power_curve.csv')
    summary = pd.read_csv(common.ROOT / 'results' / 'power' / 'power_summary.csv')
    equivalence = pd.read_csv(common.ROOT / 'results' / 'equivalence_power' / 'equivalence_curve.csv')
    eq_summary = pd.read_csv(common.ROOT / 'results' / 'equivalence_power' / 'equivalence_summary.csv')
    primary = common.CONFIG['inference']['primary_block_length']
    summary = summary[summary['block_length'] == primary]
    eq_summary = eq_summary[eq_summary['block_length'] == primary]
    margin = float(common.CONFIG['inference']['relative_equivalence_margin']) * 100
    colours = {'ZERO': BLUE, 'DIRECT_HUBER': ORANGE, 'ORDINARY_SOFT': GREEN, 'HARD_RDFL': PURPLE}
    panels = [('purged_pilot', 'Fresh purged pilot'), ('historical_p2c', 'Archived historical pipeline')]

    fig, axes = plt.subplots(2, 2, figsize=(COL_DOUBLE, 4.7), sharey=True)
    for column, (dataset, title) in enumerate(panels):
        top, bottom = axes[0, column], axes[1, column]
        top.set_title(f'({"ab"[column]}) {title}: difference test', pad=5)
        bottom.set_title(f'({"cd"[column]}) {title}: equivalence test', pad=5)
        indexed = summary[summary['dataset'] == dataset].set_index('competitor')
        eq_indexed = eq_summary[eq_summary['dataset'] == dataset].set_index('competitor')
        for ax, right in ((top, 10), (bottom, 12)):
            ax.axhline(0.80, color=GREY, lw=0.7, ls='--')
            ax.set_xlim(0, right)
            ax.set_ylim(0, 1.03)
        top.axvline(margin, color=GREY, lw=0.6, ls=':')
        bottom.axvline(margin, color=GREY, lw=0.6, ls=':')
        for name in METHOD_LABELS:
            subset = curve[(curve['competitor'] == name) & (curve['dataset'] == dataset)]
            top.plot(subset['true_relative_effect'] * 100, subset['power'],
                     color=colours[name], label=METHOD_LABELS[name])
            mde80 = indexed.loc[name, 'mde_power_80'] * 100
            if mde80 <= 10:
                top.plot([mde80], [0.80], 'o', color=colours[name], ms=3.4,
                         markeredgecolor='white', markeredgewidth=0.5, zorder=5)
            subset = equivalence[(equivalence['competitor'] == name) & (equivalence['dataset'] == dataset)]
            bottom.plot(subset['margin'] * 100, subset['equivalence_power_family'],
                        color=colours[name], label=METHOD_LABELS[name])
            margin80 = eq_indexed.loc[name, 'equivalence_margin80_family'] * 100
            if margin80 <= 12:
                bottom.plot([margin80], [0.80], 'o', color=colours[name], ms=3.4,
                            markeredgecolor='white', markeredgewidth=0.5, zorder=5)
        top.set_xlabel('True relative loss improvement (%)')
        bottom.set_xlabel('Equivalence margin $\\Delta$ (%)')

    axes[0, 0].set_ylabel('Power to reject zero\n(two-sided $\\alpha = 0.05$)')
    axes[1, 0].set_ylabel('P(97.5% family interval\ninside $\\pm\\Delta$ | true effect 0)')
    axes[0, 0].text(margin + 0.2, 0.05, f'{margin:g}%', fontsize=6.5, color=GREY)
    axes[1, 0].text(margin + 0.2, 0.05, f'$\\pm${margin:g}%', fontsize=6.5, color=GREY)
    axes[0, 0].text(3.0, 0.83, '80%', ha='left', fontsize=6.5, color=GREY)
    axes[0, 1].legend(loc='lower right', frameon=False, handlelength=1.4)
    fig.tight_layout(h_pad=1.2, w_pad=1.0)
    save(fig, 'fig5_power_curve')


def main() -> None:
    style()
    figure_observational_equivalence()
    figure_protocol_timeline()
    figure_absence_gap()
    figure_paired_intervals()
    figure_power_curve()


if __name__ == '__main__':
    main()
