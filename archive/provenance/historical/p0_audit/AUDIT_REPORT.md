# FPA-PhaFin Phase P0 Data Audit

Generated (UTC): 2026-09-17T17:24:35.612056+00:00
Protocol status: **BLOCKED_FOR_CONFIRMATORY_RUN**

No model was fitted in Phase P0. Raw inputs were read-only.

## Gate decisions

| Gate | Status | Evidence |
|---|---|---|
| P0.1 raw inputs readable and expected symbols present | PASS | news_rows=11440; financial_files=8; symbols=['BAY', 'BBL', 'KBANK', 'KKP', 'KTB', 'SCB', 'TISCO', 'TTB'] |
| P0.2 duplicate policy can be applied | ACTION_REQUIRED | excess_exact_key_duplicates=1824 |
| P0.3 publication timezone and availability verified | BLOCKED | CSV Date has no timezone/ingestion fields; verify source-level timezone before cutoff mapping. |
| P0.4 official trading calendar and zero-volume semantics verified | BLOCKED | zero_volume_rows=448; official_calendar_in_bundle=False |
| P0.5 price adjustment and corporate actions verified | BLOCKED | Adjusted/unadjusted OHLC and corporate-action metadata are not identified in the supplied panel. |
| P0.6 model checkpoint identity corrected | ACTION_REQUIRED | config.py points to airesearch/wangchanberta-base-att-spm-uncased; manuscript name must match. |

## Reproducible counts

- News records: 11,440
- Unique non-missing URLs: 8,717
- Excess exact-key duplicates: 1,824
- Missing descriptions: 6,565
- Literal `nan` tokens in Text: 1,859
- Financial rows: 5,824
- Zero-volume rows: 448
- Date range: 2023-04-24T00:00:00 to 2026-04-24T00:00:00

## Source timing summary

| source | rows | unique_urls | invalid_dates | midnight_timestamps | midnight_fraction_valid | missing_description | missing_url |
|---|---|---|---|---|---|---|---|
| BangkokPost | 167 | 164 | 0 | 167 | 1.0 | 0 | 0 |
| Kaohoon | 4408 | 3733 | 0 | 0 | 0.0 | 0 | 0 |
| NationThailand | 168 | 160 | 0 | 0 | 0.0 | 0 | 0 |
| Reuters | 132 | 112 | 0 | 0 | 0.0 | 0 | 0 |
| SET | 1651 | 1651 | 0 | 0 | 0.0 | 1651 | 0 |
| Settrade | 3055 | 3037 | 0 | 0 | 0.0 | 3055 | 0 |
| Thunhoon | 1859 | 1696 | 0 | 0 | 0.0 | 1859 | 0 |

## Financial-file summary

| file | symbol_in_file | symbol_values | rows | date_min | date_max | invalid_dates | duplicate_dates | missing_required_columns | missing_ohlcv_cells | zero_volume | negative_volume | invalid_ohlc_rows | non_monotonic_dates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| panel_BAY.csv | BAY | BAY | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 60 | 0 | 6 | False |
| panel_BBL.csv | BBL | BBL | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 58 | 0 | 4 | False |
| panel_KBANK.csv | KBANK | KBANK | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 76 | 0 | 2 | False |
| panel_KKP.csv | KKP | KKP | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 44 | 0 | 0 | False |
| panel_KTB.csv | KTB | KTB | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 40 | 0 | 0 | False |
| panel_SCB.csv | SCB | SCB | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 49 | 0 | 1 | False |
| panel_TISCO.csv | TISCO | TISCO | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 62 | 0 | 1 | False |
| panel_TTB.csv | TTB | TTB | 728 | 2023-04-24T00:00:00 | 2026-04-24T00:00:00 | 0 | 0 |  | 0 | 59 | 0 | 2 | False |

## Decision

The supplied data are sufficient to continue engineering and a non-confirmatory pilot after the listed actions. The main confirmatory experiment remains blocked until timestamp availability, the trading calendar, and price adjustment are resolved.
