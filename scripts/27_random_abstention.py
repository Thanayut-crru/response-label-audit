"""Size-matched random abstention for the text-rule repair experiment (revision analysis).

In 18_simulation_extensions.py a text rule of accuracy q flags cases holding opposing components,
and retained low-response cases it flags are dropped. Dropping cases changes both which cases are
kept and how many, so the rule's effect on forecast accuracy mixes label validity with sample size.
Here, in every replication and for every q, the same number of retained low-response cases is
dropped uniformly at random instead, and the component-absence error and the latent MSE of
RDFL soft supervision are recomputed. The rule arm is recomputed with the generator, labels, and
random flags of 18 and checked against its saved replications.

Run after all locked and published results were known, in response to reviewers
(research/PREREGISTRATION_DEVIATIONS.md, entry 6). Known-truth simulation only.
"""
from __future__ import annotations

import importlib.util
import warnings

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replication(ext, legacy, seed, q, cfg):
    d = ext.generate(seed, cfg['n_train'], cfg['n_test'], cfg['features'])
    f, _ = ext.rdfl(legacy, d)
    opposing = (d['a'] * d['b'] < 0) & (d['component'] > ext.DELTA)
    flagged = np.where(np.random.default_rng(seed + 7919).random(len(opposing)) < q, opposing, ~opposing)
    pool = f['retain'] & (f['hard'] == 1)                      # retained low-response cases
    rule_keep = f['retain'] & ~(flagged & pool)
    dropped = int((pool & flagged).sum())
    choice = np.random.default_rng(seed * 10 + int(round(10 * q))).choice(np.flatnonzero(pool), dropped,
                                                                          replace=False)
    random_keep = f['retain'].copy()
    random_keep[choice] = False

    out = {'seed': seed, 'rule_accuracy': q, 'dropped': dropped,
           'retained_low_response_before': int(pool.sum())}
    for name, keep in [('rule', rule_keep), ('random', random_keep)]:
        pred = ext.soft_predict(legacy, d['x'][keep], d['xt'], f['probabilities'][keep], f['confidence'][keep],
                                d['y'][keep])
        out[f'{name}_component_absence_error'] = ext.diagnostics(ext.low_mass(f, keep), d)[
            'weighted_component_absence_error']
        out[f'{name}_latent_mse'] = float(np.mean((pred - d['thetat']) ** 2))
        out[f'{name}_retained_fraction'] = float(keep.mean())
    return out


def paired_summary(frame, q):
    group = frame[frame.rule_accuracy == q]
    rng = np.random.default_rng(int(CONFIG['inference']['seed']) + 2700 + int(round(10 * q)))
    index = rng.integers(0, len(group), size=(10000, len(group)))
    row = {'rule_accuracy': q, 'replications': len(group), 'mean_dropped': float(group.dropped.mean())}
    for column in ['rule_component_absence_error', 'random_component_absence_error',
                   'rule_latent_mse', 'random_latent_mse', 'rule_retained_fraction', 'random_retained_fraction']:
        row[column] = float(group[column].mean())
    difference = (group.rule_latent_mse - group.random_latent_mse).to_numpy()
    boot = difference[index].mean(axis=1)
    row['mse_rule_minus_random'] = float(difference.mean())
    row['mse_rule_minus_random_ci95_low'], row['mse_rule_minus_random_ci95_high'] = common.interval(boot)
    row['raw_p'] = float((1 + np.sum(np.abs(boot - difference.mean()) >= abs(difference.mean()))) / 10001)
    return row


def main():
    out = common.start_run('random_abstention')
    cfg = CONFIG['simulation']
    legacy = common.load_legacy('06_run_known_truth_simulation.py')
    ext = load_module(common.ROOT / 'scripts/18_simulation_extensions.py', 'simulation_extensions')
    seeds = range(cfg['seed_start'], cfg['seed_start'] + cfg['replications'])

    from sklearn.exceptions import ConvergenceWarning
    warnings.filterwarnings('error', category=ConvergenceWarning)
    with threadpool_limits(limits=1):
        frame = pd.DataFrame([replication(ext, legacy, s, q, cfg) for q in ext.ACCURACIES for s in seeds])

    # Gate: the rule arm reproduces the saved replications of 18_simulation_extensions.py.
    saved = pd.read_csv(common.ROOT / 'results/simulation_extensions/rule_replications.csv')
    check = frame.merge(saved, on=['seed', 'rule_accuracy'])
    if len(check) != len(frame):
        raise ValueError('rule arm does not align with the saved replications')
    for mine, theirs in [('rule_latent_mse', 'rdfl_soft_latent_mse_after'),
                         ('rule_component_absence_error', 'weighted_component_absence_error_after'),
                         ('rule_retained_fraction', 'retained_fraction_after')]:
        gap = float(np.max(np.abs(check[mine] - check[theirs])))
        if gap > 1e-12:
            raise ValueError(f'rule arm differs from the saved run in {mine} by {gap}')
    print('Reproduction gate passed: rule arm equals 18_simulation_extensions', flush=True)

    summary = pd.DataFrame([paired_summary(frame, q) for q in ext.ACCURACIES])
    summary['holm_p'] = common.holm(summary.raw_p)
    frame.to_csv(out / 'replications.csv', index=False)
    summary.to_csv(out / 'summary.csv', index=False)
    lines = ['# Size-Matched Random Abstention', '',
             'Status: **KNOWN-TRUTH; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**', '',
             'Cancellation 0.85, delta = 0.35, 100 replications per accuracy. The random arm drops, in each '
             'replication, as many retained low-response cases as the rule drops, chosen uniformly at random.', '',
             common.markdown(summary), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, rule_accuracies=list(ext.ACCURACIES), replications=cfg['replications'],
                    delta=ext.DELTA)
    print('\n'.join(lines).encode('ascii', 'replace').decode(), flush=True)


if __name__ == '__main__':
    main()
