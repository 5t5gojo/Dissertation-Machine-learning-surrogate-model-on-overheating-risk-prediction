#!/usr/bin/env python3
"""
batch_runner_v7.py
──────────────────
LHS sampling + parallel EnergyPlus batch runner for UK residential
overheating surrogate models.

Usage
-----
    python batch_runner_v7.py                  # detached, 8 workers, 2000 samples
    python batch_runner_v7.py --workers 4      # use 4 parallel workers
    python batch_runner_v7.py --resume         # skip already-completed runs
    python batch_runner_v7.py --samples 100    # quick test run
    python batch_runner_v7.py --type semi      # semi-detached workflow

Output
------
    output/lhs_samples_<type>.csv  2000×14 LHS parameter matrix
    output/results_<type>.csv      2000×19 (14 inputs + 5 targets + metadata)
    output/runs_<type>/            per-run EP output (deleted after parsing)
"""

import argparse, subprocess, re, math, json, time, warnings, traceback, os, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# PATHS  (derived from the script location)
# ══════════════════════════════════════════════════════════════════════════════
_root        = Path(__file__).resolve().parents[2]
_ep          = Path("/Applications/EnergyPlus-25-1-0")
_fm          = _root / "formal model file"
_weather_dir = _fm / "weather file"

WEATHER_FILE = _weather_dir / "GBR_ENG_London.Wea.Ctr-St.James.Park.037700_TMYx.2009-2023.epw"
CONFIG_FILE  = _fm / "parameter_config_v7.json"
EP_EXE       = _ep   / "energyplus"

OUT_BASE     = _root / "formal model file" / "output"
LHS_DIR      = OUT_BASE / "lhs"
RESULTS_DIR  = OUT_BASE / "results"
RUNS_BASE    = OUT_BASE / "runs"
LHS_CSV      = LHS_DIR / "lhs_samples_v7.csv"
HOUSE_TYPE   = "detached"
LHS_META_JSON = LHS_DIR / "lhs_samples_v7.meta.json"
SCRIPT_HASH  = ""
TEMPLATE_HASH = ""

# CONFIG_FILE, WEATHER_FILE, LHS_CSV, IDF_TEMPLATE, RESULTS_CSV, RUNS_DIR are set in main()

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
DOOR_START_X = 4.475   # hardcoded door on ground-floor south wall
DOOR_END_X   = 5.475
MARGIN       = 0.5
GAP          = 0.3

HEATING_SP   = 21.0
COOLING_SP   = 100.0
VENT_RATE    = 0.0
INT_MASS     = 20.0
FIXED_PARAMS = {}
DIAG_COLS = [
    "wwr_realized_north",
    "wwr_realized_south_ground",
    "wwr_realized_south_upper",
    "wwr_realized_east",
    "wwr_realized_west",
    "clip_flag_north",
    "clip_flag_south_ground",
    "clip_flag_south_upper",
    "clip_flag_east",
    "clip_flag_west",
    "south_g_left_window_width",
    "south_g_right_window_width",
    "tiny_window_flag_south_ground",
]


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_metadata(cfg: dict) -> dict:
    return cfg.get("_metadata") or cfg.get("metadata") or {}


def apply_fixed_parameters(cfg: dict) -> None:
    global HEATING_SP, COOLING_SP, VENT_RATE, INT_MASS, FIXED_PARAMS

    fixed = cfg.get("fixed_parameters", {})
    FIXED_PARAMS = fixed
    HEATING_SP = float(fixed.get("heatingSetpoint", {}).get("value", 21.0))
    COOLING_SP = float(fixed.get("coolingSetpoint", {}).get("value", 100.0))
    VENT_RATE = float(fixed.get("ventilationRate", {}).get("value", 0.0))
    INT_MASS = float(fixed.get("internalMass", {}).get("value", 20.0))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Latin Hypercube Sampling
# ══════════════════════════════════════════════════════════════════════════════
def load_param_bounds() -> list[tuple[str, float, float]]:
    cfg = load_config()
    return [(p["name"], p["min"], p["max"]) for p in cfg["sampled_parameters"]]
    # Order: width, length, height, orientation, wwr,
    #        wallInsulationThickness, roofInsulationThickness, slabInsulationThickness,
    #        u_windows, g_value, roofAbsorptance, flowCoefficient, wof, fixedShadingDepth


