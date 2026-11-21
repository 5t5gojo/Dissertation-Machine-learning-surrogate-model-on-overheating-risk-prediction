import plotly.graph_objects as go
import streamlit as st

from common import FEATURES, MODEL_COLOURS, controls, page_header, result

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
left.plotly_chart(fig, use_container_width=True)

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
right.plotly_chart(fig, use_container_width=True)

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
