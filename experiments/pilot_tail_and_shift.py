"""Exploratory pilot on the existing 8,000 runs (not a paper result).

Random splits, XGBoost only, few tail designs per test fold (about 12-13 above 32 h), so the numbers
only indicate direction. Run: python experiments/pilot_tail_and_shift.py

1. Learning curve under DSY1 with a fixed 400-design test set.
2. Split conformal and CQR coverage overall and in the tail (night hours above 32 h).
3. A TMYx-trained model applied to DSY1, recalibrated with k DSY1 runs.
"""

import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
FEATURES = ast.literal_eval(re.search(r"FEATURES = (\[.*?\])", (ROOT / "src" / "common.py").read_text(), re.S).group(1))


def data(w, a):
    return pd.read_csv(ROOT / "data" / w / f"{a}.csv").set_index("run_id").sort_index()


def _fit(X, y, seed, **kw):
    params = {
        "subsample": 0.8,
        "max_depth": 4,
        "eta": 0.05,
        "min_child_weight": 3,
        "alpha": 0.1,
        "lambda": 1.0,
        "seed": seed,
        "nthread": 2,
    } | kw
    return xgb.train(params, xgb.DMatrix(X, y), num_boost_round=400)


def pred(m, X):
    return m.predict(xgb.DMatrix(X))


out = []
print("== Learning curve (DSY1), fixed 400-design test set, 3 repeats per size")
for a in ["detached", "semi"]:
    d = data("DSY1", a)
    for target in ["hours_gt26_night", "T_op_peak"]:
        X, y = d[FEATURES].to_numpy(), d[target].to_numpy()
        rng = np.random.default_rng(0)
        perm = rng.permutation(len(y))
        test, pool = perm[:400], perm[400:]
        tail = y[test] > 32
        for n in [200, 400, 800, 1200, 1600]:
            r = []
            for rep in range(3):
                tr = np.random.default_rng(100 + rep).choice(pool, n, replace=False)
                p = pred(_fit(X[tr], y[tr], rep), X[test])
                e = p - y[test]
                r.append(
                    [
                        np.sqrt(np.mean(e**2)),
                        1 - np.sum(e**2) / np.sum((y[test] - y[test].mean()) ** 2),
                        e[tail].mean() if target == "hours_gt26_night" else np.nan,
                        np.sqrt(np.mean(e[tail] ** 2)) if target == "hours_gt26_night" else np.nan,
                    ]
                )
            m = np.mean(r, axis=0)
            print(
                f"{a:8s} {target:17s} n={n:4d}  RMSE={m[0]:.3f}  R2={m[1]:.4f}"
                + (
                    f"  tail(>32h, n={tail.sum()}) bias={m[2]:+.2f} RMSE={m[3]:.2f}"
                    if target == "hours_gt26_night"
                    else ""
                )
            )

print("\n== Conformal pilot, night hours, DSY1: train 1200 / calibrate 400 / test 400, 90% target, 5 seeds")
for a in ["detached", "semi"]:
    d = data("DSY1", a)
    X, y = d[FEATURES].to_numpy(), d["hours_gt26_night"].to_numpy()
    rows = []
    for s in range(5):
        perm = np.random.default_rng(s).permutation(len(y))
        tr, ca, te = perm[:1200], perm[1200:1600], perm[1600:]
        m = _fit(X[tr], y[tr], s)
        q = np.quantile(np.abs(pred(m, X[ca]) - y[ca]), np.ceil(0.9 * 401) / 400)
        pt = pred(m, X[te])
        cov = np.abs(pt - y[te]) <= q
        lo = _fit(X[tr], y[tr], s, objective="reg:quantileerror", quantile_alpha=0.05)
        hi = _fit(X[tr], y[tr], s, objective="reg:quantileerror", quantile_alpha=0.95)
        sc = np.maximum(pred(lo, X[ca]) - y[ca], y[ca] - pred(hi, X[ca]))
        qc = np.quantile(sc, np.ceil(0.9 * 401) / 400)
        L, H = pred(lo, X[te]) - qc, pred(hi, X[te]) + qc
        cq = (y[te] >= L) & (y[te] <= H)
        t, z = y[te] > 32, y[te] == 0
        rows.append(
            [
                cov.mean(),
                cov[t].mean(),
                cov[z].mean(),
                2 * q,
                cq.mean(),
                cq[t].mean(),
                cq[z].mean(),
                (H - L).mean(),
                (H - L)[t].mean(),
                t.sum(),
            ]
        )
    r = np.mean(rows, axis=0)
    print(
        f"{a:8s} split-CP: all {r[0]:.1%}  tail {r[1]:.1%}  width {r[3]:.1f} h | "
        f"CQR: all {r[4]:.1%}  tail {r[5]:.1%}  width {r[7]:.1f} h (tail {r[8]:.1f} h) | tail n≈{r[9]:.0f}"
    )

print("\n== Shift pilot: TMYx model and calibration applied to DSY1; recalibrated with k DSY1 runs (night hours)")
for a in ["detached", "semi"]:
    dt, dd = data("TMYx", a), data("DSY1", a)
    assert (dt.index == dd.index).all()
    X, yt, yd = dt[FEATURES].to_numpy(), dt["hours_gt26_night"].to_numpy(), dd["hours_gt26_night"].to_numpy()
    res = {}
    for s in range(5):
        perm = np.random.default_rng(s).permutation(len(yt))
        tr, ca, te = perm[:1200], perm[1200:1600], perm[1600:]
        m = _fit(X[tr], yt[tr], s)
        q0 = np.quantile(np.abs(pred(m, X[ca]) - yt[ca]), 0.9)
        pte = pred(m, X[te])
        res.setdefault("TMYx-calibrated", []).append(np.mean(np.abs(pte - yd[te]) <= q0))
        for k in [10, 25, 50, 100, 200, 400]:
            c = ca[:k]
            qk = np.quantile(np.abs(pred(m, X[c]) - yd[c]), min(1, np.ceil(0.9 * (k + 1)) / k))
            cov = np.abs(pte - yd[te]) <= qk
            res.setdefault(f"recal k={k}", []).append((cov.mean(), cov[yd[te] > 32].mean(), 2 * qk))
    print(f"{a:8s} TMYx-calibrated coverage on DSY1: {np.mean(res['TMYx-calibrated']):.1%}")
    for k in [10, 25, 50, 100, 200, 400]:
        r = np.mean(res[f"recal k={k}"], axis=0)
        print(f"{a:8s}   recalibrate with {k:3d} DSY1 runs: coverage {r[0]:.1%}, tail {r[1]:.1%}, width {r[2]:.1f} h")
