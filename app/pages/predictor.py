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
    "not compliance results."
)

bounds = parameter_bounds()
archetype = st.radio("Archetype", list(ARCHETYPES), format_func=ARCHETYPES.get, horizontal=True)

st.subheader("Design")
design = {}
columns = st.columns(3)
for i, (feature, (name, unit)) in enumerate(FEATURES.items()):
    low, high = bounds[feature]
    step = float(f"{(high - low) / 100:.1g}")
    design[feature] = columns[i % 3].slider(
        f"{name} ({unit})" if unit else name,
        min_value=float(low),
        max_value=float(high),
        value=float(round((low + high) / 2 / step) * step),
        step=step,
        format="%.4g" if high < 0.1 else "%.3g",
    )
x = np.array([[design[f] for f in FEATURES]])

rows = []
for target, (name, unit) in TARGETS.items():
    row = {"Outcome": f"{name} ({unit})"}
    for weather in ["TMYx", "DSY1"]:
        value = float(surrogate(weather, archetype, target).inplace_predict(x)[0])
        if target in ("He_worst", "We_max_worst", "hours_gt26_night"):
            value = max(value, 0.0)  # counts and exceedances cannot be negative
        scores = result(weather, "performance").query(
            "archetype == @archetype and model == 'XGBoost' and target == @target and seed == 42"
        )
        row[f"{weather} prediction"] = value
        row[f"{weather} test RMSE"] = float(scores.RMSE.iloc[0])
    rows.append(row)
table = pd.DataFrame(rows).set_index("Outcome")

st.subheader("Predicted outcomes")
st.dataframe(table.style.format("{:.2f}"), use_container_width=True)
st.caption("Test RMSE is the model's error on its held-out test designs, a typical size of the prediction error.")

st.subheader("Screening flags")
for weather in ["TMYx", "DSY1"]:
    he = table.loc[f"{TARGETS['He_worst'][0]} (%)", f"{weather} prediction"]
    we = table.loc[f"{TARGETS['We_max_worst'][0]} (K h)", f"{weather} prediction"]
    night = table.loc[f"{TARGETS['hours_gt26_night'][0]} (h)", f"{weather} prediction"]
    flags = [f"Hₑ {'>' if he > 3 else '≤'} 3 %", f"Wₑ {'>' if we > 6 else '≤'} 6 K h"]
    st.markdown(f"**{weather}**: " + " · ".join(flags) + f" · night hours above 26 °C ≈ {night:.1f} h")

tail = result("DSY1", "night_subgroups").query(
    "archetype == @archetype and model == 'XGBoost' and subgroup == 'above_32h'"
)
night_dsy1 = table.loc[f"{TARGETS['hours_gt26_night'][0]} (h)", "DSY1 prediction"]
if night_dsy1 > 25:
    st.info(
        f"This design is near the high-exposure tail. Under DSY1, for simulated night hours above 32 h the XGBoost "
        f"model underpredicted by {-tail.bias.mean():.1f} h on average (RMSE {tail.RMSE.mean():.1f} h), "
        "so the true value may be substantially higher."
    )
