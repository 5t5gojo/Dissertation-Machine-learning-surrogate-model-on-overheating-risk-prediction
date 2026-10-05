from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from figure_config import (
    ARCHETYPE_LABELS,
    ARCHETYPES,
    FIG_APPENDIX_DIR,
    FIGURES_DIR,
    FIG_IN_TEXT_DIR,
    MODEL_COLORS,
    MODELS_DIR,
    PARAM_COLS,
    SURROGATE_TARGETS,
    TARGET_PLOT_META,
    ensure_dirs,
    performance_csv,
    results_csv,
    rf_importance_csv,
    shap_beeswarm_he_csv,
    shap_importance_csv,
    test_predictions_csv,
)


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


def savefig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_target_distributions(archetype: str) -> None:
    df = pd.read_csv(results_csv(archetype))
    df = df[df["status"] == "ok"].copy()

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()
    for i, target in enumerate(SURROGATE_TARGETS):
        meta = TARGET_PLOT_META[target]
        vals = df[target].dropna()
        ax = axes[i]
        ax.hist(vals, bins=40, color=meta["color"], alpha=0.88, edgecolor="white", lw=0.4)
        ax.axvline(vals.median(), color="0.2", ls="--", lw=1.2)
        stats = [f"Median = {vals.median():.2f}"]
        if meta["threshold"] is not None:
            ax.axvline(meta["threshold"], color="#B22222", ls=":", lw=1.4)
            exceedance_rate = 100 * (vals > meta["threshold"]).mean()
            stats.append(f"Above reference = {exceedance_rate:.2f}%")
        ax.text(
            0.98,
            0.96,
            "\n".join(stats),
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85, edgecolor="0.8"),
        )
        ax.set_title(meta["short"])
        ax.set_xlabel(meta["label"])
        ax.set_ylabel("Count")
        ax.grid(alpha=0.25)
    for ax in axes[len(SURROGATE_TARGETS):]:
        ax.axis("off")

    savefig(fig, FIG_IN_TEXT_DIR / f"{archetype}_target_distributions.png")


def plot_combined_model_comparison() -> None:
    detached = pd.read_csv(performance_csv("detached"))
    semi = pd.read_csv(performance_csv("semi"))
    detached = detached[detached["split"] == "test"].pivot(index="target", columns="model", values="R2")
    semi = semi[semi["split"] == "test"].pivot(index="target", columns="model", values="R2")
    detached = detached.loc[SURROGATE_TARGETS][["RF", "XGBoost", "MLP"]]
    semi = semi.loc[SURROGATE_TARGETS][["RF", "XGBoost", "MLP"]]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), sharey=True)
    for ax, data, title in zip(axes, [detached, semi], ["Detached", "Semi-detached"]):
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
        ax.set_xticklabels([TARGET_PLOT_META[t]["short"] for t in data.index], rotation=20, ha="right")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.3, axis="y")
        ax.legend(loc="lower right", frameon=True)

    savefig(fig, FIG_IN_TEXT_DIR / "combined_model_comparison_r2.png")


def plot_parity(archetype: str) -> None:
    df = pd.read_csv(test_predictions_csv(archetype))
    fig, axes = plt.subplots(2, len(SURROGATE_TARGETS), figsize=(18, 7.5))
    fig.subplots_adjust(hspace=0.45, wspace=0.28)
    for i, target in enumerate(SURROGATE_TARGETS):
        sub_t = df[df["target"] == target]
        for row_idx, model in enumerate(["XGBoost", "MLP"]):
            sub = sub_t[sub_t["model"] == model]
            ax = axes[row_idx, i]
            ax.scatter(sub["y_true"], sub["y_pred"], alpha=0.35, s=8, color=MODEL_COLORS[model])
            lo = min(sub["y_true"].min(), sub["y_pred"].min())
            hi = max(sub["y_true"].max(), sub["y_pred"].max())
            ax.plot([lo, hi], [lo, hi], "k--", lw=1)
            ax.set_title(f"{TARGET_PLOT_META[target]['short']} | {model}")
            if row_idx == 1:
                ax.set_xlabel("EnergyPlus")
            else:
                ax.set_xlabel("")
            if i == 0:
                ax.set_ylabel("Surrogate")
            else:
                ax.set_ylabel("")
            ax.tick_params(labelsize=9)
            ax.grid(alpha=0.25)
    out_dir = FIG_IN_TEXT_DIR if archetype == "detached" else FIG_APPENDIX_DIR
    savefig(fig, out_dir / f"{archetype}_parity_xgb_vs_mlp.png")


def plot_shap_global(archetype: str) -> None:
    df = pd.read_csv(shap_importance_csv(archetype))
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()
    for i, target in enumerate(SURROGATE_TARGETS):
        sub = df[df["target"] == target].sort_values("mean_abs_shap", ascending=False)
        ax = axes[i]
        ax.barh(
            sub["feature"][::-1],
            sub["mean_abs_shap"][::-1],
            color=TARGET_PLOT_META[target]["color"],
            alpha=0.85,
        )
        ax.set_title(TARGET_PLOT_META[target]["short"])
        ax.set_xlabel("Mean |SHAP|")
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(alpha=0.25, axis="x")
    for ax in axes[len(SURROGATE_TARGETS):]:
        ax.axis("off")
    savefig(fig, FIG_IN_TEXT_DIR / f"{archetype}_shap_all_targets.png")


