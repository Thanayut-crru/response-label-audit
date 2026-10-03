# Provenance Checks

Status: **DIAGNOSTIC — NARROWS BUT DOES NOT CLOSE THE PROVENANCE GATES**

## Timing

| Source | articles | date_only_share | clock_median | share_clock_00_06 | share_clock_06_18 | share_clock_18_24 | min_gap_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BangkokPost | 167 | 1 | 0 | 1 | 0 | 0 | 1 |
| Kaohoon | 4405 | 0 | 9.53528 | 0.00113507 | 0.949149 | 0.0497162 | 1 |
| NationThailand | 168 | 0 | 14.9167 | 0.00595238 | 0.755952 | 0.238095 | 1 |
| Reuters | 132 | 0 | 7.19292 | 0.378788 | 0.55303 | 0.0681818 | 1 |
| SET | 1650 | 0 | 17.1167 | 0 | 0.730303 | 0.269697 | 1 |
| Settrade | 1364 | 0 | 12.5226 | 0.0146628 | 0.928886 | 0.0564516 | 1 |
| Thunhoon | 1708 | 0 | 13.1632 | 0.0316159 | 0.837822 | 0.130562 | 1 |

Articles that could reach ICT after the 09:00 decision time of their mapped session, by offset hypothesis:

| Source | ICT_UTC+7 | US_Eastern_daylight_UTC-4 | US_Eastern_standard_UTC-5 | UTC | UTC-3 |
| --- | --- | --- | --- | --- | --- |
| BangkokPost | 0 | 109 | 109 | 0 | 109 |
| Kaohoon | 0 | 25 | 44 | 0 | 8 |
| NationThailand | 0 | 2 | 9 | 0 | 2 |
| Reuters | 0 | 3 | 6 | 0 | 2 |
| SET | 0 | 6 | 45 | 0 | 0 |
| Settrade | 0 | 2 | 5 | 0 | 1 |
| Thunhoon | 0 | 19 | 64 | 0 | 5 |

## Calendar and price basis

- panel_rows: 5824
- weekdays_in_range: 785
- weekdays_without_any_row: 57
- missing_weekdays_on_fixed_date_holiday_or_substitute: 43
- all_stock_zero_volume_weekdays: 28
- zero_volume_weekdays_on_fixed_date_holiday_or_substitute: 3
- zero_volume_rows_by_year_month: {'2024-01': 2, '2024-03': 44, '2024-04': 41, '2024-05': 63, '2024-06': 50, '2024-07': 61, '2024-08': 44, '2024-09': 77, '2024-10': 56, '2024-11': 2, '2025-10': 8}
- dates_with_partial_zero_volume: 54
- zero_volume_rows: 448
- zero_volume_rows_with_open_equal_close: 448
- incoherent_ohlc_rows: 16
- evaluation_rows_on_zero_volume_or_incoherent_rows: 0
- evaluation_rows_without_panel_match: 0
- articles_mapped: 9594
- articles_mapped_to_zero_volume_or_incoherent_rows: 581

| year | rows | incoherent_rows | close_on_tick_grid | open_on_tick_grid | zero_volume_rows |
| --- | --- | --- | --- | --- | --- |
| 2023 | 1344 | 16 | 0 | 0 | 0 |
| 2024 | 1944 | 0 | 0 | 0 | 440 |
| 2025 | 1936 | 0 | 0.105372 | 0.100207 | 8 |
| 2026 | 600 | 0 | 0.468333 | 0.465 | 0 |

## Near-duplicates remaining after exact exclusion (fresh pilot folds)

| test_start | test_articles | train_articles | test_bags | median_max_similarity | articles_ge_80 | bags_with_article_ge_80 | articles_ge_90 | bags_with_article_ge_90 | articles_ge_95 | bags_with_article_ge_95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-08-01 | 485 | 2630 | 217 | 0.329966 | 88 | 58 | 41 | 27 | 27 | 20 |
| 2024-11-01 | 664 | 3116 | 305 | 0.333701 | 137 | 92 | 50 | 43 | 36 | 33 |
| 2025-02-01 | 755 | 3697 | 309 | 0.337524 | 139 | 99 | 69 | 59 | 44 | 38 |
| 2025-05-01 | 656 | 4292 | 297 | 0.37677 | 110 | 72 | 56 | 47 | 38 | 33 |
| 2025-08-01 | 973 | 4894 | 345 | 0.31484 | 123 | 79 | 70 | 52 | 38 | 31 |
| 2025-11-01 | 1039 | 5749 | 354 | 0.314725 | 129 | 86 | 67 | 56 | 39 | 35 |
| 2026-02-01 | 1468 | 6603 | 370 | 0.282445 | 172 | 118 | 94 | 78 | 54 | 47 |
