"""Sensitivity of the pilot to near-duplicate text, and prediction dispersion.

14_provenance_checks.py found that exact-hash exclusion leaves near-verbatim
copies: training articles whose character n-gram cosine similarity to a test
article is at least 0.90. This script adds that exclusion to the fresh pilot
configuration (5-session purge, exact-overlap exclusion) and reruns the same
learners, so the remaining near-duplicate channel is measured rather than only
listed as a limitation. Paraphrased coverage of the same event is still not
detected.

It also records the dispersion of predictions before and after forward
calibration in every factorial cell, which the manuscript uses to explain why
calibrated learners become statistically indistinguishable from a zero forecast.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from threadpoolctl import threadpool_limits

import common

CONFIG = common.CONFIG
PURGE = 5
THRESHOLD = 0.90
RDFL = 'RDFL_SOFT'
COMPARATORS = ['ZERO', 'DIRECT_HUBER', 'ORDINARY_SOFT', 'HARD_RDFL']
METHODS = ['ZERO', 'DIRECT_HUBER', 'HARD_RDFL', 'ORDINARY_SOFT', RDFL]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprint(text):
    normalized = re.sub(r'\s+', ' ', str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def near_duplicate_keys(articles, train, test):
    """Training bag keys holding an article with cosine >= THRESHOLD to any test article."""
    train_articles = articles.merge(train[['Date', 'Symbol']], on=['Date', 'Symbol'])
    test_articles = articles.merge(test[['Date', 'Symbol']], on=['Date', 'Symbol'])
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=1, sublinear_tf=True,
                                 norm='l2', dtype=np.float32, max_features=200000)
    vectorizer.fit(pd.concat([train_articles.model_text, test_articles.model_text]))
    similarity = vectorizer.transform(train_articles.model_text) @ vectorizer.transform(test_articles.model_text).T
    best = np.asarray(similarity.max(axis=1).todense()).ravel()
    flagged = train_articles.loc[best >= THRESHOLD, ['Date', 'Symbol']].drop_duplicates()
    return set(zip(flagged.Date, flagged.Symbol))


def run(m, panel, bags, articles):
    valid = panel[panel.outcome_data_valid.astype(str).str.lower().eq('true')]
    dates = np.sort(valid.Date.unique())
    parts, folds = [], []
    for start, stop in zip(m.OUTER_STARTS[:-1], m.OUTER_STARTS[1:]):
        prior = dates[dates < start.to_datetime64()]
        if len(prior) <= PURGE:
            continue
        boundary = pd.Timestamp(prior[-PURGE])
        train = bags[bags.Date < boundary].copy()
        test = bags[(bags.Date >= start) & (bags.Date < stop)].copy()
        if test.empty:
            continue
        test_hashes = set().union(*test.text_hashes)
        exact = train.text_hashes.map(lambda s: bool(s & test_hashes))
        train = train.loc[~exact]
        near = near_duplicate_keys(articles, train, test)
        flagged = pd.Series([(d, s) in near for d, s in zip(train.Date, train.Symbol)], index=train.index)
        train = train.loc[~flagged].reset_index(drop=True)
        retained = train[train.retain_for_text_training]
        ordinary = train[np.isfinite(train[['residual_z', 'volume_deviation']].to_numpy(float)).all(axis=1)]
        if len(retained) < 100 or len(ordinary) < 100:
            raise RuntimeError('Insufficient fold data; do not silently omit the fold')
        vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=3, max_df=.98,
                              max_features=20000, sublinear_tf=True, norm='l2', dtype=np.float32)
        x = vec.fit_transform(train.bag_text)
        xt = vec.transform(test.bag_text)
        q = retained[['p_negative', 'p_low_response', 'p_positive']].to_numpy(float)
        w = retained.label_confidence.to_numpy(float)
        p = m.fit_soft_ensemble(x[retained.index], q, w, xt)
        rdfl = p @ m.class_centers(retained.target_open_close.to_numpy(float), q, w)
        hard = retained.weak_label.map(m.LABEL_TO_INT).to_numpy(int)
        hp = m.fit_hard_ensemble(x[retained.index], hard, xt)
        hpred = hp @ m.class_centers(retained.target_open_close.to_numpy(float), np.eye(3)[hard])
        oq = m.ordinary_probabilities(ordinary)
        op = m.fit_soft_ensemble(x[ordinary.index], oq, np.ones(len(ordinary)), xt)
        opred = op @ m.class_centers(ordinary.target_open_close.to_numpy(float), oq)
        predictions = {'ZERO': np.zeros(len(test)),
                       'DIRECT_HUBER': m.fit_direct_ensemble(x, train.target_open_close.to_numpy(float), xt),
                       'HARD_RDFL': hpred, 'ORDINARY_SOFT': opred, RDFL: rdfl}
        scales = valid[valid.Date < boundary].groupby('Symbol').target_open_close.std(ddof=1).clip(lower=1e-6)
        for method, pred in predictions.items():
            frame = test[['Date', 'Symbol', 'target_open_close']].rename(columns={'target_open_close': 'actual'}).copy()
            frame['prediction'] = pred
            frame['method'] = method
            frame['block'] = str(start.date())
            frame['stock_training_scale'] = frame.Symbol.map(scales)
            parts.append(frame)
        folds.append({'test_start': str(start.date()), 'train_bags': len(train), 'test_bags': len(test),
                      'exact_overlap_train_bags_removed': int(exact.sum()),
                      'near_duplicate_train_bags_removed': int(flagged.sum())})
        print(f'{start.date()}: exact={int(exact.sum())}, near={int(flagged.sum())}, train={len(train)}', flush=True)
    return pd.concat(parts, ignore_index=True), pd.DataFrame(folds)


def inference(frame, label, value_column):
    """Same estimands and seeds pattern as 13_factorial_ablation.py."""
    iterations = int(CONFIG['inference']['bootstrap_iterations'])
    frame = frame.copy()
    frame['loss'] = ((frame.actual - frame[value_column]) / frame.stock_training_scale) ** 2
    daily = frame.pivot_table(index='Date', columns='method', values='loss', aggfunc='mean').sort_index()
    rows = []
    for block in CONFIG['inference']['block_lengths']:
        group = []
        for k, comparator in enumerate(COMPARATORS):
            rng = np.random.default_rng(CONFIG['inference']['seed'] + 50000 + 17 * block + k + 100 * len(label))
            a, b = daily[comparator].to_numpy(), daily[RDFL].to_numpy()
            diff, rel = common.bootstrap_paired(a, b, iterations, rng, block)
            observed = float(a.mean() - b.mean())
            family = common.interval(rel, .1 / len(COMPARATORS))
            group.append({'analysis': label, 'competitor': comparator, 'block_length': block,
                          'n_dates': len(daily), 'relative_improvement': observed / float(a.mean()),
                          'bootstrap_se': float(rel[np.isfinite(rel)].std(ddof=1)),
                          'family_ci_low': family[0], 'family_ci_high': family[1],
                          'raw_p': float((1 + np.sum(np.abs(diff - observed) >= abs(observed))) / (iterations + 1))})
        for row, p in zip(group, common.holm([r['raw_p'] for r in group])):
            row['holm_p'] = float(p)
        rows += group
    return rows


def main():
    out = common.start_run('near_duplicate_sensitivity')
    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = common.ROOT / 'provenance/historical/p1_pilot_labels'
    m.SEEDS = CONFIG['real_data']['seeds']
    calibration_driver = load_module(common.ROOT / 'scripts/13_factorial_ablation.py', 'ablation')
    calibration = load_module(common.ROOT / 'provenance/supplement/source_code/05_calibrate_text_predictions.py',
                              'p2c_calibration')
    equivalence = load_module(common.ROOT / 'scripts/12_equivalence_power.py', 'equivalence')

    panel, bags = m.load_bags()
    articles = pd.read_csv(m.P1 / 'article_to_stock_day_pilot.csv')
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    articles['model_text'] = articles['model_text'].fillna('')
    articles['text_hash'] = articles['model_text'].map(fingerprint)
    groups = articles.groupby(['Date', 'Symbol'])['text_hash'].agg(set).to_dict()
    bags['text_hashes'] = [groups.get((r.Date, r.Symbol), set()) for r in bags.itertuples()]
    articles = articles.dropna(subset=['Date'])

    with threadpool_limits(limits=1):
        raw, folds = run(m, panel, bags, articles)
    fresh = pd.read_csv(common.ROOT / 'results/purged_pilot/predictions.csv')
    if not calibration_driver.keyed(raw, 'actual').index.equals(calibration_driver.keyed(fresh, 'actual').index):
        raise ValueError('Near-duplicate run is not evaluated on the fresh-pilot stock-days')
    calibrated, warmup = calibration_driver.forward_calibrate(calibration, raw)
    raw.to_csv(out / 'predictions.csv', index=False)
    calibrated.to_csv(out / 'calibrated_predictions.csv', index=False)
    folds.to_csv(out / 'fold_manifest.csv', index=False)

    rows = inference(raw, 'near_dup_excluded_raw_all_blocks', 'prediction')
    rows += inference(calibrated, 'near_dup_excluded_calibrated_blocks_2_7', 'calibrated_prediction')
    result = pd.DataFrame(rows)
    result['decision_2pct_family'] = [equivalence.decision(r.holm_p, r.family_ci_low, r.family_ci_high, .02)
                                      for r in result.itertuples()]
    result.to_csv(out / 'inference.csv', index=False)

    cells = pd.read_csv(common.ROOT / 'results/factorial_ablation/predictions.csv')
    dispersion = (cells[cells.method != 'ZERO'].groupby(['cell', 'method']).prediction.std(ddof=1)
                  .rename('prediction_sd').reset_index())
    outcome_sd = float(cells.drop_duplicates(['Date', 'Symbol']).actual.std(ddof=1))
    dispersion['outcome_sd'] = outcome_sd
    dispersion.to_csv(out / 'prediction_dispersion.csv', index=False)

    primary = result[result.block_length == CONFIG['inference']['primary_block_length']]
    lines = [
        '# Near-Duplicate Exclusion Sensitivity and Prediction Dispersion',
        '',
        'Status: **EXPLORATORY SENSITIVITY — SAME PROVENANCE GATES AS THE PILOT**',
        '',
        f'Training bags holding an article with character n-gram cosine >= {THRESHOLD} to any test-block article '
        'are removed in addition to the 5-session purge and exact-overlap exclusion.',
        '',
        common.markdown(folds),
        '',
        common.markdown(primary[['analysis', 'competitor', 'relative_improvement', 'bootstrap_se',
                                 'family_ci_low', 'family_ci_high', 'holm_p', 'decision_2pct_family']]),
        '',
        f'## Prediction SD by factorial cell (outcome SD {outcome_sd:.6f})',
        '',
        common.markdown(dispersion.pivot(index='cell', columns='method', values='prediction_sd').reset_index()),
        '',
    ]
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, threshold=THRESHOLD, purge=PURGE, warmup_block=warmup,
                    near_duplicate_train_bags_removed=int(folds.near_duplicate_train_bags_removed.sum()))
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
