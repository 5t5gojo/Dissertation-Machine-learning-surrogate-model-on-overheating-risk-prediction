"""Equal configuration-budget search and repeated held-out evaluation, without DSY."""
import os
for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[name] = '1'
import argparse
import copy
import json
import platform
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import joblib
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, ParameterSampler
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (r2_score, mean_absolute_error, mean_squared_error,
    balanced_accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix)
from xgboost import XGBRegressor
import xgboost
from revision_common import ROOT, OUT, TARGETS, FEATURES, dataset, sha, data_path, write_json

SEEDS = [42, 123, 202, 340, 567]
BASE = {
    'RF': dict(n_estimators=200, max_features='sqrt', max_depth=None, min_samples_leaf=1),
    'XGBoost': dict(n_estimators=400, learning_rate=.05, max_depth=6, subsample=.8,
                    colsample_bytree=.8, min_child_weight=3, reg_alpha=.1, reg_lambda=1.),
    'MLP': dict(hidden=[128, 64, 32], dropout=.2, lr=.001, weight_decay=.0001, batch_size=64),
}
SPACE = {
    'RF': dict(n_estimators=[200, 400], max_features=['sqrt', .7, 1.],
               max_depth=[None, 12, 24], min_samples_leaf=[1, 2, 4]),
    'XGBoost': dict(n_estimators=[200, 400, 600], learning_rate=[.03, .05, .1],
        max_depth=[3, 4, 6], subsample=[.7, .8, 1.], colsample_bytree=[.7, .8, 1.],
        min_child_weight=[1, 3, 5], reg_alpha=[0., .1, .5], reg_lambda=[1., 3., 10.]),
    'MLP': dict(hidden=[[64, 32], [128, 64, 32], [128, 128, 64]], dropout=[0., .1, .2],
        lr=[.0005, .001, .002], weight_decay=[.00001, .0001, .001], batch_size=[32, 64, 128]),
}

def candidates(n):
    return {m: [BASE[m]] + list(ParameterSampler(SPACE[m], n_iter=n-1, random_state=20260917))
            for m in BASE}

class Net(nn.Module):
    def __init__(self, hidden, dropout):
        super().__init__()
        layers = []
        width = len(FEATURES)
        for i, h in enumerate(hidden):
            layers.append(nn.Linear(width, h))
            if i < len(hidden)-1:
                layers.extend([nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(dropout)])
            else:
                layers.append(nn.ReLU())
            width = h
        layers.append(nn.Linear(width, len(TARGETS)))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

def fit_model(family, config, x, y, xv, yv, seed, epochs):
    if family != 'MLP':
        cls = RandomForestRegressor if family == 'RF' else XGBRegressor
        extra = {} if family == 'RF' else dict(objective='reg:squarederror', verbosity=0)
        models = [cls(**config, **extra, random_state=seed, n_jobs=1).fit(x, y[:, i])
                  for i in range(len(TARGETS))]
        return dict(family=family, models=models), []
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    sx, sy = StandardScaler().fit(x), StandardScaler().fit(y)
    xt = torch.tensor(sx.transform(x), dtype=torch.float32)
    yt = torch.tensor(sy.transform(y), dtype=torch.float32)
    xv = torch.tensor(sx.transform(xv), dtype=torch.float32)
    yv = torch.tensor(sy.transform(yv), dtype=torch.float32)
    model = Net(config['hidden'], config['dropout'])
    optimizer = torch.optim.Adam(model.parameters(), lr=config['lr'], weight_decay=config['weight_decay'])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=.5, min_lr=1e-5)
    best, wait, state = np.inf, 0, None
    curve = []
    for epoch in range(1, epochs+1):
        model.train()
        permutation = torch.randperm(len(xt))
        losses = []
        for idx in permutation.split(config['batch_size']):
            if len(idx) < 2:
                continue
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(model(xt[idx]), yt[idx])
            loss.backward()
            optimizer.step()
            losses.append((loss.item(), len(idx)))
        model.eval()
        with torch.no_grad():
            val = nn.functional.mse_loss(model(xv), yv).item()
        scheduler.step(val)
        curve.append(dict(epoch=epoch, train_loss=sum(l*n for l,n in losses)/sum(n for _,n in losses), val_loss=val))
        if val < best - 1e-6:
            best, wait, state = val, 0, copy.deepcopy(model.state_dict())
        else:
            wait += 1
            if wait >= 30:
                break
    model.load_state_dict(state)
    model.eval()
    return dict(family=family, model=model, sx=sx, sy=sy), curve

def predict(bundle, x):
    if bundle['family'] != 'MLP':
        return np.column_stack([m.predict(x) for m in bundle['models']])
    with torch.no_grad():
        pred = bundle['model'](torch.tensor(bundle['sx'].transform(x), dtype=torch.float32)).numpy()
    return bundle['sy'].inverse_transform(pred)

def error_metrics(y, p):
    if not len(y):
        return dict(n=0, R2=np.nan, MAE=np.nan, RMSE=np.nan, bias=np.nan)
    return dict(n=len(y), R2=r2_score(y, p) if len(y)>1 and np.var(y)>0 else np.nan,
        MAE=mean_absolute_error(y, p), RMSE=mean_squared_error(y, p)**.5, bias=float(np.mean(p-y)))

