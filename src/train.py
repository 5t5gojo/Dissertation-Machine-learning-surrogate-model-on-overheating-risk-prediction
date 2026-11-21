"""Train and evaluate the surrogates with the fixed protocol in config/training.json.

For every archetype and each of the five matched splits (70/15/15), each model family
tries the same six candidate configurations; the one with the lowest validation loss is
scored once on the test set. Results go to a new folder and never overwrite results/.

    python src/train.py TMYx --output output/training
    python src/train.py DSY1 --output output/training --seeds 42
"""

from __future__ import annotations

import os

# Single-threaded numerical libraries, as in the recorded experiment (set before import).
for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_variable] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from common import (  # noqa: E402
    ARCHETYPES,
    FEATURES,
    NIGHT,
    ROOT,
    TARGETS,
    WEATHERS,
    check_saved_split,
    dataset_path,
    load_dataset,
    read_json,
    sha256,
    split_indices,
    write_json,
)
from evaluation import (  # noqa: E402
    error_metrics,
    night_diagnostics,
    permutation_importance,
    shap_frame,
    shap_summary,
    xgboost_shap,
)
from models import fit_model, predict  # noqa: E402
from report import summarise_attributions, summarise_performance  # noqa: E402

TABLES = (
    "search_trials",
    "performance",
    "predictions",
    "night_subgroups",
    "night_event_detection",
    "permutation_importance",
    "shap_importance",
)


def select_candidate(family, configs, x, y, train, val, variance, seed, epochs, folder):
    """Fit every candidate; keep the one with the lowest variance-normalised validation MSE."""
    trials, best_score, best, selection = [], np.inf, None, None
    for k, config in enumerate(configs):
        start = time.perf_counter()
        bundle, curve = fit_model(family, config, x[train], y[train], x[val], y[val], seed, epochs)
        score = float(np.mean(np.mean((predict(bundle, x[val]) - y[val]) ** 2, axis=0) / variance))
        assert np.isfinite(score)
        record = {
            "family": family,
            "candidate": k,
            "normalized_val_mse": score,
            "seconds": time.perf_counter() - start,
            "epochs": len(curve),
            "config": json.dumps(config),
        }
        trials.append(record)
        if curve:
            pd.DataFrame(curve).to_csv(folder / f"MLP_candidate_{k}_loss.csv", index=False)
        if score < best_score:
            best_score, best, selection = score, bundle, record
        print(f"{folder.parent.name} {folder.name} {family} candidate={k} val={score:.5f}", flush=True)
    return best, selection, trials


def save_model(bundle: dict, family: str, folder: Path) -> None:
    if family == "MLP":
        torch.save(bundle["model"].state_dict(), folder / "MLP_weights.pt")
        joblib.dump((bundle["x_scaler"], bundle["y_scaler"]), folder / "MLP_scalers.joblib")
    else:
        joblib.dump(bundle["models"], folder / f"{family}_models.joblib", compress=3)


