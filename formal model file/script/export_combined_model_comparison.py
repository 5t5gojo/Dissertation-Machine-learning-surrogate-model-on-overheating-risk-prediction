from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path("/Users/hlbao/Projects/dissertation/formal model file")
OUT_BASE = ROOT / "output"
RESULTS_DIR = OUT_BASE / "results"
FIG_IN_TEXT_DIR = OUT_BASE / "figures" / "in_text"

MODEL_COLORS = {
    "RF": "#4C6A92",
    "XGBoost": "#C76D3A",
    "MLP": "#2F8F6B",
}

TARGET_LABELS = {
    "He_worst": "He_worst",
    "We_max_worst": "We_max_worst",
    "T_op_peak": "T_op_peak",
    "hours_C3_worst": "hours_C3_worst",
    "hours_gt26_night": "hours_gt26_night",
    "heat_kWh_m2": "heat_kWh_m2",
}


def load_r2(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    test = df[df["split"] == "test"]
    pivot = test.pivot(index="target", columns="model", values="R2")
    return pivot[["RF", "XGBoost", "MLP"]]


def main() -> None:
    FIG_IN_TEXT_DIR.mkdir(parents=True, exist_ok=True)

    detached = load_r2(RESULTS_DIR / "model_performance.csv")
    semi = load_r2(RESULTS_DIR / "model_performance_semi.csv")

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 9,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), sharey=True)
    for ax, data, title in zip(
        axes,
        [detached, semi],
        ["Detached", "Semi-detached"],
    ):
        data.plot(
            kind="bar",
            ax=ax,
            width=0.72,
            color=[MODEL_COLORS["RF"], MODEL_COLORS["XGBoost"], MODEL_COLORS["MLP"]],
            alpha=0.9,
            edgecolor="white",
        )
        ax.axhline(0.9, color="black", ls="--", lw=1, alpha=0.5)
        ax.set_title(title)
        ax.set_xlabel("")
        ax.set_ylabel("R² (test set)")
        ax.set_xticklabels([TARGET_LABELS[t] for t in data.index], rotation=20, ha="right")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.3, axis="y")
        ax.legend(loc="lower right", frameon=True)

    out = FIG_IN_TEXT_DIR / "combined_model_comparison_r2.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
