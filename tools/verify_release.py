"""Verify this release without any of the withheld data. Standard library only.

1. Every file in SHA256SUMS is present and unchanged (this also catches line-ending conversion).
2. The replication lock: the archived files match the original freeze record, each released file
   equals its archived original after the renaming in tools/rename_rules.py, and the derived record
   in research/ holds the same frozen time and the hashes of the released files.
3. Provenance: archived snapshots match the original manifests, and released snapshots equal them
   after renaming; withheld data snapshots are counted.
4. Each result run is complete, and the code it executed is byte-identical to the released code.
5. Every archived original result table equals the released table after renaming.

Usage (from the repository root):  python tools/verify_release.py
"""
import csv
import hashlib
import io
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rename_rules as r  # noqa: E402

EXECUTED = {   # scripts each run executed, besides config.json, scripts/common.py and the snapshotted code
    'simulation': ['scripts/01_simulation.py'],
    'purged_pilot': ['scripts/02_purged_pilot.py'],
    'report': ['scripts/03_inference_and_report.py'],
    'power': ['scripts/07_power_analysis.py'],
    'equivalence_power': ['scripts/12_equivalence_power.py'],
    'factorial_ablation': ['scripts/13_factorial_ablation.py', 'scripts/12_equivalence_power.py'],
    'provenance_checks': ['scripts/14_provenance_checks.py'],
    'near_duplicate_sensitivity': ['scripts/15_near_duplicate_sensitivity.py', 'scripts/13_factorial_ablation.py',
                                   'scripts/12_equivalence_power.py'],
    'rdfl_component_ablation': ['scripts/16_rdfl_component_ablation.py', 'scripts/12_equivalence_power.py'],
    'staleness': ['scripts/17_staleness.py'],
    'simulation_extensions': ['scripts/18_simulation_extensions.py', 'scripts/01_simulation.py'],
    'fnspid_prepared': ['scripts/20_fnspid_prepare.py'],
    'fnspid_replication': ['scripts/21_fnspid_replication.py', 'scripts/13_factorial_ablation.py',
                           'scripts/16_rdfl_component_ablation.py', 'scripts/12_equivalence_power.py'],
    'prediction_dispersion': ['scripts/22_prediction_dispersion.py'],
    'observable_bounds': ['scripts/23_observable_bounds.py', 'scripts/18_simulation_extensions.py'],
    'per_block': ['scripts/24_per_block_results.py'],
    'threshold_sensitivity': ['scripts/25_threshold_sensitivity.py', 'scripts/12_equivalence_power.py',
                              'scripts/16_rdfl_component_ablation.py', 'scripts/21_fnspid_replication.py'],
    'loss_decomposition': ['scripts/26_loss_decomposition.py'],
    'random_abstention': ['scripts/27_random_abstention.py', 'scripts/18_simulation_extensions.py'],
    'block_stability': ['scripts/28_block_stability.py', 'scripts/13_factorial_ablation.py',
                        'scripts/12_equivalence_power.py'],
    'signal_contrasts': ['scripts/29_signal_contrasts.py', 'scripts/16_rdfl_component_ablation.py',
                         'scripts/12_equivalence_power.py'],
    'historical_mean': ['scripts/30_historical_mean.py', 'scripts/13_factorial_ablation.py',
                        'scripts/12_equivalence_power.py'],
    'data_flow': ['scripts/31_data_flow.py'],
}
ALWAYS = ('config.json', 'scripts/common.py', 'provenance/source_code/', 'provenance/supplement/source_code/')
VOLATILE = {'started_utc', 'completed_utc', 'generated_at_utc', 'identity', 'versions', 'python'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def value(cell):
    try:
        number = float(cell)
    except ValueError:
        return cell
    return 'nan' if math.isnan(number) else f'{number:.10g}'


def table(data):
    rows = list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
    header, body = rows[0], rows[1:]
    order = sorted(range(len(header)), key=lambda i: header[i])
    return [header[i] for i in order], Counter(tuple(value(row[i]) for i in order) for row in body)


def strip(item):
    if isinstance(item, dict):
        return {k: strip(v) for k, v in item.items() if k not in VOLATILE}
    if isinstance(item, list):
        return [strip(v) for v in item]
    if isinstance(item, float):
        return value(repr(item))
    return item


def main():
    failures = []

    def check(condition, message):
        if not condition:
            failures.append(message)

    listed = 0
    for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        expected, relative = line.split(maxsplit=1)
        path = ROOT / relative
        check(path.is_file() and sha(path) == expected, f'missing or changed released file: {relative}')
        listed += 1
    print(f'[1] released files checked: {listed}')

    original, derived = load('archive/research/PREREGISTRATION_FREEZE.json'), load('research/PREREGISTRATION_FREEZE.json')
    check(derived['frozen_utc'] == original['frozen_utc'], 'derived freeze record has a different frozen time')
    check(set(derived['sha256']) == {r.rename_path(p) for p in original['sha256']}, 'derived record lists other files')
    for relative, expected in original['sha256'].items():
        archived, released = ROOT / 'archive' / relative, ROOT / r.rename_path(relative)
        check(archived.is_file() and sha(archived) == expected, f'archived locked file changed: {relative}')
        check(released.is_file() and released.read_bytes() == r.released_bytes(relative, archived.read_bytes()),
              f'released file differs from its locked original by more than the renaming: {released.name}')
        check(released.is_file() and sha(released) == derived['sha256'].get(r.rename_path(relative)),
              f'derived record does not match released file: {released.name}')
    print(f'[2] protocol frozen {original["frozen_utc"]}; locked files checked: {len(original["sha256"])} '
          f'(archived originals, renaming, derived record)')

    released_count = withheld = 0
    for manifest in ('archive/provenance/manifest.json', 'archive/provenance/supplement/manifest.json'):
        for item in load(manifest)['files']:
            snapshot = item['snapshot'].replace('\\', '/')
            archived, released = ROOT / 'archive' / snapshot, ROOT / r.rename_path(snapshot)
            if not archived.is_file():
                withheld += 1
                check(not released.exists(), f'released file without archived original: {snapshot}')
                continue
            check(sha(archived) == item['sha256'], f'archived snapshot changed: {snapshot}')
            check(released.is_file() and released.read_bytes() == r.released_bytes(snapshot, archived.read_bytes()),
                  f'released snapshot differs from its original by more than the renaming: {snapshot}')
            released_count += 1
    print(f'[3] provenance snapshots verified: {released_count}; withheld (data not redistributed): {withheld}')

    for name, scripts in EXECUTED.items():
        run = ROOT / 'results' / name
        check((run / 'COMPLETE.json').is_file(), f'{name}: run not complete')
        identity = {k.replace('\\', '/'): v for k, v in load(f'results/{name}/run_manifest.json')['identity'].items()}
        check(all(s in identity for s in scripts), f'{name}: executed script missing from run identity')
        for relative in (k for k in identity if k in scripts or k.startswith(ALWAYS)):
            check((ROOT / relative).is_file() and sha(ROOT / relative) == identity[relative],
                  f'{name}: executed code differs from release: {relative}')
    print(f'[4] result runs checked against the code that produced them: {len(EXECUTED)}')

    compared = 0
    for archived in sorted((ROOT / 'archive' / 'results').rglob('*')):
        relative = archived.relative_to(ROOT / 'archive').as_posix()
        if archived.suffix not in {'.csv', '.json'} or archived.name in {'run_manifest.json', 'COMPLETE.json'}:
            continue
        released = ROOT / r.rename_path(relative)
        if not released.is_file():
            check(False, f'original result without released counterpart: {relative}')
            continue
        renamed = r.rename_bytes(archived.read_bytes())
        if archived.suffix == '.csv':
            same = table(renamed) == table(released.read_bytes())
        else:
            same = strip(json.loads(renamed.decode('utf-8'))) == strip(json.loads(released.read_text(encoding='utf-8')))
        check(same, f'released result differs from the original run: {released.relative_to(ROOT).as_posix()}')
        compared += 1
    print(f'[5] original result tables compared with the rerun after renaming: {compared}')

    if failures:
        print('\nFAIL')
        for message in failures:
            print(' -', message)
        sys.exit(1)
    print('\nPASS')


if __name__ == '__main__':
    main()
