# External Replication on FNSPID U.S. Banks

Protocol frozen 2026-09-28T07:27:01.946114+00:00; run once after the freeze.

## Hypotheses (block length 20)

| hypothesis | statement | estimate | interval_low | interval_high | holm_p | decision | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1a | uncalibrated RDFL worse than ZERO beyond ±2% | -0.078743 | -0.209823 | -0.025478 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN | replicated |
| H1b | uncalibrated RDFL worse than DIRECT_HUBER beyond ±2% | -0.0700189 | -0.178758 | -0.0243435 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN | replicated |
| H1c | uncalibrated RDFL worse than ORDINARY_SOFT beyond ±2% | -0.0672037 | -0.16611 | -0.0249961 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN | replicated |
| H2 | uncalibrated RDFL beats HARD_RDFL | 0.0107318 | 0.00389052 | 0.0244363 | 0.00039996 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN | replicated |
| H3a | ordinary label rule lowers loss | 0.0507727 | 0.0240635 | 0.102222 | 0.00019998 |  | replicated |
| H3b | random size-matched selection beats confidence selection | 0.030132 | 0.0108511 | 0.0694318 | 0.00039996 |  | replicated |
| H4 | calibrated RDFL within ±2% of ZERO | -0.01477 | -0.0558346 | 0.00156507 | 0.293671 | INCONCLUSIVE | inconclusive |

## Paired inference

| analysis | competitor | relative_improvement | family_ci_low | family_ci_high | holm_p | decision_2pct_family |
| --- | --- | --- | --- | --- | --- | --- |
| uncalibrated | ZERO | -0.078743 | -0.209823 | -0.025478 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN |
| uncalibrated | DIRECT_HUBER | -0.0700189 | -0.178758 | -0.0243435 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN |
| uncalibrated | ORDINARY_SOFT | -0.0672037 | -0.16611 | -0.0249961 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN |
| uncalibrated | HARD_RDFL | 0.0107318 | 0.00389052 | 0.0244363 | 0.00039996 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN |
| calibrated | ZERO | -0.01477 | -0.0558346 | 0.00156507 | 0.293671 | INCONCLUSIVE |
| calibrated | DIRECT_HUBER | 0.00392291 | -3.2785e-05 | 0.0126087 | 0.175582 | EQUIVALENT_WITHIN_MARGIN |
| calibrated | ORDINARY_SOFT | -0.000547288 | -0.00480946 | 0.00311188 | 0.674533 | EQUIVALENT_WITHIN_MARGIN |
| calibrated | HARD_RDFL | -0.000950099 | -0.00394519 | 0.000134034 | 0.294171 | EQUIVALENT_WITHIN_MARGIN |

## Component contrasts

| contrast | relative_improvement | family_ci_low | family_ci_high | holm_p |
| --- | --- | --- | --- | --- |
| label_rule_ordinary | 0.0507727 | 0.0240635 | 0.102222 | 0.00019998 |
| random_selection_same_size | 0.030132 | 0.0108511 | 0.0694318 | 0.00039996 |

## Descriptives

- window: ['2017-06-12', '2020-06-11']
- blocks_dropped_by_rule: 0
- evaluated_blocks: 7
- evaluation_dates: 426
- evaluation_stock_days: 1874
- calibration_warmup_block: 2018-10-01
- articles_mapped: 8080
- text_bags: 2793
- retained_labels: 1656
- label_counts: {'LOW_RESPONSE': 714, 'NEGATIVE': 483, 'POSITIVE': 459}
- low_response_bags_with_2plus_articles: 0.5266106442577031
- prediction_sd_uncalibrated: {'DIRECT_HUBER': 0.0015537891525103644, 'HARD_RDFL': 0.004772140162398522, 'ORDINARY_SOFT': 0.0014825938047611773, 'RDFL_SOFT': 0.004490896263421028}
- prediction_sd_calibrated: {'DIRECT_HUBER': 0.0015013487654801884, 'HARD_RDFL': 0.0011927005135401578, 'ORDINARY_SOFT': 0.001243042618418029, 'RDFL_SOFT': 0.0012569599146441603}
- outcome_sd: 0.01970335531125328
- protocol_frozen_utc: 2026-09-28T07:27:01.946114+00:00
