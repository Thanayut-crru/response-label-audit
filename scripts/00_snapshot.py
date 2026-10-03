"""Read-only ingestion from IEEE. Never ingest results/metrics/."""
from pathlib import Path
import shutil
import json
from datetime import datetime, timezone
from common import ROOT, CONFIG, sha, dump

def main():
    source = Path(CONFIG['source_root']).resolve()
    out = ROOT / 'provenance'
    if (out / 'manifest.json').exists():
        raise RuntimeError('Snapshot already frozen; refusing to replace it')
    relatives = [
        'results/rdfl_phafin/p0_audit/AUDIT_REPORT.md',
        'results/rdfl_phafin/p0_audit/audit.json',
        'results/rdfl_phafin/p3_known_truth_simulation/replication_metrics.csv',
        'results/rdfl_phafin/p3_known_truth_simulation/simulation_config.json',
        'results/rdfl_phafin/p2c_forward_calibration/calibrated_predictions.csv',
        'results/rdfl_phafin/p2c_forward_calibration/summary.json',
        'results/rdfl_phafin/p1_pilot_labels/article_to_stock_day_pilot.csv',
        'results/rdfl_phafin/p1_pilot_labels/stock_day_labels_pilot.csv',
    ]
    codes = ['experiments/rdfl_phafin/06_run_known_truth_simulation.py',
             'experiments/rdfl_phafin/04_run_tfidf_label_methods.py',
             'experiments/rdfl_phafin/01_build_pilot_labels.py',
             'scripts/00_finetune_phayathai.py']
    records = []
    for relative in relatives + codes:
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or 'results/metrics/' in relative:
            raise RuntimeError('Source outside evidence whitelist')
        dest = out / ('source_code' if relative in codes else 'historical') / (
            path.name if relative in codes else str(Path(relative).relative_to('results/rdfl_phafin')))
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest)
        assert sha(path) == sha(dest)
        records.append({'source':str(path),'snapshot':str(dest.relative_to(ROOT)),
                        'sha256':sha(dest),'bytes':dest.stat().st_size})
    dump(out / 'manifest.json', {'created_utc':datetime.now(timezone.utc).isoformat(),
         'source_root':str(source),'files':records,'excluded':'results/metrics/ and random-FT performance'})
    print(f'Frozen {len(records)} sources; prohibited metrics excluded',flush=True)

if __name__ == '__main__':
    main()
