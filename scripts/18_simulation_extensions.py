"""Known-truth extensions: when can a response-derived absence label be repaired?

Three experiments extend 01_simulation.py, whose generator is mirrored here so
that the lambda = 0 linear case reproduces it exactly (checked before running).

1. Volume informativeness (lambda). Volume is
   0.8 * [(1 - lambda) |A + B| + lambda (|A| + |B|)] + noise.
   lambda = 0 is the original net-linked volume; lambda = 1 makes volume track
   gross component activity. Cancellation 0.85, 100 replications per level.
2. Component-aware abstention (q). A text rule reports, with accuracy q, whether
   a case holds opposing components with at least one exceeding delta. Retained
   LOW_RESPONSE cases flagged by the rule are dropped. q = 0.5 is uninformative.
3. Nonlinear signal with capacity-matched learners. The first component is a
   fixed nonlinear function of the features; direct regression and RDFL soft
   supervision both use histogram gradient boosting, so neither is favoured by
   correct specification.

Alongside the diagnostics, the partial-identification bounds of Section II.B are
computed on the retained low-response mass: with net response only, the
component-absence error lies in [P(|A+B| > 2 delta), 1]; with gross activity
G = |A| + |B| observed, opposite-sign cases are point-identified and the sharp
set is [P(activity identified), P(G + |A+B| > 2 delta)]. The simpler, non-sharp
lower bound P(G > 2 delta) is also recorded.
"""
from __future__ import annotations

import importlib.util
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG
DELTA = 0.35
LAMBDAS = [0.0, 0.25, 0.5, 0.75, 1.0]
ACCURACIES = [0.5, 0.7, 0.9, 1.0]
NONLINEAR = {'nonlinear': 0.0, 'nonlinear_cancellation_085': 0.85}
HGB = dict(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=20, early_stopping=False)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nonlinear_raw(x):
    return np.sin(1.5 * x[:, 0]) + 0.8 * x[:, 1] * x[:, 2] + 0.6 * (np.abs(x[:, 3]) - np.sqrt(2 / np.pi))


# Population scale of the nonlinear signal from a fixed reference draw, never from test data.
NONLINEAR_SCALE = float(nonlinear_raw(np.random.default_rng(999).normal(size=(2_000_000, 4))).std())


def generate(seed, n_train, n_test, features, cancel=0.85, volume_lambda=0.0, nonlinear=False):
    """Mirror of 01_simulation.generate for the cancellation scenarios, with two options."""
    rng = np.random.default_rng(seed)
    xtr = rng.normal(size=(n_train, features))
    xte = rng.normal(size=(n_test, features))
    beta = np.zeros(features)
    beta[:3] = [0.7, -0.5, 0.4]
    beta /= np.linalg.norm(beta)

    def parts(x):
        first = nonlinear_raw(x) / NONLINEAR_SCALE if nonlinear else x @ beta
        second = -cancel * first
        if cancel > 0:
            second = second + 0.3 * x[:, 5]
        return first, second, first + second

    a, b, t = parts(xtr)
    _, _, te = parts(xte)
    y = t + 0.7 * rng.normal(size=n_train)
    ye = te + 0.7 * rng.normal(size=n_test)
    activity = (1 - volume_lambda) * np.abs(t) + volume_lambda * (np.abs(a) + np.abs(b))
    volume = 0.8 * activity + rng.normal(scale=0.75, size=n_train)
    return {'x': xtr, 'xt': xte, 'y': y, 'yt': ye, 'theta': t, 'thetat': te, 'a': a, 'b': b,
            'component': np.maximum(np.abs(a), np.abs(b)), 'volume': volume}


def rdfl(legacy, d):
    v, _, _, _ = legacy.robust_standardize(d['volume'], d['volume'])
    return legacy.rdfl_labels(d['y'], np.abs(v)), np.abs(v)


def low_mass(f, keep=None):
    keep = f['retain'] if keep is None else keep
    return f['probabilities'][:, 1] * f['confidence'] * keep


