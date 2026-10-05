"""Prepare rounded targets in a new workspace without simulation or source edits."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
CONFERENCE = ROOT.parents[1]
SOURCE = CONFERENCE / '07_corrected_full/2026-10-04_combined_v2'
AUDIT = CONFERENCE / '08_metric_rounding/2026-10-05_corrected_v2/results'
WEATHERS = ['TMYx', 'DSY1']
ARCHETYPES = ['detached', 'semi']
SEEDS = [42, 123, 202, 340, 567]
UPDATED = {'He_worst', 'hours_C3_worst', 'two_of_three_proxy_dwelling'} | {
    f'{name}_{zone}' for name in ['He_all', 'He_occupied', 'C3_hours', 'two_of_three_proxy']
    for zone in ['101', '102']}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def read_csv(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def bool_value(value):
    require(value in ['True', 'False'], f'Invalid boolean: {value}')
    return value == 'True'


def rounded_record(row, case, zones):
    require(round(float(case['He_raw_pct']), 4) == float(row['He_worst']), 'Raw C1 mismatch')
    require(case['source_csv_sha256'] == row['csv_sha256'], 'Hourly provenance mismatch')
    require(case['source_idf_sha256'] == row['idf_sha256'], 'IDF provenance mismatch')
    new = dict(row)
    # Preserve original target storage precision and every untouched CSV token.
    new['He_worst'] = str(round(float(case['He_rounded_pct']), 4))
    new['hours_C3_worst'] = case['C3_hours_rounded']
    new['two_of_three_proxy_dwelling'] = case['joint_rounded']
    for zone, z in zones.items():
        new[f'He_all_{zone}'] = z['He_rounded_pct']
        new[f'He_occupied_{zone}'] = z['He_rounded_pct']
        new[f'C3_hours_{zone}'] = z['C3_hours_rounded']
        new[f'two_of_three_proxy_{zone}'] = z['joint_rounded']
    changed = {k for k in row if row[k] != new[k]}
    require(changed <= UPDATED, f'Unexpected changes: {changed - UPDATED}')
    require(bool_value(new['two_of_three_proxy_dwelling']) == any(
        bool_value(new[f'two_of_three_proxy_{z}']) for z in ['101', '102']), 'Cross-zone flag error')
    return new


def verify_sources(expected):
    for path, digest in expected.items():
        require(sha(Path(path)) == digest, f'Protected source changed: {path}')


def main():
    require(not (ROOT / 'preparation.json').exists(), 'Already prepared; no overwrites')
    require(not (ROOT / 'datasets').exists(), 'Partial preparation exists; inspect before restarting')
    record = json.loads((AUDIT / 'verification.json').read_text())
    require(record['status'] == 'complete' and record['cases'] == 8000 and record['source_results_preserved'], 'Rounding audit incomplete')
    protected = {str(SOURCE / p): v for p, v in json.loads((AUDIT / 'source_hashes.json').read_text()).items()}
    protected.update({str(AUDIT / p): v for p, v in json.loads((AUDIT / 'output_hashes.json').read_text()).items()})
    protected[str(AUDIT / 'output_hashes.json')] = sha(AUDIT / 'output_hashes.json')
    verify_sources(protected)
    for name in ['frozen_code', 'inputs', 'logs', 'reports']:
        (ROOT / name).mkdir(exist_ok=True)
    frozen_sources = {
        **{name: SOURCE / 'frozen_code' / name for name in
           ['revision_common.py', 'revision_model_eval.py', 'dsy_model_eval.py']},
        'corrected_train_models.py': SOURCE / 'scripts/train_models.py',
        'corrected_report.py': SOURCE / 'scripts/report.py',
    }
    for name, path in frozen_sources.items():
        shutil.copy2(path, ROOT / 'frozen_code' / name)
        protected[str(path)] = sha(path)
    shutil.copy2(SOURCE / 'backup/original_model_protocol.json', ROOT / 'inputs/original_model_protocol.json')
    cases = {tuple(r[k] for k in ['weather','archetype','run_id']): r
             for r in read_csv(AUDIT / 'case_comparison.csv')[1]}
    zones = {tuple(r[k] for k in ['weather','archetype','run_id','zone']): r
             for r in read_csv(AUDIT / 'zone_comparison.csv')[1]}
    require(len(cases) == 8000 and len(zones) == 16000, 'Audit keys incomplete')
    checks = []
    input_hashes = {}
    for weather in WEATHERS:
        fields, old = read_csv(SOURCE / 'datasets' / weather / 'results.csv')
        new = []
        for row in old:
            key = (weather, row['archetype'], row['run_id'])
            require(row['status'] == 'ok' and row['weather'] == weather, 'Wrong source case')
            new.append(rounded_record(row, cases[key], {z: zones[key + (z,)] for z in ['101','102']}))
        dest = ROOT / 'datasets' / weather
        write_csv(dest / 'results.csv', fields, new)
        hashes = {}
        for arch in ARCHETYPES:
            subset = sorted([r for r in new if r['archetype'] == arch], key=lambda r:r['run_id'])
            require(len(subset) == 2000, 'Wrong group size')
            target = dest / f'training_{arch}.csv'
            write_csv(target, fields, subset)
            hashes[arch] = sha(target)
            source_rows = {r['run_id']:r for r in old if r['archetype'] == arch}
            for r in read_csv(target)[1]:
                require(all(r[k] == source_rows[r['run_id']][k] for k in fields if k not in UPDATED),
                        'Features or other targets changed on disk')
            checks.append(dict(weather=weather, archetype=arch, n=2000,
                C1_gt3=sum(float(r['He_worst']) > 3 for r in subset),
                C3_nonzero=sum(int(r['hours_C3_worst']) > 0 for r in subset),
                same_zone_joint=sum(bool_value(r['two_of_three_proxy_dwelling']) for r in subset),
                other_four_targets_and_features='identical source CSV tokens'))
            for seed in SEEDS:
                old_split = SOURCE / 'datasets' / weather / 'evaluation' / arch / f'seed_{seed}/split.csv'
                fields_split, split = read_csv(old_split)
                require(len(split) == 2000 and len({r['run_id'] for r in split}) == 2000, 'Bad split')
                require({s:sum(r['split']==s for r in split) for s in ['train','validation','test']} ==
                        {'train':1400,'validation':300,'test':300}, 'Bad split sizes')
                target_split = ROOT / 'inputs/splits' / arch / f'seed_{seed}/split.csv'
                if target_split.exists():
                    require(split == read_csv(target_split)[1], 'Weather splits differ')
                else:
                    write_csv(target_split, fields_split, split)
                protected[str(old_split)] = sha(old_split)
        write_json(dest / 'complete.json', dict(preparation_verified=True, audited=4000,
            training_hashes=hashes, source='Existing corrected V2 hourlies; rounded audit targets',
            training_C1='round(100 * count(rint(DeltaT)>=1) / occupied summer hours, 4)',
            diagnostic_C3='count(rint(DeltaT)>4)', no_new_simulations=True))
    for p in ROOT.rglob('*'):
        if p.is_file() and p.parts[-2] != '__pycache__' and ('inputs' in p.parts or 'frozen_code' in p.parts or 'datasets' in p.parts):
            input_hashes[str(p.relative_to(ROOT))] = sha(p)
    verify_sources(protected)
    write_json(ROOT / 'inputs/protected_sources.json', protected)
    input_hashes['inputs/protected_sources.json'] = sha(ROOT / 'inputs/protected_sources.json')
    write_json(ROOT / 'preparation.json', dict(variant='corrected_v2_rounded', ready=True,
        prepared_utc=datetime.now(timezone.utc).isoformat(), source=str(SOURCE), rounding_audit=str(AUDIT),
        cases=8000, changed_training_targets=['He_worst'], changed_diagnostics=['C3','same_zone_joint'],
        target_storage='C1 saved to 4 decimal percentage points, as in corrected V2',
        original_protocol=str(ROOT / 'inputs/original_model_protocol.json'),
        input_hashes=input_hashes, protected_files=len(protected), group_checks=checks,
        no_new_simulations=True, no_canonical_overwrites=True))
    write_csv(ROOT / 'reports/preparation_checks.csv', list(checks[0]), checks)
    print(json.dumps(checks, indent=2), flush=True)
    print('PREPARATION VERIFIED: 8000 cases; unchanged feature/other-target CSV tokens; 20 matched split checks', flush=True)


if __name__ == '__main__':
    main()
