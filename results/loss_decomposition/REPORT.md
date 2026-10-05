# Loss Decomposition Relative to the Zero Forecast

Status: **DESCRIPTIVE; REVISION ANALYSIS RUN AFTER ALL RESULTS WERE KNOWN**

relative improvement vs zero = signal term - variance term, with signal = 2E[y yhat]/E[y^2] and variance = E[yhat^2]/E[y^2] on the scale of (5), dates weighted equally. Intervals: circular moving-block bootstrap of dates, block 20, 10000 draws.

## thai_pilot

| method | relative_improvement_vs_zero | signal_term | signal_term_ci95_low | signal_term_ci95_high | variance_term | prediction_outcome_correlation |
| --- | --- | --- | --- | --- | --- | --- |
| ZERO | 0 | 0 | 0 | 0 | 0 |  |
| DIRECT_HUBER | -0.00122298 | 0.00843149 | -0.00650243 | 0.0246718 | 0.00965447 | 0.0200672 |
| HARD_RDFL | -0.184069 | 0.0107786 | -0.0288767 | 0.0542549 | 0.194848 | 0.00818032 |
| ORDINARY_SOFT | -0.0104718 | 0.00352845 | -0.00686942 | 0.0138388 | 0.0140003 | 0.0104348 |
| RDFL_SOFT | -0.160466 | 0.00880213 | -0.0287078 | 0.0494498 | 0.169268 | 0.00590228 |

## thai_components

| cell | relative_improvement_vs_zero | signal_term | signal_term_ci95_low | signal_term_ci95_high | variance_term | prediction_outcome_correlation |
| --- | --- | --- | --- | --- | --- | --- |
| RDFL/retained/confidence | -0.160466 | 0.00880213 | -0.0287078 | 0.0494498 | 0.169268 | 0.00590228 |
| RDFL/retained/uniform | -0.154548 | 0.00889999 | -0.0277602 | 0.049262 | 0.163448 | 0.00650594 |
| RDFL/eligible/confidence | -0.0913413 | 0.0140634 | -0.0156206 | 0.0454772 | 0.105405 | 0.0192131 |
| RDFL/eligible/uniform | -0.0759231 | 0.0141572 | -0.0136338 | 0.0429012 | 0.0900803 | 0.0248935 |
| ORD/retained/confidence | -0.0438101 | 0.00687233 | -0.0117101 | 0.0266417 | 0.0506824 | 0.002142 |
| ORD/retained/uniform | -0.0406841 | 0.00666768 | -0.0112235 | 0.0257926 | 0.0473517 | 0.00243395 |
| ORD/eligible/confidence | -0.0218351 | 0.0086433 | -0.00619677 | 0.02405 | 0.0304784 | 0.0126832 |
| ORD/eligible/uniform | -0.014888 | 0.00857111 | -0.00467701 | 0.0221977 | 0.0234592 | 0.019506 |
| RDFL/retained_without_low/confidence | -0.316489 | 0.0161782 | -0.0368002 | 0.0701229 | 0.332667 | 0.00626623 |
| RDFL/random_size_matched/confidence | -0.0853797 | 0.00592938 | -0.0215407 | 0.0340413 | 0.0913091 | 0.0109317 |
| ORD/ordinary_eligible/uniform | -0.0104718 | 0.00352845 | -0.00686942 | 0.0138388 | 0.0140003 | 0.0104348 |

## thai_calibration

| method_calibration | relative_improvement_vs_zero | signal_term | signal_term_ci95_low | signal_term_ci95_high | variance_term | prediction_outcome_correlation |
| --- | --- | --- | --- | --- | --- | --- |
| ZERO uncalibrated | 0 | 0 | 0 | 0 | 0 |  |
| DIRECT_HUBER uncalibrated | -0.00850794 | 0.000475336 | -0.0127248 | 0.0120599 | 0.00898327 | 0.00684842 |
| HARD_RDFL uncalibrated | -0.206237 | 0.011055 | -0.0361506 | 0.0610425 | 0.217292 | 0.00657768 |
| ORDINARY_SOFT uncalibrated | -0.00981697 | 0.00571299 | -0.00608496 | 0.0170221 | 0.01553 | 0.0153615 |
| RDFL_SOFT uncalibrated | -0.180287 | 0.00794853 | -0.0365447 | 0.0552725 | 0.188235 | 0.00294513 |
| ZERO calibrated | 0 | 0 | 0 | 0 | 0 |  |
| DIRECT_HUBER calibrated | -0.0123759 | 0.00455782 | -0.00690895 | 0.0161347 | 0.0169337 | -0.0103706 |
| HARD_RDFL calibrated | -0.00290111 | 0.00685863 | -0.00235691 | 0.0167368 | 0.00975974 | 0.0107482 |
| ORDINARY_SOFT calibrated | -0.000696755 | 0.00649831 | -0.00190417 | 0.0153535 | 0.00719507 | 0.0112498 |
| RDFL_SOFT calibrated | -0.00325822 | 0.00700547 | -0.00231472 | 0.0169867 | 0.0102637 | 0.0118713 |