def run_job(weather: str, archetype: str, seed: int, candidates: dict, protocol: dict, output: Path) -> None:
    """Train, select and evaluate every family for one archetype and split."""
    folder = output / "evaluation" / archetype / f"seed_{seed}"
    folder.mkdir(parents=True, exist_ok=True)
    data = load_dataset(weather, archetype)
    x, y = data[FEATURES].to_numpy(), data[TARGETS].to_numpy()
    train, val, test = split_indices(len(data), seed)
    split = pd.DataFrame({"run_id": data.run_id, "split": ""})
    for label, indices in [("train", train), ("validation", val), ("test", test)]:
        split.loc[indices, "split"] = label
    split.to_csv(folder / "split.csv", index=False)
    variance = np.maximum(y[train].var(axis=0), 1e-12)
    test_ids = data.run_id.iloc[test]

    tables = {name: [] for name in TABLES}
    for family, configs in candidates.items():
        best, selection, trials = select_candidate(
            family, configs, x, y, train, val, variance, seed, protocol["epochs"], folder
        )
        tables["search_trials"] += trials
        write_json(folder / f"{family}_selected.json", selection)
        save_model(best, family, folder)

        p, p_val = predict(best, x[test]), predict(best, x[val])
        start = time.perf_counter()
        for _ in range(20):
            predict(best, x[test[:1]])
        latency_ms = (time.perf_counter() - start) / 20 * 1000
        for i, target in enumerate(TARGETS):
            tables["performance"].append(
                {
                    "model": family,
                    "target": target,
                    **error_metrics(y[test, i], p[:, i]),
                    "single_sample_ms": latency_ms,
                }
            )
            tables["predictions"] += [
                {
                    "run_id": data.run_id.iloc[j],
                    "model": family,
                    "target": target,
                    "y_true": float(y[j, i]),
                    "y_pred": float(p[k, i]),
                }
                for k, j in enumerate(test)
            ]

        subgroups, events = night_diagnostics(
            y[train, NIGHT], y[val, NIGHT], p_val[:, NIGHT], y[test, NIGHT], p[:, NIGHT]
        )
        tables["night_subgroups"] += [{"model": family, **row} for row in subgroups]
        tables["night_event_detection"].append({"model": family, **events})

        if family in ("XGBoost", "MLP"):
            rows = permutation_importance(best, x[test], y[test], variance, seed, protocol["permutation_repeats"])
            tables["permutation_importance"] += [{"model": family, **row} for row in rows]
        if family == "XGBoost":
            values = xgboost_shap(best, x[test], p)
            tables["shap_importance"] += shap_summary(values)
            for target, contributions in values.items():
                shap_frame(contributions, test_ids).to_csv(folder / f"shap_values_{target}.csv", index=False)

    # Trivial baselines: always zero, and the training mean.
    for name, p in [
        ("AlwaysZero", np.zeros_like(y[test])),
        ("TrainingMean", np.tile(y[train].mean(axis=0), (len(test), 1))),
    ]:
        tables["performance"] += [
            {"model": name, "target": t, **error_metrics(y[test, i], p[:, i])} for i, t in enumerate(TARGETS)
        ]
        subgroups, _ = night_diagnostics(
            y[train, NIGHT], y[val, NIGHT], np.zeros(len(val)), y[test, NIGHT], p[:, NIGHT]
        )
        tables["night_subgroups"] += [{"model": name, **row} for row in subgroups]

    for name, rows in tables.items():
        pd.DataFrame(rows).assign(archetype=archetype, seed=seed).to_csv(folder / f"{name}.csv", index=False)
    write_json(
        folder / "complete.json",
        {"archetype": archetype, "seed": seed, "data_hash": sha256(dataset_path(weather, archetype))},
    )


def combine(destination: Path, seeds: list[int]) -> None:
    """Concatenate per-split tables and write the summaries found in results/."""
    folder = destination / "evaluation"
    for name in TABLES:
        frames = [pd.read_csv(folder / a / f"seed_{s}" / f"{name}.csv") for a in ARCHETYPES for s in seeds]
        pd.concat(frames, ignore_index=True).to_csv(destination / f"{name}.csv", index=False)
    summarise_performance(destination)
    summarise_attributions(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("weather", choices=WEATHERS)
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--seeds", nargs="+", type=int, help="subset of the five recorded seeds")
    args = parser.parse_args()

    protocol = read_json(ROOT / "config" / "training.json")
    seeds = args.seeds if args.seeds is not None else protocol["seeds"]
    if len(set(seeds)) != len(seeds) or not set(seeds) <= set(protocol["seeds"]):
        parser.error("Use distinct seeds from config/training.json")
    destination = args.output.resolve() / args.weather
    if destination.exists():
        parser.error(f"Refusing to overwrite {destination}; choose a new output folder")
    if destination.is_relative_to(ROOT / "data") or destination.is_relative_to(ROOT / "results"):
        parser.error("The published data/ and results/ folders are read-only")

    # Validate every partition before any expensive fitting.
    for archetype in ARCHETYPES:
        frame = load_dataset(args.weather, archetype)
        for seed in seeds:
            check_saved_split(frame, archetype, seed)
    versions = {name: __import__(name).__version__ for name in protocol["versions"]}
    if versions != protocol["versions"]:
        warnings.warn("Package versions differ from the recorded experiment; scores may differ slightly.", stacklevel=1)
    write_json(
        destination / "protocol.json",
        protocol
        | {
            "seeds": seeds,
            "actual_versions": versions,
            "data_hash": {a: sha256(dataset_path(args.weather, a)) for a in ARCHETYPES},
        },
    )

    for archetype in ARCHETYPES:
        for seed in seeds:
            run_job(args.weather, archetype, seed, protocol["candidates"], protocol, destination)
    combine(destination, seeds)
    print(f"Completed: {destination}")


if __name__ == "__main__":
    main()
