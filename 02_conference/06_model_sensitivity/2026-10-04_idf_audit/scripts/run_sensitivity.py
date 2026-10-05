"""Backed-up, paired IDF sensitivity experiments; never replace canonical data."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import pandas as pd

EXPERIMENT = Path(__file__).resolve().parents[1]
PROJECT = EXPERIMENT.parents[2]
FORMAL = PROJECT / 'formal model file'
sys.path.insert(0, str(FORMAL / 'script'))
import batch_runner_v7 as baseline
import revision_metric_audit as audit
from revision_common import FEATURES, TARGETS

EP = Path('/Applications/EnergyPlus-25-1-0/energyplus')
DSY = PROJECT / '02_conference/03_data/weather_scenarios/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1/full'
SEED = 20261004
VARIANTS = {
    'control': 'Unmodified IDF rerun: environment/reproducibility control.',
    'vent_rotation': 'Rotate opening effective bearings with building and zone north.',
    'interfloor': 'Surface 6/7 use original 100 mm concrete only; loft insulation unchanged.',
    'attic_party': 'Semi Surface 16 becomes adiabatic/NoSun/NoWind; all else unchanged.',
    'combined': 'Vent rotation + interfloor; plus attic party for semi. Interior shades retained.',
    'shade_off': 'Diagnostic only: automatic interior shade controls AlwaysOff; other fields unchanged.',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + '\n')
    temp.replace(path)


def atomic_csv(path, frame):
    temp = path.with_suffix('.tmp')
    frame.to_csv(temp, index=False)
    temp.replace(path)


def parsed(text):
    """Retain exact token spans, including empty fields, without rewriting comments."""
    clean = re.sub(r'![^\n]*', lambda m: ' ' * len(m[0]), text)
    result, start = [], 0
    for end_match in re.finditer(';', clean):
        end = end_match.start()
        block = clean[start:end]
        bounds = [start - 1] + [start + m.start() for m in re.finditer(',', block)] + [end]
        fields, spans = [], []
        for left, right in zip(bounds[:-1], bounds[1:]):
            value = clean[left + 1:right]
            stripped = value.strip()
            offset = len(value) - len(value.lstrip())
            fields.append(stripped)
            spans.append((left + 1 + offset, left + 1 + offset + len(stripped)))
        if fields[0]:
            result.append({'fields': fields, 'spans': spans})
        start = end + 1
    require(not clean[start:].strip(), 'Unterminated IDF object')
    return result


def modify(text, variant, arch):
    require(variant in VARIANTS, 'Unknown variant')
    require(arch in ('detached', 'semi'), 'Unknown archetype')
    require(not (variant == 'attic_party' and arch != 'semi'), 'Attic party applies only to semi')
    obs = parsed(text)
    mapping = {(o['fields'][0].lower(), o['fields'][1]): o for o in obs if len(o['fields']) > 1}
    changes, patches = [], []

    def edit(o, field, value):
        f = o['fields']
        changes.append({'type': f[0], 'name': f[1], 'field_index': field,
                        'old': f[field], 'new': str(value)})
        patches.append((*o['spans'][field], str(value)))

    if variant in ('vent_rotation', 'combined'):
        north = float(next(o['fields'][2] for o in obs if o['fields'][0].lower() == 'building'))
        vents = [o for o in obs if o['fields'][0].lower() == 'zoneventilation:windandstackopenarea']
        require(len(vents) == (8 if arch == 'detached' else 6), 'Unexpected ventilation count')
        for o in vents:
            f = o['fields']
            zone = mapping['zone', f[2]]['fields']
            bearing = (float(f[6]) + north + float(zone[2] or 0)) % 360
            edit(o, 6, f'{bearing:.12f}')

    addition = ''
    if variant in ('interfloor', 'combined'):
        require(mapping['construction', 'Interior Ceiling']['fields'][2:] == ['Roof Insulation', 'RC_Slab_100mm'], 'Ceiling assembly changed')
        require(mapping['construction', 'Interior Floor']['fields'][2:] == ['RC_Slab_100mm', 'Roof Insulation'], 'Floor assembly changed')
        for name, old, other in [('Surface 6', 'Interior Ceiling', 'Surface 7'), ('Surface 7', 'Interior Floor', 'Surface 6')]:
            o = mapping['buildingsurface:detailed', name]
            require(o['fields'][3] == old and o['fields'][6:8] == ['Surface', other], 'Unexpected interfloor boundary')
            edit(o, 3, 'Audit_Interfloor_RC_100mm')
        addition = '\n! Isolated audit variant: original concrete slab; no sampled loft insulation.\nConstruction,\n    Audit_Interfloor_RC_100mm,\n    RC_Slab_100mm;\n'

    if variant == 'attic_party' or (variant == 'combined' and arch == 'semi'):
        o = mapping['buildingsurface:detailed', 'Surface 16']
        require(o['fields'][4] == 'Thermal Zone: Space 1' and o['fields'][6] == 'Outdoors', 'Unexpected attic boundary')
        for field, value in [(6, 'Adiabatic'), (8, 'NoSun'), (9, 'NoWind')]:
            edit(o, field, value)

    if variant == 'shade_off':
        shades = [o for o in obs if o['fields'][0].lower() == 'windowshadingcontrol']
        require(len(shades) == 2, 'Unexpected shading control count')
        for o in shades:
            require(o['fields'][4] == 'InteriorShade' and o['fields'][6] == 'OnIfHighZoneAirTemperature', 'Unexpected shading control')
            edit(o, 6, 'AlwaysOff')

    result = text
    for a, b, value in sorted(patches, reverse=True):
        result = result[:a] + value + result[b:]
    result += addition
    expected = [o['fields'][:] for o in obs]
    for change in changes:
        original = mapping[change['type'].lower(), change['name']]
        expected[obs.index(original)][change['field_index']] = change['new']
    if addition:
        expected.append(['Construction', 'Audit_Interfloor_RC_100mm', 'RC_Slab_100mm'])
    require([o['fields'] for o in parsed(result)] == expected, 'Unintended IDF field change')
    if variant == 'control':
        require(result == text, 'Control must be byte-identical')
    return result, changes


def original_frames():
    frames = {}
    for arch in ('detached', 'semi'):
        suffix = '_semi' if arch == 'semi' else ''
        frames['TMYx', arch] = pd.read_csv(FORMAL / f'output/results/results_v7{suffix}.csv').set_index('run_id')
        frames['DSY1', arch] = pd.read_csv(DSY / f'training_{arch}.csv').set_index('run_id')
        for weather in ('TMYx', 'DSY1'):
            frame = frames[weather, arch]
            require(len(frame) == 2000 and frame.index.is_unique, 'Expected 2000 unique cases')
            np.testing.assert_allclose(frame.loc[frames['TMYx', arch].index, FEATURES], frames['TMYx', arch][FEATURES], rtol=0, atol=1e-12)
    return frames


def select_cases(frames):
    ids = sorted(frames['TMYx', 'detached'].index)
    random_ids = sorted(np.random.default_rng(SEED).choice(ids, 64, replace=False).tolist())
    selected = {rid: {'run_id': rid, 'cohort': 'random64', 'reason': 'Fixed random sample without replacement'} for rid in random_ids}
    candidates = []
    for (weather, arch), frame in frames.items():
        for target in ['hours_gt26_night', 'T_op_peak', 'hours_C3_worst', 'heat_kWh_m2']:
            candidates.append((frame[target].idxmax(), f'{weather}/{arch} maximum {target}'))
    for feature in ['orientation', 'roofInsulationThickness', 'wwr', 'wof', 'width', 'length', 'g_value', 'u_windows']:
        frame = frames['TMYx', 'detached']
        candidates.extend([(frame[feature].idxmin(), f'Minimum {feature}'), (frame[feature].idxmax(), f'Maximum {feature}')])
    for rid, reason in candidates + [(rid, 'Deterministic stress-cohort fill') for rid in ids]:
        if len(selected) == 80:
            break
        if rid not in selected:
            selected[rid] = {'run_id': rid, 'cohort': 'stress16', 'reason': reason}
    return pd.DataFrame(selected.values()).sort_values(['cohort', 'run_id']).reset_index(drop=True)


def raw_metrics(folder, width, length):
    raw = pd.read_csv(folder / 'eplusout.csv', usecols=lambda c: c == 'Date/Time' or 'Operative Temperature' in c or 'Outdoor Air Drybulb' in c or 'Ideal Loads Supply Air Total' in c)
    result = audit.calculate(raw, width, length)
    second = baseline.compute_targets(folder, width, length)
    for target in TARGETS + ['hours_C3_worst']:
        require(abs(result[target] - second[target]) < 1e-6, f'Independent postprocessor mismatch: {target}')
    require(result['cooling_kWh'] < 1e-6, 'Active cooling')
    return result


def prepare():
    require(not (EXPERIMENT / 'protocol.json').exists(), 'Already prepared; use an execution stage')
    for sub in ['backup', 'inputs', 'runs', 'results', 'reports', 'figures']:
        (EXPERIMENT / sub).mkdir(exist_ok=True)
    frames = original_frames()
    selected = select_cases(frames)
    weather_paths = {'TMYx': baseline.WEATHER_FILE,
                     'DSY1': PROJECT / 'CIBSE_weather_files_z1/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1.epw'}
    files = [FORMAL / p for p in ['detachedhouse0.idf', 'semidetached_template.idf', 'parameter_config_v7.json', 'parameter_config_v7_semi.json', 'script/batch_runner_v7.py', 'script/revision_common.py', 'script/revision_metric_audit.py', 'script/dsy_runner.py']]
    for arch in ('detached', 'semi'):
        suffix = '_semi' if arch == 'semi' else ''
        files += [FORMAL / f'output/lhs/lhs_samples_v7{suffix}.csv', FORMAL / f'output/results/results_v7{suffix}.csv', DSY / f'training_{arch}.csv']
    files += list(weather_paths.values())
    files += [PROJECT / '02_conference/01_manuscript' / n for n in ['p129v1_restructured_DSY1_10pages.docx', 'response_to_reviewers_10pages.docx', 'p129_supplementary_material.docx', 'p129_submission_supplement.zip']]
    manifest, idf_hashes = {}, {}
    archive = EXPERIMENT / 'backup/original_inputs.zip'
    require(not archive.exists(), 'Backup already exists; do not overwrite')
    with ZipFile(archive, 'x', ZIP_DEFLATED, compresslevel=6) as z:
        for path in files:
            manifest[str(path)] = digest(path)
            z.write(path, str(path.relative_to(PROJECT)))
        for arch in ('detached', 'semi'):
            for rid in sorted(frames['TMYx', arch].index):
                path = FORMAL / 'output/runs' / arch / rid / 'sim.idf'
                h = digest(path)
                require(h == digest(DSY / 'runs' / arch / rid / 'sim.idf'), 'TMYx/DSY original IDFs differ')
                manifest[str(path)] = h
                manifest[str(DSY / 'runs' / arch / rid / 'sim.idf')] = h
                idf_hashes[f'{arch}/{rid}'] = h
                z.write(path, f'original_idfs/{arch}/{rid}/sim.idf')
    with ZipFile(archive) as z:
        require(z.testzip() is None, 'Backup ZIP CRC failure')
        for key, h in idf_hashes.items():
            require(hashlib.sha256(z.read(f'original_idfs/{key}/sim.idf')).hexdigest() == h, 'Backup hash mismatch')
    atomic_json(EXPERIMENT / 'backup/source_hashes.json', manifest)
    selected.to_csv(EXPERIMENT / 'inputs/selected_cases.csv', index=False)
    for weather, path in weather_paths.items():
        shutil.copy2(path, EXPERIMENT / 'inputs' / f'{weather}.epw')
    references, changes = [], {}
    for arch in ('detached', 'semi'):
        for row in selected.to_dict('records'):
            rid = row['run_id']
            text = (FORMAL / 'output/runs' / arch / rid / 'sim.idf').read_text()
            audit.occupancy_proof(text)
            variants = [v for v in VARIANTS if arch == 'semi' or v != 'attic_party']
            for variant in variants:
                new, log = modify(text, variant, arch)
                dest = EXPERIMENT / 'inputs/idfs' / variant / arch
                dest.mkdir(parents=True, exist_ok=True)
                (dest / f'{rid}.idf').write_text(new)
                changes[f'{variant}/{arch}/{rid}'] = log
            for weather in ('TMYx', 'DSY1'):
                params = frames[weather, arch].loc[rid]
                folder = (FORMAL / 'output/runs' if weather == 'TMYx' else DSY / 'runs') / arch / rid
                metrics = raw_metrics(folder, params.width, params.length)
                for target in TARGETS + ['hours_C3_worst']:
                    require(abs(metrics[target] - params[target]) < 1e-6, 'Original target mismatch')
                references.append(dict(weather=weather, archetype=arch, **row, **params[FEATURES].to_dict(), **metrics,
                                       source_csv=str(folder / 'eplusout.csv'), source_csv_sha256=digest(folder / 'eplusout.csv')))
    reference = pd.DataFrame(references)
    reference.to_csv(EXPERIMENT / 'inputs/reference_metrics.csv', index=False)
    atomic_json(EXPERIMENT / 'inputs/idf_change_log.json', changes)
    controls = sorted(selected[selected.cohort.eq('random64')].run_id)[:3]
    protocol = {'created_utc': datetime.now(timezone.utc).isoformat(), 'project': str(PROJECT),
                'selection_seed': SEED, 'random_n': 64, 'stress_n': 16, 'control_ids': controls,
                'variants': VARIANTS, 'targets': TARGETS, 'backup_sha256': digest(archive),
                'energyplus_version': subprocess.check_output([str(EP), '--version'], text=True).strip(),
                'energyplus_sha256': digest(EP),
                'script_hashes': {str(p): digest(p) for p in [Path(__file__), Path(audit.__file__), Path(baseline.__file__), FORMAL / 'script/revision_common.py']},
                'input_hashes': {str(p.relative_to(EXPERIMENT)): digest(p) for p in (EXPERIMENT / 'inputs').rglob('*') if p.is_file()},
                'scope': 'Paired sensitivity pilot, not replacement training data or physical validation.',
                'unchanged': 'Weather per pair, sampled inputs, schedules, metrics, Kiva fraction (1/.75), remaining constructions. Combined retains interior shades.',
                'stress_warning': 'Output/input-extreme selected cohort; never pool it with random64 for prevalence estimates.',
                'interfloor_assumption': 'Remove only sampled insulation from intermediate floor; retain original 100mm concrete. Not a claim of a validated floor assembly.',
                'attic_assumption': 'Test full-height adjoining dwelling; only east attic gable boundary changes.'}
    atomic_json(EXPERIMENT / 'protocol.json', protocol)
    print(json.dumps({'backed_up_idfs': len(idf_hashes), 'selected_buildings': len(selected), 'reference_hourlies_audited': len(reference), 'output': str(EXPERIMENT)}), flush=True)


def verify_frozen(protocol):
    require(digest(EP) == protocol['energyplus_sha256'], 'EnergyPlus executable changed')
    for path, h in protocol['script_hashes'].items():
        require(digest(path) == h, f'Script changed: {path}')
    for path, h in protocol['input_hashes'].items():
        require(digest(EXPERIMENT / path) == h, f'Input changed: {path}')


def worker(row, variant, protocol):
    weather, arch, rid = row['weather'], row['archetype'], row['run_id']
    folder = EXPERIMENT / 'runs' / weather / variant / arch / rid
    input_idf = EXPERIMENT / 'inputs/idfs' / variant / arch / f'{rid}.idf'
    saved = folder / 'result.json'
    if saved.exists():
        record = json.loads(saved.read_text())
        require(record['status'] == 'ok', f'Existing failed run requires explicit investigation: {saved}')
        require(digest(folder / 'sim.idf') == digest(input_idf) == record['idf_sha256'], 'Resume IDF mismatch')
        require(digest(folder / 'eplusout.csv') == record['csv_sha256'], 'Resume output mismatch')
        return record
    require(not folder.exists(), f'Unrecognized unfinished folder: {folder}')
    folder.mkdir(parents=True)
    shutil.copy2(input_idf, folder / 'sim.idf')
    start = time.perf_counter()
    result = {k: row[k] for k in ['weather', 'archetype', 'run_id', 'cohort'] + FEATURES}
    result.update(variant=variant, status='failed', idf_sha256=digest(input_idf),
                  weather_sha256=protocol['input_hashes'][f'inputs/{weather}.epw'])
    try:
        with (folder / 'stdout.log').open('w') as stdout, (folder / 'stderr.log').open('w') as stderr:
            proc = subprocess.run([str(EP), '-w', str(EXPERIMENT / 'inputs' / f'{weather}.epw'), '-d', str(folder), '-r', str(folder / 'sim.idf')], stdout=stdout, stderr=stderr, cwd=folder, timeout=180)
        require(proc.returncode == 0, f'EnergyPlus exit {proc.returncode}')
        errors = (folder / 'eplusout.err').read_text()
        result['severe_errors'] = len(re.findall(r'\*\*\s*Severe\s*\*\*', errors))
        result['warnings'] = len(re.findall(r'\*\*\s*Warning\s*\*\*', errors))
        require(result['severe_errors'] == 0 and not re.search(r'\*\*\s*Fatal\s*\*\*', errors), 'Severe/fatal errors')
        result['occupancy_minimum'] = audit.occupancy_proof((folder / 'sim.idf').read_text())
        result.update(raw_metrics(folder, row['width'], row['length']))
        if variant == 'control':
            for target in TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']:
                require(abs(result[target] - row[target]) < 1e-6, f'Control drift: {target}')
        result.update(status='ok', csv_sha256=digest(folder / 'eplusout.csv'))
    except Exception as exc:
        result['error'] = repr(exc)
    result['sim_sec'] = round(time.perf_counter() - start, 3)
    atomic_json(saved, result)
    if result['status'] == 'ok':
        keep = {'sim.idf', 'eplusout.csv', 'eplusout.err', 'stdout.log', 'stderr.log', 'result.json'}
        for path in folder.iterdir():
            if path.is_file() and path.name not in keep:
                try:
                    path.unlink()
                except OSError:
                    pass
    return result


def execute(stage, workers):
    protocol = json.loads((EXPERIMENT / 'protocol.json').read_text())
    verify_frozen(protocol)
    ref = pd.read_csv(EXPERIMENT / 'inputs/reference_metrics.csv')
    if stage != 'controls':
        gate = json.loads((EXPERIMENT / 'results/controls_completion.json').read_text())
        require(gate['all_ok'] and gate['runs'] == 12, 'Passing controls required')
    if stage == 'full':
        gate = json.loads((EXPERIMENT / 'results/smoke_completion.json').read_text())
        require(gate['all_ok'] and gate['runs'] == 18, 'Passing variant smoke tests required')
    jobs = []
    for row in ref.to_dict('records'):
        variants = ['control'] if stage == 'controls' else [v for v in VARIANTS if v != 'control']
        if stage == 'controls' and row['run_id'] not in protocol['control_ids']:
            continue
        if stage == 'smoke' and row['run_id'] != protocol['control_ids'][0]:
            continue
        for variant in variants:
            if variant != 'attic_party' or row['archetype'] == 'semi':
                jobs.append((row, variant))
    results = []
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker, row, variant, protocol) for row, variant in jobs]
        for future in as_completed(futures):
            record = future.result()
            results.append(record)
            if len(results) % 20 == 0 or record['status'] != 'ok' or len(results) == len(jobs):
                atomic_csv(EXPERIMENT / 'results' / f'{stage}_results.csv', pd.DataFrame(results).sort_values(['weather', 'variant', 'archetype', 'run_id']))
                print(f'{stage}: {len(results)}/{len(jobs)}; failures={sum(r["status"] != "ok" for r in results)}; elapsed={time.perf_counter()-start:.1f}s', flush=True)
    verify_frozen(protocol)
    completion = {'stage': stage, 'runs': len(results), 'all_ok': all(r['status'] == 'ok' for r in results), 'elapsed_sec': time.perf_counter()-start, 'finished_utc': datetime.now(timezone.utc).isoformat()}
    atomic_json(EXPERIMENT / 'results' / f'{stage}_completion.json', completion)
    require(completion['all_ok'], 'Failures: inspect results before proceeding')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'controls', 'smoke', 'full'])
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    require(1 <= args.workers <= 8, 'Workers must be 1..8')
    if args.stage == 'prepare':
        prepare()
    else:
        execute(args.stage, args.workers)
