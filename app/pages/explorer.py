import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    FEATURES,
    MODEL_COLOURS,
    MODELS,
    TARGETS,
    WEATHER_COLOURS,
    controls,
    label,
    page_header,
    paired,
    result,
)

page_header(
    "Design explorer",
    "Pick one simulated design to see its inputs, its EnergyPlus results under both weather files, "
    "and how well each surrogate predicted it when it was in a test split.",
)

chosen = controls("archetype", "target", key="explorer")
archetype, target = chosen["archetype"], chosen["target"]
pairs = paired(archetype)
dsy1_column = f"{target}_DSY1"

# Default to the highest DSY1 value among designs that were in at least one test split.
key = f"explorer_design_{archetype}"
if key not in st.session_state or st.session_state[key] not in pairs.index:
    tested = result("DSY1", "predictions").query("archetype == @archetype").run_id.unique()
    st.session_state[key] = pairs.loc[pairs.index.isin(tested), dsy1_column].idxmax()

figure = go.Figure()
figure.add_trace(
    go.Scatter(
        x=pairs[target],
        y=pairs[dsy1_column],
        mode="markers",
        customdata=pairs.index,
        marker=dict(size=6, color=WEATHER_COLOURS["DSY1"], opacity=0.45),
        hovertemplate="%{customdata}<br>TMYx %{x:.2f}<br>DSY1 %{y:.2f}<extra></extra>",
    )
)
current = st.session_state[key]
figure.add_trace(
    go.Scatter(
        x=[pairs.loc[current, target]],
        y=[pairs.loc[current, dsy1_column]],
        mode="markers",
        marker=dict(size=16, color="#1f2328", symbol="circle-open", line=dict(width=3)),
        hoverinfo="skip",
    )
)
figure.update_layout(
    title="Click a design (TMYx against DSY1 for the same design)",
    xaxis_title=f"TMYx: {label(target)}",
    yaxis_title=f"DSY1: {label(target)}",
    showlegend=False,
    height=430,
)
event = st.plotly_chart(figure, width="stretch", on_select="rerun", selection_mode="points", key=f"pick_{archetype}")
points = event.selection.points if event and event.selection else []
if points and points[0].get("customdata") is not None and points[0]["customdata"] != current:
    st.session_state[key] = points[0]["customdata"]
    st.rerun()

ordered = pairs.sort_values(dsy1_column, ascending=False).index.tolist()
design = st.selectbox(
    "Or choose a design (sorted by its DSY1 value of the selected target)",
    ordered,
    index=ordered.index(st.session_state[key]),
)
if design != st.session_state[key]:
    st.session_state[key] = design
    st.rerun()

row = pairs.loc[design]
left, right = st.columns([2, 3])

inputs = pd.DataFrame({"Input": [label(f) for f in FEATURES], "Value": [f"{row[f]:.4g}" for f in FEATURES]}).set_index(
    "Input"
)
left.subheader(f"Inputs of {design}")
left.dataframe(inputs, width="stretch", height=530)

outcomes = pd.DataFrame(
    {
        "TMYx": [row[t] for t in TARGETS],
        "DSY1": [row[f"{t}_DSY1"] for t in TARGETS],
    },
    index=[label(t) for t in TARGETS],
)
outcomes["Change"] = outcomes.DSY1 - outcomes.TMYx
right.subheader("EnergyPlus results")
right.dataframe(outcomes.style.format("{:.2f}"), width="stretch")
flags = pd.DataFrame(
    {
        "TMYx": [row.He_worst > 3, row.We_max_worst > 6, row.hours_C3_worst > 0, bool(row.two_of_three_proxy_dwelling)],
        "DSY1": [
            row.He_worst_DSY1 > 3,
            row.We_max_worst_DSY1 > 6,
            row.hours_C3_worst_DSY1 > 0,
            bool(row.two_of_three_proxy_dwelling_DSY1),
        ],
    },
    index=["Hₑ > 3 % (C1)", "Wₑ > 6 K h (C2)", "Any C3 hour", "Joint flag (same zone)"],
)
right.dataframe(flags.replace({True: "yes", False: "no"}), width="stretch")

right.subheader(f"Surrogate predictions: {TARGETS[target][0]}")
tables = []
for weather in ["TMYx", "DSY1"]:
    p = result(weather, "predictions").query("archetype == @archetype and run_id == @design and target == @target")
    if len(p):
        wide = p.pivot(index="seed", columns="model", values="y_pred")[MODELS]
        wide.insert(0, "Simulated", p.groupby("seed").y_true.first())
        wide.index = [f"{weather}, split {s}" for s in wide.index]
        tables.append(wide)
if tables:
    predictions = pd.concat(tables)
    right.dataframe(predictions.style.format("{:.2f}"), width="stretch")
    errors = predictions[MODELS].sub(predictions.Simulated, axis=0)
    bars = go.Figure()
    for model in MODELS:
        bars.add_trace(go.Bar(x=errors.index, y=errors[model], name=model, marker_color=MODEL_COLOURS[model]))
    bars.update_layout(title="Prediction − simulation", barmode="group", height=300, yaxis_title=TARGETS[target][1])
    right.plotly_chart(bars, width="stretch")
else:
    right.info(
        "This design was used for training or validation in all five splits, so there is no held-out prediction "
        "to compare. Pick another design to see model errors."
    )
