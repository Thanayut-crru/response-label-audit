"""Lock the external-replication protocol and every file the replication executes.

Writes research/PREREGISTRATION_FREEZE.json once, with a UTC timestamp and the
SHA-256 of each frozen file. Scripts 20 and 21 refuse to run if any hash differs.
The record is immutable: this script refuses to overwrite it.
"""
from datetime import datetime, timezone

import common

FROZEN = [
    'research/PREREGISTRATION_r6.md',
    'research/FNSPID_INSPECTION.json',
    'config.json',
    'scripts/common.py',
    'scripts/12_equivalence_power.py',
    'scripts/13_factorial_ablation.py',
    'scripts/16_rdfl_component_ablation.py',
    'scripts/20_fnspid_prepare.py',
    'scripts/21_fnspid_replication.py',
    'provenance/source_code/01_build_pilot_labels.py',
    'provenance/source_code/04_run_tfidf_label_methods.py',
    'provenance/supplement/source_code/05_calibrate_text_predictions.py',
]


def main():
    out = common.ROOT / 'research' / 'PREREGISTRATION_FREEZE.json'
    if out.exists():
        raise RuntimeError('Protocol already frozen; the record is immutable')
    common.dump(out, {'frozen_utc': datetime.now(timezone.utc).isoformat(),
                      'outcomes_seen_before_freeze': False,
                      'sha256': {path: common.sha(common.ROOT / path) for path in FROZEN}})
    print(out.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
