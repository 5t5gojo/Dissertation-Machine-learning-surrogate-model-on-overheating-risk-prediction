import streamlit as st

from common import TARGETS, page_header, result

page_header(
    "Machine-learning surrogates for overheating in UK houses",
    "Bao, H. and Gutland, M. (2026). Interpretable Machine Learning Surrogate Models for Overheating Assessment "
    "in UK Detached and Semi-Detached Houses. BSO-uSIM 2026, Glasgow.",
)

st.markdown(
    "This dashboard presents the simulation data and model results of the study. "
    "The same 4,000 house designs were simulated in EnergyPlus under a London typical year (TMYx) and a "
    "CIBSE design summer year for the 2030s (DSY1), and Random Forest, XGBoost and multilayer perceptron "
    "surrogates were trained to reproduce five outcomes."
)

columns = st.columns(4)
columns[0].metric("EnergyPlus simulations", "8,000")
columns[1].metric("Archetypes", "2")
columns[2].metric("Design inputs", "14")
columns[3].metric("Predicted outcomes", str(len(TARGETS)))

summary = result("DSY1", "performance_summary").set_index(["archetype", "model", "target"])
peak = summary.loc[(slice(None), "XGBoost", "T_op_peak"), "R2_mean"]
st.subheader("Main findings")
st.markdown(
    f"""
- **Peak temperature is reliably learnable**: XGBoost test R² of {peak.min():.3f}–{peak.max():.3f} under DSY1.
- **Aggregate accuracy hides tail failure**: for homes with more than 32 night hours above 26 °C, the surrogates
  underpredict by several hours even when overall R² is high (see *Model evaluation*).
- **Explanations are conditional**: the leading night-time input in semi-detached houses depends on whether SHAP or
  permutation importance is used (see *Explainability*).
"""
)

st.subheader("Pages")
st.markdown(
    """
| Page | What it shows |
| --- | --- |
| Weather comparison | How each outcome shifts from the typical year to the design summer year for the same designs |
| Model evaluation | Test scores across five splits, predicted against simulated values, and night-time tail errors |
| Explainability | XGBoost SHAP and XGBoost/MLP permutation importance for every outcome |
| Surrogate predictor | Predictions of the published seed-42 XGBoost models for a design you specify |
"""
)