def night_diagnostics(ytr, yval, pval, y, p):
    tail = float(np.quantile(ytr[ytr > 0], .9))
    rows = []
    for name, mask in [('all', np.ones(len(y), bool)), ('zero', y==0), ('nonzero', y>0),
                       ('positive_training_p90_tail', y>=tail), ('above_32h', y>32)]:
        rows.append(dict(subgroup=name, tail_threshold=tail, **error_metrics(y[mask], p[mask])))
    event_val, event = yval>0, y>0
    thresholds = np.unique(np.r_[-np.inf, np.quantile(pval, np.linspace(0,1,101)), np.inf])
    score = [balanced_accuracy_score(event_val, pval > t) for t in thresholds]
    threshold = float(thresholds[np.argmax(score)])
    detected = p > threshold
    tn, fp, fn, tp = confusion_matrix(event, detected, labels=[False,True]).ravel()
    event_row = dict(threshold=threshold, val_balanced_accuracy=max(score),
        n_test=len(y), n_nonzero=int(event.sum()), test_zero_fraction=float(np.mean(~event)),
        precision=precision_score(event, detected, zero_division=0),
        recall=recall_score(event, detected, zero_division=0), f1=f1_score(event, detected, zero_division=0),
        balanced_accuracy=balanced_accuracy_score(event, detected),
        roc_auc=roc_auc_score(event, p) if len(np.unique(event))==2 else np.nan,
        average_precision=average_precision_score(event, p) if event.any() else np.nan,
        tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))
    return rows, event_row

