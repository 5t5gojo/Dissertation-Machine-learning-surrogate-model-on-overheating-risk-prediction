"""Shared constants, paths and small file utilities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]

WEATHERS = ("TMYx", "DSY1")
ARCHETYPES = ("detached", "semi")
N_CASES = 2000

# The 14 sampled design inputs, in model-input order (bounds: config/parameters.json).
FEATURES = [
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

# The five continuous responses predicted jointly by every surrogate.
TARGETS = ["He_worst", "We_max_worst", "T_op_peak", "hours_gt26_night", "heat_kWh_m2"]
NIGHT = TARGETS.index("hours_gt26_night")


def sha256(path: Path) -> str:
    """Hex SHA-256 digest of a file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    """Write indented JSON, creating parent folders as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n")


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def dataset_path(weather: str, archetype: str) -> Path:
    return ROOT / "data" / weather / f"{archetype}.csv"


def load_dataset(weather: str, archetype: str) -> pd.DataFrame:
    """Final 2,000-case dataset for one weather file and archetype, ordered by run_id.

    pandas' default float parser is used on purpose: the published models were
    fitted on exactly these parsed values.
    """
    frame = pd.read_csv(dataset_path(weather, archetype))
    frame = frame.sort_values("run_id").reset_index(drop=True)
    values = frame[FEATURES + TARGETS].to_numpy()
    if len(frame) != N_CASES or not frame.run_id.is_unique or not np.isfinite(values).all():
        raise ValueError(f"Invalid dataset: {weather}/{archetype}")
    return frame


def load_samples(archetype: str) -> pd.DataFrame:
    """Latin hypercube samples used to build the simulation inputs.

    ``round_trip`` parsing reproduces every float exactly, so the generated IDFs are
    byte-identical to those that were simulated.
    """
    return pd.read_csv(ROOT / "data" / "samples" / f"{archetype}.csv", float_precision="round_trip")


def split_indices(n: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Row indices of the 70/15/15 train/validation/test partition for one seed."""
    train_validation, test = train_test_split(np.arange(n), test_size=0.15, random_state=seed)
    train, validation = train_test_split(train_validation, test_size=0.15 / 0.85, random_state=seed)
    return train, validation, test


def check_saved_split(frame: pd.DataFrame, archetype: str, seed: int) -> None:
    """Fail unless the recomputed partition matches data/splits/{archetype}_{seed}.csv."""
    saved = pd.read_csv(ROOT / "data" / "splits" / f"{archetype}_{seed}.csv").set_index("run_id")
    for label, indices in zip(("train", "validation", "test"), split_indices(len(frame), seed), strict=True):
        if not saved.loc[frame.run_id.iloc[indices], "split"].eq(label).all():
            raise ValueError(f"Partition differs from the published experiment: {archetype} seed {seed}")
