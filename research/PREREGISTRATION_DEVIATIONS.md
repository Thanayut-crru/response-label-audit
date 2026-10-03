# Deviations from the Locked Replication Protocol

Protocol: `research/PREREGISTRATION_r6.md`, frozen 2026-09-28T07:27:01Z
(`research/PREREGISTRATION_FREEZE.json`). The protocol file itself is hash-locked, so deviations are
recorded here instead of in its section 7.

| # | When | What | Effect on the analysis |
|---|---|---|---|
| 1 | After the run completed (07:29:45Z) | The final console echo of `HYPOTHESES.md` in `21_fnspid_replication.py` raised a Windows `cp874` encoding error on the "±" character. Every output file and `COMPLETE.json` had already been written. | None. No code was changed and nothing was rerun. |
| 2 | Revision r7, after the run | Section 2 of the protocol states that FNSPID is released under CC BY 4.0. That was the license of the arXiv paper, not of the dataset: the dataset's repository LICENSE is Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0). The dataset was used for non-commercial research only; FNSPID and derived files containing its text are not redistributed. | None on the analysis. The locked protocol file is left unchanged so that its hash still verifies; this entry is the correction. |
| 3 | Revision r7, after the run | Terminology. The protocol calls itself "locked"; the manuscript now calls the replication "locally hash-locked", because the freeze record is local and the protocol was not publicly registered before the run. | None on the analysis. |
| 4 | MDPI revision, 2026-09-30, after all results were known | An additional analysis outside the protocol: `25_threshold_sensitivity.py` varies the label rule's retention threshold (none, 0.50, 0.60, 0.70, 0.80, 0.90) and response-band percentiles (20th–80th, 40th–60th) on the Thai pilot and on the prepared FNSPID data, with everything else of RDFL_SOFT fixed. | None on the locked hypotheses or their verdicts: no locked file or earlier result was changed, and the original setting reproduces the published RDFL_SOFT predictions. The analysis is reported as exploratory, with every setting in its grid. |
| 5 | Public release, 2026-10-01, after all results were known | The procedure is renamed RDFL in the released code, protocol text, and outputs by the byte-level substitution in `tools/rename_rules.py`; `scripts/07_power_analysis.py` also subtracts one character per renamed occurrence from the name length it uses for bootstrap seeds. The files as frozen, the original freeze record, the provenance manifests, and the original outputs are kept byte-identical in `archive/`; `research/PREREGISTRATION_FREEZE.json` in the release is derived from the archived record by the same renaming. | None on the analysis. Every result was rerun with the renamed code and all 118 outputs match the originals (`results/RENAME_EQUIVALENCE.json`); `tools/verify_release.py` checks that each renamed locked file equals its archived original after renaming. |

Order of work, from the freeze record and run manifests:

1. 2026-09-28 07:24:46Z — `20_fnspid_prepare.py --inspect` (counts and dates only) wrote `research/FNSPID_INSPECTION.json`
2. 07:27:01Z — protocol frozen
3. 07:27:07Z–07:27:41Z — `20_fnspid_prepare.py` (panels, news, labels)
4. 07:27:56Z–07:29:45Z — `21_fnspid_replication.py` (single run)
5. 2026-09-30 16:07:23Z–16:08:41Z — `25_threshold_sensitivity.py` (exploratory, outside the protocol; entry 4)
6. 2026-10-01 — every result rerun with the renamed code for the public release (entry 5)

No FNSPID return, label, or model output was examined before step 2, and no choice of the locked
analysis was changed after step 4.
