"""Test-set scoring, night-time tail diagnostics and feature attributions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from common import FEATURES, TARGETS
from models import predict

NIGHT_TAIL_HOURS = 32  # diagnostic cut-off borrowed from TM59; our count is summer-only


def error_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    """R2, MAE, RMSE and mean bias (prediction - simulation); NaN where undefined."""
    if not len(y):
        return {"n": 0, "R2": np.nan, "MAE": np.nan, "RMSE": np.nan, "bias": np.nan}
    return {
        "n": len(y),
        "R2": r2_score(y, p) if len(y) > 1 and np.var(y) > 0 else np.nan,
        "MAE": mean_absolute_error(y, p),
        "RMSE": mean_squared_error(y, p) ** 0.5,
        "bias": float(np.mean(p - y)),
    }


def night_diagnostics(
    y_train: np.ndarray, y_val: np.ndarray, p_val: np.ndarray, y: np.ndarray, p: np.ndarray
) -> tuple[list[dict], dict]:
    """Errors in night-time subgroups, and how well predictions detect any night overheating.

    Subgroups: all, zero, nonzero, the tail at or above the 90th percentile of positive
    training values, and cases above 32 h. Event detection thresholds the continuous
    prediction at the value that maximises balanced accuracy on the validation set.
    """
    positives = y_train[y_train > 0]
    tail = float(np.quantile(positives, 0.9)) if len(positives) else np.nan
    subgroups = {
        "all": np.ones(len(y), bool),
        "zero": y == 0,
        "nonzero": y > 0,
        "positive_training_p90_tail": y >= tail,
        "above_32h": y > NIGHT_TAIL_HOURS,
    }
    rows = [
        {"subgroup": name, "tail_threshold": tail, **error_metrics(y[mask], p[mask])}
        for name, mask in subgroups.items()
    ]

    event_val, event = y_val > 0, y > 0
    if len(np.unique(event_val)) < 2:
        undefined = dict.fromkeys(
            ["threshold", "val_balanced_accuracy", "precision", "recall", "f1", "balanced_accuracy"]
            + ["roc_auc", "average_precision", "tn", "fp", "fn", "tp"],
            np.nan,
        )
        return rows, {
            "n_test": len(y),
            "n_nonzero": int(event.sum()),
            "test_zero_fraction": float(np.mean(~event)),
            **undefined,
            "status": "not_identifiable_single_class_validation",
        }

    thresholds = np.unique(np.r_[-np.inf, np.quantile(p_val, np.linspace(0, 1, 101)), np.inf])
    scores = [(np.mean((p_val > t)[event_val]) + np.mean((p_val <= t)[~event_val])) / 2 for t in thresholds]
    threshold = float(thresholds[np.argmax(scores)])
    detected = p > threshold
    tn, fp, fn, tp = confusion_matrix(event, detected, labels=[False, True]).ravel()
    two_classes = len(np.unique(event)) == 2
    return rows, {
        "threshold": threshold,
        "val_balanced_accuracy": max(scores),
        "n_test": len(y),
        "n_nonzero": int(event.sum()),
        "test_zero_fraction": float(np.mean(~event)),
        "precision": precision_score(event, detected, zero_division=0),
        "recall": recall_score(event, detected, zero_division=0),
        "f1": f1_score(event, detected, zero_division=0),
        "balanced_accuracy": (tp / (tp + fn) + tn / (tn + fp)) / 2 if two_classes else np.nan,
        "roc_auc": roc_auc_score(event, p) if two_classes else np.nan,
        "average_precision": average_precision_score(event, p) if two_classes else np.nan,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "status": "ok" if two_classes else "not_identifiable_single_class_test",
    }


def permutation_importance(
    bundle: dict, x: np.ndarray, y: np.ndarray, variance: np.ndarray, seed: int, repeats: int
) -> list[dict]:
    """Increase in held-out MSE (scaled by training variance) when one input is shuffled.

    Measures predictive reliance on an input, not a causal effect.
    """
    base_mse = np.mean((predict(bundle, x) - y) ** 2, axis=0)
    rng = np.random.default_rng(seed + 8000)
    rows = []
    for f, feature in enumerate(FEATURES):
        for repeat in range(repeats):
            shuffled = x.copy()
            shuffled[:, f] = shuffled[rng.permutation(len(x)), f]
            increase = (np.mean((predict(bundle, shuffled) - y) ** 2, axis=0) - base_mse) / variance
            rows += [
                {"feature": feature, "repeat": repeat, "target": t, "normalized_mse_increase": float(increase[i])}
                for i, t in enumerate(TARGETS)
            ]
    return rows


def xgboost_shap(bundle: dict, x: np.ndarray, p: np.ndarray) -> dict[str, np.ndarray]:
    """Exact TreeSHAP values per target (columns: FEATURES + base value).

    Each row of contributions must sum to the model's prediction.
    """
    values = {}
    for i, target in enumerate(TARGETS):
        booster = bundle["models"][i].get_booster()
        contributions = booster.predict(xgboost.DMatrix(x), pred_contribs=True)
        assert np.allclose(contributions.sum(axis=1), p[:, i], atol=2e-4, rtol=1e-4)
        values[target] = contributions
    return values


def shap_summary(values: dict[str, np.ndarray]) -> list[dict]:
    """Mean absolute SHAP value per target and feature, in target units."""
    return [
        {"target": target, "feature": feature, "mean_abs_shap": float(v)}
        for target, contributions in values.items()
        for feature, v in zip(FEATURES, np.abs(contributions[:, :-1]).mean(axis=0), strict=True)
    ]


def shap_frame(contributions: np.ndarray, run_ids) -> pd.DataFrame:
    return pd.DataFrame(contributions, columns=FEATURES + ["base_value"]).assign(run_id=np.asarray(run_ids))
