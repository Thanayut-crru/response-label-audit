"""Read-only supplementary ingestion from IEEE for the r5 revision.

The original snapshot in provenance/manifest.json is frozen and refuses to be
replaced. The factorial ablation and the provenance checks need four further
sources: the P2c calibration code (so calibration is imported, not
re-implemented), the uncalibrated P2b predictions (so the historical pipeline
can be reproduced), and the raw price panels (so the OHLC basis can be checked).
They are frozen here under a separate manifest with the same whitelist rules.
"""
from pathlib import Path
import shutil
from datetime import datetime, timezone
from common import ROOT, CONFIG, sha, dump

SYMBOLS = ['BAY', 'BBL', 'KBANK', 'KKP', 'KTB', 'SCB', 'TISCO', 'TTB']


def main():
    source = Path(CONFIG['source_root']).resolve()
    out = ROOT / 'provenance' / 'supplement'
    if (out / 'manifest.json').exists():
        raise RuntimeError('Supplementary snapshot already frozen; refusing to replace it')
    targets = {
        'experiments/rdfl_phafin/05_calibrate_text_predictions.py': 'source_code/05_calibrate_text_predictions.py',
        'results/rdfl_phafin/p2b_tfidf_label_methods/predictions.csv': 'historical/p2b_tfidf_label_methods/predictions.csv',
        'results/rdfl_phafin/p2b_tfidf_label_methods/fold_manifest.csv': 'historical/p2b_tfidf_label_methods/fold_manifest.csv',
        'results/rdfl_phafin/p2b_tfidf_label_methods/summary.json': 'historical/p2b_tfidf_label_methods/summary.json',
    }
    for symbol in SYMBOLS:
        targets[f'data/raw/financial/panel_{symbol}.csv'] = f'raw_financial/panel_{symbol}.csv'
    records = []
    for relative, destination in targets.items():
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or 'results/metrics/' in relative:
            raise RuntimeError('Source outside evidence whitelist')
        dest = out / destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        assert sha(path) == sha(dest)
        records.append({'source': str(path), 'snapshot': str(dest.relative_to(ROOT)),
                        'sha256': sha(dest), 'bytes': dest.stat().st_size})
    dump(out / 'manifest.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
         'source_root': str(source), 'files': records,
         'purpose': 'r5 factorial ablation and provenance checks',
         'excluded': 'results/metrics/ and random-FT performance'})
    print(f'Frozen {len(records)} supplementary sources', flush=True)


if __name__ == '__main__':
    main()
