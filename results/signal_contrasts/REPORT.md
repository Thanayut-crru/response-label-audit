# Signal Contrasts and Calibration Coefficients

Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**

Signal term 2E[y yhat]/E[y^2]; contrasts against the reference on the same resampled dates (block 20, 10000 draws), Holm within each dataset. Second moment = variance part + squared-mean part.

## thai_pilot

| method | signal_term | signal_minus_reference | signal_minus_reference_ci95_low | signal_minus_reference_ci95_high | holm_p | second_moment_term | variance_part | squared_mean_part |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DIRECT_HUBER | 0.00843149 | -0.000370638 | -0.0503051 | 0.0453113 | 1 | 0.00965447 | 0.00963489 | 1.95795e-05 |
| HARD_RDFL | 0.0107786 | 0.00197648 | -0.00297382 | 0.00757113 | 1 | 0.194848 | 0.182799 | 0.012049 |
| ORDINARY_SOFT | 0.00352845 | -0.00527367 | -0.0382277 | 0.025224 | 1 | 0.0140003 | 0.0128023 | 0.00119797 |
| RDFL_SOFT | 0.00880213 | 0 | 0 | 0 |  | 0.169268 | 0.158176 | 0.011092 |
| ZERO | 0 | -0.00880213 | -0.0494791 | 0.0299733 | 1 | 0 | 0 | 0 |

## thai_components

| cell | signal_term | signal_minus_reference | signal_minus_reference_ci95_low | signal_minus_reference_ci95_high | holm_p | second_moment_term | variance_part | squared_mean_part |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORD/eligible/confidence | 0.0086433 | -0.000158826 | -0.0275192 | 0.0248702 | 1 | 0.0304784 | 0.0266323 | 0.00384608 |
| ORD/eligible/uniform | 0.00857111 | -0.00023102 | -0.0296403 | 0.0266061 | 1 | 0.0234592 | 0.021095 | 0.00236416 |
| ORD/ordinary_eligible/uniform | 0.00352845 | -0.00527367 | -0.0382277 | 0.025224 | 1 | 0.0140003 | 0.0128023 | 0.00119797 |
| ORD/retained/confidence | 0.00687233 | -0.0019298 | -0.0238922 | 0.0187353 | 1 | 0.0506824 | 0.0438157 | 0.00686671 |
| ORD/retained/uniform | 0.00666768 | -0.00213445 | -0.0245835 | 0.0193784 | 1 | 0.0473517 | 0.0412633 | 0.00608839 |
| RDFL/eligible/confidence | 0.0140634 | 0.00526126 | -0.00682132 | 0.0160331 | 1 | 0.105405 | 0.099384 | 0.00602073 |
| RDFL/eligible/uniform | 0.0141572 | 0.00535503 | -0.0106427 | 0.0201333 | 1 | 0.0900803 | 0.0860019 | 0.00407836 |
| RDFL/random_size_matched/confidence | 0.00592938 | -0.00287274 | -0.0193903 | 0.0123577 | 1 | 0.0913091 | 0.0868973 | 0.00441184 |
| RDFL/retained_without_low/confidence | 0.0161782 | 0.00737608 | -0.0145392 | 0.0291416 | 1 | 0.332667 | 0.306623 | 0.0260443 |
| RDFL/retained/confidence | 0.00880213 | 0 | 0 | 0 |  | 0.169268 | 0.158176 | 0.011092 |
| RDFL/retained/uniform | 0.00889999 | 9.78615e-05 | -0.00171742 | 0.00221753 | 1 | 0.163448 | 0.15325 | 0.010198 |

## fnspid_pilot

| method | signal_term | signal_minus_reference | signal_minus_reference_ci95_low | signal_minus_reference_ci95_high | holm_p | second_moment_term | variance_part | squared_mean_part |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DIRECT_HUBER | 0.00033006 | 0.00599291 | -0.0208558 | 0.0451491 | 1 | 0.00848325 | 0.00845132 | 3.19297e-05 |
| HARD_RDFL | -0.00841286 | -0.00275001 | -0.010371 | 0.00255444 | 1 | 0.0820326 | 0.0791147 | 0.00291791 |
| ORDINARY_SOFT | -0.00221366 | 0.00344919 | -0.0202883 | 0.0353864 | 1 | 0.00859904 | 0.00787681 | 0.000722228 |
| RDFL_SOFT | -0.00566285 | 0 | 0 | 0 |  | 0.0730802 | 0.0703573 | 0.00272282 |
| ZERO | 0 | 0.00566285 | -0.0287888 | 0.0522559 | 1 | 0 | 0 | 0 |

