# Retrospective Power and Minimum Detectable Effect

Status: **DESIGN DIAGNOSTIC — NORMAL APPROXIMATION TO THE BOOTSTRAP**

Power is the probability of rejecting a zero relative improvement at a
two-sided 0.05 level, given the bootstrap standard error of the paired
relative-loss statistic. It is a design diagnostic, not an observed-effect
post hoc calculation.

## purged_pilot

Evaluation dates: 403; matched stock-days: 2197; bootstrap draws: 10,000.

| competitor | observed_relative_improvement | bootstrap_se | mde_power_80 | mde_power_90 | power_at_2pct_margin | observed_exceeds_mde80 |
| --- | --- | --- | --- | --- | --- | --- |
| ZERO | -0.160466 | 0.0302073 | 0.0846282 | 0.0979173 | 0.101536 | True |
| DIRECT_HUBER | -0.159049 | 0.0320288 | 0.0897314 | 0.103822 | 0.0957295 | True |
| ORDINARY_SOFT | -0.14844 | 0.0259037 | 0.0725715 | 0.0839674 | 0.120588 | True |
| HARD_FPA | 0.0199338 | 0.00315372 | 0.00883543 | 0.0102228 | 0.999994 | True |

Power at the disclosed 2% margin ranges from 0.10 to 1.00. 4 of 4 observed effects exceed their own 80% minimum detectable effect.

## historical_p2c

Evaluation dates: 356; matched stock-days: 1980; bootstrap draws: 10,000.

| competitor | observed_relative_improvement | bootstrap_se | mde_power_80 | mde_power_90 | power_at_2pct_margin | observed_exceeds_mde80 |
| --- | --- | --- | --- | --- | --- | --- |
| ZERO | -0.00260945 | 0.00454217 | 0.0127253 | 0.0147235 | 0.992721 | False |
| DIRECT_HUBER | 0.017948 | 0.00908837 | 0.0254619 | 0.0294601 | 0.595103 | False |
| ORDINARY_SOFT | -0.00232981 | 0.00219833 | 0.00615881 | 0.00712592 | 1 | False |
| HARD_FPA | 0.000390682 | 0.000269605 | 0.000755322 | 0.00087393 | 1 | False |

Power at the disclosed 2% margin ranges from 0.60 to 1.00. 0 of 4 observed effects exceed their own 80% minimum detectable effect.
