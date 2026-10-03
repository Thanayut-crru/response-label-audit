# Oracle and Observable Lower Bounds on Component-Absence Error

Status: **KNOWN-TRUTH SIMULATION; CANCELLATION 0.85; DELTA 0.35**

Oracle: requires the latent net response S. Observable: uses only Y and the known noise law.

| lambda | error | oracle_lower_known_S | observable_lower_known_gaussian_noise | observable_lower_max_over_seeds | naive_plug_in_share |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.800889 | 0.0200975 | 0 | 0 | 0.0198858 |
| 0.25 | 0.805609 | 0.0205322 | 0 | 0 | 0.0198936 |
| 0.5 | 0.809951 | 0.0211598 | 0 | 0 | 0.019922 |
| 0.75 | 0.813684 | 0.0213791 | 0 | 0 | 0.019892 |
| 1 | 0.816902 | 0.0216617 | 0 | 0 | 0.0198735 |

The naive plug-in share replaces S by Y and is not a valid bound under noise.
