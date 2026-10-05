"""Independent geometry/material/control checks on every corrected building IDF."""
import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd

from simulate import ROOT, patcher, require, sha, json_out


def main():
    checked, bearings_checked = 0, 0
    for arch in ['detached', 'semi']:
        lhs = pd.read_csv(ROOT / 'inputs' / f'lhs_{arch}.csv').set_index('run_id')
        files = sorted((ROOT / 'inputs/idfs' / arch).glob('*.idf'))
        require(len(files) == 2000, 'Missing corrected IDFs')
        for path in files:
            row = lhs.loc[path.stem]
            obs = [o['fields'] for o in patcher.parsed(path.read_text())]
            named = {(f[0].lower(), f[1]): f for f in obs if len(f) > 1}
            north = float(named['building', 'Building 1'][2])
            require(abs(north-row.orientation) < 1e-10, 'Building rotation changed')
            zones = {f[1]: float(f[2] or 0) for f in obs if f[0] == 'Zone'}
            bearings = {}
            for f in obs:
                if f[0] == 'BuildingSurface:Detailed' and f[2] == 'Wall' and f[6] == 'Outdoors' and f[4] != 'Thermal Zone: Space 1':
                    v = np.array(list(map(float, f[12:]))).reshape(-1, 3)
                    normal = np.cross(v[1]-v[0], v[2]-v[0])
                    local = math.degrees(math.atan2(normal[0], normal[1])) % 360
                    direction = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}[round(local)]
                    bearings[f[4], direction] = (local+north+zones[f[4]]) % 360
            for f in obs:
                if f[0].lower() == 'zoneventilation:windandstackopenarea':
                    expected = bearings[f[2], f[1].split('_')[-1]]
                    error = abs(((float(f[6])-expected+180) % 360)-180)
                    require(error < 1e-8, f'Opening does not match wall normal: {path}, {f[1]}')
                    bearings_checked += 1
            for name in ['Surface 6', 'Surface 7']:
                require(named['buildingsurface:detailed', name][3] == 'Audit_Interfloor_RC_100mm', 'Intermediate floor mismatch')
            require(named['construction', 'Audit_Interfloor_RC_100mm'][2:] == ['RC_Slab_100mm'], 'Intermediate floor includes unintended material')
            require(named['buildingsurface:detailed', 'Surface 12'][3] == 'Interior Ceiling', 'Loft ceiling changed')
            require(named['buildingsurface:detailed', 'Surface 13'][3] == 'Interior Floor', 'Loft floor changed')
            require(named['construction', 'Interior Ceiling'][2:] == ['Roof Insulation', 'RC_Slab_100mm'], 'Loft insulation missing')
            require(abs(float(named['material', 'Roof Insulation'][3])-row.roofInsulationThickness) < 1e-10, 'Wrong sampled loft insulation')
            shades = [f for f in obs if f[0].lower() == 'windowshadingcontrol']
            require(len(shades) == 2 and all(f[6] == 'OnIfHighZoneAirTemperature' and float(f[8]) == 26.5 for f in shades), 'Automatic shades changed')
            east_attic = named['buildingsurface:detailed', 'Surface 16']
            expected_boundary = ['Adiabatic', '', 'NoSun', 'NoWind'] if arch == 'semi' else ['Outdoors', '', 'SunExposed', 'WindExposed']
            require(east_attic[6:10] == expected_boundary, 'Attic boundary mismatch')
            checked += 1
    tree = ast.parse((ROOT / 'scripts/simulate.py').read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'run']
    require(len(calls) == 1 and any(k.arg == 'cwd' for k in calls[0].keywords), 'Subprocess must have an isolated cwd')
    record = dict(idfs_checked=checked, opening_bearings_checked=bearings_checked,
        controls_and_materials_verified=True, subprocess_cwd_verified=True,
        verifier_sha256=sha(Path(__file__)))
    json_out(ROOT / 'reports/idf_verification.json', record)
    print(record, flush=True)


if __name__ == '__main__':
    main()
