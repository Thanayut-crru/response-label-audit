# Sensitivity of RDFL (FPA in the code) to its fixed settings

Status: **EXPLORATORY AND POST HOC — outside the locked FNSPID protocol; no setting is selected**

Reproduction gates: {'thai_labels_max_gap': 1.0325074129013956e-13, 'thai_fpa_soft_max_gap': 1.3877787807814457e-16, 'fnspid_labels_max_gap': 1.928457393773897e-13, 'fnspid_fpa_soft_max_gap': 1.3183898417423734e-16}

Every cell worse than ZERO beyond the ±2% margin at all block lengths: {'fnspid': False, 'thai': True}

## Cells versus ZERO (block length 20; positive favours the cell)

| dataset | cell | band | threshold | relative_improvement | family_ci_low | family_ci_high | holm_p | decision_2pct_family | mean_training_examples | prediction_sd | outcome_sd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thai | threshold_none | 0.30-0.70 | none | -0.0913413 | -0.14943 | -0.0408953 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 930.857 | 0.0029015 | 0.0111691 |
| thai | threshold_0.50 | 0.30-0.70 | 0.50 | -0.101794 | -0.167776 | -0.049155 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 859.429 | 0.00307211 | 0.0111691 |
| thai | threshold_0.60 | 0.30-0.70 | 0.60 | -0.116196 | -0.187682 | -0.0605425 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 795.429 | 0.00325773 | 0.0111691 |
| thai | threshold_0.70 | 0.30-0.70 | 0.70 | -0.160466 | -0.24458 | -0.0952769 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 704.143 | 0.00369014 | 0.0111691 |
| thai | threshold_0.80 | 0.30-0.70 | 0.80 | -0.196278 | -0.302883 | -0.11728 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 625 | 0.00413332 | 0.0111691 |
| thai | threshold_0.90 | 0.30-0.70 | 0.90 | -0.278221 | -0.418553 | -0.172888 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 534.143 | 0.00488259 | 0.0111691 |
| thai | band_0.20_0.80 | 0.20-0.80 | 0.70 | -0.151343 | -0.236645 | -0.0872443 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 622.857 | 0.00358028 | 0.0111691 |
| thai | band_0.40_0.60 | 0.40-0.60 | 0.70 | -0.135758 | -0.217233 | -0.0750513 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 777 | 0.00366756 | 0.0111691 |
| fnspid | threshold_none | 0.30-0.70 | none | -0.0481361 | -0.14109 | -0.0102611 | 0.00159984 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN | 1121 | 0.00348681 | 0.0197034 |
| fnspid | threshold_0.50 | 0.30-0.70 | 0.50 | -0.0542839 | -0.157542 | -0.0125435 | 0.00159984 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN | 1017.71 | 0.00369904 | 0.0197034 |
| fnspid | threshold_0.60 | 0.30-0.70 | 0.60 | -0.063251 | -0.187843 | -0.0154537 | 0.00159984 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN | 908.714 | 0.0040816 | 0.0197034 |
| fnspid | threshold_0.70 | 0.30-0.70 | 0.70 | -0.078743 | -0.223175 | -0.0215047 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 808 | 0.0044909 | 0.0197034 |
| fnspid | threshold_0.80 | 0.30-0.70 | 0.80 | -0.102386 | -0.289368 | -0.0276395 | 0.00149985 | FPA_WORSE_BEYOND_MARGIN | 701.143 | 0.00508538 | 0.0197034 |
| fnspid | threshold_0.90 | 0.30-0.70 | 0.90 | -0.132278 | -0.362271 | -0.0416587 | 0.00119988 | FPA_WORSE_BEYOND_MARGIN | 600.857 | 0.00589942 | 0.0197034 |
| fnspid | band_0.20_0.80 | 0.20-0.80 | 0.70 | -0.0735544 | -0.231783 | -0.0121604 | 0.00159984 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN | 711.286 | 0.00456507 | 0.0197034 |
| fnspid | band_0.40_0.60 | 0.40-0.60 | 0.70 | -0.080526 | -0.21094 | -0.0255592 | 0.00079992 | FPA_WORSE_BEYOND_MARGIN | 888.714 | 0.00447556 | 0.0197034 |
