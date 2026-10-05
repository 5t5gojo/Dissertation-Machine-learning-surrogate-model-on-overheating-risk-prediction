"""Reuse frozen model code with rounded C1 targets and independent outputs."""
import os
for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[name] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frozen_code'))
import corrected_train_models as adapter
import revision_model_eval as base
import pandas as pd
from prepare import require, sha, write_json

# Spawned workers import this module too, keeping all writes in the new workspace.
adapter.ROOT = ROOT
adapter.OLD = ROOT / 'inputs/splits'


def main(weather, workers):
    prepared = json.loads((ROOT / 'preparation.json').read_text())
    require(prepared['ready'] and prepared['cases'] == 8000, 'Preparation incomplete')
    for path, digest in prepared['input_hashes'].items():
        require(sha(ROOT / path) == digest, f'Prepared input changed: {path}')
    original = json.loads((ROOT / 'inputs/original_model_protocol.json').read_text())
    configs = base.candidates(6)
    require(configs == original['candidates'] and base.SEEDS == original['seeds'], 'Changed search budget/seeds')
    versions = {m:__import__(m).__version__ for m in ['numpy','pandas','sklearn','torch','xgboost']}
    require(versions == original['versions'], 'Software versions differ from original protocol')
    source = ROOT / 'datasets' / weather
    complete = json.loads((source / 'complete.json').read_text())
    require(complete['preparation_verified'] and complete['audited'] == 4000, 'Bad rounded data')
    protocol = dict(variant='corrected_v2_rounded', weather=weather, seeds=base.SEEDS, candidates=configs,
        epochs=original['epochs'], permutation_repeats=original['permutation_repeats'],
        objective=original['objective'], budget=original['budget'], data_hash=complete['training_hashes'],
        adapter_hash=sha(adapter.__file__), evaluator_hash=sha(base.__file__), runner_hash=sha(__file__),
        preparation_hash=sha(ROOT / 'preparation.json'), versions=versions, platform=platform.platform(),
        hardware=dict(cpu=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
                      memory_bytes=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True)),
                      logical_cpus=int(subprocess.check_output(['sysctl','-n','hw.ncpu'],text=True)),
                      workers_per_weather=workers, estimator_threads=1, training_device='CPU'),
        training_C1=complete['training_C1'], diagnostic_C3=complete['diagnostic_C3'],
        note='Only C1 training labels change; C3 remains diagnostic. Comparisons use different C1 target definitions.')
    dest = source / 'evaluation'
    if (dest / 'protocol.json').exists():
        require(json.loads((dest / 'protocol.json').read_text()) == protocol, 'Cannot resume changed protocol')
    else:
        dest.mkdir(exist_ok=True)
        write_json(dest / 'protocol.json', protocol)
    tasks = []
    for arch in ['detached','semi']:
        for seed in base.SEEDS:
            done = dest / arch / f'seed_{seed}/complete.json'
            if done.exists():
                require(json.loads(done.read_text())['data_hash'] == complete['training_hashes'][arch], 'Stale completed split')
            else:
                tasks.append((weather, arch, seed, configs, original['epochs'], original['permutation_repeats']))
    print(f'START {weather}: {len(tasks)} splits; six candidates per family; validation-only selection', flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(adapter.job, task) for task in tasks]):
            print('COMPLETE', weather, future.result(), flush=True)
    for name in ['search_trials','performance','predictions','night_subgroups','night_event_detection','permutation_importance','shap_importance']:
        combined = pd.concat([pd.read_csv(dest / a / f'seed_{s}' / f'{name}.csv')
                              for a in ['detached','semi'] for s in base.SEEDS], ignore_index=True)
        combined.to_csv(dest / f'{name}_all.csv', index=False)
    performance = pd.read_csv(dest / 'performance_all.csv')
    summary = performance.groupby(['archetype','model','target'])[['R2','MAE','RMSE']].agg(['mean','std'])
    summary.columns = ['_'.join(c) for c in summary.columns]
    summary.to_csv(dest / 'performance_summary.csv')
    # Reload saved weights/scalers and recompute test metrics, SHAP and validation selection.
    adapter.verify(weather, protocol)
    write_json(dest / 'complete.json', dict(all_ok=True, variant='corrected_v2_rounded', trials=180,
        predictions=45000, performance_sha256=sha(dest / 'performance_all.csv'),
        verification_sha256=sha(dest / 'verification.json')))
    print(f'VERIFIED {weather}: 180 trials, 45000 held-out predictions, 150 trained-model metric rows', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weather', choices=['TMYx','DSY1'])
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    require(1 <= args.workers <= 6, 'Use 1..6 workers')
    main(args.weather, args.workers)
