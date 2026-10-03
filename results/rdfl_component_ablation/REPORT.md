# RDFL Component Ablation

Status: **EXPLORATORY — RETROSPECTIVE; SAME PROVENANCE GATES AS THE PILOT**

Fresh-pilot folds, 403 dates. Reproduction gaps: {'RDFL|retained|confidence': 9.985502008591496e-17, 'ORD|ordinary_eligible|uniform': 9.974659986866641e-17}

## Cells versus ZERO (block length 20; positive favours the cell)

| cell | relative_improvement | bootstrap_se | family_ci_low | family_ci_high | holm_p | decision_2pct_family |
| --- | --- | --- | --- | --- | --- | --- |
| RDFL/retained/confidence | -0.160466 | 0.0303208 | -0.249968 | -0.0933619 | 0.00109989 | RDFL_WORSE_BEYOND_MARGIN |
| RDFL/retained/uniform | -0.154548 | 0.0291901 | -0.242156 | -0.0896574 | 0.00109989 | RDFL_WORSE_BEYOND_MARGIN |
| RDFL/eligible/confidence | -0.0913413 | 0.0219224 | -0.154993 | -0.0398944 | 0.00109989 | RDFL_WORSE_BEYOND_MARGIN |
| RDFL/eligible/uniform | -0.0759231 | 0.0192026 | -0.131788 | -0.0311131 | 0.00109989 | RDFL_WORSE_BEYOND_MARGIN |
| ORD/retained/confidence | -0.0438101 | 0.0121058 | -0.079915 | -0.0152071 | 0.00109989 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN |
| ORD/retained/uniform | -0.0406841 | 0.0113839 | -0.0723443 | -0.0139885 | 0.00109989 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN |
| ORD/eligible/confidence | -0.0218351 | 0.00904407 | -0.0484891 | -0.00075588 | 0.0281972 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN |
| ORD/eligible/uniform | -0.014888 | 0.00757436 | -0.0360067 | 0.00297438 | 0.069793 | INCONCLUSIVE |
| RDFL/retained_without_low/confidence | -0.316489 | 0.051071 | -0.470604 | -0.201433 | 0.00109989 | RDFL_WORSE_BEYOND_MARGIN |
| RDFL/random_size_matched/confidence | -0.0853797 | 0.0208857 | -0.147052 | -0.0382963 | 0.00109989 | RDFL_WORSE_BEYOND_MARGIN |
| ORD/ordinary_eligible/uniform | -0.0104718 | 0.005349 | -0.0253129 | 0.00263884 | 0.069793 | INCONCLUSIVE |

## One-factor contrasts from RDFL_SOFT (positive favours the variant)

| contrast | relative_improvement | ci95_low | ci95_high | family_ci_low | family_ci_high | holm_p |
| --- | --- | --- | --- | --- | --- | --- |
| label_rule_ordinary | 0.100525 | 0.075016 | 0.129953 | 0.0698026 | 0.136814 | 0.00059994 |
| selection_all_eligible | 0.0595663 | 0.0464889 | 0.0753347 | 0.0435216 | 0.0790655 | 0.00059994 |
| weights_uniform | 0.00509995 | 0.00295995 | 0.0076375 | 0.00248703 | 0.0082917 | 0.00059994 |
| abstain_on_low_response | -0.134449 | -0.176469 | -0.0973616 | -0.185609 | -0.0902847 | 0.00059994 |
| random_selection_same_size | 0.0647035 | 0.0492467 | 0.0830771 | 0.0465937 | 0.087974 | 0.00059994 |
| size_given_random_selection | -0.0054926 | -0.0136849 | 0.00318195 | -0.0157233 | 0.00523756 | 0.20358 |

## Factorial main effects on improvement versus ZERO

| factor | from | to | mean_shift_in_improvement_vs_zero | shift_min | shift_max |
| --- | --- | --- | --- | --- | --- |
| rule | RDFL | ORD | 0.0902652 | 0.0610351 | 0.116656 |
| selection | retained | eligible | 0.0488801 | 0.021975 | 0.0786246 |
| weights | confidence | uniform | 0.00785238 | 0.003126 | 0.0154182 |
