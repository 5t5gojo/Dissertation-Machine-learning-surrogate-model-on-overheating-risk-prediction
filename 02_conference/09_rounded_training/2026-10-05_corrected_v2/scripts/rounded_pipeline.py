"""Run both weather evaluations and write a report only after final verification."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from prepare import ROOT, SOURCE, require, sha, verify_sources, write_json


def progress():
    counts = {}
    for weather in ['TMYx','DSY1']:
        dest = ROOT / 'datasets' / weather / 'evaluation'
        counts[weather] = sum((dest / a / f'seed_{s}/complete.json').exists()
                              for a in ['detached','semi'] for s in [42,123,202,340,567])
    return counts


def report():
    sys.path.insert(0, str(ROOT / 'frozen_code'))
    import corrected_report as reporting
    import pandas as pd
    tables, comparisons, leaders, subgroups = [], [], [], []
    for weather in ['TMYx','DSY1']:
        dest = ROOT / 'datasets' / weather / 'evaluation'
        require(json.loads((dest / 'complete.json').read_text())['all_ok'], 'Unverified model results')
        now = pd.read_csv(dest / 'performance_summary.csv')
        old = pd.read_csv(SOURCE / 'datasets' / weather / 'evaluation/performance_summary.csv')
        joined = now.merge(old, on=['archetype','model','target'], suffixes=('_rounded','_raw'), validate='one_to_one')
        for metric in ['R2','MAE','RMSE']:
            joined[f'{metric}_mean_change'] = joined[f'{metric}_mean_rounded'] - joined[f'{metric}_mean_raw']
        joined['same_target_definition'] = joined.target.ne('He_worst')
        comparisons.append(joined.assign(weather=weather))
        chosen = now[now.model.isin(['RF','XGBoost','MLP'])].copy()
        chosen['R2 mean +/- SD'] = chosen.apply(lambda r:f'{r.R2_mean:.3f} +/- {r.R2_std:.3f}',axis=1)
        table = chosen.pivot(index=['archetype','target'], columns='model', values='R2 mean +/- SD').reset_index()
        tables.append((weather, table))
        ss = reporting.attributions(dest)
        leaders.append(ss[ss.rank_of_mean.eq(1)].assign(weather=weather))
        ns = pd.read_csv(dest / 'night_subgroups_all.csv')
        ns = ns.groupby(['archetype','model','subgroup']).agg(
            RMSE_mean=('RMSE','mean'), RMSE_sd=('RMSE','std'), MAE_mean=('MAE','mean'),
            bias_mean=('bias','mean'), n_min=('n','min'), n_max=('n','max'), valid_splits=('RMSE','count')).reset_index()
        ns.to_csv(dest / 'night_subgroup_summary.csv', index=False)
        subgroups.append(ns.assign(weather=weather))
    pd.concat(comparisons, ignore_index=True).to_csv(ROOT / 'reports/raw_vs_rounded_model_comparison.csv',index=False)
    pd.concat(leaders, ignore_index=True).to_csv(ROOT / 'reports/rounded_SHAP_leaders.csv',index=False)
    pd.concat(subgroups, ignore_index=True).to_csv(ROOT / 'reports/rounded_night_subgroups.csv',index=False)
    lines = ['# Rounded C1 surrogate evaluation', '',
        'Existing corrected V2 simulations were retained. Only the He training target changed to the audited rounded-temperature definition; C3 and same-zone flags were updated as diagnostics.', '',
        'All models were freshly fit and selected using the original five matched splits and six candidates per family. Selection uses validation loss only. No EnergyPlus simulation was rerun.', '',
        'C1 performance comparisons cross different target definitions and are not direct evidence that an algorithm improved. Other target values are unchanged, but MLP shared training and joint configuration selection can change their predictions.', '']
    for weather, table in tables:
        lines.extend([f'## {weather}', '', table.to_markdown(index=False), ''])
    lines.extend(['## Scope', '',
        '- Five overlapping split SDs are descriptive, not independent confidence intervals.',
        '- No formal compliance, physical validation or frozen-model cross-weather transfer is established.',
        '- Manuscripts and old figures were not overwritten. New publication figures require a separate update and visual check.',
        '- Detailed predictions, selected models, SHAP arrays and permutation comparisons are in each weather evaluation folder.', ''])
    (ROOT / 'reports/RESULTS_SUMMARY.md').write_text('\n'.join(lines))


def main(workers):
    with (ROOT / 'logs/pipeline.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (ROOT / 'complete.json').exists(), 'Experiment already complete')
        protected = json.loads((ROOT / 'inputs/protected_sources.json').read_text())
        verify_sources(protected)
        started = datetime.now(timezone.utc).isoformat()
        processes = {}
        def state(status, **extra):
            write_json(ROOT / 'status.json', dict(status=status, pid=os.getpid(), started_utc=started,
                updated_utc=datetime.now(timezone.utc).isoformat(), completed_splits=progress(), total_splits=20,
                total_candidate_trials=360, new_simulations=0, **extra))
        try:
            for weather in ['TMYx','DSY1']:
                with (ROOT / 'logs' / f'training_{weather}.log').open('a') as log:
                    processes[weather] = subprocess.Popen([sys.executable,'-B','-u',str(ROOT / 'scripts/train_rounded.py'),weather,
                        '--workers',str(workers)], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                        stderr=subprocess.STDOUT, start_new_session=True)
            state('training', child_pids={w:p.pid for w,p in processes.items()})
            while any(p.poll() is None for p in processes.values()):
                bad = {w:p.returncode for w,p in processes.items() if p.poll() is not None and p.returncode != 0}
                require(not bad, f'Failed training jobs: {bad}; inspect logs')
                state('training', child_pids={w:p.pid for w,p in processes.items()})
                time.sleep(10)
            require(all(p.returncode == 0 for p in processes.values()), 'Training exited with failure')
            state('verifying_and_reporting')
            report()
            verify_sources(protected)
            prepared = json.loads((ROOT / 'preparation.json').read_text())
            for path, digest in prepared['input_hashes'].items():
                require(sha(ROOT / path) == digest, f'Rounded input changed: {path}')
            artifacts = {str(p.relative_to(ROOT)):sha(p) for name in ['datasets','reports']
                         for p in (ROOT/name).rglob('*') if p.is_file()}
            write_json(ROOT / 'artifact_hashes.json', artifacts)
            write_json(ROOT / 'complete.json', dict(all_ok=True, cases=8000, trials=360, predictions=90000,
                trained_metric_rows_verified=300, source_files_preserved=len(protected),
                new_simulations=0, finished_utc=datetime.now(timezone.utc).isoformat()))
            state('complete')
        except Exception as exc:
            for proc in processes.values():
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait()
            state('failed', error=repr(exc), child_pids={w:p.pid for w,p in processes.items()})
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers-per-weather', type=int, default=3)
    args = parser.parse_args()
    require(1 <= args.workers_per_weather <= 3, 'Use 1..3 workers per weather')
    main(args.workers_per_weather)
