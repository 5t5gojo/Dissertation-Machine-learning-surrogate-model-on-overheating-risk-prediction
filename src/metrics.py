"""Screening targets computed from one annual hourly EnergyPlus output.

The overheating indicators follow CIBSE TM52 and TM59 but are screening proxies, not
formal compliance results:

* Adaptive limit (TM52, Category II): T_max = 0.33 T_rm + 21.8, where the running mean
  outdoor temperature is T_rm(d) = 0.2 T_od(d-1) + 0.8 T_rm(d-1).
* dT = operative temperature - T_max, rounded to the nearest kelvin (NumPy ``rint``).
* C1 (He, frequency): % of summer hours with rounded dT >= 1 K; flagged above 3 %.
* C2 (We, intensity): largest daily sum of positive rounded dT, in K h; flagged above 6.
* C3 (upper limit): hours with rounded dT > 4 K; flagged if any.
* Night hours: summer bedroom hours above 26 deg C between 22:00 and 07:00 (after TM59,
  but counted May-September only).

Summer is May-September. Zone 101 is the ground floor and zone 102 the bedroom floor.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

ZONES = ("101", "102")
BEDROOM_ZONE = "102"


def idf_objects(text: str) -> list[list[str]]:
    """Coarse IDF split (fields of each object), sufficient for schedule checks."""
    clean = re.sub(r"!.*", "", text)
    return [[value.strip() for value in block.split(",")] for block in clean.split(";") if block.strip()]


def check_occupancy(text: str) -> float:
    """Prove that both zones are occupied in every hour and timestamps are as assumed.

    The targets count all summer hours as occupied hours; this is only valid if every
    occupancy schedule value is positive. Returns the smallest schedule value.
    """
    by_type: dict[str, list[list[str]]] = {}
    for obj in idf_objects(text):
        by_type.setdefault(obj[0].lower(), []).append(obj)
    people = by_type["people"]
    assert len(people) == 2 and all(float(p[5]) > 0 for p in people)
    schedule_names = {p[3] for p in people}
    years = [o for o in by_type["schedule:year"] if o[1] in schedule_names]
    assert len(years) == len(schedule_names)
    week_names = {y[i] for y in years for i in range(3, len(y), 5)}
    weeks = [o for o in by_type["schedule:week:daily"] if o[1] in week_names]
    assert len(weeks) == len(week_names)
    day_names = {name for o in weeks for name in o[2:]}
    days = [o for o in by_type["schedule:day:interval"] if o[1] in day_names]
    assert len(days) == len(day_names)
    minimum = min(float(o[i]) for o in days for i in range(5, len(o), 2))
    assert minimum > 0, "Zero occupancy would require evaluating the actual hourly schedule."
    timestamp = by_type["outputcontrol:timestamp"][0]
    assert timestamp[1:] == ["Yes", "Yes"], "Expected ISO beginning-of-interval timestamps."
    return minimum


def adaptive_limit(outdoor: np.ndarray) -> np.ndarray:
    """Hourly TM52 Category II upper limit from hourly outdoor dry-bulb temperature."""
    daily = outdoor.reshape(365, 24).mean(axis=1)
    running_mean = np.empty(365)
    running_mean[0] = daily[0]
    for day in range(1, 365):
        running_mean[day] = 0.2 * daily[day - 1] + 0.8 * running_mean[day - 1]
    return np.repeat(0.33 * running_mean + 21.8, 24)


def calculate(raw: pd.DataFrame, width: float, length: float) -> dict:
    """All screening targets and diagnostics for one simulated design."""
    timestamps = pd.DatetimeIndex(pd.to_datetime(raw["Date/Time"].str.strip()))
    expected = pd.date_range("2025-01-01", periods=8760, freq="h")
    assert timestamps.equals(expected), "Missing, duplicate or shifted annual hourly timestamps"

    def column(*parts: str) -> np.ndarray:
        found = [c for c in raw if all(p.lower() in c.lower() for p in parts)]
        assert len(found) == 1, (parts, found)
        values = raw[found[0]].to_numpy(float)
        assert np.isfinite(values).all()
        return values

    t_max = adaptive_limit(column("outdoor", "drybulb"))
    summer = (timestamps.month >= 5) & (timestamps.month <= 9)
    night = (timestamps.hour >= 22) | (timestamps.hour < 7)
    result = {
        "summer_hours": int(summer.sum()),
        "annual_night_hours": int(night.sum()),
        "summer_night_hours": int((summer & night).sum()),
    }

    peaks, joint_flags = [], []
    for zone in ZONES:
        operative = column(zone, "operative temperature")
        delta = (operative - t_max)[summer]
        rounded = np.rint(delta)
        he = 100 * np.mean(rounded >= 1)
        we = float(np.rint(np.maximum(delta, 0)).reshape(-1, 24).sum(axis=1).max())
        c3 = int(np.sum(rounded > 4))
        joint = int(he > 3) + int(we > 6) + int(c3 > 0) >= 2  # TM52: fail two of three
        peaks.append(operative[summer].max())
        joint_flags.append(joint)
        result |= {f"He_{zone}": he, f"We_{zone}": we, f"C3_hours_{zone}": c3, f"two_of_three_proxy_{zone}": joint}
        if zone == BEDROOM_ZONE:
            hot = operative > 26
            result["hours_gt26_night"] = int(np.sum(hot & summer & night))
            result["hours_gt26_night_annual"] = int(np.sum(hot & night))

    heating = sum(column(zone, "ideal loads supply air total heating energy").sum() for zone in ZONES)
    result |= {
        "He_worst": round(max(result["He_101"], result["He_102"]), 4),
        "We_max_worst": max(result["We_101"], result["We_102"]),
        "T_op_peak": round(max(peaks), 3),
        "hours_C3_worst": max(result["C3_hours_101"], result["C3_hours_102"]),
        "two_of_three_proxy_dwelling": any(joint_flags),
        # J -> kWh, per m2 of total occupied floor area (two storeys).
        "heat_kWh_m2": round(heating / 3600000 / (2 * width * length), 4),
    }
    return result
