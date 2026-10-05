# Historical-Mean Baselines

Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**

Relative improvement of the variant over the baseline, 1 - L_variant / L_baseline, on the scale of (5); paired circular moving-block bootstrap, block 20; family-adjusted intervals at 1 - 0.10/family size.

| analysis | baseline | variant | relative_improvement | family_ci_low | family_ci_high | holm_p | decision_2pct_family |
| --- | --- | --- | --- | --- | --- | --- | --- |
| thai_pilot_uncalibrated | ZERO | HIST_MEAN_STOCK | -0.00474406 | -0.00996574 | 0.000775452 | 0.116388 | EQUIVALENT_WITHIN_MARGIN |
| thai_pilot_uncalibrated | ZERO | HIST_MEAN_POOLED | -0.00327693 | -0.0100026 | 0.00246935 | 0.257674 | EQUIVALENT_WITHIN_MARGIN |
| thai_pilot_uncalibrated | HIST_MEAN_STOCK | RDFL_SOFT | -0.154987 | -0.229751 | -0.0963102 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN |
| thai_pilot_uncalibrated | HIST_MEAN_POOLED | RDFL_SOFT | -0.156676 | -0.233777 | -0.0954553 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN |
| fnspid_pilot_uncalibrated | ZERO | HIST_MEAN_STOCK | -0.00265861 | -0.0123823 | 0.00156308 | 0.446155 | EQUIVALENT_WITHIN_MARGIN |
| fnspid_pilot_uncalibrated | ZERO | HIST_MEAN_POOLED | -0.00154259 | -0.0102057 | 0.00265363 | 0.465953 | EQUIVALENT_WITHIN_MARGIN |
| fnspid_pilot_uncalibrated | HIST_MEAN_STOCK | RDFL_SOFT | -0.0758827 | -0.19207 | -0.024439 | 0.00039996 | RDFL_WORSE_BEYOND_MARGIN |
| fnspid_pilot_uncalibrated | HIST_MEAN_POOLED | RDFL_SOFT | -0.0770815 | -0.194628 | -0.0256638 | 0.00059994 | RDFL_WORSE_BEYOND_MARGIN |
| thai_calibrated | ZERO | INTERCEPT_ONLY | -0.000656684 | -0.00888323 | 0.00714123 | 0.871313 | EQUIVALENT_WITHIN_MARGIN |
| thai_calibrated | INTERCEPT_ONLY | RDFL_SOFT_CALIBRATED | -0.00259983 | -0.00639523 | 0.000691227 | 0.291571 | EQUIVALENT_WITHIN_MARGIN |
| fnspid_calibrated | ZERO | INTERCEPT_ONLY | -0.0111889 | -0.0354062 | 0.000443164 | 0.19638 | INCONCLUSIVE |
| fnspid_calibrated | INTERCEPT_ONLY | RDFL_SOFT_CALIBRATED | -0.00354154 | -0.0130757 | 0.000510705 | 0.19638 | EQUIVALENT_WITHIN_MARGIN |
