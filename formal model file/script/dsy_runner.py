"""Isolated, resumable weather experiments using unchanged baseline IDFs."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

import numpy as np
import pandas as pd

import batch_runner_v7 as baseline
import revision_metric_audit as audit
from revision_common import FEATURES, TARGETS, ROOT, sha

PROJECT = ROOT.parent
OUTPUT = PROJECT / '02_conference/03_data/weather_scenarios'
DEFAULT_WEATHER = PROJECT / 'CIBSE_weather_files_z1/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1.epw'
EP = Path('/Applications/EnergyPlus-25-1-0/energyplus')
ARCHETYPES = ('detached', 'semi')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, default=str) + '\n')
    temp.replace(path)


def atomic_csv(path, rows):
    temp = path.with_suffix('.tmp')
    pd.DataFrame(rows).sort_values(['archetype', 'run_id']).to_csv(temp, index=False)
    temp.replace(path)


def weather_info(path):
    with path.open(encoding='utf-8-sig') as stream:
        rows = list(csv.reader(stream))
    require(len(rows) == 8768, 'Expected eight EPW header lines and 8760 hours')
    require(rows[0][0] == 'LOCATION', 'Not an EPW LOCATION header')
    expected = [(d.month, d.day, d.hour + 1) for d in pd.date_range('2001-01-01', periods=8760, freq='h')]
    actual = [(int(r[1]), int(r[2]), int(r[3])) for r in rows[8:]]
    require(actual == expected, 'Missing, duplicate or misordered EPW hours')
    require(all(len(r) >= 35 for r in rows[8:]), 'Truncated EPW record')
    require(all(int(r[4]) in (0, 60) for r in rows[8:]), 'Unexpected subhourly EPW minute')
    for index, missing in [(6, 99.9), (7, 99.9), (8, 999), (9, 999999), (12, 9999), (13, 9999), (14, 9999), (15, 9999), (20, 999), (21, 999)]:
        values = np.array([float(r[index]) for r in rows[8:]])
        require(np.isfinite(values).all() and not (values == missing).any(), f'Missing weather column {index}')
    return {'name': path.name, 'sha256': sha(path), 'location': rows[0],
            'description': rows[6], 'hours': 8760,
            'max_drybulb_C': max(float(r[6]) for r in rows[8:])}


def select_ids(frame, mode, count):
    require(frame.run_id.is_unique, 'Duplicate LHS run IDs')
    require(frame.run_id.str.fullmatch(r'run_\d{4}').all(), 'Invalid run ID')
    if mode == 'full':
        return sorted(frame.run_id.tolist())
    require(12 <= count <= len(frame), 'Pilot size must be between 12 and dataset size')
    # Cover input extremes, not observed outputs, then add reproducible random cases.
    selected = set()
    for col in ('wwr', 'g_value', 'wof', 'orientation', 'u_windows'):
        selected.update([frame.loc[frame[col].idxmin(), 'run_id'], frame.loc[frame[col].idxmax(), 'run_id']])
    for run_id in np.random.default_rng(20261003).permutation(frame.run_id):
        if len(selected) >= count:
            break
        selected.add(str(run_id))
    return sorted(selected)


def prepare(args):
    weather = args.weather.resolve()
    info = weather_info(weather)
    require(re.fullmatch(r'[A-Za-z0-9_.-]+', weather.stem), 'Unsafe weather name')
    dest = OUTPUT / weather.stem / args.mode
    source_hashes, inputs, reference = {}, {}, {}
    for arch in ARCHETYPES:
        suffix = '_semi' if arch == 'semi' else ''
        lhs = ROOT / f'output/lhs/lhs_samples_v7{suffix}.csv'
        result = ROOT / f'output/results/results_v7{suffix}.csv'
        inputs[arch] = pd.read_csv(lhs)
        reference[arch] = pd.read_csv(result).set_index('run_id')
        require(len(inputs[arch]) == 2000 and len(reference[arch]) == 2000, 'Expected original 2000 samples')
        require(reference[arch].status.eq('ok').all(), 'Baseline contains failed cases')
        np.testing.assert_allclose(inputs[arch][FEATURES], reference[arch].loc[inputs[arch].run_id, FEATURES], atol=1e-12, rtol=0)
        source_hashes[str(lhs)] = sha(lhs)
        source_hashes[str(result)] = sha(result)
    np.testing.assert_allclose(inputs['detached'][FEATURES], inputs['semi'][FEATURES], atol=1e-12, rtol=0)
    require(inputs['detached'].run_id.equals(inputs['semi'].run_id), 'Unpaired archetype IDs')
    ids = select_ids(inputs['detached'], args.mode, args.pilot_size)
    source_idfs = {}
    for arch in ARCHETYPES:
        for rid in ids:
            path = ROOT / 'output/runs' / arch / rid / 'sim.idf'
            source_idfs[f'{arch}/{rid}'] = sha(path)
    scripts = [Path(__file__), Path(baseline.__file__), Path(audit.__file__), ROOT / 'script/revision_common.py']
    protocol = {'weather': info, 'mode': args.mode, 'run_ids': ids,
                'source_hashes': source_hashes, 'source_idfs': source_idfs,
                'script_hashes': {p.name: sha(p) for p in scripts},
                'energyplus_sha256': sha(EP),
                'energyplus_version': subprocess.check_output([str(EP), '--version'], text=True).strip(),
                'calendar': 'Original IDF 2025 non-leap calendar; EPW is not treated as actual weather',
                'compliance_claim': False, 'selection_seed': 20261003}
    return dest, weather, protocol, inputs, reference


def worker(arch, params, dest, weather, protocol):
    rid = params['run_id']
    folder = dest / 'runs' / arch / rid
    folder.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'output/runs' / arch / rid / 'sim.idf'
    result = dict(params, archetype=arch, status='failed', weather_sha256=protocol['weather']['sha256'])
    start = time.perf_counter()
    try:
        expected_hash = protocol['source_idfs'][f'{arch}/{rid}']
        require(sha(source) == expected_hash, 'Source IDF changed since preflight')
        shutil.copy2(source, folder / 'sim.idf')
        require(sha(folder / 'sim.idf') == expected_hash, 'Copied IDF differs from baseline')
        result['idf_sha256'] = expected_hash
        result['occupancy_minimum'] = audit.occupancy_proof(source.read_text())
        with (folder / 'stdout.log').open('w') as stdout, (folder / 'stderr.log').open('w') as stderr:
            proc = subprocess.run([str(EP), '-w', str(weather), '-d', str(folder), '-r', str(folder / 'sim.idf')],
                                  stdout=stdout, stderr=stderr, timeout=300)
        require(proc.returncode == 0, f'EnergyPlus exit {proc.returncode}')
        errors = (folder / 'eplusout.err').read_text()
        result['severe_errors'] = len(re.findall(r'\*\*\s*Severe\s*\*\*', errors))
        result['warnings'] = len(re.findall(r'\*\*\s*Warning\s*\*\*', errors))
        require('** Fatal' not in errors and result['severe_errors'] == 0, 'EnergyPlus severe/fatal errors')
        raw = pd.read_csv(folder / 'eplusout.csv', usecols=lambda c: c == 'Date/Time' or
                          'Operative Temperature' in c or 'Outdoor Air Drybulb' in c or
                          'Ideal Loads Supply Air Total' in c)
        metrics = audit.calculate(raw, params['width'], params['length'])
        canonical = baseline.compute_targets(folder, params['width'], params['length'])
        for target in TARGETS + ['hours_C3_worst']:
            require(abs(metrics[target] - canonical[target]) < 1e-6, f'Metric mismatch: {target}')
        require(metrics['cooling_kWh'] < 1e-6, 'Active cooling detected')
        result.update(metrics)
        result['csv_sha256'] = sha(folder / 'eplusout.csv')
        result['status'] = 'ok'
    except Exception as exc:
        result['error'] = repr(exc)
    result['sim_sec'] = round(time.perf_counter() - start, 3)
    # Persist scientific results before optional housekeeping. A deletion failure
    # must not invalidate a successful simulation or abort aggregate collection.
    atomic_json(folder / 'result.json', result)
    if result['status'] == 'ok':
        cleanup_warnings = []
        for file in folder.iterdir():
            if file.is_file() and file.suffix not in ('.idf', '.csv', '.err', '.log'):
                if file.name == 'result.json':
                    continue
                try:
                    file.unlink()
                except OSError as exc:
                    cleanup_warnings.append({'file': file.name, 'error': repr(exc)})
        if cleanup_warnings:
            result['cleanup_warnings'] = cleanup_warnings
            atomic_json(folder / 'result.json', result)
    return result


def summarize(dest, rows, reference):
    data = pd.DataFrame(rows)
    good = data[data.status.eq('ok')].copy()
    if good.empty:
        return
    summaries, pairs = [], []
    for arch, group in good.groupby('archetype'):
        summaries.append({'archetype': arch, 'n_ok': len(group),
            'C1_gt3': int((group.He_worst > 3).sum()), 'C2_gt6': int((group.We_max_worst > 6).sum()),
            'C3_nonzero': int((group.hours_C3_worst > 0).sum()),
            'two_of_three_proxy': int(group.two_of_three_proxy_dwelling.sum()),
            'night_zero_pct': 100 * group.hours_gt26_night.eq(0).mean(),
            'night_summer_gt32': int((group.hours_gt26_night > 32).sum()),
            'night_annual_gt32': int((group.hours_gt26_night_annual > 32).sum()),
            'max_peak_C': float(group.T_op_peak.max()), 'max_cooling_kWh': float(group.cooling_kWh.max())})
        for row in group.to_dict('records'):
            pair = {'archetype': arch, 'run_id': row['run_id']}
            for target in TARGETS + ['hours_C3_worst']:
                old = float(reference[arch].loc[row['run_id'], target])
                pair[f'TMYx_{target}'] = old
                pair[f'DSY_{target}'] = row[target]
                pair[f'delta_{target}'] = row[target] - old
            pairs.append(pair)
    pd.DataFrame(summaries).to_csv(dest / 'summary.csv', index=False)
    atomic_csv(dest / 'paired_comparison.csv', pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weather', type=Path, default=DEFAULT_WEATHER)
    parser.add_argument('--mode', choices=['pilot', 'full'], default='pilot')
    parser.add_argument('--pilot-size', type=int, default=20)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--execute', action='store_true', help='Otherwise read-only preflight')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    require(1 <= args.workers <= 16, 'Workers must be 1..16')
    dest, weather, protocol, inputs, reference = prepare(args)
    print(json.dumps({'output': str(dest), 'weather': protocol['weather'],
                      'runs_per_archetype': len(protocol['run_ids']), 'execute': args.execute}, indent=2), flush=True)
    if not args.execute:
        return
    if args.mode == 'full':
        pilot = dest.parent / 'pilot'
        gate = json.loads((pilot / 'completion.json').read_text())
        old_protocol = json.loads((pilot / 'protocol.json').read_text())
        require(gate['all_ok'] and gate['runs'] >= 40, 'A passing >=40-run pilot is required')
        for key in ['weather', 'source_hashes', 'script_hashes', 'energyplus_sha256']:
            require(old_protocol[key] == protocol[key], f'Pilot provenance changed: {key}')
    if (dest / 'protocol.json').exists():
        require(args.resume, 'Output already exists; use --resume, never overwrite')
        require(json.loads((dest / 'protocol.json').read_text()) == protocol, 'Resume provenance mismatch')
    else:
        require(not dest.exists(), 'Unrecognized existing output folder')
        dest.mkdir(parents=True)
        atomic_json(dest / 'protocol.json', protocol)
    atomic_json(dest / 'execution.json', {'workers': args.workers, 'platform': platform.platform(),
                'started_utc': datetime.now(timezone.utc).isoformat(), 'resume': args.resume})
    jobs, rows = [], []
    for arch in ARCHETYPES:
        frame = inputs[arch].set_index('run_id')
        for rid in protocol['run_ids']:
            saved = dest / 'runs' / arch / rid / 'result.json'
            if args.resume and saved.exists():
                record = json.loads(saved.read_text())
                if record['status'] == 'ok':
                    require(record['weather_sha256'] == protocol['weather']['sha256'], 'Saved weather mismatch')
                    require(record['idf_sha256'] == sha(saved.parent / 'sim.idf') == protocol['source_idfs'][f'{arch}/{rid}'], 'Saved IDF mismatch')
                    require(record['csv_sha256'] == sha(saved.parent / 'eplusout.csv'), 'Saved CSV mismatch')
                    rows.append(record)
                    continue
            jobs.append((arch, dict(frame.loc[rid], run_id=rid), dest, weather, protocol))
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(worker, *job) for job in jobs]
        for future in as_completed(futures):
            record = future.result()
            rows.append(record)
            atomic_csv(dest / 'results.csv', rows)
            print(f"[{len(rows)}/{2*len(protocol['run_ids'])}] {record['archetype']} {record['run_id']} {record['status']} {record.get('error', '')}", flush=True)
    atomic_csv(dest / 'results.csv', rows)
    summarize(dest, rows, reference)
    for path, expected in protocol['source_hashes'].items():
        require(sha(path) == expected, f'Baseline modified: {path}')
    require(sha(weather) == protocol['weather']['sha256'], 'Weather changed during execution')
    complete = {'runs': len(rows), 'all_ok': all(r['status'] == 'ok' for r in rows),
                'elapsed_seconds_this_execution': time.perf_counter()-start,
                'baseline_files_unchanged': True, 'pilot_not_population_estimate': args.mode == 'pilot'}
    atomic_json(dest / 'completion.json', complete)
    print(json.dumps(complete, indent=2), flush=True)
    require(complete['all_ok'], 'Failures remain; inspect outputs before full run')


if __name__ == '__main__':
    main()
