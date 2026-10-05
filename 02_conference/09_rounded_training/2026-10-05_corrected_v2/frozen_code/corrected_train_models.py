"""Apply the unchanged repeated-validation protocol to corrected simulation data."""
import os
for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[name] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(ROOT / 'frozen_code'))
import revision_model_eval as base
from dsy_model_eval import night_diagnostics
from revision_common import FEATURES, TARGETS, sha, write_json
import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
import xgboost

OLD = PROJECT / '02_conference/03_data/evaluation'


def frame(weather, arch):
    d = pd.read_csv(ROOT / 'datasets' / weather / f'training_{arch}.csv').sort_values('run_id').reset_index(drop=True)
    assert len(d) == 2000 and d.run_id.is_unique and d.status.eq('ok').all()
    assert np.isfinite(d[FEATURES + TARGETS]).all().all()
    return d


def job(task):
    weather, arch, seed, configs, epochs, repeats = task
    d = frame(weather, arch)
    tv, te = train_test_split(np.arange(len(d)), test_size=.15, random_state=seed)
    tr, va = train_test_split(tv, test_size=.15/.85, random_state=seed)
    original = pd.read_csv(OLD / arch / f'seed_{seed}/split.csv').set_index('run_id')
    for label, idx in [('train', tr), ('validation', va), ('test', te)]:
        assert original.loc[d.run_id.iloc[idx], 'split'].eq(label).all()
    base.OUT = ROOT / 'datasets' / weather
    base.dataset = lambda a: frame(weather, a)
    base.data_path = lambda a: ROOT / 'datasets' / weather / f'training_{a}.csv'
    # Same diagnostic calculation with guards for empty/single-class subgroups.
    base.night_diagnostics = night_diagnostics
    return base.job((arch, seed, configs, epochs, repeats))


def verify(weather, protocol):
    dest = ROOT / 'datasets' / weather / 'evaluation'
    all_preds = pd.read_csv(dest / 'predictions_all.csv')
    all_metrics = pd.read_csv(dest / 'performance_all.csv')
    trials = pd.read_csv(dest / 'search_trials_all.csv')
    assert len(all_preds) == 45000 and len(trials) == 180
    errors, checked_metrics, shap_checks = [], 0, 0
    for arch in ['detached', 'semi']:
        d = frame(weather, arch)
        x, y = d[FEATURES].to_numpy(), d[TARGETS].to_numpy()
        for seed in base.SEEDS:
            folder = dest / arch / f'seed_{seed}'
            split = pd.read_csv(folder / 'split.csv').set_index('run_id')
            original = pd.read_csv(OLD / arch / f'seed_{seed}/split.csv').set_index('run_id')
            assert split.loc[d.run_id, 'split'].equals(original.loc[d.run_id, 'split'])
            tr = np.flatnonzero(split.loc[d.run_id, 'split'].eq('train').to_numpy())
            va = np.flatnonzero(split.loc[d.run_id, 'split'].eq('validation').to_numpy())
            te = np.flatnonzero(split.loc[d.run_id, 'split'].eq('test').to_numpy())
            assert (len(tr), len(va), len(te)) == (1400, 300, 300)
            for family in ['RF', 'XGBoost', 'MLP']:
                selected = json.loads((folder / f'{family}_selected.json').read_text())
                records = trials[trials.archetype.eq(arch) & trials.seed.eq(seed) & trials.family.eq(family)]
                best = records.loc[records.normalized_val_mse.idxmin()]
                assert int(best.candidate) == selected['candidate']
                assert json.loads(selected['config']) == protocol['candidates'][family][selected['candidate']]
                if family == 'MLP':
                    config = json.loads(selected['config'])
                    model = base.Net(config['hidden'], config['dropout'])
                    model.load_state_dict(torch.load(folder / 'MLP_weights.pt', map_location='cpu', weights_only=True))
                    model.eval()
                    sx, sy = joblib.load(folder / 'MLP_scalers.joblib')
                    np.testing.assert_allclose(sx.mean_, x[tr].mean(axis=0), rtol=1e-12, atol=1e-12)
                    np.testing.assert_allclose(sy.mean_, y[tr].mean(axis=0), rtol=1e-12, atol=1e-12)
                    np.testing.assert_allclose(sx.var_, x[tr].var(axis=0), rtol=1e-12, atol=1e-12)
                    np.testing.assert_allclose(sy.var_, y[tr].var(axis=0), rtol=1e-12, atol=1e-12)
                    bundle = dict(family=family, model=model, sx=sx, sy=sy)
                else:
                    bundle = dict(family=family, models=joblib.load(folder / f'{family}_models.joblib'))
                pv, pt = base.predict(bundle, x[va]), base.predict(bundle, x[te])
                loss = np.mean(np.mean((pv-y[va])**2, axis=0) / np.maximum(y[tr].var(axis=0), 1e-12))
                np.testing.assert_allclose(loss, selected['normalized_val_mse'], rtol=3e-5, atol=1e-7)
                for i, target in enumerate(TARGETS):
                    saved = all_preds[all_preds.archetype.eq(arch) & all_preds.seed.eq(seed) & all_preds.model.eq(family) & all_preds.target.eq(target)].set_index('run_id')
                    np.testing.assert_allclose(saved.loc[d.run_id.iloc[te], 'y_true'], y[te, i], rtol=0, atol=1e-10)
                    diff = np.max(np.abs(saved.loc[d.run_id.iloc[te], 'y_pred'].to_numpy()-pt[:, i]))
                    assert diff < 2e-5
                    errors.append(float(diff))
                    recorded = all_metrics[all_metrics.archetype.eq(arch) & all_metrics.seed.eq(seed) & all_metrics.model.eq(family) & all_metrics.target.eq(target)].iloc[0]
                    for metric, value in base.error_metrics(y[te, i], pt[:, i]).items():
                        np.testing.assert_allclose(recorded[metric], value, rtol=2e-5, atol=1e-7, equal_nan=True)
                    checked_metrics += 1
                    if family == 'XGBoost':
                        sv = pd.read_csv(folder / f'shap_values_{target}.csv').set_index('run_id').loc[d.run_id.iloc[te]]
                        recalculated = bundle['models'][i].get_booster().predict(xgboost.DMatrix(x[te]), pred_contribs=True)
                        np.testing.assert_allclose(sv[FEATURES + ['base_value']], recalculated, rtol=1e-5, atol=2e-5)
                        np.testing.assert_allclose(recalculated.sum(axis=1), pt[:, i], rtol=1e-4, atol=2e-4)
                        shap_checks += 1
    write_json(dest / 'verification.json', dict(trials=len(trials), predictions=len(all_preds), metric_rows_recomputed=checked_metrics,
        shap_arrays_recomputed=shap_checks, maximum_prediction_difference=max(errors),
        split_assignments_match_original=True, scalers_training_only=True, selection_minimum_validation_loss=True,
        adapter_sha256=sha(__file__), protocol_sha256=sha(dest / 'protocol.json')))


