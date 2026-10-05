"""Shared paths and definitions for the non-DSY reviewer revision."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'reviewer_revision'
TARGETS = ['He_worst', 'We_max_worst', 'T_op_peak', 'hours_gt26_night', 'heat_kWh_m2']
FEATURES = ['width', 'length', 'height', 'orientation', 'wwr',
            'wallInsulationThickness', 'roofInsulationThickness', 'slabInsulationThickness',
            'u_windows', 'g_value', 'roofAbsorptance', 'flowCoefficient', 'wof', 'fixedShadingDepth']
LABELS = ['Width', 'Length', 'Storey height', 'Orientation', 'WWR', 'Wall insulation',
          'Roof insulation', 'Slab insulation', 'Window U-factor', 'g-value',
          'Roof absorptance', 'Infiltration coefficient', 'Window opening factor', 'Overhang depth']
UNITS = ['percentage points', 'K h (stepped proxy)', 'deg C', 'hours', 'kWh/m2/year']
TITLES = ['Seasonal exceedance proxy', 'Stepped daily exceedance proxy',
          'Peak operative temperature', 'Summer bedroom night exceedance', 'Ideal heating demand intensity']

def data_path(arch):
    return ROOT / 'output/results' / ('results_v7_semi.csv' if arch == 'semi' else 'results_v7.csv')

def dataset(arch):
    d = pd.read_csv(data_path(arch))
    assert len(d) == 2000 and d.status.eq('ok').all()
    assert d.run_id.is_unique and np.isfinite(d[FEATURES + TARGETS]).all().all()
    return d.reset_index(drop=True)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + '\n')
