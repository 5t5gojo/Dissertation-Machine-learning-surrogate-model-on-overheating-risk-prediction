import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import FEATURES, MODEL_COLOURS, WEATHER_COLOURS, controls, page_header, result

page_header(
    "Explainability",
    "Mean absolute XGBoost SHAP values and held-out permutation importance (normalised MSE increase) for XGBoost "
    "and the MLP. Both are predictive attributions, not causal effects.",
)

chosen = controls("weather", "archetype", "target", key="explain")
weather, archetype, target = chosen["weather"], chosen["archetype"], chosen["target"]
names = {f: FEATURES[f][0] for f in FEATURES}

shap = result(weather, "shap_mean_values_and_ranks").query("archetype == @archetype and target == @target")
shap = shap.sort_values("mean_abs_shap")
perm = result(weather, "permutation_importance").query("archetype == @archetype and target == @target")
perm = perm.groupby(["feature", "model"]).normalized_mse_increase.mean().unstack()

left, right = st.columns(2)
fig = go.Figure(
    go.Bar(
        x=shap.mean_abs_shap,
        y=[names[f] for f in shap.feature],
        orientation="h",
        marker_color=MODEL_COLOURS["XGBoost"],
        error_x=dict(type="data", array=shap.sd_abs_shap),
        customdata=shap[["min_rank", "max_rank"]],
        hovertemplate="%{y}: %{x:.3g}<br>rank across splits %{customdata[0]:.0f}–%{customdata[1]:.0f}<extra></extra>",
    )
)
fig.update_layout(title="XGBoost SHAP: mean |SHAP| (target units, ± SD of splits)", height=520)
left.plotly_chart(fig, width="stretch")

order = perm.mean(axis=1).sort_values().index
fig = go.Figure()
for model in ["XGBoost", "MLP"]:
    fig.add_trace(
        go.Bar(
            x=perm.loc[order, model],
            y=[names[f] for f in order],
            orientation="h",
            name=model,
            marker_color=MODEL_COLOURS[model],
        )
    )
fig.update_layout(
    title="Permutation importance (normalised MSE increase)",
    barmode="group",
    height=520,
    legend=dict(orientation="h", y=-0.12),
)
right.plotly_chart(fig, width="stretch")

leaders = {
    "XGBoost SHAP": shap.iloc[-1].feature,
    "XGBoost permutation": perm.XGBoost.idxmax(),
    "MLP permutation": perm.MLP.idxmax(),
}
agree = result(weather, "cross_model_importance_comparison").query("archetype == @archetype and target == @target")
st.subheader("Leading input by method")
st.markdown(
    " · ".join(f"**{method}**: {names[feature]}" for method, feature in leaders.items())
    + f" · XGBoost–MLP permutation rank agreement (Spearman): **{agree.rank_spearman.iloc[0]:.2f}**"
)
if len(set(leaders.values())) > 1:
    st.info(
        "The methods disagree on the leading input for this outcome, "
        "so its ranking should be reported together with the method used."
    )

st.divider()
st.subheader("Typical year against design summer year")
st.caption(
    "XGBoost SHAP for the same archetype and outcome under both weather files. Absolute SHAP values scale with the "
    "spread of the target, which differs between weather files, so each input is shown as a share of the total "
    "and by rank. A change in rank reflects a change in predictive reliance, not an isolated causal effect."
)
both = {}
for w in ["TMYx", "DSY1"]:
    s = result(w, "shap_mean_values_and_ranks").query("archetype == @archetype and target == @target")
    s = s.set_index("feature")
    both[w] = pd.DataFrame({"share": s.mean_abs_shap / s.mean_abs_shap.sum(), "rank": s.rank_of_mean})
comparison = pd.DataFrame(
    {
        "TMYx share": both["TMYx"].share,
        "DSY1 share": both["DSY1"].share,
        "TMYx rank": both["TMYx"]["rank"].astype(int),
        "DSY1 rank": both["DSY1"]["rank"].astype(int),
    }
)
comparison["Rank change"] = comparison["TMYx rank"] - comparison["DSY1 rank"]
comparison = comparison.sort_values("DSY1 share", ascending=False)

left, right = st.columns([3, 2])
top = comparison.head(8).iloc[::-1]
fig = go.Figure()
for w in ["TMYx", "DSY1"]:
    fig.add_trace(
        go.Bar(
            x=top[f"{w} share"] * 100,
            y=[names[f] for f in top.index],
            orientation="h",
            name=w,
            marker_color=WEATHER_COLOURS[w],
        )
    )
fig.update_layout(
    title="Share of total mean |SHAP| (%), eight leading inputs under DSY1",
    barmode="group",
    height=460,
    legend=dict(orientation="h", y=-0.15),
)
left.plotly_chart(fig, width="stretch")
table = comparison.rename(index=names)
right.dataframe(
    table.style.format({"TMYx share": "{:.1%}", "DSY1 share": "{:.1%}", "Rank change": "{:+d}"}),
    width="stretch",
    height=460,
)
right.caption("Rank change > 0: the input ranks higher under DSY1.")
