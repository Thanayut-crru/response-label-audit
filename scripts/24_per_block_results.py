"""Block-by-block relative loss of RDFL_SOFT, for the supplementary material.

The pooled paired inference averages over seven test blocks. Reviewers asked how
stable the direction is across blocks and how much the size varies. This script
reports, for each block, the equal-date mean loss ratio of RDFL_SOFT to each
comparator in the Thai fresh pilot and in the U.S. replication (uncalibrated and
calibrated). It is descriptive: blocks hold about 60 dates, too few for separate
moving-block inference, and no test is performed per block.
"""
import numpy as np
import pandas as pd

import common

COMPARATORS = ['ZERO', 'DIRECT_HUBER', 'ORDINARY_SOFT', 'HARD_RDFL']
SOURCES = {
    'thai_fresh_pilot': ('results/purged_pilot/predictions.csv', 'prediction'),
    'us_uncalibrated': ('results/fnspid_replication/predictions.csv', 'prediction'),
    'us_calibrated': ('results/fnspid_replication/calibrated_predictions.csv', 'calibrated_prediction'),
}


def per_block(path, column):
    frame = pd.read_csv(common.ROOT / path)
    frame['loss'] = ((frame.actual - frame[column]) / frame.stock_training_scale) ** 2
    daily = frame.pivot_table(index=['block', 'Date'], columns='method', values='loss', aggfunc='mean')
    means = daily.groupby(level='block').mean()
    out = pd.DataFrame({'dates': daily.groupby(level='block').size(),
                        'stock_days': frame[frame.method == 'RDFL_SOFT'].groupby('block').size()})
    for comparator in COMPARATORS:
        out[f'improvement_vs_{comparator}'] = 1 - means['RDFL_SOFT'] / means[comparator]
    pooled = daily.mean()
    total = {'dates': len(daily), 'stock_days': int((frame.method == 'RDFL_SOFT').sum())}
    total.update({f'improvement_vs_{c}': 1 - pooled['RDFL_SOFT'] / pooled[c] for c in COMPARATORS})
    return pd.concat([out, pd.DataFrame([total], index=['ALL'])]).reset_index(names='block')


def main():
    out = common.start_run('per_block')
    summary = {}
    lines = ['# Block-by-Block Relative Loss of RDFL_SOFT', '', 'Status: **DESCRIPTIVE; NO PER-BLOCK TEST**', '']
    for name, (path, column) in SOURCES.items():
        table = per_block(path, column)
        table.to_csv(out / f'{name}.csv', index=False)
        blocks = table[table.block != 'ALL']
        zero = blocks['improvement_vs_ZERO']
        summary[name] = {'blocks': int(len(blocks)), 'blocks_rdfl_worse_than_zero': int((zero < 0).sum()),
                         'min_improvement_vs_zero': float(zero.min()), 'max_improvement_vs_zero': float(zero.max()),
                         'pooled_improvement_vs_zero': float(table.loc[table.block == 'ALL', 'improvement_vs_ZERO'].iloc[0])}
        lines += [f'## {name}', '', common.markdown(table), '']
    common.dump(out / 'summary.json', summary)
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, sources=list(SOURCES), status='DESCRIPTIVE')
    for name, values in summary.items():
        print(name, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in values.items()})


if __name__ == '__main__':
    main()
