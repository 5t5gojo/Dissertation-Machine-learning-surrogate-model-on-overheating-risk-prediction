# Figure Manifest

This folder is split into two publication tiers:

- `in_text/`: figures intended for the dissertation main body
- `appendix/`: supporting figures retained as supplementary evidence

`hours_C3_worst` is treated as a diagnostic variable, not a surrogate training
target. It must not appear in model-performance, parity, SHAP, or RF-importance
figures.

## Recommended in-text figures

- `in_text/detached_target_distributions.png`
- `in_text/semi_target_distributions.png`
- `in_text/combined_model_comparison_r2.png`
- `in_text/detached_parity_xgb_vs_mlp.png`
- `in_text/detached_shap_all_targets.png`
- `in_text/semi_shap_all_targets.png`
- `in_text/detached_shap_He_worst.png`

## Recommended appendix figures

- `appendix/semi_parity_xgb_vs_mlp.png`
- `appendix/detached_rf_importance.png`
- `appendix/semi_rf_importance.png`
- `appendix/semi_shap_He_worst.png`
