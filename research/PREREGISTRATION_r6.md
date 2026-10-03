# External Replication Protocol — FNSPID U.S. Banks

Status: **LOCKED BEFORE OUTCOME ANALYSIS** — frozen by `scripts/19_freeze_protocol.py`, which writes
the SHA-256 of this file and of every script the replication executes to
`research/PREREGISTRATION_FREEZE.json`. Scripts 20 and 21 refuse to run if any hash differs.

This is a local lock. It is not a public registration; the author may register this file
(for example on OSF) before submission, with the freeze record as evidence of the order of work.

## 1. What had been seen before the lock

- The FNSPID file listing and sizes, the price-file schema, the list of tickers present, and the
  first and last price date of each candidate ticker. No price level, return, volume value, or news
  text was examined.
- The news-file schema and per-ticker article counts and date ranges (inspected after download,
  before freezing, by `20_fnspid_prepare.py --inspect`, which reads no prices; the output is
  `research/FNSPID_INSPECTION.json`). Result: bank news in `All_external.csv` ends on 2020-06-11, so
  the window rule selects 2017-06-12 to 2020-06-11, with 8,066 articles for seven banks; TFC has no
  news in the file and therefore contributes no text bags. JPM news starts on 2018-09-15.
- While checking the schema, the first 1,500 bytes of the news file were displayed: seven headlines
  about ticker A (Agilent), not a bank. They showed that the recorded "UTC" times can precede the
  events a headline describes (a list of Friday's 52-week highs stamped 06:30 UTC on that Friday),
  so the recorded times may lag true publication by several hours. The next-session mapping remains
  safe as long as that lag is below 9.5 hours; this cannot be verified from the file.
- Nothing from any FNSPID return, label, or model output.

The Thai results, the method, and every design choice below were fixed on the Thai data, which were
fully inspected during development. This replication is the first use of FNSPID in the project.

## 2. Data

- Source: Dong, Fan and Peng (2024), FNSPID, CC BY 4.0. News `Stock_news/All_external.csv`;
  prices `Stock_price/full_history.zip`.
- Universe (fixed by price availability only): JPM, WFC, C, USB, PNC, COF, BK, TFC — eight large
  U.S. banks with prices through 2023-12-28. BAC was excluded because its price file ends on
  2020-07-02. Market proxy: SPY.
- Window: T_end = the earlier of the last price date common to all nine series and the last news
  date for the eight banks; the window is the 36 months ending at T_end, matching the Thai design.
- News text: `Article_title` followed by `Lsa_summary` when present. Deduplication on
  (date, symbol, title, URL). Language English.
- Timing: each article is mapped to the first trading session strictly after its recorded calendar
  date, as in the Thai pilot. Under UTC or U.S. Eastern recording this cannot place an article after
  the 09:30 ET open of its mapped session.

## 3. Features and labels (identical procedure to the Thai pilot)

Features, computed on the full price history and then restricted to the window:
log_ret = log(C_t / C_{t-1}); vol_5d, vol_22d = rolling standard deviation (ddof 1) of log_ret;
mom_5d, mom_22d = log(C_t / C_{t-k}); hl_range = (H - L) / C; turnover_rel = V / rolling 60-day mean V;
beta_60d = rolling 60-day covariance of log_ret with SPY log return over its variance;
set_ret = SPY log return; set_vol_22d = rolling 22-day standard deviation of set_ret.
These formulas reproduce the Thai panel features to about 1e-9 for all features except beta_60d
(correlation 0.98), set_ret and set_vol_22d (0.9997), whose original construction is undocumented.

Labels: the frozen Thai label builder `provenance/source_code/01_build_pilot_labels.py`, unchanged,
with the panel and news paths pointed at the FNSPID-derived files. Target: same-day open-to-close
log return. Validity: positive, coherent OHLC and positive volume.

## 4. Evaluation design (identical to the fresh pilot)

- Seven quarterly test blocks. The first starts on the first day of the month at or after the window
  start plus 15 months; blocks advance by three months, and the last block ends at the window end.
  With the inspected window this gives blocks starting 2018-10-01 through 2020-04-01. Empty blocks
  are skipped and recorded. If the earliest fold has fewer than 100 retained or 100 ordinary training
  examples, that block is dropped and the rule is applied again to the next block; the number of
  blocks may then fall below seven, and the count is reported.
- Expanding training window, five-session purge, exact normalized-text overlap exclusion.
- Learners, seeds, vectorizer, and loss: those of `02_purged_pilot.py`, reused through
  `13_factorial_ablation.train_config` and `16_rdfl_component_ablation.run`.
- Calibrated arm: the archived P2c calibrator, first block as warm-up.
- Inference: equal-date weighting, circular moving-block bootstrap, 10,000 draws, block length 20
  primary, 10 and 40 sensitivity; Holm within each family; family interval 97.5% for four comparators.
- Decision categories and the ±2% margin exactly as in Section II.G of the manuscript.

## 5. Hypotheses and decision rules

Each hypothesis is read at block length 20 and classified as **replicated**, **partially
replicated**, **not replicated**, or **inconclusive**.

| ID | Hypothesis (from the Thai results) | Replicated if | Partially replicated if | Not replicated if |
|---|---|---|---|---|
| H1a | Uncalibrated RDFL_SOFT is worse than ZERO beyond the margin | decision = worse beyond margin | Holm p < 0.05 with RDFL worse, interval not wholly beyond −2% | equivalent within margin or RDFL better |
| H1b | Same against DIRECT_HUBER | as H1a | as H1a | as H1a |
| H1c | Same against ORDINARY_SOFT | as H1a | as H1a | as H1a |
| H2 | Uncalibrated RDFL_SOFT beats HARD_RDFL | Holm p < 0.05 and RDFL better | — | Holm p < 0.05 and RDFL worse |
| H3a | Replacing the RDFL label rule by the ordinary rule (retained, confidence) lowers loss | family-interval lower bound > 0 | point estimate > 0 | upper bound < 0 |
| H3b | Random size-matched selection beats confidence-based selection | as H3a | as H3a | as H3a |
| H4 | Forward-calibrated RDFL_SOFT is within ±2% of ZERO | decision = equivalent within margin | — | worse or better beyond margin |

Anything not meeting a listed condition is inconclusive. The contrasts H3a and H3b form one family
of two (97.5% family interval). All other quantities reported are secondary and descriptive.

## 6. Reporting commitments

- All seven hypotheses are reported whatever their outcome, in the manuscript and in
  `results/fnspid_replication/HYPOTHESES.md`.
- Any deviation from this protocol after the freeze is recorded in section 7 with its reason and
  whether it was made before or after outcomes were seen.
- The replication is external in market, language, and period; a failure to replicate is a result,
  not a reason to change the Thai analysis.

## 7. Deviations

None at the time of freezing.