def generate_lhs(n_samples: int, seed: int = 42) -> pd.DataFrame:
    """Generate n_samples × 14 LHS matrix scaled to [min, max] per parameter."""
    params = load_param_bounds()
    n_params = len(params)

    try:
        from scipy.stats.qmc import LatinHypercube
        sampler = LatinHypercube(d=n_params, seed=seed)
        unit = sampler.random(n=n_samples)
    except ImportError:
        try:
            import pyDOE2
            unit = pyDOE2.lhs(n_params, samples=n_samples, criterion="maximin", random_state=seed)
        except ImportError:
            raise ImportError("Install scipy>=1.7 or pyDOE2:  pip install scipy")

    data = {}
    for i, (name, lo, hi) in enumerate(params):
        data[name] = lo + (hi - lo) * unit[:, i]

    df = pd.DataFrame(data)
    df.insert(0, "run_id", [f"run_{i:04d}" for i in range(n_samples)])
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Derive IDF placeholder values from sampled parameters
# ══════════════════════════════════════════════════════════════════════════════
def derive_substitutions(row: dict) -> dict:
    """
    Given a dict of 14 sampled parameter values, return a full
    {placeholder: value_string} dict for IDF substitution.
    """
    W   = row["width"]
    L   = row["length"]
    H   = row["height"]
    WWR = row["wwr"]
    WOF = row["wof"]

    # Window z-coordinates
    z1            = 0.8
    z2            = min(2.2, H - 0.3)
    window_height = z2 - z1

    def build_three_window_band(facade_width: float, target_wwr: float) -> tuple[tuple[float, float, float, float, float, float], float]:
        target_total_w = target_wwr * facade_width * H / window_height
        max_total_w = max(0.0, facade_width - 2 * MARGIN - 2 * GAP)
        total_w = min(target_total_w, max_total_w)
        single_w = total_w / 3.0
        x1 = MARGIN
        x2 = x1 + single_w
        x3 = x2 + GAP
        x4 = x3 + single_w
        x5 = x4 + GAP
        x6 = x5 + single_w
        return (x1, x2, x3, x4, x5, x6), total_w * window_height

    def build_two_window_band_with_door(facade_width: float, target_wwr: float) -> tuple[tuple[float, float, float, float, float, float], float]:
        target_total_w = target_wwr * facade_width * H / window_height
        left_avail = max(0.0, DOOR_START_X - MARGIN)
        right_avail = max(0.0, facade_width - MARGIN - DOOR_END_X)
        max_total_w = left_avail + right_avail
        total_w = min(target_total_w, max_total_w)

        if max_total_w > 0:
            left_w = total_w * left_avail / max_total_w
            right_w = total_w * right_avail / max_total_w
        else:
            left_w = right_w = 0.0

        x1 = MARGIN
        x2 = x1 + left_w
        x3 = DOOR_START_X
        x4 = DOOR_START_X
        x5 = max(DOOR_END_X, facade_width - MARGIN - right_w)
        x6 = facade_width - MARGIN
        return (x1, x2, x3, x4, x5, x6), (left_w + right_w) * window_height

    north_band, actual_N = build_three_window_band(W, WWR)
    south_upper_band, actual_S_102 = build_three_window_band(W, WWR)
    south_ground_band, actual_S_101 = build_two_window_band_with_door(W, WWR)

    # E/W windows — 1 per face, centred, based on target facade WWR.
    target_ew_w = WWR * L * H / window_height
    max_ew_w = max(0.0, L - 1.0)
    ew_w  = min(target_ew_w, max_ew_w)
    y_ctr = L / 2.0
    ew_y1 = max(0.5, y_ctr - ew_w / 2.0)
    ew_y2 = min(L - 0.5, y_ctr + ew_w / 2.0)

    actual_EW = max(0.0, ew_y2 - ew_y1) * window_height
    open_S_101 = WOF * actual_S_101
    open_S_102 = WOF * actual_S_102
    open_N = WOF * actual_N
    open_E = WOF * actual_EW
    open_W = WOF * actual_EW
    south_g_left_window_width = max(0.0, south_ground_band[1] - south_ground_band[0])
    south_g_right_window_width = max(0.0, south_ground_band[5] - south_ground_band[4])
    tiny_window_flag_south_ground = int(
        south_g_left_window_width < 0.1 or south_g_right_window_width < 0.1
    )

    # SAP 2012 occupancy for the whole dwelling. The model has two equal-area
    # habitable zones, so split the household size evenly between them.
    TFA = 2 * W * L
    N   = 1 + 1.76 * (1 - math.exp(-0.000349 * (TFA - 13.9) ** 2)) + 0.0013 * (TFA - 13.9)
    num_people_per_zone = N / 2.0

    # Treat the sampled leakage coefficient as a whole-dwelling input and
    # split it evenly across the two equal-area occupied zones.
    flow_coeff_per_zone = row["flowCoefficient"] / 2.0

    facade_area_ns = W * H
    facade_area_ew = L * H
    wwr_realized_north = actual_N / facade_area_ns if facade_area_ns > 0 else np.nan
    wwr_realized_south_ground = actual_S_101 / facade_area_ns if facade_area_ns > 0 else np.nan
    wwr_realized_south_upper = actual_S_102 / facade_area_ns if facade_area_ns > 0 else np.nan
    wwr_realized_east = actual_EW / facade_area_ew if facade_area_ew > 0 else np.nan
    wwr_realized_west = actual_EW / facade_area_ew if facade_area_ew > 0 else np.nan

    target_area_ns = WWR * facade_area_ns
    target_area_ew = WWR * facade_area_ew
    clip_flag_north = int(actual_N + 1e-9 < target_area_ns)
    clip_flag_south_ground = int(actual_S_101 + 1e-9 < target_area_ns)
    clip_flag_south_upper = int(actual_S_102 + 1e-9 < target_area_ns)
    clip_flag_east = int(actual_EW + 1e-9 < target_area_ew)
    clip_flag_west = int(actual_EW + 1e-9 < target_area_ew)

    diagnostics = {
        "wwr_realized_north": round(float(wwr_realized_north), 6),
        "wwr_realized_south_ground": round(float(wwr_realized_south_ground), 6),
        "wwr_realized_south_upper": round(float(wwr_realized_south_upper), 6),
        "wwr_realized_east": round(float(wwr_realized_east), 6),
        "wwr_realized_west": round(float(wwr_realized_west), 6),
        "clip_flag_north": clip_flag_north,
        "clip_flag_south_ground": clip_flag_south_ground,
        "clip_flag_south_upper": clip_flag_south_upper,
        "clip_flag_east": clip_flag_east,
        "clip_flag_west": clip_flag_west,
        "south_g_left_window_width": round(float(south_g_left_window_width), 6),
        "south_g_right_window_width": round(float(south_g_right_window_width), 6),
        "tiny_window_flag_south_ground": tiny_window_flag_south_ground,
    }

    substitutions = {
        "@width@"                    : f"{W}",
        "@length@"                   : f"{L}",
        "@height@"                   : f"{H}",
        "@orientation@"              : f"{row['orientation']}",
        "@wallInsulationThickness@"  : f"{row['wallInsulationThickness']}",
        "@roofInsulationThickness@"  : f"{row['roofInsulationThickness']}",
        "@slabInsulationThickness@"  : f"{row['slabInsulationThickness']}",
        "@u_windows@"                : f"{row['u_windows']}",
        "@g_value@"                  : f"{row['g_value']}",
        "@roofAbsorptance@"          : f"{row['roofAbsorptance']}",
        "@flowCoefficient_101@"      : f"{flow_coeff_per_zone:.8f}",
        "@flowCoefficient_102@"      : f"{flow_coeff_per_zone:.8f}",
        "@fixedShadingDepth@"        : f"{row['fixedShadingDepth']}",
        "@heatingSetpoint@"          : f"{HEATING_SP}",
        "@coolingSetpoint@"          : f"{COOLING_SP}",
        "@ventilationRate@"          : f"{VENT_RATE}",
        "@internalMass@"             : f"{INT_MASS}",
        "@numPeople_101@"            : f"{num_people_per_zone:.6f}",
        "@numPeople_102@"            : f"{num_people_per_zone:.6f}",
        "@2height@"                  : f"{2 * H}",
        "@length/2@"                 : f"{L / 2}",
        "@windownorth_x1@"           : f"{north_band[0]:.6f}",
        "@windownorth_x2@"           : f"{north_band[1]:.6f}",
        "@windownorth_x3@"           : f"{north_band[2]:.6f}",
        "@windownorth_x4@"           : f"{north_band[3]:.6f}",
        "@windownorth_x5@"           : f"{north_band[4]:.6f}",
        "@windownorth_x6@"           : f"{north_band[5]:.6f}",
        "@windowsouth_u_x1@"         : f"{south_upper_band[0]:.6f}",
        "@windowsouth_u_x2@"         : f"{south_upper_band[1]:.6f}",
        "@windowsouth_u_x3@"         : f"{south_upper_band[2]:.6f}",
        "@windowsouth_u_x4@"         : f"{south_upper_band[3]:.6f}",
        "@windowsouth_u_x5@"         : f"{south_upper_band[4]:.6f}",
        "@windowsouth_u_x6@"         : f"{south_upper_band[5]:.6f}",
        "@windowsouth_g_x1@"         : f"{south_ground_band[0]:.6f}",
        "@windowsouth_g_x2@"         : f"{south_ground_band[1]:.6f}",
        "@windowsouth_g_x3@"         : f"{south_ground_band[2]:.6f}",
        "@windowsouth_g_x4@"         : f"{south_ground_band[3]:.6f}",
        "@windowsouth_g_x5@"         : f"{south_ground_band[4]:.6f}",
        "@windowsouth_g_x6@"         : f"{south_ground_band[5]:.6f}",
        "@windowEast_y1@"            : f"{ew_y1:.6f}",
        "@windowEast_y2@"            : f"{ew_y2:.6f}",
        "@window_z1@"                : f"{z1:.6f}",
        "@window_z2@"                : f"{z2:.6f}",
        "@windowOpeningArea_S_101@"  : f"{open_S_101:.8f}",
        "@windowOpeningArea_S_102@"  : f"{open_S_102:.8f}",
        "@windowOpeningArea_N@"      : f"{open_N:.8f}",
        "@windowOpeningArea_E@"      : f"{open_E:.8f}",
        "@windowOpeningArea_W@"      : f"{open_W:.8f}",
        "@daylightReference_x@"      : f"{W / 2}",
        "@daylightReference_y@"      : f"{L / 2}",
    }
    substitutions["__diagnostics__"] = diagnostics
    return substitutions


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Parse EnergyPlus CSV and compute TM52/TM59 targets
# ══════════════════════════════════════════════════════════════════════════════
def _find_col(df: pd.DataFrame, *keywords: str) -> str | None:
    kws = [k.lower() for k in keywords]
    for col in df.columns:
        if all(k in col.lower() for k in kws):
            return col
    return None


