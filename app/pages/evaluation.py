import plotly.graph_objects as go
import streamlit as st

from common import BASELINES, MODEL_COLOURS, MODELS, controls, label, page_header, result

page_header(
    "Model evaluation",
    "Held-out test scores across five matched 70/15/15 splits; each model family was tuned on validation loss only.",
)

chosen = controls("weather", "archetype", "target", key="evaluation")
weather, archetype, target = chosen["weather"], chosen["archetype"], chosen["target"]

summary = (
    result(weather, "performance_summary").query("archetype == @archetype and target == @target").set_index("model")
)
left, right = st.columns([2, 3])

r2 = summary.loc[MODELS]
bars = go.Figure(
    go.Bar(
        x=r2.index,
        y=r2.R2_mean,
        error_y=dict(type="data", array=r2.R2_std),
        marker_color=[MODEL_COLOURS[m] for m in r2.index],
        text=[f"{v:.3f}" for v in r2.R2_mean],
        textposition="outside",
    )
)
bars.update_layout(title="Test R² (mean ± SD of five splits)", yaxis=dict(range=[min(0, r2.R2_mean.min() - 0.1), 1.05]))
left.plotly_chart(bars, width="stretch")

table = summary.loc[MODELS + BASELINES, ["R2_mean", "R2_std", "MAE_mean", "RMSE_mean"]]
table.columns = ["R² mean", "R² SD", "MAE", "RMSE"]
left.dataframe(table.style.format("{:.3f}"), width="stretch")
left.caption("SDs describe overlapping splits, not independent confidence intervals.")

model = right.radio("Model", MODELS, index=MODELS.index("MLP") if target == "hours_gt26_night" else 1, horizontal=True)
p = result(weather, "predictions").query("archetype == @archetype and target == @target and model == @model")
low, high = min(p.y_true.min(), p.y_pred.min()), max(p.y_true.max(), p.y_pred.max())
parity = go.Figure()
if target == "hours_gt26_night" and high > 32:
    parity.add_vrect(x0=32, x1=high, fillcolor="#D1495B", opacity=0.08, line_width=0, annotation_text="> 32 h")
parity.add_trace(
    go.Scattergl(
        x=p.y_true,
        y=p.y_pred,
        mode="markers",
        marker=dict(size=5, color=MODEL_COLOURS[model], opacity=0.55),
        customdata=p[["run_id", "seed"]],
        hovertemplate=(
            "%{customdata[0]} (split %{customdata[1]})<br>simulated %{x:.2f}<br>predicted %{y:.2f}<extra></extra>"
        ),
    )
)
parity.add_trace(go.Scatter(x=[low, high], y=[low, high], mode="lines", line=dict(color="#6b7280", dash="dash")))
parity.update_layout(
    title=f"{model}: predicted against simulated (five test splits pooled)",
    showlegend=False,
    xaxis_title=f"Simulated {label(target)}",
    yaxis_title="Predicted",
)
right.plotly_chart(parity, width="stretch")
right.caption("A design can appear in more than one test split.")

if target == "hours_gt26_night":
    st.subheader("Night-time errors by subgroup")
    sub = result(weather, "night_subgroups").query("archetype == @archetype and model in @MODELS + @BASELINES")
    sub = sub.groupby(["subgroup", "model"])[["n", "MAE", "RMSE", "bias"]].mean().reset_index()
    order = ["all", "zero", "nonzero", "positive_training_p90_tail", "above_32h"]
    wide = sub.pivot(index="subgroup", columns="model", values=["RMSE", "bias"]).reindex(order)
    wide.index = ["All", "Zero", "Nonzero", "P90 tail of positive training values", "Above 32 h"]
    counts = sub[sub.model == "XGBoost"].set_index("subgroup").reindex(order)["n"].round(1).to_numpy()
    wide.insert(0, ("", "Test cases per split"), counts)
    st.dataframe(wide.style.format("{:.2f}", na_rep="–"), width="stretch")
    st.caption("Mean over the five splits. Bias = prediction − simulation; negative values are underpredictions.")
