"""Refit and save the published split-seed-42 XGBoost models used by the dashboard.

For each weather file and archetype, the XGBoost configuration selected on validation loss
(results/*/search_trials.csv) is refitted on the seed-42 training partition, one model per
target, and saved to models/xgboost_seed42/{weather}_{archetype}_{target}.ubj.

    python src/export_models.py --output models/xgboost_seed42
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import ARCHETYPES, FEATURES, ROOT, TARGETS, WEATHERS, load_dataset, split_indices
from models import fit_model, predict

SEED = 42


def selected_config(weather: str, archetype: str) -> dict:
    trials = pd.read_csv(ROOT / "results" / weather / "search_trials.csv")
    group = trials[(trials.archetype == archetype) & (trials.seed == SEED) & (trials.family == "XGBoost")]
    return json.loads(group.loc[group.normalized_val_mse.idxmin(), "config"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "xgboost_seed42")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    for weather in WEATHERS:
        published = pd.read_csv(ROOT / "results" / weather / "predictions.csv")
        for archetype in ARCHETYPES:
            data = load_dataset(weather, archetype)
            x, y = data[FEATURES].to_numpy(), data[TARGETS].to_numpy()
            train, val, test = split_indices(len(data), SEED)
            bundle, _ = fit_model(
                "XGBoost", selected_config(weather, archetype), x[train], y[train], x[val], y[val], SEED, 0
            )
            p = predict(bundle, x[test])
            for i, target in enumerate(TARGETS):
                bundle["models"][i].save_model(args.output / f"{weather}_{archetype}_{target}.ubj")
                ref = published[
                    (published.archetype == archetype)
                    & (published.seed == SEED)
                    & (published.model == "XGBoost")
                    & (published.target == target)
                ].set_index("run_id")
                difference = np.abs(p[:, i] - ref.loc[data.run_id.iloc[test], "y_pred"].to_numpy()).max()
                print(f"{weather} {archetype} {target}: max |prediction - published| = {difference:.2g}")


if __name__ == "__main__":
    main()
