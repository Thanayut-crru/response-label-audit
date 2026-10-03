# Simulation Extensions

Status: **KNOWN-TRUTH; CONDITIONAL ON THE STATED GENERATORS**

## Volume informativeness (cancellation 0.85, delta = 0.35)

| lambda | replications | weighted_component_absence_error | weighted_component_absence_error_ci95_low | weighted_component_absence_error_ci95_high | component_prevalence | component_prevalence_ci95_low | component_prevalence_ci95_high | weighted_net_absence_error | weighted_net_absence_error_ci95_low | weighted_net_absence_error_ci95_high | bound_net_only_lower | bound_net_only_lower_ci95_low | bound_net_only_lower_ci95_high | bound_gross_lower | bound_gross_lower_ci95_low | bound_gross_lower_ci95_high | bound_gross_sharp_lower | bound_gross_sharp_lower_ci95_low | bound_gross_sharp_lower_ci95_high | bound_gross_upper | bound_gross_upper_ci95_low | bound_gross_upper_ci95_high | retained_fraction | retained_fraction_ci95_low | retained_fraction_ci95_high | rdfl_soft_latent_mse | rdfl_soft_latent_mse_ci95_low | rdfl_soft_latent_mse_ci95_high | direct_latent_mse | direct_latent_mse_ci95_low | direct_latent_mse_ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 100 | 0.800889 | 0.798195 | 0.80358 | 0.8103 | 0.808933 | 0.811671 | 0.250495 | 0.247723 | 0.253297 | 0.0200975 | 0.0192255 | 0.0209835 | 0.709058 | 0.706091 | 0.712112 | 0.77885 | 0.776162 | 0.781499 | 0.822417 | 0.819918 | 0.824968 | 0.693779 | 0.692308 | 0.695233 | 0.00972462 | 0.00922177 | 0.0102376 | 0.00425229 | 0.00399154 | 0.00451852 |
| 0.25 | 100 | 0.805609 | 0.802795 | 0.80841 | 0.8103 | 0.808933 | 0.811671 | 0.251466 | 0.248592 | 0.254406 | 0.0205322 | 0.0196143 | 0.0214729 | 0.712229 | 0.709083 | 0.715527 | 0.782336 | 0.779491 | 0.785249 | 0.827755 | 0.825138 | 0.830351 | 0.693596 | 0.691975 | 0.695204 | 0.0097796 | 0.00928455 | 0.0102834 | 0.00425229 | 0.00399154 | 0.00451852 |
| 0.5 | 100 | 0.809951 | 0.807142 | 0.812756 | 0.8103 | 0.808933 | 0.811671 | 0.252721 | 0.249957 | 0.255587 | 0.0211598 | 0.0202826 | 0.0220606 | 0.714905 | 0.711749 | 0.718117 | 0.786087 | 0.783205 | 0.789062 | 0.832093 | 0.829502 | 0.834628 | 0.693921 | 0.692325 | 0.695483 | 0.00986862 | 0.009363 | 0.0103898 | 0.00425229 | 0.00399154 | 0.00451852 |
| 0.75 | 100 | 0.813684 | 0.810833 | 0.816524 | 0.8103 | 0.808933 | 0.811671 | 0.253346 | 0.250561 | 0.256178 | 0.0213791 | 0.0204572 | 0.0223032 | 0.717455 | 0.714417 | 0.720569 | 0.789988 | 0.78707 | 0.792965 | 0.835631 | 0.833047 | 0.838157 | 0.694496 | 0.692987 | 0.695979 | 0.00999311 | 0.00947811 | 0.0105307 | 0.00425229 | 0.00399154 | 0.00451852 |
| 1 | 100 | 0.816902 | 0.813988 | 0.819864 | 0.8103 | 0.808933 | 0.811671 | 0.254021 | 0.251189 | 0.256927 | 0.0216617 | 0.0207224 | 0.0226269 | 0.719547 | 0.716349 | 0.722836 | 0.793416 | 0.790409 | 0.796528 | 0.838241 | 0.835633 | 0.840863 | 0.694958 | 0.693379 | 0.696496 | 0.0100578 | 0.0095341 | 0.0106031 | 0.00425229 | 0.00399154 | 0.00451852 |

## Component-aware abstention

