"""Summary tables derived from the per-split results.

python src/report.py results/TMYx --check    # recompute and compare with saved tables
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr


def performance_summary(performance: pd.DataFrame) -> pd.DataFrame:
    """Mean and sample SD of R2, MAE and RMSE across the five splits."""
    summary = performance.groupby(["archetype", "model", "target"])[["R2", "MAE", "RMSE"]].agg(["mean", "std"])
    summary.columns = ["_".join(column) for column in summary.columns]
    return summary


def shap_ranks(shap: pd.DataFrame) -> pd.DataFrame:
    """Mean |SHAP| per archetype, target and feature, with rank stability across splits."""
    shap = shap.copy()
    shap["rank"] = shap.groupby(["archetype", "seed", "target"]).mean_abs_shap.rank(ascending=False, method="min")
    summary = (
        shap.groupby(["archetype", "target", "feature"])
        .agg(
            mean_abs_shap=("mean_abs_shap", "mean"),
            sd_abs_shap=("mean_abs_shap", "std"),
            min_rank=("rank", "min"),
            max_rank=("rank", "max"),
            first_rank_splits=("rank", lambda ranks: int(ranks.eq(1).sum())),
        )
        .reset_index()
    )
    summary["rank_of_mean"] = summary.groupby(["archetype", "target"]).mean_abs_shap.rank(ascending=False, method="min")
    return summary


def cross_model_agreement(permutation: pd.DataFrame) -> pd.DataFrame:
    """Spearman agreement between XGBoost and MLP permutation importances, and each top feature."""
    by_split = (
        permutation.groupby(["archetype", "seed", "model", "target", "feature"])
        .normalized_mse_increase.mean()
        .reset_index()
    )
    rows = []
    for (archetype, target), group in by_split.groupby(["archetype", "target"]):
        wide = group.groupby(["feature", "model"]).normalized_mse_increase.mean().unstack()
        rows.append(
            {
                "archetype": archetype,
                "target": target,
                "rank_spearman": spearmanr(wide.XGBoost, wide.MLP).statistic,
                "xgb_top_feature": wide.XGBoost.idxmax(),
                "mlp_top_feature": wide.MLP.idxmax(),
            }
        )
    return pd.DataFrame(rows)


def summarise_performance(folder: Path) -> None:
    performance_summary(pd.read_csv(folder / "performance.csv")).to_csv(folder / "performance_summary.csv")


def summarise_attributions(folder: Path) -> None:
    shap_ranks(pd.read_csv(folder / "shap_importance.csv")).to_csv(
        folder / "shap_mean_values_and_ranks.csv", index=False
    )
    cross_model_agreement(pd.read_csv(folder / "permutation_importance.csv")).to_csv(
        folder / "cross_model_importance_comparison.csv", index=False
    )


def check(folder: Path) -> None:
    """Recompute the three summary tables in memory and compare with the saved files."""
    recomputed = {
        "performance_summary": performance_summary(pd.read_csv(folder / "performance.csv")).reset_index(),
        "shap_mean_values_and_ranks": shap_ranks(pd.read_csv(folder / "shap_importance.csv")),
        "cross_model_importance_comparison": cross_model_agreement(pd.read_csv(folder / "permutation_importance.csv")),
    }
    for name, frame in recomputed.items():
        saved = pd.read_csv(folder / f"{name}.csv")
        pd.testing.assert_frame_equal(frame.reset_index(drop=True), saved, check_dtype=False, rtol=1e-12, atol=1e-12)
        print(f"{name}: matches")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--check", action="store_true", help="compare instead of writing")
    args = parser.parse_args()
    if args.check:
        check(args.folder)
    else:
        summarise_performance(args.folder)
        summarise_attributions(args.folder)
