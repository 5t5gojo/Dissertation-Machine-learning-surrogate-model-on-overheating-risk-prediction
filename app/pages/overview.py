import streamlit as st

from common import ROOT, result

REPOSITORY = "https://github.com/5t5gojo/Dissertation-Machine-learning-surrogate-model-on-overheating-risk-prediction"

st.title("Interpretable machine-learning surrogates for overheating in UK houses")
st.markdown(
    "**Houlin Bao and Michael Gutland**, The Bartlett, University College London  \n"
    "*BSO-uSIM 2026, University of Strathclyde, Glasgow, 23–24 November 2026 (Paper 166)*  \n"
    f"[Code, data and results on GitHub]({REPOSITORY})"
)
st.page_link("pages/design.py", label="Try the design explorer", icon=":material/home_work:")

columns = st.columns(5)
columns[0].metric("EnergyPlus simulations", "8,000")
columns[1].metric("Weather files", "2")
columns[2].metric("Archetypes", "2")
columns[3].metric("Design inputs", "14")
columns[4].metric("Predicted outcomes", "5")

st.markdown(
    "The same 4,000 detached and semi-detached house designs were simulated under a London typical year (TMYx) "
    "and a CIBSE design summer year for the 2030s (DSY1). Random Forest, XGBoost and multilayer perceptron "
    "surrogates were trained to reproduce overheating indicators and heating demand, and the study asks where "
    "their reliability breaks down."
)
st.image(
    str(ROOT / "figures" / "night_parity_DSY1.png"),
    caption="Under DSY1, the designs with the most night-time overheating are underpredicted.",
)

summary = result("DSY1", "performance_summary").set_index(["archetype", "model", "target"])
peak = summary.loc[(slice(None), "XGBoost", "T_op_peak"), "R2_mean"]
night_r2 = summary.loc[("detached", "MLP", "hours_gt26_night"), "R2_mean"]
tail = result("DSY1", "night_subgroups").query("model == 'MLP' and subgroup == 'above_32h'")
bias = tail.groupby("archetype").bias.mean()

st.subheader("Findings")
st.markdown(
    f"**1. Peak temperature is reliably learnable.** XGBoost reaches a test R² of {peak.min():.3f}–{peak.max():.3f} "
    "under DSY1 for both archetypes."
)
st.page_link("pages/evaluation.py", label="Model evaluation")
st.markdown(
    f"**2. Aggregate accuracy hides tail failure.** Under DSY1 the MLP's night-time R² is {night_r2:.2f} (detached), "
    f"yet homes with more than 32 night hours above 26 °C are underpredicted by {-bias['detached']:.1f} h "
    f"(detached) and {-bias['semi']:.1f} h (semi-detached) on average."
)
st.page_link("pages/explorer.py", label="Simulated cases")
st.markdown(
    "**3. Explanations are conditional.** In semi-detached houses, the leading night-time input changes between "
    "SHAP and permutation importance. Between the two weather files the leading inputs stay the same, while "
    "lower-ranked inputs shift."
)
st.page_link("pages/explainability.py", label="Explainability")

st.subheader("Scope and limitations")
st.markdown(
    """
- Results come from a simplified EnergyPlus model and have not been validated against monitored homes.
- The overheating indicators are screening proxies derived from CIBSE TM52 and TM59, not compliance results.
- Models are retrained for each weather file; transferring a trained model between climates is not tested.
- The 14 inputs are sampled independently over fixed ranges; combinations are not weighted by the UK housing stock.
"""
)
