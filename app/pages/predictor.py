import math

import numpy as np
import pandas as pd
import streamlit as st

from common import ARCHETYPES, FEATURES, TARGETS, page_header, parameter_bounds, result, surrogate

page_header(
    "Surrogate predictor",
    "Predictions of the published XGBoost models (split seed 42) for a design within the sampled ranges.",
)
st.warning(
    "These are surrogate predictions of EnergyPlus results for the simplified study model, not predictions of "
    "measured temperatures in a real home. The overheating indicators are TM52/TM59-derived screening proxies, "
    "not compliance results. Staying within each input's range does not guarantee that a combination of inputs "
    "is representative of the UK housing stock."
)

bounds = parameter_bounds()
MIDPOINT = {feature: (low + high) / 2 for feature, (low, high) in bounds.items()}
PRESETS = {
    "Mid-range design": {},
    "High solar gain": {"wwr": 0.40, "g_value": 0.70, "fixedShadingDepth": 0.0, "wof": 0.10},
    "Improved glazing and shading": {"u_windows": 1.2, "g_value": 0.30, "fixedShadingDepth": 0.8, "wof": 0.60},
}


def step_of(feature: str) -> float:
    """Power-of-ten slider step giving at least 100 positions across the range."""
    low, high = bounds[feature]
    return 10.0 ** math.floor(math.log10((high - low) / 100))


def snap(feature: str, value: float) -> float:
    low, high = bounds[feature]
    decimals = max(0, round(-math.log10(step_of(feature))))
    return min(max(round(round(value / step_of(feature)) * step_of(feature), decimals), low), high)


def apply_preset() -> None:
    values = MIDPOINT | PRESETS[st.session_state.preset]
    for feature in FEATURES:
        st.session_state[f"x_{feature}"] = snap(feature, values[feature])


if "x_width" not in st.session_state:
    st.session_state.preset = "Mid-range design"
    apply_preset()

left, right = st.columns(2)
archetype = left.radio("Archetype", list(ARCHETYPES), format_func=ARCHETYPES.get, horizontal=True)
right.selectbox("Start from an illustrative scenario", list(PRESETS), key="preset", on_change=apply_preset)
right.caption(
    "Scenarios change a few window-related inputs from mid-range values. They illustrate the model's behaviour "
    "and are not statistically typical homes."
)

st.subheader("Design")
columns = st.columns(3)
for i, (feature, (name, unit)) in enumerate(FEATURES.items()):
    low, high = bounds[feature]
    columns[i % 3].slider(
        f"{name} ({unit})" if unit else name,
        min_value=float(low),
        max_value=float(high),
        step=step_of(feature),
        format="%.4g" if high < 0.1 else "%.3g",
        key=f"x_{feature}",
    )
x = np.array([[st.session_state[f"x_{feature}"] for feature in FEATURES]])

predictions = {}
rows = []
for target, (name, unit) in TARGETS.items():
    row = {"Outcome": f"{name} ({unit})"}
    for weather in ["TMYx", "DSY1"]:
        value = float(surrogate(weather, archetype, target).inplace_predict(x)[0])
        if target in ("He_worst", "We_max_worst", "hours_gt26_night"):
            value = max(value, 0.0)  # counts and exceedances cannot be negative
        predictions[weather, target] = value
        scores = result(weather, "performance").query(
            "archetype == @archetype and model == 'XGBoost' and target == @target and seed == 42"
        )
        row[f"{weather} prediction"] = value
        row[f"{weather} test RMSE"] = float(scores.RMSE.iloc[0])
    rows.append(row)
table = pd.DataFrame(rows).set_index("Outcome")

st.subheader("Predicted outcomes")
st.dataframe(table.style.format("{:.2f}"), width="stretch")
st.caption(
    "Held-out test RMSE summarises the average squared-error magnitude across the test designs of split 42. "
    "It is not a prediction interval for this specific design."
)

st.subheader("Screening flags (from the predicted values)")
for weather in ["TMYx", "DSY1"]:
    he, we = predictions[weather, "He_worst"], predictions[weather, "We_max_worst"]
    night = predictions[weather, "hours_gt26_night"]
    flags = [f"Hₑ {'>' if he > 3 else '≤'} 3 %", f"Wₑ {'>' if we > 6 else '≤'} 6 K h"]
    st.markdown(f"**{weather}**: " + " · ".join(flags) + f" · night hours above 26 °C ≈ {night:.1f} h")

if max(predictions["TMYx", "hours_gt26_night"], predictions["DSY1", "hours_gt26_night"]) > 25:
    st.info(
        "This prediction is in the high night-time exposure range. On held-out test designs, the surrogates "
        "systematically underpredicted designs whose simulated night hours were highest, so treat high predictions "
        "as a lower-confidence screening signal (see the tail errors on the Model evaluation page)."
    )
