from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_BASE = ROOT / "output"

RESULTS_DIR = OUT_BASE / "results"
FIGURES_DIR = OUT_BASE / "figures"
FIG_IN_TEXT_DIR = FIGURES_DIR / "in_text"
FIG_APPENDIX_DIR = FIGURES_DIR / "appendix"
MODELS_DIR = OUT_BASE / "models"

SURROGATE_TARGETS = [
    "He_worst",
    "We_max_worst",
    "T_op_peak",
    "hours_gt26_night",
    "heat_kWh_m2",
]

DIAGNOSTIC_TARGETS = [
    "hours_C3_worst",
]

assert "hours_C3_worst" not in SURROGATE_TARGETS
assert len(SURROGATE_TARGETS) == 5

ARCHETYPES = ["detached", "semi"]

PARAM_COLS = [
    "width",
    "length",
    "height",
    "orientation",
    "wwr",
    "wallInsulationThickness",
    "roofInsulationThickness",
    "slabInsulationThickness",
    "u_windows",
    "g_value",
    "roofAbsorptance",
    "flowCoefficient",
    "wof",
    "fixedShadingDepth",
]

MODEL_COLORS = {
    "RF": "#4C6A92",
    "XGBoost": "#C76D3A",
    "MLP": "#2F8F6B",
}

TARGET_PLOT_META = {
    "He_worst": {
        "short": "He_worst",
        "label": "He proxy (% summer hours)",
        "color": "#D95F02",
        "threshold": 3.0,
        "threshold_label": "C1 proxy reference: 3%",
    },
    "We_max_worst": {
        "short": "We_max_worst",
        "label": "Stepped daily exceedance proxy",
        "color": "#E6AB02",
        "threshold": 6.0,
        "threshold_label": "C2 proxy reference: 6",
    },
    "T_op_peak": {
        "short": "T_op_peak",
        "label": "Peak operative temperature (°C)",
        "color": "#7570B3",
        "threshold": None,
        "threshold_label": None,
    },
    "hours_gt26_night": {
        "short": "hours_gt26_night",
        "label": "Summer bedroom night hours > 26°C",
        "color": "#1F78B4",
        "threshold": 32.0,
        "threshold_label": "32 h reference (annual TM59:2017 basis)",
    },
    "heat_kWh_m2": {
        "short": "heat_kWh_m2",
        "label": "Ideal heating demand (kWh/m²·yr)",
        "color": "#1B9E77",
        "threshold": None,
        "threshold_label": None,
    },
}

ARCHETYPE_LABELS = {
    "detached": "Detached",
    "semi": "Semi-detached",
}


def results_csv(archetype: str) -> Path:
    return RESULTS_DIR / ("results_v7_semi.csv" if archetype == "semi" else "results_v7.csv")


def performance_csv(archetype: str) -> Path:
    return RESULTS_DIR / (
        "model_performance_semi.csv" if archetype == "semi" else "model_performance.csv"
    )


def test_predictions_csv(archetype: str) -> Path:
    return RESULTS_DIR / f"test_predictions_{archetype}.csv"


def shap_importance_csv(archetype: str) -> Path:
    return RESULTS_DIR / f"shap_importance_{archetype}.csv"


def shap_beeswarm_he_csv(archetype: str) -> Path:
    return RESULTS_DIR / f"shap_beeswarm_he_{archetype}.csv"


def rf_importance_csv(archetype: str) -> Path:
    return RESULTS_DIR / f"rf_importance_{archetype}.csv"


def ensure_dirs() -> None:
    for p in [FIG_IN_TEXT_DIR, FIG_APPENDIX_DIR]:
        p.mkdir(parents=True, exist_ok=True)
