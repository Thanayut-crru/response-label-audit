"""Checks of the empirical provenance gates that the local data can support.

The manuscript labels every real-data result retrospective and exploratory
because four gates are open: publication time and availability, the trading
calendar, price adjustment and corporate actions, and near-duplicate events.
None of them can be closed from the supplied files alone. This script measures
how far each gate can be narrowed with the data at hand, and records what
remains unverifiable. It changes no prediction, label, or inference.

1. Timing. Every article is mapped to the first observed trading date strictly
   after its recorded calendar date, and the declared decision time is 09:00 ICT.
   For a source recording local time with UTC offset o, an article recorded at
   clock time t on date L reaches ICT at L + t + (7 - o) hours, so it can arrive
   after the 09:00 ICT decision time of a session g days later only if
   t + 7 - o >= 24 g + 9. The script counts such articles under several offsets.
2. Calendar. Weekdays absent from the panel and weekday rows with zero volume
   are compared with fixed-date Thai holidays (lunar holidays are not encoded,
   so a non-match is not proof of a trading day); evaluation rows must be valid
   sessions, and articles mapped onto invalid rows are counted because they are
   dropped from the text bags.
3. Price basis. The target log(Close/Open) is taken within one row, so any
   multiplicative adjustment of the row cancels. Open, High, Low and Close must
   share one basis for this to hold; a mixed basis would violate
   Low <= Open, Close <= High on older rows.
4. Near-duplicates. For each fresh-pilot fold, the maximum character n-gram
   cosine similarity between each test article and any retained training
   article is reported. This detects near-verbatim reuse, not paraphrased
   coverage of the same event.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

import common

SYMBOLS = ['BAY', 'BBL', 'KBANK', 'KKP', 'KTB', 'SCB', 'TISCO', 'TTB']
DECISION_HOUR_ICT = 9.0
OFFSETS = {'ICT_UTC+7': 7, 'UTC': 0, 'UTC-3': -3, 'US_Eastern_daylight_UTC-4': -4, 'US_Eastern_standard_UTC-5': -5}
SIMILARITY_THRESHOLDS = [0.80, 0.90, 0.95]
# SET tick sizes by price band (THB), used only to show where prices are back-adjusted.
TICKS = [(2, .01), (5, .02), (10, .05), (25, .10), (100, .25), (200, .50), (400, 1.0), (np.inf, 2.0)]
FIXED_HOLIDAYS = {(1, 1), (4, 6), (4, 13), (4, 14), (4, 15), (5, 1), (5, 4), (6, 3), (7, 28),
                  (8, 12), (10, 13), (10, 23), (12, 5), (12, 10), (12, 31)}


def fingerprint(text):
    normalized = re.sub(r'\s+', ' ', str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def on_tick_grid(price):
    tick = next(size for bound, size in TICKS if price < bound)
    return bool(abs(price / tick - round(price / tick)) < 1e-6)


def timing(articles):
    articles = articles.copy()
    stamp = pd.to_datetime(articles['published_raw'], errors='coerce')
    articles['clock'] = stamp.dt.hour + stamp.dt.minute / 60 + stamp.dt.second / 3600
    articles['date_only'] = (stamp.dt.hour == 0) & (stamp.dt.minute == 0) & (stamp.dt.second == 0)
    articles['published_date'] = pd.to_datetime(articles['published_date'])
    articles['decision_date'] = pd.to_datetime(articles['decision_date'])
    mapped = articles.dropna(subset=['decision_date']).copy()
    if not (mapped['decision_date'] > mapped['published_date']).all():
        raise ValueError('An article is mapped to a session on or before its recorded date')
    mapped['gap_days'] = (mapped['decision_date'] - mapped['published_date']).dt.days
    # Date-only records could have been published at any clock time; bound them by the worst case.
    mapped['worst_clock'] = np.where(mapped['date_only'], 24.0, mapped['clock'])

    by_source = mapped.groupby('Source').agg(
        articles=('article_id', 'size'), date_only_share=('date_only', 'mean'),
        clock_median=('clock', 'median'),
        share_clock_00_06=('clock', lambda c: float(((c >= 0) & (c < 6)).mean())),
        share_clock_06_18=('clock', lambda c: float(((c >= 6) & (c < 18)).mean())),
        share_clock_18_24=('clock', lambda c: float((c >= 18).mean())),
        min_gap_days=('gap_days', 'min')).reset_index()

    scenarios = []
    for name, offset in OFFSETS.items():
        arrival = mapped['worst_clock'] + 7 - offset
        at_risk = arrival >= 24 * mapped['gap_days'] + DECISION_HOUR_ICT
        for source, group in mapped.assign(at_risk=at_risk).groupby('Source'):
            scenarios.append({'offset_hypothesis': name, 'utc_offset': offset, 'Source': source,
                              'articles': len(group), 'articles_possibly_after_decision_time': int(group.at_risk.sum())})
    return by_source, pd.DataFrame(scenarios), mapped


def calendar_and_prices(panels, evaluation):
    frame = pd.concat(panels, ignore_index=True)
    frame['Date'] = pd.to_datetime(frame['Date'])
    ohlc = frame[['Open', 'High', 'Low', 'Close']].apply(pd.to_numeric, errors='coerce')
    frame['coherent'] = ((ohlc['High'] + 1e-9 >= ohlc[['Open', 'Close', 'Low']].max(axis=1))
                         & (ohlc['Low'] - 1e-9 <= ohlc[['Open', 'Close', 'High']].min(axis=1)))
    frame['zero_volume'] = pd.to_numeric(frame['Volume'], errors='coerce').fillna(0) <= 0
    frame['open_eq_close'] = np.isclose(ohlc['Open'], ohlc['Close'])
    frame['close_on_grid'] = ohlc['Close'].map(on_tick_grid)
    frame['open_on_grid'] = ohlc['Open'].map(on_tick_grid)
    frame['year'] = frame['Date'].dt.year

    by_date = frame.groupby('Date').agg(stocks=('Symbol', 'nunique'), zero=('zero_volume', 'sum'))
    weekdays = pd.bdate_range(frame['Date'].min(), frame['Date'].max())
    missing_weekdays = weekdays.difference(by_date.index)
    closures = by_date[(by_date.zero == by_date.stocks) & (by_date.index.dayofweek < 5)].index
    partial = by_date[(by_date.zero > 0) & (by_date.zero < by_date.stocks)].index

    def fixed_or_substitute(day):
        if (day.month, day.day) in FIXED_HOLIDAYS:
            return True
        # Substitution: a Monday or Tuesday following a weekend holiday.
        for back in (1, 2, 3):
            earlier = day - pd.Timedelta(days=back)
            if earlier.dayofweek >= 5 and (earlier.month, earlier.day) in FIXED_HOLIDAYS:
                return True
        return False

    closure_table = pd.concat([
        pd.DataFrame({'Date': closures, 'kind': 'all_stock_zero_volume_row',
                      'fixed_date_holiday_or_substitute': [fixed_or_substitute(d) for d in closures]}),
        pd.DataFrame({'Date': missing_weekdays, 'kind': 'weekday_without_any_row',
                      'fixed_date_holiday_or_substitute': [fixed_or_substitute(d) for d in missing_weekdays]}),
    ], ignore_index=True).sort_values('Date')
    evaluation = evaluation.merge(frame[['Date', 'Symbol', 'zero_volume', 'coherent']],
                                  on=['Date', 'Symbol'], how='left', validate='many_to_one')
    price_basis = frame.groupby('year').agg(
        rows=('Symbol', 'size'), incoherent_rows=('coherent', lambda c: int((~c).sum())),
        close_on_tick_grid=('close_on_grid', 'mean'), open_on_tick_grid=('open_on_grid', 'mean'),
        zero_volume_rows=('zero_volume', 'sum')).reset_index()
    zero = frame[frame.zero_volume]
    kinds = closure_table.groupby('kind').fixed_date_holiday_or_substitute.sum()
    summary = {
        'panel_rows': len(frame), 'weekdays_in_range': len(weekdays),
        'weekdays_without_any_row': len(missing_weekdays),
        'missing_weekdays_on_fixed_date_holiday_or_substitute': int(kinds.get('weekday_without_any_row', 0)),
        'all_stock_zero_volume_weekdays': len(closures),
        'zero_volume_weekdays_on_fixed_date_holiday_or_substitute': int(kinds.get('all_stock_zero_volume_row', 0)),
        'zero_volume_rows_by_year_month': {str(k): int(v) for k, v in
                                           zero.groupby(zero.Date.dt.to_period('M')).size().items()},
        'dates_with_partial_zero_volume': len(partial),
        'zero_volume_rows': int(frame.zero_volume.sum()),
        'zero_volume_rows_with_open_equal_close': int(zero.open_eq_close.sum()),
        'incoherent_ohlc_rows': int((~frame.coherent).sum()),
        'evaluation_rows_on_zero_volume_or_incoherent_rows': int((evaluation.zero_volume | ~evaluation.coherent).sum()),
        'evaluation_rows_without_panel_match': int(evaluation.zero_volume.isna().sum()),
    }
    return summary, closure_table, price_basis, frame


def near_duplicates(articles, bags, folds):
    articles = articles.dropna(subset=['decision_date']).copy()
    articles['Date'] = pd.to_datetime(articles['decision_date'])
    articles['model_text'] = articles['model_text'].fillna('').astype(str).str.strip()
    articles = articles[articles['model_text'].ne('')]
    articles['text_hash'] = articles['model_text'].map(fingerprint)
    keys = bags[['Date', 'Symbol']].drop_duplicates()
    articles = articles.merge(keys, on=['Date', 'Symbol'], how='inner')
    bag_hashes = articles.groupby(['Date', 'Symbol'])['text_hash'].agg(set)
    rows = []
    for fold in folds.itertuples(index=False):
        start, stop = pd.Timestamp(fold.test_start), pd.Timestamp(fold.test_stop_exclusive)
        boundary = pd.Timestamp(fold.purge_start)
        test = articles[(articles.Date >= start) & (articles.Date < stop)]
        test_hashes = set(test.text_hash)
        train_keys = [k for k, hashes in bag_hashes.items() if k[0] < boundary and not (hashes & test_hashes)]
        train = articles.set_index(['Date', 'Symbol']).loc[train_keys].reset_index()
        vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=1, sublinear_tf=True,
                                     norm='l2', dtype=np.float32, max_features=200000)
        vectorizer.fit(pd.concat([train.model_text, test.model_text]))
        similarity = (vectorizer.transform(test.model_text) @ vectorizer.transform(train.model_text).T).max(axis=1)
        best = np.asarray(similarity.todense()).ravel()
        test = test.assign(max_similarity=best)
        bag_max = test.groupby(['Date', 'Symbol']).max_similarity.max()
        row = {'test_start': fold.test_start, 'test_articles': len(test), 'train_articles': len(train),
               'test_bags': len(bag_max), 'median_max_similarity': float(np.median(best))}
        for threshold in SIMILARITY_THRESHOLDS:
            tag = f'{int(round(threshold * 100))}'
            row[f'articles_ge_{tag}'] = int((best >= threshold).sum())
            row[f'bags_with_article_ge_{tag}'] = int((bag_max >= threshold).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    out = common.start_run('provenance_checks')
    articles = pd.read_csv(common.ROOT / 'provenance/historical/p1_pilot_labels/article_to_stock_day_pilot.csv',
                           low_memory=False)
    by_source, scenarios, _ = timing(articles)
    by_source.to_csv(out / 'timing_by_source.csv', index=False)
    scenarios.to_csv(out / 'timezone_scenarios.csv', index=False)

    panels = [pd.read_csv(common.ROOT / f'provenance/supplement/raw_financial/panel_{s}.csv', low_memory=False)
              .assign(Symbol=s) for s in SYMBOLS]
    evaluation = pd.read_csv(common.ROOT / 'results/purged_pilot/predictions.csv')
    evaluation = evaluation[evaluation.method == 'RDFL_SOFT'][['Date', 'Symbol']].copy()
    evaluation['Date'] = pd.to_datetime(evaluation['Date'])
    calendar, closures, price_basis, frame = calendar_and_prices(panels, evaluation)
    mapped = articles.dropna(subset=['decision_date']).assign(Date=lambda a: pd.to_datetime(a.decision_date))
    mapped = mapped.merge(frame[['Date', 'Symbol', 'zero_volume', 'coherent']], on=['Date', 'Symbol'],
                          how='left', validate='many_to_one')
    calendar['articles_mapped'] = len(mapped)
    if mapped.zero_volume.isna().any():
        raise ValueError('An article is mapped to a date absent from the raw panel')
    invalid = mapped.zero_volume.astype(bool) | ~mapped.coherent.astype(bool)
    calendar['articles_mapped_to_zero_volume_or_incoherent_rows'] = int(invalid.sum())
    closures.to_csv(out / 'calendar_exceptions.csv', index=False)
    price_basis.to_csv(out / 'price_basis_by_year.csv', index=False)

    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = common.ROOT / 'provenance/historical/p1_pilot_labels'
    _, bags = m.load_bags()
    folds = pd.read_csv(common.ROOT / 'results/purged_pilot/fold_manifest.csv')
    duplicates = near_duplicates(articles, bags, folds)
    duplicates.to_csv(out / 'near_duplicates_by_fold.csv', index=False)

    totals = scenarios.groupby('offset_hypothesis').articles_possibly_after_decision_time.sum().to_dict()
    dup_total = {c: int(duplicates[c].sum()) for c in duplicates.columns if c.startswith(('articles_ge', 'bags_with'))}
    common.dump(out / 'summary.json', {
        'timing_articles_possibly_after_decision_time_by_offset': {k: int(v) for k, v in totals.items()},
        'calendar_and_price_basis': calendar,
        'near_duplicates_total_over_folds': dup_total,
        'test_articles_total': int(duplicates.test_articles.sum()),
        'test_bags_total': int(duplicates.test_bags.sum()),
        'gates_still_open': [
            'recorded timestamps are not verified as first-availability times (backdating cannot be excluded)',
            'source time zones are inferred from clock-time distributions, not documented',
            'the trading calendar is not matched to an official SET calendar',
            'zero-volume rows with Open equal to Close cluster in March-October 2024 and look like source gaps, '
            'not closures; their cause is undocumented',
            'the adjustment vendor, date, and method (multiplicative or additive) are undocumented',
            'paraphrased coverage of the same event across outlets is not detected by n-gram similarity',
        ]})
    lines = [
        '# Provenance Checks',
        '',
        'Status: **DIAGNOSTIC — NARROWS BUT DOES NOT CLOSE THE PROVENANCE GATES**',
        '',
        '## Timing',
        '',
        common.markdown(by_source),
        '',
        'Articles that could reach ICT after the 09:00 decision time of their mapped session, by offset hypothesis:',
        '',
        common.markdown(scenarios.pivot(index='Source', columns='offset_hypothesis',
                                        values='articles_possibly_after_decision_time').reset_index()),
        '',
        '## Calendar and price basis',
        '',
        '\n'.join(f'- {k}: {v}' for k, v in calendar.items()),
        '',
        common.markdown(price_basis),
        '',
        '## Near-duplicates remaining after exact exclusion (fresh pilot folds)',
        '',
        common.markdown(duplicates),
        '',
    ]
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, status='DIAGNOSTIC_ONLY', decision_hour_ict=DECISION_HOUR_ICT,
                    similarity_thresholds=SIMILARITY_THRESHOLDS)
    print((out / 'REPORT.md').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
