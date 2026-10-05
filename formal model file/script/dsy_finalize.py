"""Independently audit DSY outputs and recover interrupted aggregation, without reruns."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import time

import pandas as pd
import batch_runner_v7 as baseline
import revision_metric_audit as audit
from revision_common import ROOT, TARGETS, FEATURES, sha
from dsy_runner import OUTPUT, atomic_json, atomic_csv, require, summarize

SCENARIO = 'Z1_DSY1_2030s_HIGH50_CIBSE_v1.1'


def verify_one(arg):
    arch, params, folder, protocol = arg
    rid = params['run_id']
    run = folder / 'runs' / arch / rid
    saved = run / 'result.json'
    old = json.loads(saved.read_text()) if saved.exists() else None
    source = ROOT / 'output/runs' / arch / rid / 'sim.idf'
    require(sha(source) == sha(run / 'sim.idf') == protocol['source_idfs'][f'{arch}/{rid}'], 'IDF mismatch')
    errors = (run / 'eplusout.err').read_text()
    require('EnergyPlus Completed Successfully' in errors, 'No EnergyPlus completion record')
    require(not re.search(r'\*\*\s*(?:Severe|Fatal)\s*\*\*', errors), 'Severe/fatal EnergyPlus error')
    minimum = audit.occupancy_proof((run / 'sim.idf').read_text())
    raw = pd.read_csv(run / 'eplusout.csv', usecols=lambda c: c == 'Date/Time' or
                     'Operative Temperature' in c or 'Outdoor Air Drybulb' in c or
                     'Ideal Loads Supply Air Total' in c)
    metrics = audit.calculate(raw, params['width'], params['length'])
    original = baseline.compute_targets(run, params['width'], params['length'])
    for target in TARGETS + ['hours_C3_worst']:
        require(abs(metrics[target] - original[target]) < 1e-6, f'Independent metric mismatch {target}')
        if old:
            require(abs(metrics[target] - old[target]) < 1e-6, f'Checkpoint target mismatch {target}')
    require(metrics['cooling_kWh'] < 1e-6, 'Active cooling')
    digest = sha(run / 'eplusout.csv')
    if old:
        require(old['status'] == 'ok' and old['weather_sha256'] == protocol['weather']['sha256'], 'Invalid checkpoint provenance')
        require(old['csv_sha256'] == digest, 'CSV changed since checkpoint')
    record = dict(params, archetype=arch, status='ok', occupancy_minimum=minimum, **metrics,
                  weather_sha256=protocol['weather']['sha256'], idf_sha256=sha(run / 'sim.idf'),
                  csv_sha256=digest, sim_sec=old.get('sim_sec') if old else None,
                  severe_errors=0, warnings=len(re.findall(r'\*\*\s*Warning\s*\*\*', errors)),
                  checkpoint_recovered=old is None)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-pid', type=int, required=True, help='Wait for the original runner to exit')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    while True:
        try:
            os.kill(args.wait_pid, 0)
        except ProcessLookupError:
            break
        print(f'Waiting for original simulation process {args.wait_pid} to exit', flush=True)
        time.sleep(15)
    folder = OUTPUT / SCENARIO / 'full'
    require(not (folder / 'finalization.json').exists(), 'Already independently finalized')
    protocol = json.loads((folder / 'protocol.json').read_text())
    require(protocol['mode'] == 'full' and len(protocol['run_ids']) == 2000, 'Not a full paired experiment')
    for path, digest in protocol['source_hashes'].items():
        require(sha(path) == digest, f'Original data changed: {path}')
    weather = ROOT.parent / 'CIBSE_weather_files_z1' / protocol['weather']['name']
    require(sha(weather) == protocol['weather']['sha256'], 'Weather file changed')
    jobs, reference = [], {}
    for arch in ('detached', 'semi'):
        suffix = '_semi' if arch == 'semi' else ''
        lhs = pd.read_csv(ROOT / f'output/lhs/lhs_samples_v7{suffix}.csv').set_index('run_id')
        reference[arch] = pd.read_csv(ROOT / f'output/results/results_v7{suffix}.csv').set_index('run_id')
        jobs.extend((arch, dict(lhs.loc[rid], run_id=rid), folder, protocol) for rid in protocol['run_ids'])
    records, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(verify_one, job): (job[0], job[1]['run_id']) for job in jobs}
        for future in as_completed(futures):
            arch, rid = futures[future]
            try:
                records.append(future.result())
            except Exception as exc:
                failures.append(dict(archetype=arch, run_id=rid, error=repr(exc)))
            if (len(records) + len(failures)) % 250 == 0:
                print(f'Audited {len(records)+len(failures)}/4000; failed={len(failures)}', flush=True)
    atomic_json(folder / 'finalization_errors.json', failures)
    require(not failures and len(records) == 4000, 'Audit failures: inspect finalization_errors.json')
    # Preserve the stalled aggregate as evidence before replacing it with verified records.
    backup = folder / 'results_before_recovery.csv'
    require(not backup.exists(), 'Recovery backup already exists')
    shutil.copy2(folder / 'results.csv', backup)
    for record in records:
        if record['checkpoint_recovered']:
            atomic_json(folder / 'runs' / record['archetype'] / record['run_id'] / 'result.json', record)
    atomic_csv(folder / 'results.csv', records)
    summarize(folder, records, reference)
    for arch in ('detached', 'semi'):
        subset = pd.DataFrame([r for r in records if r['archetype'] == arch]).sort_values('run_id')
        subset.to_csv(folder / f'training_{arch}.csv', index=False)
    final = {'audited': 4000, 'all_ok': True,
             'recovered_checkpoint_ids': [f"{r['archetype']}/{r['run_id']}" for r in records if r['checkpoint_recovered']],
             'results_sha256': sha(folder / 'results.csv'), 'script_sha256': sha(__file__),
             'training_hashes': {a: sha(folder / f'training_{a}.csv') for a in ('detached', 'semi')},
             'finished_utc': datetime.now(timezone.utc).isoformat(), 'physical_simulations_repeated': 0}
    atomic_json(folder / 'finalization.json', final)
    atomic_json(folder / 'completion.json', {'runs': 4000, 'all_ok': True, 'baseline_files_unchanged': True,
                                           'completed_by': 'Independent post-run recovery audit',
                                           'finalization_manifest': 'finalization.json'})
    print(json.dumps(final, indent=2), flush=True)


if __name__ == '__main__':
    main()
