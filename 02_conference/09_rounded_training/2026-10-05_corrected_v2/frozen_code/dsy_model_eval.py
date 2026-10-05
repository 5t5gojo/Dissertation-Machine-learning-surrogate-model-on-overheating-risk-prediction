"""Reuse the original evaluation protocol on audited DSY data, in separate outputs."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import platform

import revision_model_eval as base
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split
from revision_common import ROOT, TARGETS, FEATURES, sha, write_json

SCENARIO = 'Z1_DSY1_2030s_HIGH50_CIBSE_v1.1'
FOLDER = ROOT.parent / '02_conference/03_data/weather_scenarios' / SCENARIO / 'full'
OLD = ROOT.parent / '02_conference/03_data/evaluation'


def data_path(arch):
    return FOLDER / f'training_{arch}.csv'


def dataset(arch):
    frame = pd.read_csv(data_path(arch)).sort_values('run_id').reset_index(drop=True)
    if len(frame) != 2000 or not frame.run_id.is_unique or not frame.status.eq('ok').all():
        raise ValueError('DSY training dataset is incomplete')
    if not np.isfinite(frame[FEATURES + TARGETS]).all().all():
        raise ValueError('Non-finite DSY model inputs/targets')
    return frame


def night_diagnostics(ytr, yval, pval, y, p):
    positives = ytr[ytr > 0]
    tail = float(np.quantile(positives, .9)) if len(positives) else np.nan
    rows = [dict(subgroup=name, tail_threshold=tail, **base.error_metrics(y[mask], p[mask]))
            for name, mask in [('all', np.ones(len(y), bool)), ('zero', y == 0), ('nonzero', y > 0),
                               ('positive_training_p90_tail', y >= tail), ('above_32h', y > 32)]]
    event_val, event = yval > 0, y > 0
    if len(np.unique(event_val)) < 2:
        return rows, dict(n_test=len(y), n_nonzero=int(event.sum()), test_zero_fraction=float(np.mean(~event)),
                         threshold=np.nan, val_balanced_accuracy=np.nan, precision=np.nan, recall=np.nan,
                         f1=np.nan, balanced_accuracy=np.nan, roc_auc=np.nan, average_precision=np.nan,
                         tn=np.nan, fp=np.nan, fn=np.nan, tp=np.nan,
                         status='not_identifiable_single_class_validation')
    thresholds = np.unique(np.r_[-np.inf, np.quantile(pval, np.linspace(0, 1, 101)), np.inf])
    scores = [(np.mean((pval > t)[event_val]) + np.mean((pval <= t)[~event_val])) / 2 for t in thresholds]
    threshold = float(thresholds[np.argmax(scores)])
    detected = p > threshold
    tn, fp, fn, tp = confusion_matrix(event, detected, labels=[False, True]).ravel()
    two_classes = len(np.unique(event)) == 2
    return rows, dict(threshold=threshold, val_balanced_accuracy=max(scores), n_test=len(y),
        n_nonzero=int(event.sum()), test_zero_fraction=float(np.mean(~event)),
        precision=precision_score(event, detected, zero_division=0), recall=recall_score(event, detected, zero_division=0),
        f1=f1_score(event, detected, zero_division=0),
        balanced_accuracy=(tp / (tp + fn) + tn / (tn + fp)) / 2 if two_classes else np.nan,
        roc_auc=roc_auc_score(event, p) if two_classes else np.nan,
        average_precision=average_precision_score(event, p) if two_classes else np.nan,
        tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
        status='ok' if two_classes else 'not_identifiable_single_class_test')


def job(arg):
    arch, seed, configs, epochs, permutations = arg
    # Verify identical record assignments before using the established training code.
    d = dataset(arch)
    tv, te = train_test_split(np.arange(len(d)), test_size=.15, random_state=seed)
    tr, va = train_test_split(tv, test_size=.15/.85, random_state=seed)
    original = pd.read_csv(OLD / arch / f'seed_{seed}/split.csv').set_index('run_id')
    for label, idx in [('train', tr), ('validation', va), ('test', te)]:
        if not original.loc[d.run_id.iloc[idx], 'split'].eq(label).all():
            raise ValueError('DSY partition differs from original repeated evaluation')
    base.OUT = FOLDER
    base.dataset = dataset
    base.data_path = data_path
    base.night_diagnostics = night_diagnostics
    return base.job(arg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    final = json.loads((FOLDER / 'finalization.json').read_text())
    assert final['all_ok'] and final['audited'] == 4000
    for arch, digest in final['training_hashes'].items():
        assert sha(data_path(arch)) == digest
    old = json.loads((OLD / 'protocol.json').read_text())
    configs = base.candidates(6)
    assert configs == old['candidates'] and base.SEEDS == old['seeds']
    dest = FOLDER / 'evaluation'
    protocol = dict(weather=SCENARIO, seeds=base.SEEDS, candidates=configs, epochs=old['epochs'],
                    permutation_repeats=old['permutation_repeats'], budget=old['budget'],
                    objective=old['objective'], data_hash=final['training_hashes'],
                    original_protocol_hash=sha(OLD / 'protocol.json'),
                    adapter_hash=sha(__file__), base_evaluator_hash=sha(base.__file__),
                    versions={m:__import__(m).__version__ for m in ['numpy','pandas','sklearn','torch','xgboost']},
                    platform=platform.platform(),
                    night_change='Undefined single-class discrimination is reported as NA, not perfect performance')
    if dest.exists():
        assert args.resume and json.loads((dest / 'protocol.json').read_text()) == protocol, 'Existing evaluation or changed protocol'
    else:
        dest.mkdir()
        write_json(dest / 'protocol.json', protocol)
    tasks = [(a, s, configs, old['epochs'], old['permutation_repeats']) for a in ['detached', 'semi'] for s in base.SEEDS
             if not (args.resume and (dest / a / f'seed_{s}/complete.json').exists())]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(job, task) for task in tasks]):
            print('COMPLETE', future.result(), flush=True)
    for name in ['search_trials','performance','predictions','night_subgroups','night_event_detection','permutation_importance','shap_importance']:
        combined = pd.concat([pd.read_csv(dest / a / f'seed_{s}' / f'{name}.csv') for a in ['detached','semi'] for s in base.SEEDS], ignore_index=True)
        combined.to_csv(dest / f'{name}_all.csv', index=False)
    p = pd.read_csv(dest / 'performance_all.csv')
    summary = p.groupby(['archetype','model','target'])[['R2','MAE','RMSE']].agg(['mean','std'])
    summary.columns = ['_'.join(c) for c in summary.columns]
    summary.to_csv(dest / 'performance_summary.csv')
    trials = pd.read_csv(dest / 'search_trials_all.csv')
    pred = pd.read_csv(dest / 'predictions_all.csv')
    assert len(trials) == 180 and len(pred) == 45000
    write_json(dest / 'complete.json', dict(trials=180, prediction_rows=45000, seeds=base.SEEDS,
                                          performance_sha256=sha(dest / 'performance_all.csv')))
    print('DSY five-split, six-candidate evaluation complete', flush=True)


if __name__ == '__main__':
    main()
