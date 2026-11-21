"""Shared data loading, labels and styling for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import xgboost

ROOT = Path(__file__).resolve().parents[1]

WEATHERS = {"TMYx": "London TMYx (typical year)", "DSY1": "CIBSE DSY1 2030s (design summer year)"}
ARCHETYPES = {"detached": "Detached", "semi": "Semi-detached"}
MODELS = ["RF", "XGBoost", "MLP"]
BASELINES = ["AlwaysZero", "TrainingMean"]

TARGETS = {
    "He_worst": ("Hₑ: exceedance frequency", "% of hours"),
    "We_max_worst": ("Wₑ: worst daily weighted exceedance", "K h"),
    "T_op_peak": ("Peak operative temperature", "°C"),
    "hours_gt26_night": ("Bedroom night hours above 26 °C", "h"),
    "heat_kWh_m2": ("Annual ideal heating demand", "kWh/m²"),
}
FEATURES = {
    "width": ("Width", "m"),
    "length": ("Length", "m"),
    "height": ("Storey height", "m"),
    "orientation": ("Orientation", "°"),
    "wwr": ("Window-to-wall ratio", ""),
    "wallInsulationThickness": ("Wall insulation", "m"),
    "roofInsulationThickness": ("Loft insulation", "m"),
    "slabInsulationThickness": ("Slab insulation", "m"),
    "u_windows": ("Window U-value", "W/m²K"),
    "g_value": ("Glazing g-value", ""),
    "roofAbsorptance": ("Roof absorptance", ""),
    "flowCoefficient": ("Infiltration coefficient", "m³/(s·Paⁿ)"),
    "wof": ("Window opening factor", ""),
    "fixedShadingDepth": ("Overhang depth", "m"),
}

WEATHER_COLOURS = {"TMYx": "#5B7F9E", "DSY1": "#D1495B"}
ARCHETYPE_COLOURS = {"detached": "#0B7A9E", "semi": "#C65F35"}
MODEL_COLOURS = {"RF": "#8C6BB1", "XGBoost": "#0B7A9E", "MLP": "#E0A030"}

DISCLAIMER = (
    "All values are EnergyPlus simulation results or surrogate predictions of them, not measurements in real homes. "
    "The overheating indicators are screening proxies derived from CIBSE TM52 and TM59 on simplified schedules, "
    "not formal compliance results."
)


def label(column: str) -> str:
    """Readable label with unit for a target or design input."""
    name, unit = {**TARGETS, **FEATURES}.get(column, (column, ""))
    return f"{name} ({unit})" if unit else name


@st.cache_data
def dataset(weather: str, archetype: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / weather / f"{archetype}.csv")


@st.cache_data
def paired(archetype: str) -> pd.DataFrame:
    """The same designs under both weather files, one row per design."""
    tmyx = dataset("TMYx", archetype).set_index("run_id")
    dsy1 = dataset("DSY1", archetype).set_index("run_id")
    return tmyx.join(dsy1[list(TARGETS) + ["hours_C3_worst", "two_of_three_proxy_dwelling"]], rsuffix="_DSY1")


@st.cache_data
def result(weather: str, name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / weather / f"{name}.csv")


@st.cache_data
def parameter_bounds() -> dict[str, tuple[float, float]]:
    spec = json.loads((ROOT / "config" / "parameters.json").read_text())["sampled_parameters"]
    return {p["name"]: (p["min"], p["max"]) for p in spec}


@st.cache_resource
def surrogate(weather: str, archetype: str, target: str) -> xgboost.Booster:
    """Published seed-42 XGBoost model for one weather file, archetype and target."""
    return xgboost.Booster(model_file=str(ROOT / "models" / "xgboost_seed42" / f"{weather}_{archetype}_{target}.ubj"))


def page_header(title: str, caption: str) -> None:
    st.title(title)
    st.caption(caption)


def controls(*names: str, key: str) -> dict[str, str]:
    """A row of selectors shared by the analysis pages."""
    options = {
        "weather": ("Weather file", WEATHERS),
        "archetype": ("Archetype", ARCHETYPES),
        "target": ("Target", {t: TARGETS[t][0] for t in TARGETS}),
    }
    columns = st.columns(len(names))
    chosen = {}
    for column, name in zip(columns, names, strict=True):
        title, choices = options[name]
        chosen[name] = column.selectbox(title, list(choices), format_func=choices.get, key=f"{key}_{name}")
    return chosen
