"""Isolated full corrected simulation: preserve all legacy results and manuscripts."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
FORMAL = PROJECT / 'formal model file'
PILOT = PROJECT / '02_conference/06_model_sensitivity/2026-10-04_idf_audit'
OLD_DSY = PROJECT / '02_conference/03_data/weather_scenarios/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1/full'
OLD_EVAL = PROJECT / '02_conference/03_data/evaluation'
FROZEN = ROOT / 'frozen_code'
EP = Path('/Applications/EnergyPlus-25-1-0/energyplus')
sys.path.insert(0, str(FROZEN if FROZEN.exists() else FORMAL / 'script'))
import revision_metric_audit as audit
import batch_runner_v7 as baseline
from revision_common import FEATURES, TARGETS

PATCHER = FROZEN / 'pilot_idf.py' if FROZEN.exists() else PILOT / 'scripts/run_sensitivity.py'
spec = importlib.util.spec_from_file_location('pilot_idf', PATCHER)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)
sys.path.insert(0, str(FROZEN if FROZEN.exists() else FORMAL / 'script'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_out(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + '\n')
    temp.replace(path)


def csv_out(path, frame):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    frame.to_csv(temp, index=False)
    temp.replace(path)


def metric_check(folder, width, length):
    raw = pd.read_csv(folder / 'eplusout.csv', usecols=lambda c: c == 'Date/Time' or 'Operative Temperature' in c or 'Outdoor Air Drybulb' in c or 'Ideal Loads Supply Air Total' in c)
    values = audit.calculate(raw, width, length)
    independent = baseline.compute_targets(folder, width, length)
    for target in TARGETS + ['hours_C3_worst']:
        require(abs(values[target] - independent[target]) < 1e-6, f'Target mismatch: {target}')
    require(values['cooling_kWh'] < 1e-6, 'Active cooling')
    return values


def prepare():
    require(not (ROOT / 'protocol.json').exists(), 'Already prepared; originals must never be overwritten')
    prior = json.loads((PILOT / 'results/verification.json').read_text())
    require(prior['unique_successful_runs'] == 1452 and prior['controls_exact'], 'Pilot gate failed')
    prior_protocol = json.loads((PILOT / 'protocol.json').read_text())
    require(sha(PILOT / 'backup/original_inputs.zip') == prior['backup_sha256'], 'Original backup changed')
    protected = json.loads((PILOT / 'backup/source_hashes.json').read_text())
    for name, digest in protected.items():
        require(sha(name) == digest, f'Legacy source changed since pilot: {name}')
    for folder in ['backup', 'inputs', 'weather', 'frozen_code', 'reports', 'figures', 'datasets', 'logs']:
        (ROOT / folder).mkdir(exist_ok=True)
    for name in ['revision_metric_audit.py', 'batch_runner_v7.py', 'revision_common.py', 'revision_model_eval.py', 'dsy_model_eval.py']:
        src = FORMAL / 'script' / name
        shutil.copy2(src, FROZEN / name)
        protected[str(src)] = sha(src)
    shutil.copy2(PILOT / 'scripts/run_sensitivity.py', FROZEN / 'pilot_idf.py')
    protected[str(PILOT / 'scripts/run_sensitivity.py')] = sha(PILOT / 'scripts/run_sensitivity.py')
    for p in [OLD_EVAL / 'protocol.json', OLD_DSY / 'evaluation/protocol.json']:
        protected[str(p)] = sha(p)
    shutil.copy2(OLD_EVAL / 'protocol.json', ROOT / 'backup/original_model_protocol.json')
    # Reference the verified 82 MB backup instead of creating confusing duplicate archives.
    json_out(ROOT / 'backup/original_backup_reference.json', {'path': str(PILOT / 'backup/original_inputs.zip'), 'sha256': prior['backup_sha256'], 'contents': 'All 4000 original IDFs, templates, configs, weather, key scripts, datasets and original manuscripts.'})
    json_out(ROOT / 'backup/protected_sources.json', protected)
    for weather in ['TMYx', 'DSY1']:
        shutil.copy2(PILOT / 'inputs' / f'{weather}.epw', ROOT / 'weather' / f'{weather}.epw')
    lhs = {}
    changes, pilot_refs = {}, {}
    old_audit = pd.read_csv(PROJECT / '02_conference/03_data/audit/hourly_audit.csv')
    old_dsy = pd.read_csv(OLD_DSY / 'results.csv')
    for arch in ['detached', 'semi']:
        suffix = '_semi' if arch == 'semi' else ''
        lhs[arch] = pd.read_csv(FORMAL / f'output/lhs/lhs_samples_v7{suffix}.csv').sort_values('run_id').reset_index(drop=True)
        original = pd.read_csv(FORMAL / f'output/results/results_v7{suffix}.csv').set_index('run_id')
        require(len(lhs[arch]) == 2000 and lhs[arch].run_id.is_unique, 'LHS incomplete')
        np.testing.assert_allclose(lhs[arch][FEATURES], original.loc[lhs[arch].run_id, FEATURES], atol=1e-12, rtol=0)
        lhs[arch].to_csv(ROOT / 'inputs' / f'lhs_{arch}.csv', index=False)
        path = ROOT / 'inputs/idfs' / arch
        path.mkdir(parents=True)
        for row in lhs[arch].to_dict('records'):
            rid = row['run_id']
            source = FORMAL / 'output/runs' / arch / rid / 'sim.idf'
            require(sha(source) == sha(OLD_DSY / 'runs' / arch / rid / 'sim.idf'), 'Original weather inputs differ')
            new, log = patcher.modify(source.read_text(), 'combined', arch)
            (path / f'{rid}.idf').write_text(new)
            audit.occupancy_proof(new)
            changes[f'{arch}/{rid}'] = log
            for weather in ['TMYx', 'DSY1']:
                prior_file = PILOT / 'runs' / weather / 'combined' / arch / rid / 'result.json'
                if prior_file.exists():
                    record = json.loads(prior_file.read_text())
                    require(record['status'] == 'ok', 'Unsuccessful pilot cannot be reused')
                    require(record['idf_sha256'] == sha(path / f'{rid}.idf'), 'Pilot differs from full variant')
                    require(record['weather_sha256'] == sha(ROOT / 'weather' / f'{weather}.epw'), 'Pilot weather differs')
                    require(record['csv_sha256'] == sha(prior_file.parent / 'eplusout.csv'), 'Pilot output changed')
                    pilot_refs[f'{weather}/{arch}/{rid}'] = {'path': str(prior_file.parent), 'result_sha256': sha(prior_file), 'csv_sha256': record['csv_sha256']}
        for weather, frame in [('TMYx', old_audit), ('DSY1', old_dsy)]:
            frame = frame[frame.archetype.eq(arch)].sort_values('run_id').reset_index(drop=True)
            require(len(frame) == 2000 and frame.status.eq('ok').all(), 'Original audit incomplete')
            frame.to_csv(ROOT / 'inputs' / f'original_{weather}_{arch}.csv', index=False)
            canonical = original if weather == 'TMYx' else pd.read_csv(OLD_DSY / f'training_{arch}.csv').set_index('run_id')
            np.testing.assert_allclose(frame[TARGETS], canonical.loc[frame.run_id, TARGETS], atol=1e-6, rtol=0)
    np.testing.assert_allclose(lhs['detached'][FEATURES], lhs['semi'][FEATURES], atol=1e-12, rtol=0)
    require(lhs['detached'].run_id.equals(lhs['semi'].run_id), 'Archetype sample IDs differ')
    json_out(ROOT / 'inputs/idf_changes.json', changes)
    json_out(ROOT / 'inputs/pilot_reuse.json', pilot_refs)
    inputs = [p for folder in ['inputs', 'weather', 'frozen_code', 'backup'] for p in (ROOT / folder).rglob('*') if p.is_file()]
    protocol = {'variant': 'combined_v2', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'samples_per_archetype_weather': 2000, 'total_cases': 8000,
        'weather': ['TMYx', 'DSY1'], 'corrections': prior_protocol['variants']['combined'],
        'retained': 'Automatic interior shades at 26.5 C; original schedules; semi Kiva fraction 0.75; proxy definitions and original LHS.',
        'boundaries': 'Interfloor test assembly is original 100mm concrete only; semi attic gable assumes full-height attachment. No monitored physical validation.',
        'input_hashes': {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        'runner_sha256': sha(Path(__file__)), 'energyplus_sha256': sha(EP),
        'energyplus_version': subprocess.check_output([str(EP), '--version'], text=True).strip(),
        'pilot_reusable_cases': len(pilot_refs), 'original_results_preserved': True,
        'simulation_working_directory': 'Each individual run folder; avoids ReadVarsESO audit-file races.'}
    require(len(pilot_refs) == 320, 'Expected 320 audited combined pilot cases')
    json_out(ROOT / 'protocol.json', protocol)
    print(json.dumps({'output': str(ROOT), 'total': 8000, 'reusable': len(pilot_refs), 'new_runs': 8000-len(pilot_refs)}), flush=True)


def verify_inputs(protocol):
    require(sha(Path(__file__)) == protocol['runner_sha256'], 'Runner changed')
    require(sha(EP) == protocol['energyplus_sha256'], 'EnergyPlus changed')
    for path, digest in protocol['input_hashes'].items():
        require(sha(ROOT / path) == digest, f'Frozen input changed: {path}')


def worker(weather, arch, params, protocol, reuse):
    rid = params['run_id']
    folder = ROOT / 'datasets' / weather / 'runs' / arch / rid
    saved = folder / 'result.json'
    source = ROOT / 'inputs/idfs' / arch / f'{rid}.idf'
    idf_hash = protocol['input_hashes'][str(source.relative_to(ROOT))]
    weather_hash = protocol['input_hashes'][f'weather/{weather}.epw']
    if saved.exists():
        record = json.loads(saved.read_text())
        require(record['status'] == 'ok', f'Failed run must be investigated: {saved}')
        require(record['idf_sha256'] == sha(folder / 'sim.idf') == idf_hash, 'Resume IDF mismatch')
        require(record['weather_sha256'] == weather_hash and record['csv_sha256'] == sha(folder / 'eplusout.csv'), 'Resume weather/output mismatch')
        return record
    require(not folder.exists(), f'Unrecognized unfinished folder: {folder}')
    folder.mkdir(parents=True)
    result = dict(params, weather=weather, archetype=arch, status='failed', idf_sha256=idf_hash, weather_sha256=weather_hash)
    start = time.perf_counter()
    key = f'{weather}/{arch}/{rid}'
    try:
        if key in reuse:
            old = Path(reuse[key]['path'])
            require(sha(old / 'result.json') == reuse[key]['result_sha256'], 'Pilot record changed')
            require(sha(old / 'eplusout.csv') == reuse[key]['csv_sha256'], 'Pilot CSV changed')
            for name in ['sim.idf', 'eplusout.csv', 'eplusout.err', 'stdout.log', 'stderr.log']:
                shutil.copy2(old / name, folder / name)
            result['reused_pilot'] = True
            result['pilot_source'] = str(old)
        else:
            shutil.copy2(source, folder / 'sim.idf')
            with (folder / 'stdout.log').open('w') as stdout, (folder / 'stderr.log').open('w') as stderr:
                proc = subprocess.run([str(EP), '-w', str(ROOT / 'weather' / f'{weather}.epw'), '-d', str(folder), '-r', str(folder / 'sim.idf')], cwd=folder, stdout=stdout, stderr=stderr, timeout=180)
            require(proc.returncode == 0, f'EnergyPlus exit {proc.returncode}')
            result['reused_pilot'] = False
        require(sha(folder / 'sim.idf') == idf_hash, 'Actual IDF differs from assigned IDF')
        errors = (folder / 'eplusout.err').read_text()
        result['severe_errors'] = len(re.findall(r'\*\*\s*Severe\s*\*\*', errors))
        result['warnings'] = len(re.findall(r'\*\*\s*Warning\s*\*\*', errors))
        require(result['severe_errors'] == 0 and not re.search(r'\*\*\s*Fatal\s*\*\*', errors), 'Severe/fatal error')
        result['occupancy_minimum'] = audit.occupancy_proof((folder / 'sim.idf').read_text())
        result.update(metric_check(folder, params['width'], params['length']))
        result.update(status='ok', csv_sha256=sha(folder / 'eplusout.csv'))
    except Exception as exc:
        result['error'] = repr(exc)
    result['processing_seconds'] = time.perf_counter() - start
    json_out(saved, result)
    if result['status'] == 'ok':
        keep = {'result.json', 'sim.idf', 'eplusout.csv', 'eplusout.err', 'stdout.log', 'stderr.log'}
        for p in folder.iterdir():
            if p.is_file() and p.name not in keep:
                try:
                    p.unlink()
                except OSError:
                    pass
    return result


def execute(weather, workers):
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    verify_inputs(protocol)
    reuse = json.loads((ROOT / 'inputs/pilot_reuse.json').read_text())
    jobs = [(arch, r) for arch in ['detached', 'semi'] for r in pd.read_csv(ROOT / 'inputs' / f'lhs_{arch}.csv').to_dict('records')]
    dest = ROOT / 'datasets' / weather
    dest.mkdir(exist_ok=True)
    rows = []
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker, weather, a, r, protocol, reuse) for a, r in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 40 == 0 or rows[-1]['status'] != 'ok' or len(rows) == len(jobs):
                csv_out(dest / 'results_in_progress.csv', pd.DataFrame(rows).sort_values(['archetype', 'run_id']))
                status = dict(weather=weather, completed=len(rows), total=4000, failures=sum(r['status'] != 'ok' for r in rows), reused=sum(r.get('reused_pilot', False) for r in rows), elapsed_seconds=time.perf_counter()-start)
                json_out(dest / 'progress.json', status)
                print(json.dumps(status), flush=True)
    require(len(rows) == 4000 and all(r['status'] == 'ok' for r in rows), 'Incomplete/failed simulations; not eligible for training')
    # Independent second pass over every saved hourly file before training is enabled.
    for i, row in enumerate(rows, 1):
        folder = dest / 'runs' / row['archetype'] / row['run_id']
        require(sha(folder / 'eplusout.csv') == row['csv_sha256'], 'Output changed during run')
        checked = metric_check(folder, row['width'], row['length'])
        for metric, value in checked.items():
            require(abs(float(row[metric])-float(value)) < 1e-6, f'Final audit mismatch: {metric}')
        if i % 1000 == 0:
            print(f'{weather}: independently re-audited {i}/4000 hourlies', flush=True)
    verify_inputs(protocol)
    frame = pd.DataFrame(rows).sort_values(['archetype', 'run_id']).reset_index(drop=True)
    csv_out(dest / 'results.csv', frame)
    hashes = {}
    for arch in ['detached', 'semi']:
        training = frame[frame.archetype.eq(arch)].sort_values('run_id').reset_index(drop=True)
        require(len(training) == 2000 and training.run_id.is_unique, 'Training dataset incomplete')
        path = dest / f'training_{arch}.csv'
        csv_out(path, training)
        hashes[arch] = sha(path)
    json_out(dest / 'complete.json', dict(all_ok=True, audited=4000, training_hashes=hashes,
        source_protocol_sha256=sha(ROOT / 'protocol.json'), reused_pilot_cases=int(frame.reused_pilot.sum()),
        finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-start))
    print(f'{weather}: 4000/4000 audited and ready for corrected-model training', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'TMYx', 'DSY1'])
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    require(1 <= args.workers <= 12, 'Use 1..12 workers')
    prepare() if args.stage == 'prepare' else execute(args.stage, args.workers)
