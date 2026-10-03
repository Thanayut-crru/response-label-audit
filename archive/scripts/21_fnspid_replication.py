"""Run the locked external replication on FNSPID U.S. banks and score the hypotheses.

Follows research/PREREGISTRATION_r6.md and refuses to run unless the freeze record
matches every frozen file. The training and inference code is the Thai code itself:
13_factorial_ablation.train_config for the five learners, 16_fpa_component_ablation.run
for the FPA components, the archived P2c calibrator, and the decision rule of
12_equivalence_power. Nothing here is tuned on FNSPID.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG
PREPARED = common.ROOT / 'results' / 'fnspid_prepared'
FREEZE = common.ROOT / 'research' / 'PREREGISTRATION_FREEZE.json'
COMPARATORS = ['ZERO', 'DIRECT_HUBER', 'ORDINARY_SOFT', 'HARD_FPA']
PRIMARY = CONFIG['inference']['primary_block_length']


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_freeze():
    if not FREEZE.exists():
        raise RuntimeError('Protocol is not frozen; run 19_freeze_protocol.py first')
    record = json.loads(FREEZE.read_text(encoding='utf-8'))
    for relative, expected in record['sha256'].items():
        if common.sha(common.ROOT / relative) != expected:
            raise RuntimeError(f'Frozen file changed after the lock: {relative}')
    return record


def fingerprint(text):
    normalized = re.sub(r'\s+', ' ', str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def block_starts(window_start, window_end):
    first = (pd.Timestamp(window_start) + pd.DateOffset(months=15))
    first = first if first.day == 1 else (first + pd.offsets.MonthBegin(1))
    starts = [first + pd.DateOffset(months=3 * k) for k in range(7)]
    return pd.to_datetime(starts + [pd.Timestamp(window_end) + pd.Timedelta(days=1)])


def with_leading_folds_dropped(function, m, starts, *args):
    """Protocol rule: drop the earliest block while its fold lacks 100 training examples."""
    dropped = 0
    while True:
        m.OUTER_STARTS = starts[dropped:]
        try:
            return function(m, *args), dropped
        except RuntimeError as error:
            if 'Insufficient fold data' not in str(error) or len(m.OUTER_STARTS) <= 2:
                raise
            dropped += 1


def daily_losses(frame, value_column, key):
    frame = frame.copy()
    frame['loss'] = ((frame.actual - frame[value_column]) / frame.stock_training_scale) ** 2
    return frame.pivot_table(index='Date', columns=key, values='loss', aggfunc='mean').sort_index()


def compare(daily, ablation, equivalence, label, seed_offset):
    rows = []
    for block in CONFIG['inference']['block_lengths']:
        group = []
        for k, comparator in enumerate(COMPARATORS):
            rng = np.random.default_rng(CONFIG['inference']['seed'] + seed_offset + 17 * block + k)
            row = ablation.paired(daily[comparator].to_numpy(), daily['FPA_SOFT'].to_numpy(), rng, block,
                                  len(COMPARATORS))
            row.update(analysis=label, competitor=comparator, block_length=block, n_dates=len(daily))
            group.append(row)
        for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
            row['holm_p'] = float(p)
            row['decision_2pct_family'] = equivalence.decision(p, row['family_ci_low'], row['family_ci_high'], .02)
        rows += group
    return rows


def score(result, contrasts):
    primary = result[(result.block_length == PRIMARY)].set_index(['analysis', 'competitor'])
    c = contrasts[contrasts.block_length == PRIMARY].set_index('contrast')
    verdicts = []

    def h1(identifier, comparator):
        row = primary.loc[('uncalibrated', comparator)]
        if row.decision_2pct_family == 'FPA_WORSE_BEYOND_MARGIN':
            verdict = 'replicated'
        elif row.holm_p < .05 and row.relative_improvement < 0:
            verdict = 'partially replicated'
        elif row.decision_2pct_family in ('EQUIVALENT_WITHIN_MARGIN', 'FPA_BETTER_BEYOND_MARGIN') or (
                row.holm_p < .05 and row.relative_improvement > 0):
            verdict = 'not replicated'
        else:
            verdict = 'inconclusive'
        verdicts.append({'hypothesis': identifier, 'statement': f'uncalibrated FPA worse than {comparator} beyond ±2%',
                         'estimate': row.relative_improvement, 'interval_low': row.family_ci_low,
                         'interval_high': row.family_ci_high, 'holm_p': row.holm_p,
                         'decision': row.decision_2pct_family, 'verdict': verdict})

    h1('H1a', 'ZERO')
    h1('H1b', 'DIRECT_HUBER')
    h1('H1c', 'ORDINARY_SOFT')
    row = primary.loc[('uncalibrated', 'HARD_FPA')]
    verdict = ('replicated' if row.holm_p < .05 and row.relative_improvement > 0 else
               'not replicated' if row.holm_p < .05 and row.relative_improvement < 0 else 'inconclusive')
    verdicts.append({'hypothesis': 'H2', 'statement': 'uncalibrated FPA beats HARD_FPA',
                     'estimate': row.relative_improvement, 'interval_low': row.family_ci_low,
                     'interval_high': row.family_ci_high, 'holm_p': row.holm_p,
                     'decision': row.decision_2pct_family, 'verdict': verdict})
    for identifier, name, statement in [('H3a', 'label_rule_ordinary', 'ordinary label rule lowers loss'),
                                        ('H3b', 'random_selection_same_size',
                                         'random size-matched selection beats confidence selection')]:
        row = c.loc[name]
        verdict = ('replicated' if row.family_ci_low > 0 else 'not replicated' if row.family_ci_high < 0 else
                   'partially replicated' if row.relative_improvement > 0 else 'inconclusive')
        verdicts.append({'hypothesis': identifier, 'statement': statement, 'estimate': row.relative_improvement,
                         'interval_low': row.family_ci_low, 'interval_high': row.family_ci_high,
                         'holm_p': row.holm_p, 'decision': '', 'verdict': verdict})
    row = primary.loc[('calibrated', 'ZERO')]
    verdict = ('replicated' if row.decision_2pct_family == 'EQUIVALENT_WITHIN_MARGIN' else
               'not replicated' if row.decision_2pct_family.endswith('BEYOND_MARGIN') else 'inconclusive')
    verdicts.append({'hypothesis': 'H4', 'statement': 'calibrated FPA within ±2% of ZERO',
                     'estimate': row.relative_improvement, 'interval_low': row.family_ci_low,
                     'interval_high': row.family_ci_high, 'holm_p': row.holm_p,
                     'decision': row.decision_2pct_family, 'verdict': verdict})
    return pd.DataFrame(verdicts)


def main():
    record = verify_freeze()
    out = common.start_run('fnspid_replication')
    prepared = json.loads((PREPARED / 'COMPLETE.json').read_text(encoding='utf-8'))
    ablation = load_module(common.ROOT / 'scripts/13_factorial_ablation.py', 'ablation')
    components = load_module(common.ROOT / 'scripts/16_fpa_component_ablation.py', 'components')
    equivalence = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')
    calibration = load_module(common.ROOT / 'provenance/supplement/source_code/05_calibrate_text_predictions.py',
                              'p2c_calibration')

    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = PREPARED / 'p1_labels'
    m.SEEDS = CONFIG['real_data']['seeds']
    starts = block_starts(prepared['window_start'], prepared['window_end'])
    panel, bags = m.load_bags()
    articles = pd.read_csv(m.P1 / 'article_to_stock_day_pilot.csv', low_memory=False)
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    articles['text_hash'] = articles['model_text'].fillna('').map(fingerprint)
    groups = articles.groupby(['Date', 'Symbol'])['text_hash'].agg(set).to_dict()
    bags['text_hashes'] = [groups.get((r.Date, r.Symbol), set()) for r in bags.itertuples()]

    with threadpool_limits(limits=1):
        (raw, folds), dropped = with_leading_folds_dropped(
            lambda mm, *a: ablation.train_config(mm, *a), m, starts, panel, bags, 5, True)
        m.OUTER_STARTS = starts[dropped:]
        cells, sizes = components.run(m, panel, bags)

    consistency = float(np.max(np.abs(
        cells[cells.cell == components.REFERENCE].set_index(['Date', 'Symbol']).prediction.sort_index().to_numpy()
        - raw[raw.method == 'FPA_SOFT'].set_index(['Date', 'Symbol']).prediction.sort_index().to_numpy())))
    if consistency > 1e-12:
        raise ValueError('Component run and main run disagree on FPA_SOFT')
    calibrated, warmup = ablation.forward_calibrate(calibration, raw)
    raw.to_csv(out / 'predictions.csv', index=False)
    calibrated.to_csv(out / 'calibrated_predictions.csv', index=False)
    cells.to_csv(out / 'component_predictions.csv', index=False)
    pd.DataFrame(folds).to_csv(out / 'fold_manifest.csv', index=False)
    sizes.to_csv(out / 'component_training_sizes.csv', index=False)

    rows = compare(daily_losses(raw, 'prediction', 'method'), ablation, equivalence, 'uncalibrated', 80000)
    rows += compare(daily_losses(calibrated, 'calibrated_prediction', 'method'), ablation, equivalence,
                    'calibrated', 81000)
    result = pd.DataFrame(rows)
    result.to_csv(out / 'paired_inference.csv', index=False)

    cell_daily = daily_losses(cells, 'prediction', 'cell')
    contrast_rows = []
    for block in CONFIG['inference']['block_lengths']:
        group = []
        for k, name in enumerate(['label_rule_ordinary', 'random_selection_same_size']):
            base, variant = components.CONTRASTS[name]
            rng = np.random.default_rng(CONFIG['inference']['seed'] + 82000 + 17 * block + k)
            row = components.paired(cell_daily[base].to_numpy(), cell_daily[variant].to_numpy(), rng, block, 2)
            row.update(contrast=name, baseline=base, variant=variant, block_length=block)
            group.append(row)
        for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
            row['holm_p'] = float(p)
        contrast_rows += group
    contrasts = pd.DataFrame(contrast_rows)
    contrasts.to_csv(out / 'contrasts.csv', index=False)

    verdicts = score(result, contrasts)
    verdicts.to_csv(out / 'hypotheses.csv', index=False)
    labels = pd.read_csv(m.P1 / 'stock_day_labels_pilot.csv', low_memory=False)
    retained = labels[labels.retain_for_text_training.astype(str).str.lower().eq('true')]
    low = retained[retained.weak_label == 'LOW_RESPONSE']
    descriptives = {
        'window': [prepared['window_start'], prepared['window_end']], 'blocks_dropped_by_rule': dropped,
        'evaluated_blocks': int(raw.block.nunique()), 'evaluation_dates': int(raw.Date.nunique()),
        'evaluation_stock_days': int(len(raw) / raw.method.nunique()), 'calibration_warmup_block': warmup,
        'articles_mapped': int(articles.decision_date.notna().sum()), 'text_bags': int(len(bags)),
        'retained_labels': int(len(retained)),
        'label_counts': {str(k): int(v) for k, v in retained.weak_label.value_counts().items()},
        'low_response_bags_with_2plus_articles': float((low.news_count >= 2).mean()),
        'prediction_sd_uncalibrated': raw[raw.method != 'ZERO'].groupby('method').prediction.std().to_dict(),
        'prediction_sd_calibrated': calibrated[calibrated.method != 'ZERO'].groupby('method')
        .calibrated_prediction.std().to_dict(),
        'outcome_sd': float(raw.drop_duplicates(['Date', 'Symbol']).actual.std()),
        'protocol_frozen_utc': record['frozen_utc'],
    }
    common.dump(out / 'descriptives.json', descriptives)
    lines = ['# External Replication on FNSPID U.S. Banks', '',
             f'Protocol frozen {record["frozen_utc"]}; run once after the freeze.', '',
             '## Hypotheses (block length 20)', '', common.markdown(verdicts), '',
             '## Paired inference', '',
             common.markdown(result[result.block_length == PRIMARY][
                 ['analysis', 'competitor', 'relative_improvement', 'family_ci_low', 'family_ci_high', 'holm_p',
                  'decision_2pct_family']]), '',
             '## Component contrasts', '',
             common.markdown(contrasts[contrasts.block_length == PRIMARY][
                 ['contrast', 'relative_improvement', 'family_ci_low', 'family_ci_high', 'holm_p']]), '',
             '## Descriptives', '', '\n'.join(f'- {k}: {v}' for k, v in descriptives.items()), '']
    (out / 'HYPOTHESES.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, protocol_frozen_utc=record['frozen_utc'], blocks_dropped_by_rule=dropped,
                    consistency_gap=consistency)
    print((out / 'HYPOTHESES.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
