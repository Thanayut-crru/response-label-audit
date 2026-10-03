"""Observable bounds on component-absence error when only Y = S + noise is seen.

Proposition 1 of Section II.B bounds the error of absence labels from below by
P(|S| > 2 delta | L = 1). That is an oracle bound: it needs the latent net
response S. The data contain only Y = S + epsilon. Because |S| >= |Y| - |epsilon|,
for any kappa >= 0

    E[w 1{|S| > 2 delta}] >= E[w 1{|Y| > 2 delta + kappa}] - P(|epsilon| > kappa)

for weights 0 <= w <= 1, so the weighted error is at least

    max_kappa ( E[w 1{|Y| > 2 delta + kappa}] - P(|epsilon| > kappa) ) / E[w],

truncated at zero. This needs the noise distribution to be known (here the
simulation's Gaussian noise with standard deviation 0.7). Without any restriction
on the noise the lower bound is zero. The script evaluates both bounds on the
retained low-response mass of the lambda experiments, with the same generator,
seeds, and labels as 18_simulation_extensions.py.
"""
from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd
from scipy import stats

import common

CONFIG = common.CONFIG
DELTA = 0.35
NOISE_SD = 0.7
KAPPAS = np.round(np.linspace(0, 3.5, 141), 4)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observable_lower_bound(weights, observed, noise_sd, delta=DELTA, kappas=KAPPAS):
    """Largest lower bound over kappa, using sample means for E[w ...] and the known noise tail."""
    mean_weight = weights.mean()
    if mean_weight <= 0:
        return np.nan, np.nan
    best, best_kappa = 0.0, np.nan
    for kappa in kappas:
        tail = 2 * stats.norm.sf(kappa / noise_sd)
        value = ((weights * (np.abs(observed) > 2 * delta + kappa)).mean() - tail) / mean_weight
        if value > best:
            best, best_kappa = float(value), float(kappa)
    return best, best_kappa


def main():
    out = common.start_run('observable_bounds')
    cfg = CONFIG['simulation']
    legacy = common.load_legacy('06_run_known_truth_simulation.py')
    extensions = load_module(common.ROOT / 'scripts/18_simulation_extensions.py', 'extensions')
    archived = pd.read_csv(common.ROOT / 'results/simulation_extensions/lambda_replications.csv')
    rows = []
    for lam in extensions.LAMBDAS:
        for seed in range(cfg['seed_start'], cfg['seed_start'] + cfg['replications']):
            d = extensions.generate(seed, cfg['n_train'], cfg['n_test'], cfg['features'], volume_lambda=lam)
            f, _ = extensions.rdfl(legacy, d)
            w = extensions.low_mass(f)
            oracle = extensions.diagnostics(w, d)
            reference = archived[(archived['lambda'] == lam) & (archived.seed == seed)]
            if abs(oracle['weighted_component_absence_error'] - reference.weighted_component_absence_error.iloc[0]) > 1e-12:
                raise ValueError('Labels differ from the archived lambda experiment')
            bound, kappa = observable_lower_bound(w, d['y'], NOISE_SD)
            rows.append({'lambda': lam, 'seed': seed,
                         'error': oracle['weighted_component_absence_error'],
                         'oracle_lower_known_S': oracle['bound_net_only_lower'],
                         'observable_lower_known_gaussian_noise': bound, 'best_kappa': kappa,
                         'observable_lower_unrestricted_noise': 0.0,
                         'share_low_mass_with_abs_y_above_2delta': float(w @ (np.abs(d['y']) > 2 * DELTA) / w.sum())})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / 'replications.csv', index=False)
    summary = frame.groupby('lambda').agg(
        error=('error', 'mean'), oracle_lower_known_S=('oracle_lower_known_S', 'mean'),
        observable_lower_known_gaussian_noise=('observable_lower_known_gaussian_noise', 'mean'),
        observable_lower_max_over_seeds=('observable_lower_known_gaussian_noise', 'max'),
        naive_plug_in_share=('share_low_mass_with_abs_y_above_2delta', 'mean')).reset_index()
    summary.to_csv(out / 'summary.csv', index=False)
    lines = ['# Oracle and Observable Lower Bounds on Component-Absence Error', '',
             'Status: **KNOWN-TRUTH SIMULATION; CANCELLATION 0.85; DELTA 0.35**', '',
             'Oracle: requires the latent net response S. Observable: uses only Y and the known noise law.', '',
             common.markdown(summary), '',
             'The naive plug-in share replaces S by Y and is not a valid bound under noise.', '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, delta=DELTA, noise_sd=NOISE_SD, kappa_grid=[float(KAPPAS[0]), float(KAPPAS[-1]), len(KAPPAS)])
    print('\n'.join(lines).encode('ascii', 'replace').decode())


if __name__ == '__main__':
    main()