def job(arg):
    arch, seed, configs, epochs, permutations = arg
    folder = OUT / 'evaluation' / arch / f'seed_{seed}'
    folder.mkdir(parents=True, exist_ok=True)
    d = dataset(arch)
    x, y = d[FEATURES].to_numpy(), d[TARGETS].to_numpy()
    tv, te = train_test_split(np.arange(len(d)), test_size=.15, random_state=seed)
    tr, va = train_test_split(tv, test_size=.15/.85, random_state=seed)
    split = pd.DataFrame({'run_id': d.run_id, 'split': ''})
    for label, idx in [('train',tr),('validation',va),('test',te)]:
        split.loc[idx, 'split'] = label
    split.to_csv(folder/'split.csv', index=False)
    variance = np.maximum(y[tr].var(axis=0), 1e-12)
    trials, metrics, predictions, diagnostics, events, imports, shap_rows = [], [], [], [], [], [], []
    for family in configs:
        best_score, best, selection = np.inf, None, None
        for k, config in enumerate(configs[family]):
            start = time.perf_counter()
            bundle, curve = fit_model(family, config, x[tr], y[tr], x[va], y[va], seed, epochs)
            pval = predict(bundle, x[va])
            score = float(np.mean(np.mean((pval-y[va])**2, axis=0)/variance))
            assert np.isfinite(score)
            record = dict(family=family, candidate=k, normalized_val_mse=score,
                          seconds=time.perf_counter()-start, epochs=len(curve), config=json.dumps(config))
            trials.append(record)
            if curve:
                pd.DataFrame(curve).to_csv(folder/f'MLP_candidate_{k}_loss.csv', index=False)
            if score < best_score:
                best_score, best, selection = score, bundle, record
            print(f'{arch} seed={seed} {family} candidate={k} val={score:.5f}', flush=True)
        write_json(folder/f'{family}_selected.json', selection)
        if family == 'MLP':
            torch.save(best['model'].state_dict(), folder/'MLP_weights.pt')
            joblib.dump((best['sx'], best['sy']), folder/'MLP_scalers.joblib')
        else:
            joblib.dump(best['models'], folder/f'{family}_models.joblib', compress=3)
        p, pv = predict(best, x[te]), predict(best, x[va])
        start = time.perf_counter()
        for _ in range(20):
            predict(best, x[te[:1]])
        latency = (time.perf_counter()-start)/20*1000
        for i,t in enumerate(TARGETS):
            metrics.append(dict(model=family, target=t, **error_metrics(y[te,i],p[:,i]), single_sample_ms=latency))
            predictions.extend(dict(run_id=d.run_id.iloc[j], model=family, target=t,
                                    y_true=float(y[j,i]), y_pred=float(p[k,i])) for k,j in enumerate(te))
        sub, ev = night_diagnostics(y[tr,3], y[va,3], pv[:,3], y[te,3], p[:,3])
        diagnostics.extend(dict(model=family, **r) for r in sub)
        events.append(dict(model=family, **ev))
        # Held-out permutation loss measures predictive reliance, not causality or SHAP direction.
        if family in ['XGBoost', 'MLP']:
            base_mse = np.mean((p-y[te])**2, axis=0)
            rng = np.random.default_rng(seed+8000)
            for f,feature in enumerate(FEATURES):
                for rep in range(permutations):
                    shuffled = x[te].copy()
                    shuffled[:,f] = shuffled[rng.permutation(len(te)),f]
                    delta = (np.mean((predict(best, shuffled)-y[te])**2,axis=0)-base_mse)/variance
                    imports.extend(dict(model=family, feature=feature, repeat=rep, target=t,
                                        normalized_mse_increase=float(delta[i])) for i,t in enumerate(TARGETS))
        if family == 'XGBoost':
            for i,t in enumerate(TARGETS):
                model = best['models'][i]
                sv = model.get_booster().predict(xgboost.DMatrix(x[te]), pred_contribs=True)
                assert np.allclose(sv.sum(axis=1), p[:,i], atol=2e-4, rtol=1e-4)
                shap_rows.extend(dict(target=t, feature=f, mean_abs_shap=float(v))
                                 for f,v in zip(FEATURES,np.abs(sv[:,:-1]).mean(axis=0)))
                pd.DataFrame(sv, columns=FEATURES+['base_value']).assign(run_id=d.run_id.iloc[te].to_numpy()).to_csv(
                    folder/f'shap_values_{t}.csv', index=False)
    for name, pred in [('AlwaysZero',np.zeros_like(y[te])),('TrainingMean',np.tile(y[tr].mean(axis=0),(len(te),1)))]:
        metrics.extend(dict(model=name,target=t,**error_metrics(y[te,i],pred[:,i])) for i,t in enumerate(TARGETS))
        sub,_ = night_diagnostics(y[tr,3],y[va,3],np.zeros(len(va)),y[te,3],pred[:,3])
        diagnostics.extend(dict(model=name,**r) for r in sub)
    for name,rows in [('search_trials',trials),('performance',metrics),('predictions',predictions),
                      ('night_subgroups',diagnostics),('night_event_detection',events),
                      ('permutation_importance',imports),('shap_importance',shap_rows)]:
        pd.DataFrame(rows).assign(archetype=arch,seed=seed).to_csv(folder/f'{name}.csv', index=False)
    write_json(folder/'complete.json',dict(archetype=arch,seed=seed,data_hash=sha(data_path(arch))))
    return arch,seed

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--candidates',type=int,default=6)
    ap.add_argument('--epochs',type=int,default=300)
    ap.add_argument('--permutations',type=int,default=5)
    ap.add_argument('--seeds',type=int,nargs='+',default=SEEDS)
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args()
    manifest=json.loads((OUT/'audit/manifest.json').read_text())
    assert manifest['rows_audited']==4000
    for a in ['detached','semi']:
        assert manifest['data_sha256'][a]==sha(data_path(a))
    configs=candidates(args.candidates)
    dest=OUT/'evaluation'
    dest.mkdir(parents=True,exist_ok=True)
    protocol=dict(seeds=args.seeds,candidates=configs,search_space=SPACE,epochs=args.epochs,
        permutation_repeats=args.permutations,workers=args.workers,
        objective='Mean validation MSE / training target variance over five outputs',
        budget='Equal candidate pipeline evaluations; not equal wall time or fitted estimator count',
        selection='One joint hyperparameter configuration per family, archetype and split',
        data_hash=manifest['data_sha256'],script_hash=sha(__file__),
        machine=platform.platform(),processor=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
        versions={m:__import__(m).__version__ for m in ['numpy','pandas','sklearn','torch','xgboost']})
    if args.resume:
        assert json.loads((dest/'protocol.json').read_text())==protocol,'Resume protocol changed'
    write_json(dest/'protocol.json',protocol)
    tasks=[(a,s,configs,args.epochs,args.permutations) for a in ['detached','semi'] for s in args.seeds
           if not (args.resume and (dest/a/f'seed_{s}/complete.json').exists())]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(job,t) for t in tasks]
        for f in as_completed(futures):
            print('COMPLETE',f.result(),flush=True)
    for name in ['search_trials','performance','predictions','night_subgroups','night_event_detection',
                 'permutation_importance','shap_importance']:
        combined=pd.concat([pd.read_csv(dest/a/f'seed_{s}'/f'{name}.csv')
                            for a in ['detached','semi'] for s in args.seeds],ignore_index=True)
        combined.to_csv(dest/f'{name}_all.csv',index=False)
    p=pd.read_csv(dest/'performance_all.csv')
    summary=p.groupby(['archetype','model','target'])[['R2','MAE','RMSE']].agg(['mean','std'])
    summary.columns=['_'.join(c) for c in summary.columns]
    summary.to_csv(dest/'performance_summary.csv')
    pairs=[]
    for (a,t),g in p[p.model.isin(BASE)].groupby(['archetype','target']):
        wide=g.pivot(index='seed',columns='model',values='R2')
        for m1,m2 in [('MLP','XGBoost'),('MLP','RF'),('XGBoost','RF')]:
            diff=wide[m1]-wide[m2]
            pairs.append(dict(archetype=a,target=t,comparison=f'{m1} minus {m2}',
                mean_R2_difference=diff.mean(),std_R2_difference=diff.std(),wins=int((diff>0).sum()),n=len(diff)))
    pd.DataFrame(pairs).to_csv(dest/'paired_differences.csv',index=False)
    print('All repeated evaluations and summaries completed.',flush=True)

if __name__=='__main__':
    main()
