# Size-Matched Random Abstention

Status: **KNOWN-TRUTH; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**

Cancellation 0.85, delta = 0.35, 100 replications per accuracy. The random arm drops, in each replication, as many retained low-response cases as the rule drops, chosen uniformly at random.

| rule_accuracy | replications | mean_dropped | rule_component_absence_error | random_component_absence_error | rule_latent_mse | random_latent_mse | rule_retained_fraction | random_retained_fraction | mse_rule_minus_random | mse_rule_minus_random_ci95_low | mse_rule_minus_random_ci95_high | raw_p | holm_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | 100 | 352.14 | 0.801144 | 0.801038 | 0.0264517 | 0.0261493 | 0.547054 | 0.547054 | 0.000302376 | -9.5708e-05 | 0.000707902 | 0.135586 | 0.135586 |
| 0.7 | 100 | 429.35 | 0.658168 | 0.800204 | 0.0344072 | 0.0335371 | 0.514883 | 0.514883 | 0.00087019 | 0.000301678 | 0.00143582 | 0.00289971 | 0.00579942 |
| 0.9 | 100 | 504.21 | 0.422891 | 0.800833 | 0.0446972 | 0.0433625 | 0.483692 | 0.483692 | 0.00133468 | 0.00071955 | 0.0019621 | 9.999e-05 | 0.00039996 |
| 1 | 100 | 542.8 | 0.229043 | 0.804288 | 0.0513187 | 0.0488012 | 0.467612 | 0.467612 | 0.00251749 | 0.00186996 | 0.00314107 | 9.999e-05 | 0.00039996 |
