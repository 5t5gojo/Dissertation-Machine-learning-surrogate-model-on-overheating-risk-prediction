import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import ARCHETYPES, WEATHER_COLOURS, controls, dataset, label, page_header, paired

page_header(
    "Weather comparison",
    "The same 2,000 designs per archetype simulated under London TMYx and CIBSE DSY1. "
    "The two files differ in source, period and scenario, so the comparison is descriptive.",
)

chosen = controls("archetype", "target", key="weather")
archetype, target = chosen["archetype"], chosen["target"]
pairs = paired(archetype)
before, after = pairs[target], pairs[f"{target}_DSY1"]

columns = st.columns(4)
columns[0].metric("Median, TMYx", f"{before.median():.2f}")
columns[1].metric("Median, DSY1", f"{after.median():.2f}")
columns[2].metric("Mean paired change", f"{(after - before).mean():+.2f}")
columns[3].metric("Designs that increase", f"{(after > before).mean():.0%}")

left, right = st.columns(2)
long = pd.concat(
    [pd.DataFrame({"value": before, "weather": "TMYx"}), pd.DataFrame({"value": after, "weather": "DSY1"})]
)
histogram = px.histogram(
    long,
    x="value",
    color="weather",
    barmode="overlay",
    nbins=60,
    opacity=0.65,
    color_discrete_map=WEATHER_COLOURS,
    labels={"value": label(target), "weather": "Weather file"},
)
histogram.update_layout(title="Distribution across designs", yaxis_title="Designs", legend_title=None)
left.plotly_chart(histogram, width="stretch")

low, high = min(before.min(), after.min()), max(before.max(), after.max())
scatter = go.Figure()
scatter.add_trace(
    go.Scattergl(
        x=before,
        y=after,
        mode="markers",
        marker=dict(size=5, color=WEATHER_COLOURS["DSY1"], opacity=0.5),
        hovertemplate="TMYx %{x:.2f}<br>DSY1 %{y:.2f}<extra></extra>",
        name="Design",
    )
)
scatter.add_trace(
    go.Scatter(x=[low, high], y=[low, high], mode="lines", line=dict(color="#6b7280", dash="dash"), name="No change")
)
scatter.update_layout(
    title="Each design under both weather files",
    xaxis_title=f"TMYx: {label(target)}",
    yaxis_title=f"DSY1: {label(target)}",
    showlegend=False,
)
right.plotly_chart(scatter, width="stretch")

st.subheader("Screening flags (share of designs)")
rows = []
for code in ARCHETYPES:
    for weather in ["TMYx", "DSY1"]:
        d = dataset(weather, code)
        rows.append(
            {
                "Archetype": ARCHETYPES[code],
                "Weather": weather,
                "Hₑ > 3 % (C1)": (d.He_worst > 3).mean(),
                "Wₑ > 6 K h (C2)": (d.We_max_worst > 6).mean(),
                "Any C3 hour": (d.hours_C3_worst > 0).mean(),
                "Joint flag (same zone)": d.two_of_three_proxy_dwelling.mean(),
                "Night hours = 0": (d.hours_gt26_night == 0).mean(),
                "Night hours > 32": (d.hours_gt26_night > 32).mean(),
            }
        )
flags = pd.DataFrame(rows).set_index(["Archetype", "Weather"])
st.dataframe(flags.style.format("{:.1%}"), width="stretch")
st.caption("Night hours count May–September only, so the 32 h line is a diagnostic reference, not the TM59 criterion.")
