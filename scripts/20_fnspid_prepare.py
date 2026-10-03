"""Prepare FNSPID U.S. bank data in the Thai pilot format and build RDFL labels.

Follows research/PREREGISTRATION_r6.md. Two modes:

--inspect  Reads only the news file's symbol and date columns and the price files'
           date columns: per-ticker article counts and date ranges, and the window
           that the protocol's rule selects. No price, return, or text is examined.
           Allowed before the protocol is frozen.
(default)  Refuses to run unless the protocol freeze matches. Writes Thai-format
           price panels and a news file, then runs the frozen Thai label builder
           (provenance/source_code/01_build_pilot_labels.py) unchanged on them.
"""
from __future__ import annotations

import argparse
import io
import json
import zipfile

import numpy as np
import pandas as pd

import common

SOURCE = common.ROOT / 'external' / 'fnspid'
UNIVERSE = ['JPM', 'WFC', 'C', 'USB', 'PNC', 'COF', 'BK', 'TFC']
MARKET = 'SPY'
WINDOW_MONTHS = 36
NEWS_COLUMNS = ['Date', 'Article_title', 'Stock_symbol', 'Url', 'Publisher', 'Lsa_summary']
FREEZE = common.ROOT / 'research' / 'PREREGISTRATION_FREEZE.json'


def verify_freeze():
    if not FREEZE.exists():
        raise RuntimeError('Protocol is not frozen; run 19_freeze_protocol.py first')
    record = json.loads(FREEZE.read_text(encoding='utf-8'))
    for relative, expected in record['sha256'].items():
        if common.sha(common.ROOT / relative) != expected:
            raise RuntimeError(f'Frozen file changed after the lock: {relative}')
    return record


def read_prices(symbol, columns=None):
    with zipfile.ZipFile(SOURCE / 'full_history.zip') as archive:
        name = next(n for n in archive.namelist()
                    if n.startswith('full_history/') and n.split('/')[-1].upper() == f'{symbol}.CSV')
        frame = pd.read_csv(io.BytesIO(archive.read(name)), usecols=columns)
    frame.columns = [c.lower() for c in frame.columns]
    frame['date'] = pd.to_datetime(frame['date'])
    return frame.sort_values('date').drop_duplicates('date', keep='first').reset_index(drop=True)


def read_news(columns):
    parts = []
    for chunk in pd.read_csv(SOURCE / 'All_external.csv', usecols=columns, chunksize=500_000,
                             dtype=str, on_bad_lines='skip', engine='c'):
        chunk = chunk[chunk['Stock_symbol'].str.upper().isin(UNIVERSE)]
        if len(chunk):
            parts.append(chunk)
    news = pd.concat(parts, ignore_index=True)
    news['Stock_symbol'] = news['Stock_symbol'].str.upper()
    news['stamp'] = pd.to_datetime(news['Date'].str.replace(' UTC', '', regex=False), errors='coerce')
    return news.dropna(subset=['stamp'])


def window(news):
    price_end = min(read_prices(s, ['date'])['date'].max() for s in UNIVERSE + [MARKET])
    news_end = news['stamp'].max().normalize()
    end = min(price_end, news_end)
    start = end - pd.DateOffset(months=WINDOW_MONTHS) + pd.Timedelta(days=1)
    return start, end, price_end, news_end


def features(frame, market):
    frame = frame.merge(market, on='date', how='left', validate='one_to_one')
    close = frame['close']
    frame['log_ret'] = np.log(close / close.shift(1))
    frame['vol_5d'] = frame['log_ret'].rolling(5).std(ddof=1)
    frame['vol_22d'] = frame['log_ret'].rolling(22).std(ddof=1)
    frame['mom_5d'] = np.log(close / close.shift(5))
    frame['mom_22d'] = np.log(close / close.shift(22))
    frame['hl_range'] = (frame['high'] - frame['low']) / close
    frame['turnover_rel'] = frame['volume'] / frame['volume'].rolling(60).mean()
    frame['beta_60d'] = frame['log_ret'].rolling(60).cov(frame['set_ret']) / frame['set_ret'].rolling(60).var()
    return frame


def inspect():
    news = read_news(['Date', 'Stock_symbol'])
    start, end, price_end, news_end = window(news)
    inside = news[(news.stamp >= start) & (news.stamp <= end + pd.Timedelta(days=1))]
    counts = inside.groupby('Stock_symbol').agg(articles=('stamp', 'size'), first=('stamp', 'min'), last=('stamp', 'max'))
    report = {'price_end': str(price_end.date()), 'news_end': str(news_end.date()),
              'window_start': str(start.date()), 'window_end': str(end.date()),
              'articles_in_window': int(len(inside)), 'per_ticker': counts.astype(str).to_dict(orient='index'),
              'all_time_articles_per_ticker': news.Stock_symbol.value_counts().to_dict()}
    out = common.ROOT / 'research' / 'FNSPID_INSPECTION.json'
    common.dump(out, report)
    print(json.dumps(report, indent=2, default=str))


def prepare():
    record = verify_freeze()
    out = common.start_run('fnspid_prepared')
    news = read_news(NEWS_COLUMNS)
    start, end, price_end, news_end = window(news)
    financial = out / 'financial'
    financial.mkdir(parents=True, exist_ok=True)
    spy = read_prices(MARKET)[['date', 'close']].rename(columns={'close': 'market_close'})
    spy['set_ret'] = np.log(spy['market_close'] / spy['market_close'].shift(1))
    spy['set_vol_22d'] = spy['set_ret'].rolling(22).std(ddof=1)
    rows = {}
    for symbol in UNIVERSE:
        panel = features(read_prices(symbol), spy[['date', 'set_ret', 'set_vol_22d']])
        panel = panel[(panel['date'] >= start) & (panel['date'] <= end)].copy()
        panel = panel.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low',
                                      'close': 'Close', 'volume': 'Volume'})
        panel.insert(1, 'Symbol', symbol)
        panel['Date'] = panel['Date'].dt.strftime('%Y-%m-%d')
        panel.to_csv(financial / f'panel_{symbol}.csv', index=False)
        rows[symbol] = len(panel)

    news = news[(news.stamp >= start - pd.Timedelta(days=30)) & (news.stamp <= end)].copy()
    summary = news['Lsa_summary'].fillna('').astype(str).replace({'nan': ''})
    thai_format = pd.DataFrame({
        'Date': news['stamp'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'Symbol': news['Stock_symbol'], 'Source': news['Publisher'].fillna('unknown'),
        'Language': 'en', 'Headline': news['Article_title'].fillna(''), 'Description': summary,
        'Text': '', 'URL': news['Url'].fillna(''),
    })
    news_path = out / 'news.csv'
    thai_format.to_csv(news_path, index=False)

    builder = common.load_legacy('01_build_pilot_labels.py')
    builder.SYMBOLS = UNIVERSE
    builder.RAW = out
    builder.FIN_DIR = financial
    builder.NEWS_PATH = news_path
    builder.OUT = out / 'p1_labels'
    builder.main()
    common.complete(out, window_start=str(start.date()), window_end=str(end.date()),
                    price_end=str(price_end.date()), news_end=str(news_end.date()),
                    panel_rows=rows, news_rows=len(thai_format), freeze_utc=record['frozen_utc'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inspect', action='store_true')
    inspect() if parser.parse_args().inspect else prepare()
