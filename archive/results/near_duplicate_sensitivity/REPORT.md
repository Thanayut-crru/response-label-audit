# Near-Duplicate Exclusion Sensitivity and Prediction Dispersion

Status: **EXPLORATORY SENSITIVITY — SAME PROVENANCE GATES AS THE PILOT**

Training bags holding an article with character n-gram cosine >= 0.9 to any test-block article are removed in addition to the 5-session purge and exact-overlap exclusion.

| test_start | train_bags | test_bags | exact_overlap_train_bags_removed | near_duplicate_train_bags_removed |
| --- | --- | --- | --- | --- |
| 2024-08-01 | 1196 | 217 | 61 | 74 |
| 2024-11-01 | 1398 | 305 | 85 | 77 |
| 2025-02-01 | 1649 | 309 | 112 | 95 |
| 2025-05-01 | 1932 | 297 | 142 | 92 |
| 2025-08-01 | 2201 | 345 | 158 | 110 |
| 2025-11-01 | 2454 | 354 | 195 | 164 |
| 2026-02-01 | 2745 | 370 | 234 | 183 |

| analysis | competitor | relative_improvement | bootstrap_se | family_ci_low | family_ci_high | holm_p | decision_2pct_family |
| --- | --- | --- | --- | --- | --- | --- | --- |
| near_dup_excluded_raw_all_blocks | ZERO | -0.164422 | 0.0348213 | -0.253074 | -0.0942087 | 0.00039996 | FPA_WORSE_BEYOND_MARGIN |
| near_dup_excluded_raw_all_blocks | DIRECT_HUBER | -0.16166 | 0.0334564 | -0.246963 | -0.0954385 | 0.00039996 | FPA_WORSE_BEYOND_MARGIN |
| near_dup_excluded_raw_all_blocks | ORDINARY_SOFT | -0.151162 | 0.0302572 | -0.226243 | -0.0893004 | 0.00039996 | FPA_WORSE_BEYOND_MARGIN |
| near_dup_excluded_raw_all_blocks | HARD_FPA | 0.0237827 | 0.00378212 | 0.0161443 | 0.0330929 | 0.00039996 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN |
| near_dup_excluded_calibrated_blocks_2_7 | ZERO | -0.00984252 | 0.00663997 | -0.0263341 | 0.00350731 | 0.253175 | INCONCLUSIVE |
| near_dup_excluded_calibrated_blocks_2_7 | DIRECT_HUBER | -0.000143443 | 0.00386904 | -0.00849289 | 0.00891846 | 0.970003 | EQUIVALENT_WITHIN_MARGIN |
| near_dup_excluded_calibrated_blocks_2_7 | ORDINARY_SOFT | -0.0057124 | 0.00319994 | -0.01454 | 9.32471e-05 | 0.178182 | EQUIVALENT_WITHIN_MARGIN |
| near_dup_excluded_calibrated_blocks_2_7 | HARD_FPA | -0.00153538 | 0.000811639 | -0.00366388 | -9.49962e-05 | 0.158384 | EQUIVALENT_WITHIN_MARGIN |

## Prediction SD by factorial cell (outcome SD 0.010962)

| cell | DIRECT_HUBER | FPA_SOFT | HARD_FPA | ORDINARY_SOFT |
| --- | --- | --- | --- | --- |
| purge0_excl_cal | 0.000905719 | 0.000541394 | 0.000499638 | 0.000351126 |
| purge0_excl_raw | 0.000923739 | 0.00369493 | 0.00398187 | 0.00104514 |
| purge0_noexcl_cal | 0.00113991 | 0.00045337 | 0.000460288 | 0.000396212 |
| purge0_noexcl_raw | 0.00111677 | 0.00387474 | 0.00412435 | 0.00110625 |
| purge5_excl_cal | 0.000868859 | 0.000481201 | 0.000449227 | 0.000298115 |
| purge5_excl_raw | 0.000906784 | 0.00368058 | 0.00398121 | 0.00104556 |
| purge5_noexcl_cal | 0.00103846 | 0.000422557 | 0.000429609 | 0.00048397 |
| purge5_noexcl_raw | 0.00109984 | 0.00389457 | 0.00416492 | 0.00110996 |
