# Methodological results: scope-limited evidence

Status: completed simulations and retrospective empirical pilot; NOT confirmatory market evidence.

## Legacy result audit

Legacy P3 weighted component-absence error in cancellation: 0.985496. This is a selected-training-label diagnostic with a net-SD-dependent threshold, not test-set accuracy. No files from results/metrics/ were ingested.

## Fresh known-truth simulation

100 independent replications per scenario; common train/test draws across methods. Primary learner functions are reused from a hashed P3 snapshot; the DGP is newly specified. Net-effect MSE and component absence answer different questions.

| scenario | loss_difference_baseline_minus_rdfl | ci95_low | ci95_high | holm_p |
| --- | --- | --- | --- | --- |
| anticipation | 0.058665 | 0.0562964 | 0.0611215 | 0.0019998 |
| cancellation_050 | -0.0141048 | -0.0146976 | -0.013547 | 0.0019998 |
| cancellation_085 | -0.00547234 | -0.00589435 | -0.00505788 | 0.0019998 |
| cancellation_100 | -0.0048299 | -0.0051899 | -0.00449081 | 0.0019998 |
| high_noise | -0.0515026 | -0.0544812 | -0.0485772 | 0.0019998 |
| informative_missing | -0.0612284 | -0.0629536 | -0.0595144 | 0.0019998 |
| null_effect | -0.00565037 | -0.00629033 | -0.0050432 | 0.0019998 |
| regime_shift | 0.125569 | 0.110889 | 0.140047 | 0.0019998 |
| stale_price | -0.0026974 | -0.00460919 | -0.000770181 | 0.00529947 |
| strong_signal | -0.0572949 | -0.0589426 | -0.0556599 | 0.0019998 |

Positive differences favor RDFL. Report positive scenarios as well as failures. Holm correction spans DIRECT and ZERO comparisons across all scenarios.

## Fixed-threshold component diagnostic

| scenario | component_error | ci95_low | ci95_high | component_prevalence | net_error |
| --- | --- | --- | --- | --- | --- |
| anticipation | 0.715519 | 0.712699 | 0.718307 | 0.724883 | 0.715519 |
| cancellation_050 | 0.759997 | 0.757193 | 0.762804 | 0.798279 | 0.455442 |
| cancellation_085 | 0.800889 | 0.798221 | 0.803517 | 0.8103 | 0.250495 |
| cancellation_100 | 0.810825 | 0.808257 | 0.813356 | 0.817213 | 0.206129 |
| high_noise | 0.705187 | 0.702437 | 0.707985 | 0.724883 | 0.705187 |
| informative_missing | 0.545566 | 0.541754 | 0.549316 | 0.66337 | 0.545566 |
| null_effect | 0 | 0 | 0 | 0 | 0 |
| regime_shift | 0.608676 | 0.605585 | 0.611768 | 0.724883 | 0.608676 |
| stale_price | 0.682828 | 0.679677 | 0.686021 | 0.724883 | 0.682828 |
| strong_signal | 0.529106 | 0.525751 | 0.532369 | 0.724883 | 0.529106 |

Error is conditional on low-response soft weights. Compare population prevalence; the rate is not a conventional false-positive rate. Thresholds 0.2/0.5 and the net-SD threshold are in absence_summary.csv. The synthetic oracle and planted positive control are in simulation outputs.

## Fresh purged empirical pilot

| competitor | relative_improvement | relative_ci95_low | relative_ci95_high | holm_p | equivalence_2pct_family |
| --- | --- | --- | --- | --- | --- |
| DIRECT_HUBER | -0.159049 | -0.225622 | -0.100685 | 0.00039996 | False |
| HARD_RDFL | 0.0199338 | 0.0141628 | 0.0267313 | 0.00039996 | False |
| ORDINARY_SOFT | -0.14844 | -0.202825 | -0.103132 | 0.00039996 | False |
| ZERO | -0.160466 | -0.226424 | -0.107066 | 0.00039996 | False |

Loss uses training-stock-SD normalization and equal-date weighting; it is not NMSE against zero. Relative improvement is a proportion (0.02 = 2%). Block length 20 is primary; 10/40 sensitivity is supplied. Equivalence is a conservative family-adjusted CI diagnostic at +/-2%, not proof of exact equality. Confidence intervals displayed here are unadjusted; simultaneous intervals are in CSV files.

## Historical P2c sensitivity (already examined)

| competitor | relative_improvement | relative_ci95_low | relative_ci95_high | holm_p | equivalence_2pct_family |
| --- | --- | --- | --- | --- | --- |
| DIRECT_HUBER | 0.017948 | 0.00276062 | 0.0376794 | 0.129987 | False |
| HARD_RDFL | 0.000390682 | -0.000154616 | 0.000911541 | 0.487751 | True |
| ORDINARY_SOFT | -0.00232981 | -0.00669579 | 0.00187638 | 0.576342 | True |
| ZERO | -0.00260945 | -0.0118255 | 0.00614524 | 0.576342 | True |

Do not attribute differences between historical P2c and the fresh rerun solely to leakage: purging, overlap exclusion, calibration, evaluation dates, and fitted samples differ.

## Claim boundary and remaining work

The experiment tests outcome-derived RDFL labels and TF-IDF learners. It does not show that FinBERT, XLM-R, Gemma, or all emerging-market news lack predictive information. The identifiability counterexample assumes available observables do not reveal opposing components. A future article needs resolved temporal/price provenance, verified event deduplication, independent replication, related-work positioning, and an audited multi-teacher experiment if multi-teacher claims are retained. The current data cannot identify real-world causal absence.