def diagnostics(weights, d):
    mass = weights.sum()
    net = np.abs(d['theta'])
    gross = np.abs(d['a']) + np.abs(d['b'])
    share = lambda event: float(weights @ event / mass) if mass > 0 else np.nan
    # With G observed, G > |S| reveals opposite signs and max(|A|,|B|) = (G + |S|)/2 exactly;
    # G = |S| (same sign) leaves max(|A|,|B|) anywhere in [G/2, G].
    same_sign = np.isclose(gross, net, rtol=0, atol=1e-12)
    identified_active = np.where(same_sign, gross > 2 * DELTA, gross + net > 2 * DELTA)
    return {'weighted_component_absence_error': share(d['component'] > DELTA),
            'weighted_net_absence_error': share(net > DELTA),
            'component_prevalence': float((d['component'] > DELTA).mean()),
            'low_response_weight_mass': float(mass),
            'bound_net_only_lower': share(net > 2 * DELTA), 'bound_net_only_upper': 1.0,
            'bound_gross_lower': share(gross > 2 * DELTA),
            'bound_gross_sharp_lower': share(identified_active),
            'bound_gross_upper': share(gross + net > 2 * DELTA)}


def soft_predict(legacy, x, xt, q, w, y):
    model = legacy.fit_soft_classifier(x, q, w)
    return legacy.predict_probabilities(model, xt) @ legacy.class_centers(y, q, w)


def hgb_soft_predict(x, xt, q, w, y, seed):
    """Soft labels through the same expanded-sample trick as the legacy learner."""
    n = len(x)
    labels = np.repeat([0, 1, 2], n)
    weights = np.concatenate([q[:, k] * w for k in range(3)])
    keep = weights > 1e-10
    model = HistGradientBoostingClassifier(random_state=seed, **HGB)
    model.fit(np.vstack([x, x, x])[keep], labels[keep], sample_weight=weights[keep])
    probabilities = np.zeros((len(xt), 3))
    probabilities[:, model.classes_] = model.predict_proba(xt)
    centers = np.array([np.sum(q[:, k] * w * y) / np.sum(q[:, k] * w) if np.sum(q[:, k] * w) > 1e-10
                        else float(y.mean()) for k in range(3)])
    return probabilities @ centers


def lambda_replication(legacy, seed, lam, cfg):
    d = generate(seed, cfg['n_train'], cfg['n_test'], cfg['features'], volume_lambda=lam)
    f, _ = rdfl(legacy, d)
    sel = f['retain']
    pred = soft_predict(legacy, d['x'][sel], d['xt'], f['probabilities'][sel], f['confidence'][sel], d['y'][sel])
    return {'seed': seed, 'lambda': lam, **diagnostics(low_mass(f), d),
            'retained_fraction': float(sel.mean()),
            'rdfl_soft_latent_mse': float(np.mean((pred - d['thetat']) ** 2)),
            'direct_latent_mse': float(np.mean((Ridge(alpha=1.0).fit(d['x'], d['y']).predict(d['xt']) - d['thetat']) ** 2))}


def rule_replication(legacy, seed, q, cfg):
    d = generate(seed, cfg['n_train'], cfg['n_test'], cfg['features'])
    f, _ = rdfl(legacy, d)
    opposing = (d['a'] * d['b'] < 0) & (d['component'] > DELTA)
    rng = np.random.default_rng(seed + 7919)
    flagged = np.where(rng.random(len(opposing)) < q, opposing, ~opposing)
    keep = f['retain'] & ~(flagged & (f['hard'] == 1))
    base = f['retain']
    out = {'seed': seed, 'rule_accuracy': q, 'retained_fraction_before': float(base.mean()),
           'retained_fraction_after': float(keep.mean())}
    before, after = diagnostics(low_mass(f), d), diagnostics(low_mass(f, keep), d)
    out.update({f'{k}_before': v for k, v in before.items()})
    out.update({f'{k}_after': v for k, v in after.items()})
    for name, mask in [('before', base), ('after', keep)]:
        pred = soft_predict(legacy, d['x'][mask], d['xt'], f['probabilities'][mask], f['confidence'][mask], d['y'][mask])
        out[f'rdfl_soft_latent_mse_{name}'] = float(np.mean((pred - d['thetat']) ** 2))
    return out