## fnspid_components

| cell | signal_term | signal_minus_reference | signal_minus_reference_ci95_low | signal_minus_reference_ci95_high | holm_p | second_moment_term | variance_part | squared_mean_part |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORD/eligible/confidence | -0.00181646 | 0.00384639 | -0.0149177 | 0.0304315 | 1 | 0.0135038 | 0.0116121 | 0.0018917 |
| ORD/eligible/uniform | -0.00163999 | 0.00402286 | -0.0168949 | 0.0338488 | 1 | 0.0106996 | 0.00966475 | 0.00103485 |
| ORD/ordinary_eligible/uniform | -0.00221366 | 0.00344919 | -0.0202883 | 0.0353864 | 1 | 0.00859904 | 0.00787681 | 0.000722228 |
| ORD/retained/confidence | -0.00212508 | 0.00353778 | -0.0103273 | 0.0238758 | 1 | 0.0218473 | 0.0186662 | 0.00318113 |
| ORD/retained/uniform | -0.00206526 | 0.00359759 | -0.0107496 | 0.0247989 | 1 | 0.0205655 | 0.017922 | 0.0026435 |
| RDFL/eligible/confidence | -0.00476319 | 0.000899658 | -0.0120819 | 0.0174004 | 1 | 0.0433729 | 0.0420745 | 0.00129837 |
| RDFL/eligible/uniform | -0.00485663 | 0.000806218 | -0.0155621 | 0.0232847 | 1 | 0.0382905 | 0.0375322 | 0.000758277 |
| RDFL/random_size_matched/confidence | -0.00789708 | -0.00223423 | -0.0202827 | 0.0183333 | 1 | 0.0383412 | 0.0372234 | 0.00111786 |
| RDFL/retained_without_low/confidence | -0.0146118 | -0.00894898 | -0.0334582 | 0.0183072 | 1 | 0.198178 | 0.19351 | 0.00466792 |
| RDFL/retained/confidence | -0.00566285 | 0 | 0 | 0 |  | 0.0730802 | 0.0703573 | 0.00272282 |
| RDFL/retained/uniform | -0.00532025 | 0.000342597 | -0.00102754 | 0.00207459 | 1 | 0.070631 | 0.068256 | 0.002375 |

## Calibration of the RDFL soft learner

| dataset | block | history_stock_days | ridge_alpha | intercept | slope | raw_prediction_sd | calibrated_prediction_sd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| thai_calibrated | 2024-11-01 | 217 | 10 | 0.00136375 | 0.148388 | 0.00425687 | 0.000631669 |
| thai_calibrated | 2025-02-01 | 522 | 10 | 0.000724249 | 0.0954295 | 0.00407077 | 0.000388472 |
| thai_calibrated | 2025-05-01 | 831 | 10 | 0.000717094 | -0.0345351 | 0.00399048 | 0.000137812 |
| thai_calibrated | 2025-08-01 | 1128 | 10 | 0.000710686 | -0.032585 | 0.00372931 | 0.00012152 |
| thai_calibrated | 2025-11-01 | 1473 | 10 | 0.000505573 | -0.0194966 | 0.00305614 | 5.95845e-05 |
| thai_calibrated | 2026-02-01 | 1827 | 10 | 0.000507733 | -0.0176467 | 0.00277295 | 4.89334e-05 |
| fnspid_calibrated | 2019-01-01 | 258 | 10 | -0.00182302 | 0.288108 | 0.00553219 | 0.00159386 |
| fnspid_calibrated | 2019-04-01 | 483 | 10 | -0.000105763 | 0.00125747 | 0.00418161 | 5.25825e-06 |
| fnspid_calibrated | 2019-07-01 | 740 | 10 | 0.000516847 | -0.001252 | 0.00442314 | 5.53779e-06 |
| fnspid_calibrated | 2019-10-01 | 1016 | 10 | 0.000742286 | 0.00629285 | 0.00406709 | 2.55936e-05 |
| fnspid_calibrated | 2020-01-01 | 1304 | 10 | 0.000854739 | -0.00647528 | 0.0033287 | 2.15543e-05 |
| fnspid_calibrated | 2020-04-01 | 1588 | 10 | 0.000537824 | 0.00289911 | 0.00462884 | 1.34195e-05 |
