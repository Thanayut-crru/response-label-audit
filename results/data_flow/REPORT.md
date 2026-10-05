# Thai Data Flow

Status: **DESCRIPTIVE; REVISION ANALYSIS**

Negative counts are removals; the other rows are the units remaining at that step.

| step | count | unit |
| --- | --- | --- |
| news records in the source file | 11440 | records |
| exact duplicates removed (date, stock, headline, URL) | -1824 | records |
| unique articles | 9616 | articles |
| not mapped to an observed trading session (after the last price date) | -22 | articles |
| articles mapped to a stock and trading session | 9594 | articles |
| mapped articles with empty text | 0 | articles |
| mapped to a session without a valid outcome (zero-volume or invalid row) | -581 | articles |
| articles in stock-day text bags | 9013 | articles |
| stock-day text bags (one per stock and session) | 3561 | stock-days |
| bags whose RDFL label is defined (eligible) | 2684 | stock-days |
| bags retained for RDFL training (confidence >= 0.70) | 1722 | stock-days |
| bags in the seven test blocks from 2024-08-01 (evaluated) | 2197 | stock-days |
| evaluation dates | 403 | dates |

## Missing descriptions by stock

| Symbol | articles | missing_description |
| --- | --- | --- |
| BAY | 578 | 0.622837 |
| BBL | 1650 | 0.404242 |
| KBANK | 921 | 0.800217 |
| KKP | 806 | 0.635236 |
| KTB | 1100 | 0.590909 |
| SCB | 1448 | 0.439227 |
| TISCO | 854 | 0.614754 |
| TTB | 2259 | 0.289509 |

## By year

| year | articles | missing_description |
| --- | --- | --- |
| 2023 | 1713 | 0.40397 |
| 2024 | 2656 | 0.377636 |
| 2025 | 3334 | 0.491302 |
| 2026 | 1913 | 0.736017 |

## By source

| Source | Language | articles | missing_description |
| --- | --- | --- | --- |
| BangkokPost | EN | 167 | 0 |
| Kaohoon | TH | 4408 | 0 |
| NationThailand | EN | 168 | 0 |
| Reuters | EN | 132 | 0 |
| SET | TH | 1651 | 1 |
| Settrade | TH | 1381 | 1 |
| Thunhoon | TH | 1709 | 1 |

## Facts

```
{
 "articles_with_one_stock_each": true,
 "urls_mapped_to_more_than_one_stock": 524,
 "stocks_per_evaluation_date": {
  "min": 1,
  "median": 5.0,
  "max": 8
 },
 "stock_day_weight_range_relative_to_equal": [
  0.6814516129032258,
  5.451612903225806
 ],
 "text_rule": "model_text = headline + description, with missing or literal 'nan' descriptions replaced by an empty string before any split (01_build_pilot_labels.py)",
 "audit_literal_nan_in_text_field": 1859,
 "audit_missing_description": 6565
}
```