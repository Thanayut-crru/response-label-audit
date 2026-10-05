"""Flow of Thai data units from news records to evaluated stock-days (revision analysis, entry 7).

The 2026-10-05 review asked for the path from articles to evaluated stock-days, with non-overlapping
counts, and for missing-description and literal-"nan" rates by stock and period. Counts come from
the P0 audit, the P1 article map and stock-day labels, the text bags built exactly as in the pilot
(04_run_tfidf_label_methods.load_bags), and the pilot's saved predictions. Only counts are written.
"""
import json

import numpy as np
import pandas as pd

import common

RESULTS = common.ROOT / 'results'
P1 = common.ROOT / 'provenance/historical/p1_pilot_labels'


def blank(series):
    text = series.fillna('').astype(str).str.strip()
    return text.eq('') | text.str.casefold().eq('nan')


def main():
    out = common.start_run('data_flow')
    audit = json.loads((common.ROOT / 'provenance/historical/p0_audit/audit.json').read_text(encoding='utf-8'))
    news = audit['news']
    m = common.load_legacy('04_run_tfidf_label_methods.py')
    m.P1 = P1
    panel, bags = m.load_bags()
    articles = pd.read_csv(P1 / 'article_to_stock_day_pilot.csv', low_memory=False)
    articles['decision_date'] = pd.to_datetime(articles.decision_date, errors='coerce')
    articles['model_text'] = articles.model_text.fillna('').astype(str).str.strip()
    pilot = pd.read_csv(RESULTS / 'purged_pilot/predictions.csv')
    evaluated = pilot[pilot.method == 'ZERO']

    mapped = articles[articles.decision_date.notna()]
    with_text = mapped[mapped.model_text.ne('')]
    keyed = with_text.merge(panel[['Date', 'Symbol', 'outcome_data_valid', 'target_open_close']],
                            left_on=['decision_date', 'Symbol'], right_on=['Date', 'Symbol'], how='left')
    usable = keyed.outcome_data_valid.fillna(False).astype(bool) & np.isfinite(
        pd.to_numeric(keyed.target_open_close, errors='coerce'))
    eligible = bags[np.isfinite(bags[['residual_z', 'volume_deviation']].to_numpy(float)).all(axis=1)]
    retained = bags[bags.retain_for_text_training]
    first_test = pd.Timestamp(m.OUTER_STARTS[0])
    flow = [
        ('news records in the source file', news['rows'], 'records'),
        ('exact duplicates removed (date, stock, headline, URL)', -news['duplicate_rows_after_first_by_date_symbol_headline_url'], 'records'),
        ('unique articles', len(articles), 'articles'),
        ('not mapped to an observed trading session (after the last price date)', -int(articles.decision_date.isna().sum()), 'articles'),
        ('articles mapped to a stock and trading session', len(mapped), 'articles'),
        ('mapped articles with empty text', -int(mapped.model_text.eq('').sum()), 'articles'),
        ('mapped to a session without a valid outcome (zero-volume or invalid row)', -int((~usable).sum()), 'articles'),
        ('articles in stock-day text bags', int(usable.sum()), 'articles'),
        ('stock-day text bags (one per stock and session)', len(bags), 'stock-days'),
        ('bags whose RDFL label is defined (eligible)', len(eligible), 'stock-days'),
        ('bags retained for RDFL training (confidence >= 0.70)', len(retained), 'stock-days'),
        (f'bags in the seven test blocks from {first_test.date()} (evaluated)', len(evaluated), 'stock-days'),
        ('evaluation dates', int(evaluated.Date.nunique()), 'dates'),
    ]
    flow = pd.DataFrame(flow, columns=['step', 'count', 'unit'])
    flow.to_csv(out / 'flow.csv', index=False)

    articles['year'] = pd.to_datetime(articles.published_date, errors='coerce').dt.year
    articles['missing_description'] = blank(articles.Description)
    articles['headline_only_text'] = articles.missing_description
    by_stock = articles.groupby('Symbol').agg(articles=('article_id', 'size'),
                                              missing_description=('missing_description', 'mean')).reset_index()
    by_year = articles.groupby('year').agg(articles=('article_id', 'size'),
                                           missing_description=('missing_description', 'mean')).reset_index()
    by_source = articles.groupby(['Source', 'Language']).agg(articles=('article_id', 'size'),
                                                             missing_description=('missing_description', 'mean')).reset_index()
    by_stock.to_csv(out / 'missing_description_by_stock.csv', index=False)
    by_year.to_csv(out / 'missing_description_by_year.csv', index=False)
    by_source.to_csv(out / 'articles_by_source.csv', index=False)

    urls = articles.groupby('URL').Symbol.nunique()
    per_date = evaluated.groupby('Date').Symbol.nunique()
    weights = (1 / evaluated.Date.map(per_date)) / evaluated.Date.nunique()
    facts = {
        'articles_with_one_stock_each': bool(articles.groupby('article_id').Symbol.nunique().max() == 1),
        'urls_mapped_to_more_than_one_stock': int((urls > 1).sum()),
        'stocks_per_evaluation_date': {'min': int(per_date.min()), 'median': float(per_date.median()),
                                       'max': int(per_date.max())},
        'stock_day_weight_range_relative_to_equal': [float(weights.min() * len(evaluated)),
                                                     float(weights.max() * len(evaluated))],
        'text_rule': "model_text = headline + description, with missing or literal 'nan' descriptions replaced by "
                     "an empty string before any split (01_build_pilot_labels.py)",
        'audit_literal_nan_in_text_field': news['literal_nan_in_text'],
        'audit_missing_description': news['missing_description'],
    }
    common.dump(out / 'facts.json', facts)
    lines = ['# Thai Data Flow', '', 'Status: **DESCRIPTIVE; REVISION ANALYSIS**', '',
             'Negative counts are removals; the other rows are the units remaining at that step.', '',
             common.markdown(flow), '', '## Missing descriptions by stock', '', common.markdown(by_stock), '',
             '## By year', '', common.markdown(by_year), '', '## By source', '', common.markdown(by_source), '',
             '## Facts', '', '```', json.dumps(facts, indent=1), '```']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    common.complete(out, steps=len(flow))
    print('\n'.join(lines).encode('ascii', 'replace').decode(), flush=True)


if __name__ == '__main__':
    main()
