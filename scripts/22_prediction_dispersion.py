"""Prediction dispersion and its relation to loss across RDFL component cells.

The component ablation (16) and the external replication (21) store predictions
but not their dispersion. This script records the standard deviation of each
cell's predictions and its equal-date mean loss relative to the zero forecast, so
that the manuscript's mechanism statement rests on a saved artifact. Descriptive.
"""
import numpy as np
import pandas as pd
from scipy import stats

import common


def summarize(predictions, key, value):
    frame = predictions.copy()
    frame['loss'] = ((frame.actual - frame[value]) / frame.stock_training_scale) ** 2
    frame['zero_loss'] = (frame.actual / frame.stock_training_scale) ** 2
    daily = frame.groupby([key, 'Date'])[['loss', 'zero_loss']].mean().groupby(key).mean()
    out = pd.DataFrame({'prediction_sd': frame.groupby(key)[value].std(ddof=1),
                        'relative_improvement_vs_zero': 1 - daily['loss'] / daily['zero_loss']})
    out['outcome_sd'] = float(frame.drop_duplicates(['Date', 'Symbol']).actual.std(ddof=1))
    return out.reset_index()


def main():
    out = common.start_run('prediction_dispersion')
    rows = {}
    components = pd.read_csv(common.ROOT / 'results/rdfl_component_ablation/predictions.csv')
    rows['thai_components'] = summarize(components, 'cell', 'prediction')
    external = pd.read_csv(common.ROOT / 'results/fnspid_replication/component_predictions.csv')
    rows['fnspid_components'] = summarize(external, 'cell', 'prediction')
    summary = {}
    for name, table in rows.items():
        table.to_csv(out / f'{name}.csv', index=False)
        rho = stats.spearmanr(table.prediction_sd, table.relative_improvement_vs_zero).statistic
        summary[name] = {'cells': len(table), 'spearman_sd_vs_improvement': float(rho)}
    common.dump(out / 'summary.json', summary)
    lines = ['# Prediction Dispersion by Component Cell', '', 'Status: **DESCRIPTIVE**', '']
    for name, table in rows.items():
        lines += [f'## {name}', '', common.markdown(table.sort_values('prediction_sd')), '',
                  f'Spearman(prediction SD, improvement vs zero) = {summary[name]["spearman_sd_vs_improvement"]:.3f}', '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, **{k: v['cells'] for k, v in summary.items()})
    print(json_safe := '\n'.join(lines).encode('ascii', 'replace').decode())


if __name__ == '__main__':
    main()
