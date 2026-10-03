from __future__ import annotations
import hashlib
import importlib.util
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def load_legacy(filename):
    path = ROOT / 'provenance' / 'source_code' / filename
    spec = importlib.util.spec_from_file_location('legacy_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def identity():
    paths = [ROOT / 'config.json', *sorted((ROOT / 'scripts').glob('*.py')),
             *sorted((ROOT / 'provenance' / 'source_code').glob('*.py'))]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}

def start_run(name, resume=False):
    out = ROOT / 'results' / name
    manifest = out / 'run_manifest.json'
    if (out / 'COMPLETE.json').exists():
        raise RuntimeError(f'Refusing to overwrite completed run: {out}')
    if manifest.exists():
        old = json.loads(manifest.read_text(encoding='utf-8'))
        if not resume or old['identity'] != identity():
            raise RuntimeError('Run exists or its code/config hashes changed; use a new output name.')
        return out
    out.mkdir(parents=True, exist_ok=True)
    import scipy, sklearn
    dump(manifest, {'started_utc': datetime.now(timezone.utc).isoformat(),
                   'identity': identity(), 'config': CONFIG, 'python': platform.python_version(),
                   'versions': {'numpy': np.__version__, 'pandas': pd.__version__,
                                'scipy': scipy.__version__, 'sklearn': sklearn.__version__}})
    return out

def complete(out, **details):
    dump(out / 'COMPLETE.json', {'completed_utc': datetime.now(timezone.utc).isoformat(), **details})

def holm(pvalues):
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    adjusted = np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1))
    result = np.empty(len(p))
    result[order] = np.minimum(adjusted, 1.0)
    return result

def bootstrap_paired(a, b, iterations, rng, block=1):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape or a.ndim != 1 or not np.isfinite([a,b]).all() or len(a) < 2:
        raise ValueError('Need aligned finite paired losses with at least two observations')
    n = len(a)
    diffs, ratios = [], []
    for lo in range(0, iterations, 256):
        size = min(256, iterations-lo)
        starts = rng.integers(0, n, size=(size, int(np.ceil(n/block))))
        idx = ((starts[...,None]+np.arange(block)) % n).reshape(size,-1)[:,:n]
        ma, mb = a[idx].mean(axis=1), b[idx].mean(axis=1)
        diffs.append(ma-mb)
        ratios.append(np.divide(ma-mb, ma, out=np.full(size, np.nan), where=ma>1e-15))
    return np.concatenate(diffs), np.concatenate(ratios)

def interval(values, alpha=0.05):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return [float(x) for x in np.quantile(values, [alpha/2,1-alpha/2])] if len(values) else [None,None]

def markdown(frame):
    frame = frame.copy()
    def fmt(x):
        if isinstance(x, (float, np.floating)):
            return '' if not np.isfinite(x) else f'{x:.6g}'
        return str(x).replace('|','/')
    rows = ['| ' + ' | '.join(map(str, frame.columns)) + ' |',
            '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |']
    rows += ['| ' + ' | '.join(fmt(x) for x in row) + ' |' for row in frame.itertuples(index=False,name=None)]
    return '\n'.join(rows)