def nonlinear_replication(legacy, seed, scenario, cfg):
    d = generate(seed, cfg['n_train'], cfg['n_test'], cfg['features'], cancel=NONLINEAR[scenario], nonlinear=True)
    f, v = rdfl(legacy, d)
    sel = f['retain']
    q, w = f['probabilities'][sel], f['confidence'][sel]
    ordinary = legacy.ordinary_labels(d['y'], v)
    ones = np.ones(len(d['x']))
    preds = {
        'ZERO': np.zeros(len(d['xt'])),
        'DIRECT_RIDGE': Ridge(alpha=1.0).fit(d['x'], d['y']).predict(d['xt']),
        'RDFL_SOFT_LOGISTIC': soft_predict(legacy, d['x'][sel], d['xt'], q, w, d['y'][sel]),
        'DIRECT_HGB': HistGradientBoostingRegressor(random_state=seed, **HGB).fit(d['x'], d['y']).predict(d['xt']),
        'RDFL_SOFT_HGB': hgb_soft_predict(d['x'][sel], d['xt'], q, w, d['y'][sel], seed),
        'ORDINARY_SOFT_HGB': hgb_soft_predict(d['x'], d['xt'], ordinary, ones, d['y'], seed),
        'ORACLE_HGB': HistGradientBoostingRegressor(random_state=seed, **HGB).fit(d['x'], d['theta']).predict(d['xt']),
    }
    rows = [{'scenario': scenario, 'seed': seed, 'method': k, 'latent_mse': float(np.mean((p - d['thetat']) ** 2))}
            for k, p in preds.items()]
    return rows, {'scenario': scenario, 'seed': seed, **diagnostics(low_mass(f), d)}