def _beeswarm_output_dir(target: str) -> Path:
    if target in {"T_op_peak", "hours_gt26_night"}:
        return FIG_IN_TEXT_DIR
    return FIG_APPENDIX_DIR


def plot_shap_beeswarms(archetype: str) -> None:
    import shap

    df = pd.read_csv(results_csv(archetype))
    df = df[df["status"] == "ok"].copy().reset_index(drop=True)

    X = df[PARAM_COLS].to_numpy()
    y = df[SURROGATE_TARGETS].to_numpy()

    # Reconstruct the same held-out split used during surrogate training so the
    # beeswarm plots reflect the saved XGBoost test-set explanations.
    X_tv, X_test, y_tv, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    _ = train_test_split(X_tv, y_tv, test_size=0.15 / 0.85, random_state=42)

    model_dir = MODELS_DIR / archetype
    for target in SURROGATE_TARGETS:
        with open(model_dir / f"xgb_{target}.pkl", "rb") as f:
            model = pickle.load(f)

        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_test)

        plt.figure(figsize=(8, 6))
        shap.summary_plot(
            shap_vals,
            X_test,
            feature_names=PARAM_COLS,
            show=False,
            plot_size=None,
            max_display=len(PARAM_COLS),
        )
        plt.tight_layout()
        out_dir = _beeswarm_output_dir(target)
        savefig(plt.gcf(), out_dir / f"{archetype}_shap_{target}.png")


def plot_rf_importance(archetype: str) -> None:
    df = pd.read_csv(rf_importance_csv(archetype))
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()
    for i, target in enumerate(SURROGATE_TARGETS):
        sub = df[df["target"] == target].sort_values("importance", ascending=False)
        ax = axes[i]
        ax.barh(
            sub["feature"][::-1],
            sub["importance"][::-1],
            color=TARGET_PLOT_META[target]["color"],
            alpha=0.85,
        )
        ax.set_title(TARGET_PLOT_META[target]["short"])
        ax.set_xlabel("MDI importance")
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(alpha=0.25, axis="x")
    for ax in axes[len(SURROGATE_TARGETS):]:
        ax.axis("off")
    savefig(fig, FIG_APPENDIX_DIR / f"{archetype}_rf_importance.png")


def write_criterion3_diagnostic() -> None:
    detached = pd.read_csv(results_csv("detached"))
    semi = pd.read_csv(results_csv("semi"))
    d = detached["hours_C3_worst"]
    s = semi["hours_C3_worst"]
    text = (
        "# Criterion 3 Diagnostic\n\n"
        f"Detached: {(d > 0).sum()}/{len(d)} simulations with any exceedance, max = {int(d.max())} hours\n"
        f"Semi-detached: {(s > 0).sum()}/{len(s)} simulations with any exceedance, max = {int(s.max())} hours\n"
        f"Total: {((d > 0).sum() + (s > 0).sum())}/{len(d) + len(s)} simulations with any exceedance\n"
    )
    (FIGURES_DIR / "criterion3_diagnostic.md").write_text(text)


def write_manifest() -> None:
    manifest = """# Figure Manifest

This folder is split into two publication tiers:

- `in_text/`: figures intended for the dissertation main body
- `appendix/`: supporting figures retained as supplementary evidence

`hours_C3_worst` is treated as a diagnostic variable, not a surrogate training
target. It must not appear in model-performance, parity, SHAP, or RF-importance
figures.

## Recommended in-text figures

- `in_text/detached_target_distributions.png`
- `in_text/semi_target_distributions.png`
- `in_text/combined_model_comparison_r2.png`
- `in_text/detached_parity_xgb_vs_mlp.png`
- `in_text/detached_shap_all_targets.png`
- `in_text/semi_shap_all_targets.png`
- `in_text/detached_shap_T_op_peak.png`
- `in_text/semi_shap_T_op_peak.png`
- `in_text/detached_shap_hours_gt26_night.png`
- `in_text/semi_shap_hours_gt26_night.png`

## Recommended appendix figures

- `appendix/semi_parity_xgb_vs_mlp.png`
- `appendix/detached_rf_importance.png`
- `appendix/semi_rf_importance.png`
- `appendix/detached_shap_He_worst.png`
- `appendix/semi_shap_He_worst.png`
- `appendix/detached_shap_We_max_worst.png`
- `appendix/semi_shap_We_max_worst.png`
- `appendix/detached_shap_heat_kWh_m2.png`
- `appendix/semi_shap_heat_kWh_m2.png`
"""
    (FIGURES_DIR / "FIGURE_MANIFEST.md").write_text(manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    for archetype in ARCHETYPES:
        plot_target_distributions(archetype)
        plot_shap_global(archetype)
        plot_rf_importance(archetype)
        plot_parity(archetype)
        plot_shap_beeswarms(archetype)
    plot_combined_model_comparison()
    write_criterion3_diagnostic()
    write_manifest()
    print("Publication figures generated")


if __name__ == "__main__":
    main()
