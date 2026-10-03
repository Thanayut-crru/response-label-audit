# Equivalence Sensitivity Separated from Difference-Test Power

Status: **DESIGN DIAGNOSTIC — NORMAL APPROXIMATION TO THE BOOTSTRAP**

`difference_power_2pct` is the power of the test of a zero effect when the true effect is 2%.
`equivalence_power_2pct_family` is the probability that the 97.5% family interval lies inside
(-2%, +2%) when the true effect is zero. They are different tests and are not interchangeable.
Decisions are read from the observed intervals, not from either power quantity.

| dataset | competitor | relative_improvement | family_ci_low | family_ci_high | holm_p | decision_2pct_family | bootstrap_se | mde80_difference | difference_power_2pct | equivalence_power_2pct_family | equivalence_margin80_family |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| purged_pilot | DIRECT_HUBER | -0.159049 | -0.236178 | -0.0921554 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN | 0.0320288 | 0.0897314 | 0.0957295 | 0 | 0.112836 |
| purged_pilot | HARD_RDFL | 0.0199338 | 0.0133674 | 0.0278676 | 0.00039996 | DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN | 0.00315372 | 0.00883543 | 0.999994 | 0.999959 | 0.0111104 |
| purged_pilot | ORDINARY_SOFT | -0.14844 | -0.211406 | -0.0971615 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN | 0.0259037 | 0.0725715 | 0.120588 | 0 | 0.0912577 |
| purged_pilot | ZERO | -0.160466 | -0.235456 | -0.100383 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN | 0.0302073 | 0.0846282 | 0.101536 | 0 | 0.106419 |
| historical_p2c | DIRECT_HUBER | 0.017948 | 0.00131239 | 0.0409117 | 0.129987 | INCONCLUSIVE | 0.00908837 | 0.0254619 | 0.595103 | 0 | 0.0320179 |
| historical_p2c | HARD_RDFL | 0.000390682 | -0.000234975 | 0.000987475 | 0.487751 | EQUIVALENT_WITHIN_MARGIN | 0.000269605 | 0.000755322 | 1 | 1 | 0.000949807 |
| historical_p2c | ORDINARY_SOFT | -0.00232981 | -0.00729776 | 0.00241277 | 0.576342 | EQUIVALENT_WITHIN_MARGIN | 0.00219833 | 0.00615881 | 1 | 1 | 0.00774462 |
| historical_p2c | ZERO | -0.00260945 | -0.0132111 | 0.00735756 | 0.576342 | EQUIVALENT_WITHIN_MARGIN | 0.00454217 | 0.0127253 | 0.992721 | 0.969365 | 0.0160019 |

- purged_pilot: decisions at +/-2% = {'RDFL_WORSE_BEYOND_MARGIN': 3, 'DIFFERENCE_DETECTED_EQUIVALENCE_NOT_SHOWN': 1}
- historical_p2c: decisions at +/-2% = {'EQUIVALENT_WITHIN_MARGIN': 3, 'INCONCLUSIVE': 1}
