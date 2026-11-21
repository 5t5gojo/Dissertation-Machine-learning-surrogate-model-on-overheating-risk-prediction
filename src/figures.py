"""Draw the summary figures in figures/ from the published tables in results/.

python src/figures.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from common import ARCHETYPES, ROOT, WEATHERS  # noqa: E402

COLOURS = {"detached": "#0B7A9E", "semi": "#C65F35"}
LABELS = {"detached": "Detached", "semi": "Semi-detached"}
TARGET_LABELS = {
    "He_worst": "Hₑ (frequency)",
    "We_max_worst": "Wₑ (intensity)",
    "T_op_peak": "Peak temperature",
    "hours_gt26_night": "Night hours >26°C",
    "heat_kWh_m2": "Heating demand",
}
INK, MUTED, GRID = "#1f2328", "#5b636b", "#e3e6e8"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    }
)


def results(weather: str, name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / weather / f"{name}.csv")


def performance() -> plt.Figure:
    """XGBoost test R2 by target, archetype and weather file."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True, layout="constrained")
    order = ["T_op_peak", "He_worst", "We_max_worst", "heat_kWh_m2", "hours_gt26_night"]
    for ax, weather in zip(axes, WEATHERS, strict=True):
        summary = results(weather, "performance_summary").query("model == 'XGBoost'")
        for k, archetype in enumerate(ARCHETYPES):
            r2 = summary[summary.archetype == archetype].set_index("target").loc[order, "R2_mean"]
            positions = [i + (k - 0.5) * 0.36 for i in range(len(order))]
            ax.barh(positions, r2, height=0.32, color=COLOURS[archetype], label=LABELS[archetype])
            night = r2["hours_gt26_night"]
            ax.text(night + 0.01, positions[-1], f"{night:.2f}", va="center", fontsize=8.5, color=INK)
        ax.set_yticks(range(len(order)), [TARGET_LABELS[t] for t in order])
        ax.set_xlim(0, 1)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlabel("Test R² (mean of five splits)")
        ax.set_title("London TMYx (typical year)" if weather == "TMYx" else "CIBSE DSY1 2030s (design summer)")
    axes[0].invert_yaxis()  # shared y-axis: invert once
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside upper right", ncols=2)
    fig.suptitle("XGBoost: peak temperature is easy, night-time hours are hard", x=0.01, ha="left", fontsize=12)
    return fig


def night_parity() -> plt.Figure:
    """MLP predicted vs simulated night hours under DSY1, five test splits pooled."""
    predictions = results("DSY1", "predictions").query("model == 'MLP' and target == 'hours_gt26_night'")
    subgroups = results("DSY1", "night_subgroups").query("model == 'MLP' and subgroup == 'above_32h'")
    limit = predictions[["y_true", "y_pred"]].to_numpy().max() * 1.05
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.6), sharey=True, layout="constrained")
    for ax, archetype in zip(axes, ARCHETYPES, strict=True):
        p = predictions[predictions.archetype == archetype]
        tail = subgroups[subgroups.archetype == archetype]
        ax.axvspan(32, limit, color=COLOURS["semi"], alpha=0.07, linewidth=0)
        ax.plot([0, limit], [0, limit], color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.scatter(p.y_true, p.y_pred, s=14, color=COLOURS[archetype], alpha=0.55, edgecolors="white", linewidths=0.5)
        ax.text(34, limit * 0.95, "> 32 h", color=MUTED, fontsize=9, va="top")
        ax.text(
            limit * 0.97,
            limit * 0.06,
            f"Above 32 h (mean of five splits)\nbias {tail.bias.mean():.2f} h, RMSE {tail.RMSE.mean():.2f} h".replace(
                "-", "\u2212"
            ),
            ha="right",
            fontsize=9,
            color=INK,
        )
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_aspect("equal")
        ax.grid(color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlabel("Simulated summer night hours >26°C (h)")
        ax.set_title(LABELS[archetype])
    axes[0].set_ylabel("MLP prediction (h)")
    fig.suptitle(
        "DSY1 night-time exposure: the highest-exposure homes are underpredicted", x=0.01, ha="left", fontsize=12
    )
    return fig


def importance_ratio() -> plt.Figure:
    """Night hours: opening-factor importance divided by g-value importance, by method."""
    rows = []
    for weather in WEATHERS:
        night = "target == 'hours_gt26_night' and feature in ['wof', 'g_value']"
        shap = results(weather, "shap_importance").query(night)
        shap = shap.groupby(["archetype", "feature"]).mean_abs_shap.mean().unstack()
        rows.append({"label": f"SHAP · XGBoost · {weather}", **(shap.wof / shap.g_value).to_dict()})
        permutation = results(weather, "permutation_importance").query(night)
        for model in ["XGBoost", "MLP"]:
            mean = (
                permutation[permutation.model == model]
                .groupby(["archetype", "feature"])
                .normalized_mse_increase.mean()
                .unstack()
            )
            rows.append({"label": f"Permutation · {model} · {weather}", **(mean.wof / mean.g_value).to_dict()})
    table = pd.DataFrame(rows).set_index("label")
    order = [table.index[i] for i in (0, 3, 1, 4, 2, 5)]
    table = table.loc[order]

    fig, ax = plt.subplots(figsize=(8, 4.2), layout="constrained")
    for k, archetype in enumerate(ARCHETYPES):
        positions = [i + (k - 0.5) * 0.36 for i in range(len(table))]
        ax.barh(positions, table[archetype], height=0.32, color=COLOURS[archetype], label=LABELS[archetype])
    ax.axvline(1, color=INK, linewidth=1)
    ax.text(1.01, len(table) - 0.45, "equal importance", fontsize=8.5, color=MUTED, va="center")
    ax.set_yticks(range(len(table)), table.index)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Opening factor ÷ g-value importance  (>1: opening factor ranks first)")
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncols=2)
    fig.suptitle(
        "Night hours: the leading input in semi-detached houses depends on the method", x=0.01, ha="left", fontsize=12
    )
    return fig


def main() -> None:
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    for name, draw in [
        ("performance", performance),
        ("night_parity_DSY1", night_parity),
        ("night_importance_ratio", importance_ratio),
    ]:
        draw().savefig(folder / f"{name}.png")
        plt.close("all")
        print(folder / f"{name}.png")


if __name__ == "__main__":
    main()