| rule_accuracy | replications | weighted_component_absence_error_before | weighted_component_absence_error_before_ci95_low | weighted_component_absence_error_before_ci95_high | weighted_component_absence_error_after | weighted_component_absence_error_after_ci95_low | weighted_component_absence_error_after_ci95_high | component_prevalence_after | component_prevalence_after_ci95_low | component_prevalence_after_ci95_high | retained_fraction_after | retained_fraction_after_ci95_low | retained_fraction_after_ci95_high | rdfl_soft_latent_mse_before | rdfl_soft_latent_mse_before_ci95_low | rdfl_soft_latent_mse_before_ci95_high | rdfl_soft_latent_mse_after | rdfl_soft_latent_mse_after_ci95_low | rdfl_soft_latent_mse_after_ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | 100 | 0.800889 | 0.798195 | 0.80358 | 0.801144 | 0.79724 | 0.804903 | 0.8103 | 0.808933 | 0.811671 | 0.547054 | 0.545496 | 0.548592 | 0.00972462 | 0.00922177 | 0.0102376 | 0.0264517 | 0.0252172 | 0.0277507 |
| 0.7 | 100 | 0.800889 | 0.798195 | 0.80358 | 0.658168 | 0.653158 | 0.66317 | 0.8103 | 0.808933 | 0.811671 | 0.514883 | 0.513417 | 0.516363 | 0.00972462 | 0.00922177 | 0.0102376 | 0.0344072 | 0.0329041 | 0.0359975 |
| 0.9 | 100 | 0.800889 | 0.798195 | 0.80358 | 0.422891 | 0.416719 | 0.429105 | 0.8103 | 0.808933 | 0.811671 | 0.483692 | 0.482325 | 0.485067 | 0.00972462 | 0.00922177 | 0.0102376 | 0.0446972 | 0.0427424 | 0.0467377 |
| 1 | 100 | 0.800889 | 0.798195 | 0.80358 | 0.229043 | 0.223934 | 0.234088 | 0.8103 | 0.808933 | 0.811671 | 0.467612 | 0.466333 | 0.468879 | 0.00972462 | 0.00922177 | 0.0102376 | 0.0513187 | 0.0491037 | 0.0536791 |

## Nonlinear signal, capacity-matched learners (latent MSE)

| scenario | DIRECT_HGB | DIRECT_RIDGE | ORACLE_HGB | ORDINARY_SOFT_HGB | RDFL_SOFT_HGB | RDFL_SOFT_LOGISTIC | ZERO |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nonlinear | 0.239559 | 0.830103 | 0.116224 | 0.54685 | 0.315925 | 0.812923 | 1.00233 |
| nonlinear_cancellation_085 | 0.0391838 | 0.0228507 | 0.00502608 | 0.0568884 | 0.070602 | 0.0277588 | 0.112787 |

| scenario | baseline | variant | mean_difference_baseline_minus_variant | ci95_low | ci95_high | raw_p | holm_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nonlinear | DIRECT_HGB | RDFL_SOFT_HGB | -0.0763666 | -0.0842596 | -0.0685252 | 9.999e-05 | 0.00079992 |
| nonlinear | ORDINARY_SOFT_HGB | RDFL_SOFT_HGB | 0.230925 | 0.223295 | 0.238155 | 9.999e-05 | 0.00079992 |
| nonlinear | DIRECT_RIDGE | RDFL_SOFT_LOGISTIC | 0.0171806 | 0.0156249 | 0.0187791 | 9.999e-05 | 0.00079992 |
| nonlinear | ZERO | RDFL_SOFT_HGB | 0.686403 | 0.676234 | 0.696318 | 9.999e-05 | 0.00079992 |
| nonlinear_cancellation_085 | DIRECT_HGB | RDFL_SOFT_HGB | -0.0314182 | -0.0323926 | -0.0304461 | 9.999e-05 | 0.00079992 |
| nonlinear_cancellation_085 | ORDINARY_SOFT_HGB | RDFL_SOFT_HGB | -0.0137136 | -0.0150282 | -0.0123611 | 9.999e-05 | 0.00079992 |
| nonlinear_cancellation_085 | DIRECT_RIDGE | RDFL_SOFT_LOGISTIC | -0.00490814 | -0.0052822 | -0.00454591 | 9.999e-05 | 0.00079992 |
| nonlinear_cancellation_085 | ZERO | RDFL_SOFT_HGB | 0.0421848 | 0.0406594 | 0.0437326 | 9.999e-05 | 0.00079992 |
