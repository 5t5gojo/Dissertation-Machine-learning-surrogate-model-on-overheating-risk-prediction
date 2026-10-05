# DSY1 full simulation and repeated-model results

Weather: Z1_DSY1_2030s_HIGH50_CIBSE_v1.1. All 4000 simulations were independently audited before training. IDFs and original TMYx result files were not overwritten. This is a weather-scenario comparison, not a formal compliance assessment or a controlled isolation of severity alone.

## Simulation coverage

| archetype   |   n_ok |   C1_gt3 |   C2_gt6 |   C3_nonzero |   two_of_three_proxy |   night_zero_pct |   night_summer_gt32 |   night_annual_gt32 |   max_peak_C |   max_cooling_kWh |
|:------------|-------:|---------:|---------:|-------------:|---------------------:|-----------------:|--------------------:|--------------------:|-------------:|------------------:|
| detached    |   2000 |       28 |     2000 |         1999 |                 1999 |                0 |                  64 |                  87 |       36.433 |                 0 |
| semi        |   2000 |        8 |     2000 |         1994 |                 1994 |                0 |                  39 |                  64 |       36.006 |                 0 |

These counts now use the full original 2000-sample design per archetype, not the input-extreme pilot. C1 uses the verified positive-occupancy schedule; C2 is the stepped proxy with strict >6; same-zone joint flags remain proxies. Annual-night values are diagnostics, not training targets.

## Repeated model comparison

| archetype   | target           | MLP             | RF              | XGBoost         |
|:------------|:-----------------|:----------------|:----------------|:----------------|
| detached    | He_worst         | 0.921 +/- 0.015 | 0.831 +/- 0.015 | 0.886 +/- 0.014 |
| detached    | T_op_peak        | 0.977 +/- 0.003 | 0.925 +/- 0.009 | 0.976 +/- 0.006 |
| detached    | We_max_worst     | 0.957 +/- 0.003 | 0.895 +/- 0.007 | 0.945 +/- 0.003 |
| detached    | heat_kWh_m2      | 0.968 +/- 0.005 | 0.870 +/- 0.013 | 0.930 +/- 0.009 |
| detached    | hours_gt26_night | 0.862 +/- 0.039 | 0.742 +/- 0.019 | 0.826 +/- 0.029 |
| semi        | He_worst         | 0.893 +/- 0.026 | 0.806 +/- 0.012 | 0.880 +/- 0.018 |
| semi        | T_op_peak        | 0.966 +/- 0.004 | 0.904 +/- 0.007 | 0.972 +/- 0.005 |
| semi        | We_max_worst     | 0.933 +/- 0.009 | 0.854 +/- 0.004 | 0.927 +/- 0.004 |
| semi        | heat_kWh_m2      | 0.943 +/- 0.007 | 0.825 +/- 0.023 | 0.901 +/- 0.009 |
| semi        | hours_gt26_night | 0.843 +/- 0.032 | 0.710 +/- 0.023 | 0.821 +/- 0.018 |

Exactly the original five split assignments and six candidate configurations per model were reused. Each pipeline is selected by normalized validation loss, never test results. Equal configuration budget is not equal runtime. Standard deviations describe overlapping repeated splits and are not independent-sample confidence intervals. This evaluates DSY-trained models, not transfer of frozen TMYx models.

## Night-time evaluation

Nonzero/high-tail/above-32-hour errors and AlwaysZero/TrainingMean baselines are in evaluation/night_subgroups_all.csv. Event-status counts:

| archetype   | status                                   |   model_split_count |
|:------------|:-----------------------------------------|--------------------:|
| detached    | not_identifiable_single_class_validation |                  15 |
| semi        | not_identifiable_single_class_validation |                  15 |

Where a validation or test set contains only one class, discrimination is not identifiable; undefined metrics are NA rather than being advertised as perfect classification.

## Paired weather changes

| archetype   | target           |   mean_paired_change |   median_paired_change |   fraction_increased |
|:------------|:-----------------|---------------------:|-----------------------:|---------------------:|
| detached    | He_worst         |               1.4343 |                 1.4161 |               1.0000 |
| detached    | We_max_worst     |              39.3320 |                39.0000 |               1.0000 |
| detached    | T_op_peak        |               4.7612 |                 4.8000 |               1.0000 |
| detached    | hours_gt26_night |              14.2430 |                13.0000 |               1.0000 |
| detached    | heat_kWh_m2      |             -13.0678 |                -7.1753 |               0.1780 |
| detached    | hours_C3_worst   |              11.6050 |                 8.0000 |               0.9995 |
| semi        | He_worst         |               1.4094 |                 1.3889 |               1.0000 |
| semi        | We_max_worst     |              38.3960 |                38.0000 |               1.0000 |
| semi        | T_op_peak        |               4.8276 |                 4.8730 |               1.0000 |
| semi        | hours_gt26_night |              13.5530 |                12.0000 |               1.0000 |
| semi        | heat_kWh_m2      |              -8.0642 |                -4.7663 |               0.1550 |
| semi        | hours_C3_worst   |               7.9340 |                 6.0000 |               0.9970 |

## Interpretation and boundaries

Leading DSY night-time features:

| archetype   | feature   |   mean_abs_shap |   sd_abs_shap |   rank_of_mean |
|:------------|:----------|----------------:|--------------:|---------------:|
| detached    | g_value   |          3.0643 |        0.1207 |         1.0000 |
| detached    | u_windows |          2.4690 |        0.0677 |         2.0000 |
| detached    | wof       |          1.8815 |        0.0479 |         3.0000 |
| semi        | g_value   |          2.4130 |        0.1421 |         1.0000 |
| semi        | wof       |          2.1733 |        0.0953 |         2.0000 |
| semi        | u_windows |          1.5912 |        0.0629 |         3.0000 |

In this DSY experiment g-value ranks first in both archetypes; semi-detached window opening factor ranks second. The previous TMYx semi-detached opening-factor-first result is therefore weather-dependent, not a universal built-form mechanism. These are predictive attributions, not a controlled causal experiment.

- SHAP values/ranks are recalculated from the selected DSY XGBoost models; tables are in evaluation/shap_mean_values_and_ranks.csv. Cross-model permutation agreement is in evaluation/cross_model_importance_comparison.csv.
- C3 is retained as a diagnostic to keep the same five-target comparison. Because DSY activates it, a supplementary C3 surrogate is a possible additional experiment, not claimed here.
- Source location, weather-generation method and scenario period differ from St James's Park TMYx. Do not attribute every paired change solely to a hotter summer.
- No DSY2/DSY3, TRY control, physical validation or causal ablation has been performed.
- This report does not modify the preserved no-DSY Word manuscript or original reviewer response. Their numerical claims must be updated before a new submission.

## Verification

4000 audited simulations; 180 candidate trials; ten matched 1400/300/300 partitions; 45000 held-out predictions; all 150 trained-model metric rows recomputed; hyperparameter selection checked against minimum validation loss. Figures are stored separately under 02_conference/04_figures/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1.