def compute_targets(run_dir: Path, W: float, L: float) -> dict:
    """
    Parse eplusout.csv from run_dir and return the 5 surrogate target variables.
    Returns a dict with NaN values if parsing fails.
    """
    nan_targets = dict(
        He_worst=np.nan, We_max_worst=np.nan,
        T_op_peak=np.nan, hours_C3_worst=np.nan,
        hours_gt26_night=np.nan, heat_kWh_m2=np.nan,
    )

    csv_path = run_dir / "eplusout.csv"
    if not csv_path.exists():
        return nan_targets

    try:
        df_raw = pd.read_csv(csv_path)
    except Exception:
        return nan_targets

    # Column identification
    col_oat    = _find_col(df_raw, "outdoor", "drybulb")
    col_op101  = _find_col(df_raw, "101", "operative") or _find_col(df_raw, "101", "air temperature")
    col_op102  = _find_col(df_raw, "102", "operative") or _find_col(df_raw, "102", "air temperature")
    col_h101   = _find_col(df_raw, "101", "heating energy")
    col_h102   = _find_col(df_raw, "102", "heating energy")

    if col_oat is None or col_op101 is None or col_op102 is None:
        return nan_targets

    n = len(df_raw)
    T_out  = df_raw[col_oat].values
    T_101  = df_raw[col_op101].values
    T_102  = df_raw[col_op102].values

    # Month array (row i = hour i of the year, 0-indexed)
    months = np.zeros(n, dtype=int)
    day_bounds = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]
    for m in range(12):
        s = day_bounds[m] * 24
        e = day_bounds[m + 1] * 24
        months[s:e] = m + 1

    # Hour-of-day (0–23)
    hours_of_day = np.tile(np.arange(24), n // 24 + 1)[:n]

    # ── Running mean Trm ─────────────────────────────────────────────────────
    n_days = n // 24
    daily_T = np.array([T_out[d * 24:(d + 1) * 24].mean() for d in range(n_days)])
    alpha   = 0.8
    Trm_d   = np.zeros(n_days)
    Trm_d[0] = daily_T[0]
    for d in range(1, n_days):
        Trm_d[d] = (1 - alpha) * daily_T[d - 1] + alpha * Trm_d[d - 1]
    Trm_h = np.repeat(Trm_d, 24)[:n]
    Tmax_h = 0.33 * Trm_h + 21.8
    Tupp_h = Tmax_h + 4.0

    # Summer mask (May–Sep = months 5–9). With the current residential
    # occupancy schedules, people are present throughout the day, so occupied
    # summer hours are equivalent to all summer hours unless a more explicit
    # occupancy mask is introduced.
    summer = (months >= 5) & (months <= 9)
    occupied_summer = summer
    n_occ  = occupied_summer.sum()

    def zone_tm52(T_op):
        dT    = T_op[occupied_summer] - Tmax_h[occupied_summer]
        doy_s = np.repeat(np.arange(n_days), 24)[:n][occupied_summer]
        # Criterion 1
        He = 100.0 * (dT >= 1.0).sum() / n_occ
        # Criterion 2 — TM52 weighted exceedance using rounded positive ΔT
        dT_pos = np.maximum(dT, 0.0)
        W_i = np.rint(dT_pos).astype(int)
        We_daily = pd.Series(W_i, index=doy_s).groupby(level=0).sum()
        We_max = We_daily.max()
        return He, We_max

    He_101, We_101 = zone_tm52(T_101)
    He_102, We_102 = zone_tm52(T_102)

    He_worst     = max(He_101, He_102)
    We_max_worst = max(We_101, We_102)
    T_op_peak    = max(T_101[summer].max(), T_102[summer].max())
    hours_C3_101 = int((T_101[summer] > Tupp_h[summer]).sum())
    hours_C3_102 = int((T_102[summer] > Tupp_h[summer]).sum())
    hours_C3_worst = max(hours_C3_101, hours_C3_102)

    # TM59 Criterion B: nighttime hours >26°C in the first-floor bedroom
    # (Space 102) only. Ground-floor living is excluded as TM59 specifies
    # bedrooms as the zones subject to the nighttime criterion.
    night_summer = summer & ((hours_of_day >= 22) | (hours_of_day <= 6))
    hours_gt26_night = int((T_102[night_summer] > 26).sum())

    # Annual heating energy → kWh/m²
    J2kWh = 1.0 / 3_600_000.0
    heat_J = 0.0
    if col_h101:
        heat_J += df_raw[col_h101].sum()
    if col_h102:
        heat_J += df_raw[col_h102].sum()
    floor_area  = 2 * W * L
    heat_kWh_m2 = heat_J * J2kWh / floor_area

    return dict(
        He_worst=round(He_worst, 4),
        We_max_worst=round(float(We_max_worst), 2),
        T_op_peak=round(float(T_op_peak), 3),
        hours_C3_worst=hours_C3_worst,
        hours_gt26_night=hours_gt26_night,
        heat_kWh_m2=round(heat_kWh_m2, 4),
    )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Single-run worker  (must be top-level for multiprocessing)
# ══════════════════════════════════════════════════════════════════════════════
def run_single(args: tuple) -> dict:
    """
    Worker function.  args = (run_id_str, param_dict, template_text, cleanup)
    Returns a result dict (inputs + targets + metadata).
    """
    run_id, params, template_text, cleanup = args

    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    result = {k: v for k, v in params.items() if k != "run_id"}
    result["run_id"]  = run_id
    result["status"]  = "failed"
    result["sim_sec"] = np.nan
    result["script_hash"] = SCRIPT_HASH
    result["template_hash"] = TEMPLATE_HASH

    try:
        t0 = time.perf_counter()

        # Substitute placeholders
        subs     = derive_substitutions(params)
        diagnostics = subs.pop("__diagnostics__", {})
        result.update(diagnostics)
        idf_text = template_text
        for k, v in subs.items():
            idf_text = idf_text.replace(k, v)

        # Check for unreplaced placeholders
        remaining = re.findall(r"@[\w/]+@", idf_text)
        if remaining:
            result["status"] = f"placeholder_error: {set(remaining)}"
            return result

        idf_path = run_dir / "sim.idf"
        idf_path.write_text(idf_text)

        # Run EnergyPlus
        ep_proc = subprocess.run(
            [str(EP_EXE), "-w", str(WEATHER_FILE), "-d", str(run_dir), "-r", str(idf_path)],
            capture_output=True, text=True, timeout=300,
        )

        if ep_proc.returncode != 0:
            result["status"] = f"ep_exit_{ep_proc.returncode}"
            return result

        # Check for fatal errors
        err_file = run_dir / "eplusout.err"
        if err_file.exists():
            if "** Fatal" in err_file.read_text():
                result["status"] = "ep_fatal"
                return result

        # Compute targets
        targets = compute_targets(run_dir, params["width"], params["length"])
        if any(not np.isfinite(v) for v in targets.values()):
            result.update(targets)
            result["status"] = "postprocess_nan"
            return result
        result.update(targets)
        result["sim_sec"] = round(time.perf_counter() - t0, 2)
        result["status"]  = "ok"

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except Exception as e:
        result["status"] = f"error: {e.__class__.__name__}"
        # Uncomment for debugging:
        # traceback.print_exc()
    finally:
        # Clean up large EP output files (keep .err and .csv for diagnostics)
        if cleanup and run_dir.exists():
            keep = {".err", ".csv", ".idf"}
            for f in run_dir.iterdir():
                if f.suffix not in keep:
                    try:
                        f.unlink()
                    except OSError:
                        pass

    return result


def reprocess_single(args: tuple) -> dict:
    """
    Recompute targets from existing EnergyPlus outputs without rerunning the
    simulation. args = (run_id_str, param_dict, prior_result_dict | None)
    """
    run_id, params, prior = args
    run_dir = RUNS_DIR / run_id

    result = {k: v for k, v in params.items() if k != "run_id"}
    result["run_id"] = run_id
    result["status"] = "failed"
    result["sim_sec"] = prior.get("sim_sec", np.nan) if prior is not None else np.nan
    result["script_hash"] = SCRIPT_HASH
    result["template_hash"] = TEMPLATE_HASH

    try:
        err_file = run_dir / "eplusout.err"
        csv_file = run_dir / "eplusout.csv"

        if not run_dir.exists():
            result["status"] = "missing_run_dir"
            return result
        if not csv_file.exists():
            result["status"] = "missing_csv"
            return result
        if err_file.exists() and "** Fatal" in err_file.read_text():
            result["status"] = "ep_fatal"
            return result

        diagnostics = derive_substitutions(params).pop("__diagnostics__", {})
        result.update(diagnostics)
        targets = compute_targets(run_dir, params["width"], params["length"])
        result.update(targets)
        if any(not np.isfinite(v) for v in targets.values()):
            result["status"] = "postprocess_nan"
            return result
        result["status"] = "ok"
    except Exception as e:
        result["status"] = f"postprocess_error: {e.__class__.__name__}"

    return result


def load_lhs_or_generate(args, legacy_ok: bool = True) -> pd.DataFrame:
    requested = {"samples": args.samples, "seed": args.seed, "house_type": HOUSE_TYPE}

    if args.force_regenerate_lhs or not LHS_CSV.exists():
        print(f"[LHS]  Generating {args.samples}×14 LHS matrix (seed={args.seed}) …")
        lhs_df = generate_lhs(args.samples, args.seed)
        lhs_df.to_csv(LHS_CSV, index=False)
        LHS_META_JSON.write_text(json.dumps(requested, indent=2))
        print(f"[LHS]  Saved → {LHS_CSV}")
        return lhs_df

    lhs_df = pd.read_csv(LHS_CSV)
    if LHS_META_JSON.exists():
        meta = json.loads(LHS_META_JSON.read_text())
        if meta == requested:
            print(f"[LHS]  Loading existing sample matrix: {LHS_CSV}")
            return lhs_df
        raise ValueError(
            f"Existing LHS metadata {meta} does not match requested "
            f"{requested}. Use --force-regenerate-lhs to overwrite."
        )

    if legacy_ok and len(lhs_df) == args.samples and args.seed == 42:
        print(f"[LHS]  Loading legacy sample matrix without metadata: {LHS_CSV}")
        LHS_META_JSON.write_text(json.dumps(requested, indent=2))
        return lhs_df

    raise ValueError(
        f"Existing LHS file {LHS_CSV.name} does not carry metadata and cannot "
        f"be assumed to match --samples {args.samples} / --seed {args.seed}. "
        f"Use --force-regenerate-lhs to overwrite it."
    )


def validate_results_hashes(prev: pd.DataFrame, mode: str) -> None:
    if prev.empty:
        return

    missing = [c for c in ["script_hash", "template_hash"] if c not in prev.columns]
    if missing:
        raise ValueError(
            f"Existing results are missing {missing}; refusing {mode} across "
            "unknown geometry/code versions."
        )

    script_hashes = {str(v) for v in prev["script_hash"].dropna().unique()}
    template_hashes = {str(v) for v in prev["template_hash"].dropna().unique()}

    if script_hashes != {SCRIPT_HASH} or template_hashes != {TEMPLATE_HASH}:
        raise ValueError(
            f"Existing results hashes do not match current code/template for {mode}. "
            f"script_hashes={script_hashes}, current={SCRIPT_HASH}; "
            f"template_hashes={template_hashes}, current={TEMPLATE_HASH}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Batch EnergyPlus runner v7")
    parser.add_argument("--workers",  type=int,  default=8,    help="Parallel workers (default 8)")
    parser.add_argument("--samples",  type=int,  default=2000, help="LHS samples (default 2000)")
    parser.add_argument("--seed",     type=int,  default=42,   help="LHS random seed")
    parser.add_argument("--force-regenerate-lhs", action="store_true",
                        help="Overwrite any existing LHS CSV/meta with a newly generated matrix")
    parser.add_argument("--resume",   action="store_true",     help="Skip already-completed runs")
    parser.add_argument("--no-clean", action="store_true",     help="Keep all EP output files")
    parser.add_argument("--postprocess-only", action="store_true",
                        help="Recompute targets from existing run directories without rerunning EnergyPlus")
    parser.add_argument("--type",     choices=["detached", "semi"], default="detached",
                        help="House type: detached (default) or semi")
    args = parser.parse_args()

    # ── Set type-dependent config and paths ───────────────────────────────────
    global CONFIG_FILE, WEATHER_FILE, LHS_CSV, LHS_META_JSON, IDF_TEMPLATE, RESULTS_CSV, RUNS_DIR, HOUSE_TYPE, SCRIPT_HASH, TEMPLATE_HASH
    HOUSE_TYPE = args.type
    if args.type == "semi":
        CONFIG_FILE  = _fm / "parameter_config_v7_semi.json"
        IDF_TEMPLATE = _fm / "semidetached_template.idf"
        RESULTS_CSV  = RESULTS_DIR / "results_v7_semi.csv"
        RUNS_DIR     = RUNS_BASE / "semi"
        LHS_CSV      = LHS_DIR / "lhs_samples_v7_semi.csv"
        LHS_META_JSON = LHS_DIR / "lhs_samples_v7_semi.meta.json"
    else:
        CONFIG_FILE  = _fm / "parameter_config_v7.json"
        IDF_TEMPLATE = _fm / "detachedhouse0.idf"
        RESULTS_CSV  = RESULTS_DIR / "results_v7.csv"
        RUNS_DIR     = RUNS_BASE / "detached"
        LHS_CSV      = LHS_DIR / "lhs_samples_v7.csv"
        LHS_META_JSON = LHS_DIR / "lhs_samples_v7.meta.json"

    cfg = load_config()
    meta = config_metadata(cfg)
    apply_fixed_parameters(cfg)
    SCRIPT_HASH = sha256_file(Path(__file__).resolve())

    weather_name = meta.get("weather_file")
    if weather_name:
        WEATHER_FILE = _weather_dir / weather_name
    TEMPLATE_HASH = sha256_file(IDF_TEMPLATE)

    print(f"[INFO] House type  : {args.type}")
    print(f"[INFO] Config file : {CONFIG_FILE.name}")
    print(f"[INFO] IDF template: {IDF_TEMPLATE.name}")
    print(f"[INFO] Weather file: {WEATHER_FILE.name}")
    print(f"[INFO] LHS CSV     : {LHS_CSV.name}")
    print(f"[INFO] Results CSV : {RESULTS_CSV.name}")

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    LHS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: LHS samples ───────────────────────────────────────────────────
    lhs_df = load_lhs_or_generate(args)

    # ── Step 2: Determine which runs to execute ───────────────────────────────
    completed_ids: set[str] = set()
    prev = pd.read_csv(RESULTS_CSV) if RESULTS_CSV.exists() else pd.DataFrame()
    if args.resume and RESULTS_CSV.exists():
        validate_results_hashes(prev, "resume")
        completed_ids = set(prev.loc[prev["status"] == "ok", "run_id"].tolist())
        print(f"[INFO] Resume mode: {len(completed_ids)} runs already completed, "
              f"{len(lhs_df) - len(completed_ids)} remaining.")

    template_text = IDF_TEMPLATE.read_text()
    cleanup       = not args.no_clean

    if args.postprocess_only:
        prior_by_run = {}
        if RESULTS_CSV.exists():
            validate_results_hashes(prev, "postprocess-only")
            prior_by_run = {row["run_id"]: row for _, row in prev.iterrows()}

        jobs = [
            (row["run_id"], row.to_dict(), prior_by_run.get(row["run_id"]))
            for _, row in lhs_df.iterrows()
        ]

        print(f"[INFO] Recomputing targets from {len(jobs)} existing run directories …\n")
        results: list[dict] = []
        n_ok = n_fail = 0
        for i, job in enumerate(jobs, 1):
            res = reprocess_single(job)
            results.append(res)
            if res.get("status") == "ok":
                n_ok += 1
            else:
                n_fail += 1
            if i % 50 == 0 or i == len(jobs):
                _save_results(results, set())
            print(f"  [{i:>4d}/{len(jobs)}]  {res['run_id']}  status={res['status']}")

        print(f"\n[DONE]  {n_ok} ok / {n_fail} failed")
        print(f"        Results → {RESULTS_CSV}")
        return

    todo = [
        (row["run_id"], row.to_dict(), template_text, cleanup)
        for _, row in lhs_df.iterrows()
        if row["run_id"] not in completed_ids
    ]

    n_total = len(todo)
    print(f"[INFO] Running {n_total} simulations with {args.workers} workers …\n")

    # ── Step 3: Parallel execution ────────────────────────────────────────────
    results: list[dict] = []
    n_ok = n_fail = 0
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_single, job): job[0] for job in todo}
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.append(res)

            status  = res.get("status", "?")
            sim_sec = res.get("sim_sec", "?")
            if status == "ok":
                n_ok += 1
            else:
                n_fail += 1

            elapsed  = time.perf_counter() - t_start
            rate     = i / elapsed                    # runs/s
            eta_min  = (n_total - i) / rate / 60 if rate > 0 else 0
            He       = res.get("He_worst", "?")
            print(
                f"  [{i:>4d}/{n_total}]  {res['run_id']}  "
                f"status={status:<12}  He={str(He):<8}  "
                f"{sim_sec}s  |  ETA {eta_min:.0f} min"
            )

            # ── Incremental save every 50 runs ──────────────────────────────
            if i % 50 == 0 or i == n_total:
                _save_results(results, completed_ids)

    # ── Final save ────────────────────────────────────────────────────────────
    _save_results(results, completed_ids)

    elapsed_min = (time.perf_counter() - t_start) / 60
    print(f"\n[DONE]  {n_ok} ok / {n_fail} failed  —  {elapsed_min:.1f} min total")
    print(f"        Results → {RESULTS_CSV}")


def _save_results(new_results: list[dict], prev_completed: set[str]):
    """Merge new results with any previously saved completed runs."""
    new_df = pd.DataFrame(new_results)

    if RESULTS_CSV.exists() and prev_completed:
        old_df = pd.read_csv(RESULTS_CSV)
        old_ok = old_df[old_df["run_id"].isin(prev_completed)]
        combined = pd.concat([old_ok, new_df], ignore_index=True)
    else:
        combined = new_df

    # Canonical column order
    id_cols     = ["run_id"]
    param_cols  = [p[0] for p in load_param_bounds()]
    diag_cols   = DIAG_COLS
    target_cols = ["He_worst", "We_max_worst", "T_op_peak", "hours_gt26_night", "heat_kWh_m2"]
    diagnostic_cols = ["hours_C3_worst"]
    meta_cols   = ["status", "sim_sec", "script_hash", "template_hash"]
    all_cols    = id_cols + param_cols + diag_cols + target_cols + diagnostic_cols + meta_cols
    available   = [c for c in all_cols if c in combined.columns]
    combined    = combined[available].sort_values("run_id").reset_index(drop=True)

    combined.to_csv(RESULTS_CSV, index=False)


if __name__ == "__main__":
    main()
