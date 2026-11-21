"""Check the published data and results for internal consistency, without training.

    python src/verify.py

Checks: file checksums; dataset inputs equal the saved samples; every split equals the
saved partition; every search trial uses the recorded candidate configuration; every
score in results/*/performance.csv is recomputed from the saved predictions (including
the two baselines); and the summary tables are recomputed from the per-split tables.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import (
    ARCHETYPES,
    FEATURES,
    N_CASES,
    ROOT,
    TARGETS,
    WEATHERS,
    check_saved_split,
    load_dataset,
    read_json,
    sha256,
    split_indices,
)
from report import cross_model_agreement, performance_summary, shap_ranks

BASELINES = ("AlwaysZero", "TrainingMean")


def scores(actual: np.ndarray, predicted: np.ndarray) -> list[float]:
    delta = predicted - actual
    return [
        1 - np.sum(delta**2) / np.sum((actual - actual.mean()) ** 2),
        np.abs(delta).mean(),
        np.sqrt(np.mean(delta**2)),
        delta.mean(),
    ]


def verify_weather(weather: str, protocol: dict) -> int:
    folder = ROOT / "results" / weather
    predictions = pd.read_csv(folder / "predictions.csv")
    performance = pd.read_csv(folder / "performance.csv")
    trials = pd.read_csv(folder / "search_trials.csv")
    families = list(protocol["candidates"])
    seeds = protocol["seeds"]
    n_test = round(0.15 * N_CASES)
    assert len(predictions) == len(ARCHETYPES) * len(seeds) * len(families) * len(TARGETS) * n_test
    assert len(trials) == len(ARCHETYPES) * len(seeds) * len(families) * 6
    assert not predictions.duplicated(["archetype", "seed", "model", "target", "run_id"]).any()
    predictions = predictions.set_index(["archetype", "seed", "model", "target", "run_id"]).sort_index()
    performance = performance.set_index(["archetype", "seed", "model", "target"]).sort_index()

    checked = 0
    for archetype in ARCHETYPES:
        data = load_dataset(weather, archetype)
        samples = pd.read_csv(ROOT / "data" / "samples" / f"{archetype}.csv").set_index("run_id")
        np.testing.assert_array_equal(data[FEATURES], samples.loc[data.run_id, FEATURES])
        for seed in seeds:
            check_saved_split(data, archetype, seed)
            train, _, test = split_indices(len(data), seed)
            test_ids = data.run_id.iloc[test]

            for family in families:
                group = trials[(trials.archetype == archetype) & (trials.seed == seed) & (trials.family == family)]
                assert len(group) == 6
                for trial in group.itertuples():
                    assert json.loads(trial.config) == protocol["candidates"][family][trial.candidate]

            for target in TARGETS:
                actual = data[target].to_numpy()[test]
                for model in families + list(BASELINES):
                    if model == "AlwaysZero":
                        predicted = np.zeros_like(actual)
                    elif model == "TrainingMean":
                        predicted = np.full(actual.shape, data[target].iloc[train].mean(), dtype=float)
                    else:
                        saved = predictions.loc[(archetype, seed, model, target)].loc[test_ids]
                        np.testing.assert_array_equal(saved.y_true, actual)
                        predicted = saved.y_pred.to_numpy()
                    row = performance.loc[(archetype, seed, model, target)]
                    assert row["n"] == n_test
                    np.testing.assert_allclose(
                        row[["R2", "MAE", "RMSE", "bias"]], scores(actual, predicted), rtol=1e-9, atol=1e-9
                    )
                    checked += 1

    recomputed = {
        "performance_summary": performance_summary(performance.reset_index()).reset_index(),
        "shap_mean_values_and_ranks": shap_ranks(pd.read_csv(folder / "shap_importance.csv")),
        "cross_model_importance_comparison": cross_model_agreement(pd.read_csv(folder / "permutation_importance.csv")),
    }
    for name, frame in recomputed.items():
        saved = pd.read_csv(folder / f"{name}.csv")
        pd.testing.assert_frame_equal(frame.reset_index(drop=True), saved, check_dtype=False, rtol=1e-9, atol=1e-9)
    return checked


def main() -> None:
    checksums = read_json(ROOT / "config" / "checksums.json")
    for path, digest in checksums.items():
        if sha256(ROOT / path) != digest:
            raise ValueError(f"Checksum mismatch: {path}")
    protocol = read_json(ROOT / "config" / "training.json")
    rows = sum(verify_weather(weather, protocol) for weather in WEATHERS)
    print(
        f"Verified {len(checksums)} checksummed files, {len(WEATHERS) * len(ARCHETYPES) * N_CASES:,} cases "
        f"and {rows} recomputed score rows (including baselines)."
    )


if __name__ == "__main__":
    main()