def mc_summary(frame, by, columns):
    rows = []
    for key, group in frame.groupby(by):
        row = {by: key, 'replications': len(group)}
        for column in columns:
            values = group[column].to_numpy(float)
            boot = values[np.random.default_rng(5).integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
            row[column] = float(values.mean())
            row[f'{column}_ci95_low'], row[f'{column}_ci95_high'] = common.interval(boot)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    out = common.start_run('simulation_extensions')
    cfg = CONFIG['simulation']
    legacy = common.load_legacy('06_run_known_truth_simulation.py')
    original = load_module(common.ROOT / 'scripts/01_simulation.py', 'simulation')
    seeds = range(cfg['seed_start'], cfg['seed_start'] + cfg['replications'])

    # Reproduction gate: lambda = 0, linear, cancellation 0.85 equals 01_simulation's scenario.
    reference = pd.read_csv(common.ROOT / 'results/simulation/absence_diagnostics.csv')
    reference = reference[(reference.scenario == 'cancellation_085') & (reference.threshold_definition == 'fixed_0.35')]
    for seed in list(seeds)[:5]:
        mine = generate(seed, cfg['n_train'], cfg['n_test'], cfg['features'])
        theirs = original.generate(seed, 'cancellation_085', cfg['n_train'], cfg['n_test'], cfg['features'])
        for key in ['x', 'y', 'theta', 'volume', 'component']:
            np.testing.assert_array_equal(mine[key], theirs[key])
        f, _ = rdfl(legacy, mine)
        value = diagnostics(low_mass(f), mine)['weighted_component_absence_error']
        archived = float(reference.loc[reference.seed == seed, 'weighted_component_absence_error'].iloc[0])
        if abs(value - archived) > 1e-12:
            raise ValueError(f'lambda = 0 does not reproduce the archived diagnostic for seed {seed}')
    print('Reproduction gate passed for lambda = 0', flush=True)

    from sklearn.exceptions import ConvergenceWarning
    warnings.filterwarnings('error', category=ConvergenceWarning)
    with threadpool_limits(limits=1):
        lam = pd.DataFrame([lambda_replication(legacy, s, v, cfg) for v in LAMBDAS for s in seeds])
        print('lambda experiment complete', flush=True)
        rule = pd.DataFrame([rule_replication(legacy, s, q, cfg) for q in ACCURACIES for s in seeds])
        print('rule experiment complete', flush=True)
        metrics, diag = [], []
        for scenario in NONLINEAR:
            for s in seeds:
                rows, dd = nonlinear_replication(legacy, s, scenario, cfg)
                metrics += rows
                diag.append(dd)
            print(f'{scenario} complete', flush=True)
    metrics, diag = pd.DataFrame(metrics), pd.DataFrame(diag)
    lam.to_csv(out / 'lambda_replications.csv', index=False)
    rule.to_csv(out / 'rule_replications.csv', index=False)
    metrics.to_csv(out / 'nonlinear_metrics.csv', index=False)
    diag.to_csv(out / 'nonlinear_diagnostics.csv', index=False)

    lam_summary = mc_summary(lam, 'lambda', ['weighted_component_absence_error', 'component_prevalence',
                                             'weighted_net_absence_error', 'bound_net_only_lower',
                                             'bound_gross_lower', 'bound_gross_sharp_lower', 'bound_gross_upper',
                                             'retained_fraction',
                                             'rdfl_soft_latent_mse', 'direct_latent_mse'])
    rule_summary = mc_summary(rule, 'rule_accuracy', ['weighted_component_absence_error_before',
                                                      'weighted_component_absence_error_after',
                                                      'component_prevalence_after', 'retained_fraction_after',
                                                      'rdfl_soft_latent_mse_before', 'rdfl_soft_latent_mse_after'])
    lam_summary.to_csv(out / 'lambda_summary.csv', index=False)
    rule_summary.to_csv(out / 'rule_summary.csv', index=False)

    pairs = []
    wide = metrics.pivot_table(index=['scenario', 'seed'], columns='method', values='latent_mse')
    comparisons = [('DIRECT_HGB', 'RDFL_SOFT_HGB'), ('ORDINARY_SOFT_HGB', 'RDFL_SOFT_HGB'),
                   ('DIRECT_RIDGE', 'RDFL_SOFT_LOGISTIC'), ('ZERO', 'RDFL_SOFT_HGB')]
    rng = np.random.default_rng(CONFIG['inference']['seed'] + 90)
    for scenario in NONLINEAR:
        block = wide.loc[scenario]
        for base, variant in comparisons:
            difference = (block[base] - block[variant]).to_numpy()
            boot = difference[rng.integers(0, len(difference), size=(10000, len(difference)))].mean(axis=1)
            centered = boot - difference.mean()
            pairs.append({'scenario': scenario, 'baseline': base, 'variant': variant,
                          'mean_difference_baseline_minus_variant': float(difference.mean()),
                          'ci95_low': common.interval(boot)[0], 'ci95_high': common.interval(boot)[1],
                          'raw_p': float((1 + np.sum(np.abs(centered) >= abs(difference.mean()))) / 10001)})
    pairs = pd.DataFrame(pairs)
    pairs['holm_p'] = common.holm(pairs.raw_p)
    pairs.to_csv(out / 'nonlinear_paired_inference.csv', index=False)
    means = metrics.groupby(['scenario', 'method']).latent_mse.mean().unstack()
    means.to_csv(out / 'nonlinear_means.csv')

    lines = ['# Simulation Extensions', '', 'Status: **KNOWN-TRUTH; CONDITIONAL ON THE STATED GENERATORS**', '',
             '## Volume informativeness (cancellation 0.85, delta = 0.35)', '', common.markdown(lam_summary), '',
             '## Component-aware abstention', '', common.markdown(rule_summary), '',
             '## Nonlinear signal, capacity-matched learners (latent MSE)', '', common.markdown(means.reset_index()), '',
             common.markdown(pairs), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, delta=DELTA, lambdas=LAMBDAS, rule_accuracies=ACCURACIES,
                    nonlinear_scenarios=list(NONLINEAR), replications=cfg['replications'],
                    nonlinear_scale=NONLINEAR_SCALE)
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