def main(weather, workers):
    source = ROOT / 'datasets' / weather
    complete = json.loads((source / 'complete.json').read_text())
    assert complete['all_ok'] and complete['audited'] == 4000
    for arch, digest in complete['training_hashes'].items():
        assert sha(source / f'training_{arch}.csv') == digest
    original = json.loads((ROOT / 'backup/original_model_protocol.json').read_text())
    configs = base.candidates(6)
    assert configs == original['candidates'] and base.SEEDS == original['seeds']
    protocol = dict(variant='combined_v2', weather=weather, seeds=base.SEEDS, candidates=configs,
        epochs=original['epochs'], permutation_repeats=original['permutation_repeats'],
        objective=original['objective'], budget=original['budget'], data_hash=complete['training_hashes'],
        adapter_hash=sha(__file__), evaluator_hash=sha(base.__file__),
        original_protocol_hash=sha(ROOT / 'backup/original_model_protocol.json'),
        source_simulation_protocol_hash=sha(ROOT / 'protocol.json'),
        versions={m:__import__(m).__version__ for m in ['numpy', 'pandas', 'sklearn', 'torch', 'xgboost']},
        platform=platform.platform(), single_class_discrimination='NA, not perfect classification')
    dest = source / 'evaluation'
    if (dest / 'protocol.json').exists():
        assert json.loads((dest / 'protocol.json').read_text()) == protocol, 'Evaluation provenance changed'
    else:
        dest.mkdir(exist_ok=True)
        write_json(dest / 'protocol.json', protocol)
    tasks = []
    for arch in ['detached', 'semi']:
        for seed in base.SEEDS:
            done = dest / arch / f'seed_{seed}/complete.json'
            if done.exists():
                assert json.loads(done.read_text())['data_hash'] == complete['training_hashes'][arch]
            else:
                tasks.append((weather, arch, seed, configs, original['epochs'], original['permutation_repeats']))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(job, task) for task in tasks]):
            print('COMPLETE', weather, future.result(), flush=True)
    for name in ['search_trials', 'performance', 'predictions', 'night_subgroups', 'night_event_detection', 'permutation_importance', 'shap_importance']:
        combined = pd.concat([pd.read_csv(dest / a / f'seed_{s}' / f'{name}.csv') for a in ['detached', 'semi'] for s in base.SEEDS], ignore_index=True)
        combined.to_csv(dest / f'{name}_all.csv', index=False)
    p = pd.read_csv(dest / 'performance_all.csv')
    summary = p.groupby(['archetype', 'model', 'target'])[['R2', 'MAE', 'RMSE']].agg(['mean', 'std'])
    summary.columns = ['_'.join(c) for c in summary.columns]
    summary.to_csv(dest / 'performance_summary.csv')
    verify(weather, protocol)
    write_json(dest / 'complete.json', dict(all_ok=True, trials=180, predictions=45000,
        performance_sha256=sha(dest / 'performance_all.csv'), verification_sha256=sha(dest / 'verification.json')))
    print(weather, 'corrected five-split evaluation verified', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weather', choices=['TMYx', 'DSY1'])
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    assert 1 <= args.workers <= 6
    main(args.weather, args.workers)
