"""Are low-response labels concentrated on stale news?

Tetlock (2011) finds that returns respond less to stale news, measured by the
textual similarity of a story to the previous ten stories about the same firm.
If RDFL's LOW_RESPONSE labels fall disproportionately on stale news, a low
response has a second explanation besides cancellation: the information was
already known. This script measures an adapted staleness score and relates it
to the RDFL labels. It is descriptive and changes no prediction or inference.

Staleness of an article is the cosine similarity between its character 3-5-gram
TF-IDF vector and the normalized sum of the vectors of the previous ten articles
about the same stock. A bag's staleness is the mean over its articles. The
vectorizer is fitted on all articles because this is a diagnostic, not a
predictor. Uncertainty resamples evaluation dates, since bags on one date share
market conditions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

import common

CONFIG = common.CONFIG
WINDOW = 10
CORRELATION_DRAWS = 2000


def article_staleness(articles):
    articles = articles.copy()
    articles['stamp'] = pd.to_datetime(articles['published_raw'], errors='coerce')
    articles = articles.dropna(subset=['stamp', 'decision_date']).sort_values(['Symbol', 'stamp', 'source_row'])
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, sublinear_tf=True,
                                 norm='l2', dtype=np.float32, max_features=50000)
    matrix = vectorizer.fit_transform(articles['model_text'].fillna('').astype(str))
    score = np.full(len(articles), np.nan)
    positions = np.arange(len(articles))
    for _, index in articles.groupby('Symbol').indices.items():
        rows = positions[index]
        for k in range(1, len(rows)):
            previous = matrix[rows[max(0, k - WINDOW):k]]
            reference = normalize(np.asarray(previous.sum(axis=0)))
            score[rows[k]] = float(matrix[rows[k]].dot(reference.T)[0, 0])
    articles['staleness'] = score
    articles['previous_articles'] = articles.groupby('Symbol').cumcount().clip(upper=WINDOW)
    return articles


def date_bootstrap(frame, statistic, draws, seed):
    """Resample whole dates; `statistic` receives the resampled frame."""
    frame = frame.reset_index(drop=True)
    groups = list(frame.groupby('Date').indices.values())
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        chosen = rng.integers(0, len(groups), size=len(groups))
        values.append(statistic(frame.iloc[np.concatenate([groups[i] for i in chosen])]))
    return common.interval(np.asarray(values, dtype=float))


def main():
    out = common.start_run('staleness')
    root = common.ROOT / 'provenance/historical/p1_pilot_labels'
    articles = article_staleness(pd.read_csv(root / 'article_to_stock_day_pilot.csv', low_memory=False))
    articles.to_csv(out / 'article_staleness.csv', index=False,
                    columns=['article_id', 'Symbol', 'Source', 'stamp', 'decision_date', 'staleness', 'previous_articles'])
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    bags = (articles[articles.previous_articles >= 1].groupby(['Symbol', 'Date'])
            .agg(staleness=('staleness', 'mean'), articles=('article_id', 'size')).reset_index())

    panel = pd.read_csv(root / 'stock_day_labels_pilot.csv', low_memory=False)
    panel['Date'] = pd.to_datetime(panel['Date'])
    panel = panel[panel.outcome_data_valid.astype(str).str.lower().eq('true')]
    frame = bags.merge(panel[['Symbol', 'Date', 'weak_label', 'retain_for_text_training', 'residual_z',
                              'p_low_response']], on=['Symbol', 'Date'], how='inner', validate='one_to_one')
    frame['retained'] = frame.retain_for_text_training.astype(str).str.lower().eq('true')
    frame['abs_z'] = frame.residual_z.abs()
    frame.to_csv(out / 'bag_staleness.csv', index=False)

    iterations = int(CONFIG['inference']['bootstrap_iterations'])
    labeled = frame[frame.retained].copy()
    labeled['is_low'] = labeled.weak_label.eq('LOW_RESPONSE')

    def low_minus_directional(sample):
        return sample.loc[sample.is_low, 'staleness'].mean() - sample.loc[~sample.is_low, 'staleness'].mean()

    def spearman(column):
        return lambda sample: stats.spearmanr(sample['staleness'], sample[column]).statistic

    finite = frame[np.isfinite(frame.abs_z)]
    defined = frame[np.isfinite(frame.p_low_response)]
    results = {
        'bags_with_staleness': len(frame),
        'retained_labeled_bags': len(labeled),
        'mean_staleness_low_response': float(labeled.loc[labeled.is_low, 'staleness'].mean()),
        'mean_staleness_directional': float(labeled.loc[~labeled.is_low, 'staleness'].mean()),
        'difference_low_minus_directional': float(low_minus_directional(labeled)),
        'difference_ci95_date_bootstrap': date_bootstrap(labeled, low_minus_directional, iterations,
                                                         CONFIG['inference']['seed'] + 81),
        'spearman_staleness_abs_residual_z': float(stats.spearmanr(finite.staleness, finite.abs_z).statistic),
        'spearman_abs_z_ci95_date_bootstrap': date_bootstrap(finite, spearman('abs_z'), CORRELATION_DRAWS,
                                                             CONFIG['inference']['seed'] + 82),
        'spearman_staleness_p_low_response': float(stats.spearmanr(defined.staleness, defined.p_low_response).statistic),
        'spearman_p_low_ci95_date_bootstrap': date_bootstrap(defined, spearman('p_low_response'), CORRELATION_DRAWS,
                                                             CONFIG['inference']['seed'] + 83),
        'bootstrap': f'dates resampled; {iterations} draws for the mean difference, {CORRELATION_DRAWS} for correlations',
    }
    labeled['staleness_quintile'] = pd.qcut(labeled.staleness, 5, labels=[1, 2, 3, 4, 5])
    quintiles = (labeled.groupby('staleness_quintile', observed=True)
                 .agg(bags=('is_low', 'size'), share_low_response=('is_low', 'mean'),
                      mean_staleness=('staleness', 'mean')).reset_index())
    quintiles.to_csv(out / 'low_response_by_staleness_quintile.csv', index=False)
    common.dump(out / 'summary.json', results)
    lines = ['# Staleness of News and Low-Response Labels', '',
             'Status: **DESCRIPTIVE DIAGNOSTIC — ADAPTED FROM TETLOCK (2011)**', '',
             '\n'.join(f'- {k}: {v}' for k, v in results.items()), '',
             common.markdown(quintiles), '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, window=WINDOW, status='DESCRIPTIVE')
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