## fnspid_pilot

| method | relative_improvement_vs_zero | signal_term | signal_term_ci95_low | signal_term_ci95_high | variance_term | prediction_outcome_correlation |
| --- | --- | --- | --- | --- | --- | --- |
| ZERO | 0 | 0 | 0 | 0 | 0 |  |
| DIRECT_HUBER | -0.00815319 | 0.00033006 | -0.0132061 | 0.0126686 | 0.00848325 | 0.00151021 |
| HARD_RDFL | -0.0904455 | -0.00841286 | -0.0554608 | 0.0244883 | 0.0820326 | -0.0197426 |
| ORDINARY_SOFT | -0.0108127 | -0.00221366 | -0.0195542 | 0.0108631 | 0.00859904 | -0.0181792 |
| RDFL_SOFT | -0.078743 | -0.00566285 | -0.0528709 | 0.0293875 | 0.0730802 | -0.0155442 |

## fnspid_calibrated

| method | relative_improvement_vs_zero | signal_term | signal_term_ci95_low | signal_term_ci95_high | variance_term | prediction_outcome_correlation |
| --- | --- | --- | --- | --- | --- | --- |
| ZERO | 0 | 0 | 0 | 0 | 0 |  |
| DIRECT_HUBER | -0.0187666 | -0.0100726 | -0.038109 | 0.00538543 | 0.008694 | -0.0501571 |
| HARD_RDFL | -0.0138068 | -0.00839986 | -0.0315665 | 0.00494609 | 0.00540694 | -0.0576675 |
| ORDINARY_SOFT | -0.014215 | -0.00837884 | -0.031955 | 0.00545203 | 0.00583611 | -0.0545919 |
| RDFL_SOFT | -0.01477 | -0.00881447 | -0.0335505 | 0.00538514 | 0.00595555 | -0.0579823 |

## fnspid_components

| cell | relative_improvement_vs_zero | signal_term | signal_term_ci95_low | signal_term_ci95_high | variance_term | prediction_outcome_correlation |
| --- | --- | --- | --- | --- | --- | --- |
| RDFL/retained/confidence | -0.078743 | -0.00566285 | -0.0528709 | 0.0293875 | 0.0730802 | -0.0155442 |
| RDFL/retained/uniform | -0.0759512 | -0.00532025 | -0.051484 | 0.028694 | 0.070631 | -0.0150719 |
| RDFL/eligible/confidence | -0.0481361 | -0.00476319 | -0.0382377 | 0.0200655 | 0.0433729 | -0.0160668 |
| RDFL/eligible/uniform | -0.0431471 | -0.00485663 | -0.0350582 | 0.0189795 | 0.0382905 | -0.0166606 |
| ORD/retained/confidence | -0.0239724 | -0.00212508 | -0.0330988 | 0.0222076 | 0.0218473 | -0.0159164 |
| ORD/retained/uniform | -0.0226308 | -0.00206526 | -0.0316821 | 0.021382 | 0.0205655 | -0.0155252 |
| ORD/eligible/confidence | -0.0153203 | -0.00181646 | -0.0253946 | 0.0163308 | 0.0135038 | -0.016603 |
| ORD/eligible/uniform | -0.0123396 | -0.00163999 | -0.0215215 | 0.0142599 | 0.0106996 | -0.0154288 |
| RDFL/retained_without_low/confidence | -0.21279 | -0.0146118 | -0.0815883 | 0.0434102 | 0.198178 | -0.025129 |
| RDFL/random_size_matched/confidence | -0.0462383 | -0.00789708 | -0.0400239 | 0.015383 | 0.0383412 | -0.0252683 |
| ORD/ordinary_eligible/uniform | -0.0108127 | -0.00221366 | -0.0195542 | 0.0108631 | 0.00859904 | -0.0181792 |
