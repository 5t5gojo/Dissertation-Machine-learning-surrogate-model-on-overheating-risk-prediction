# DSY1: Corrected Full Results (Combined V2)

This report replaces neither the preserved legacy data nor the existing Word manuscripts. Use corrected tables and figures together, not mixed with legacy values.

## Model and Simulation

Full original LHS: 2,000 detached + 2,000 semi-detached cases. Three IDF corrections: wind-opening bearings follow rotation; intermediate-floor construction no longer contains sampled loft insulation; semi attic east gable is adiabatic. Automatic interior shades at 26.5 C remain enabled. The semi Kiva exposed fraction remains 0.75. All schedules, weather files and proxy definitions otherwise remain fixed.

| archetype   |    n |   C1_gt3 |   C2_gt6 |   C3_nonzero |   same_zone_two_of_three_proxy |   night_zero_pct |   night_summer_gt32 |   night_annual_gt32 |   median_peak_C |   max_peak_C |   median_heating_kWh_m2 |   max_cooling_kWh |
|:------------|-----:|---------:|---------:|-------------:|-------------------------------:|-----------------:|--------------------:|--------------------:|----------------:|-------------:|------------------------:|------------------:|
| detached    | 2000 |       15 |     2000 |         1969 |                           1969 |           0.0000 |                  71 |                  82 |         34.2070 |      35.8350 |                 69.8306 |            0.0000 |
| semi        | 2000 |        3 |     2000 |         1822 |                           1822 |           0.0000 |                  62 |                  74 |         33.8560 |      35.4670 |                 48.4870 |            0.0000 |

C1 uses the verified positive-occupancy schedule; C2 is the stepped proxy with strict >6; joint flags require two criteria in the SAME zone. None are formal compliance outcomes. Annual-night counts are diagnostic only.

## Repeated Model Accuracy

| archetype   | target           | MLP             | RF              | XGBoost         |
|:------------|:-----------------|:----------------|:----------------|:----------------|
| detached    | He_worst         | 0.899 +/- 0.023 | 0.854 +/- 0.021 | 0.908 +/- 0.011 |
| detached    | T_op_peak        | 0.977 +/- 0.004 | 0.919 +/- 0.004 | 0.977 +/- 0.003 |
| detached    | We_max_worst     | 0.957 +/- 0.007 | 0.894 +/- 0.009 | 0.945 +/- 0.004 |
| detached    | heat_kWh_m2      | 0.960 +/- 0.009 | 0.864 +/- 0.015 | 0.926 +/- 0.005 |
| detached    | hours_gt26_night | 0.799 +/- 0.068 | 0.703 +/- 0.026 | 0.799 +/- 0.052 |
| semi        | He_worst         | 0.908 +/- 0.011 | 0.839 +/- 0.020 | 0.908 +/- 0.022 |
| semi        | T_op_peak        | 0.951 +/- 0.011 | 0.889 +/- 0.004 | 0.965 +/- 0.003 |
| semi        | We_max_worst     | 0.930 +/- 0.014 | 0.861 +/- 0.009 | 0.933 +/- 0.005 |
| semi        | heat_kWh_m2      | 0.933 +/- 0.016 | 0.813 +/- 0.034 | 0.886 +/- 0.015 |
| semi        | hours_gt26_night | 0.826 +/- 0.035 | 0.686 +/- 0.032 | 0.806 +/- 0.027 |

Five matched original 1400/300/300 splits; six candidate pipelines per model; validation-only selection. Equal configuration budget is not equal runtime. SD over overlapping splits is not an independent-sample confidence interval. Each weather dataset is retrained separately, not transferred.

## Night-Time Diagnostics

| archetype   | model        | subgroup                   |   RMSE_mean |   RMSE_sd |   MAE_mean |   bias_mean |   n_min |   n_max |   valid_splits |
|:------------|:-------------|:---------------------------|------------:|----------:|-----------:|------------:|--------:|--------:|---------------:|
| detached    | AlwaysZero   | above_32h                  |     53.8253 |    5.7890 |    48.3846 |    -48.3846 |      10 |      13 |              5 |
| detached    | AlwaysZero   | all                        |     20.3695 |    0.7014 |    18.3633 |    -18.3633 |     300 |     300 |              5 |
| detached    | AlwaysZero   | nonzero                    |     20.3695 |    0.7014 |    18.3633 |    -18.3633 |     300 |     300 |              5 |
| detached    | AlwaysZero   | positive_training_p90_tail |     38.7957 |    2.6483 |    34.9904 |    -34.9904 |      31 |      40 |              5 |
| detached    | AlwaysZero   | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| detached    | MLP          | above_32h                  |     18.3105 |    6.0315 |    11.5732 |     -7.5337 |      10 |      13 |              5 |
| detached    | MLP          | all                        |      3.9121 |    0.9692 |     1.5891 |     -0.1418 |     300 |     300 |              5 |
| detached    | MLP          | nonzero                    |      3.9121 |    0.9692 |     1.5891 |     -0.1418 |     300 |     300 |              5 |
| detached    | MLP          | positive_training_p90_tail |     10.9865 |    3.2247 |     5.8325 |     -2.8184 |      31 |      40 |              5 |
| detached    | MLP          | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| detached    | TrainingMean | above_32h                  |     38.1217 |    6.7240 |    30.1000 |    -30.1000 |      10 |      13 |              5 |
| detached    | TrainingMean | all                        |      8.8001 |    0.9739 |     4.9315 |     -0.0788 |     300 |     300 |              5 |
| detached    | TrainingMean | nonzero                    |      8.8001 |    0.9739 |     4.9315 |     -0.0788 |     300 |     300 |              5 |
| detached    | TrainingMean | positive_training_p90_tail |     23.5475 |    3.7230 |    16.7059 |    -16.7059 |      31 |      40 |              5 |
| detached    | TrainingMean | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| detached    | XGBoost      | above_32h                  |     16.8644 |    2.7122 |    12.0207 |     -8.6839 |      10 |      13 |              5 |
| detached    | XGBoost      | all                        |      3.9019 |    0.6003 |     1.6221 |     -0.1685 |     300 |     300 |              5 |
| detached    | XGBoost      | nonzero                    |      3.9019 |    0.6003 |     1.6221 |     -0.1685 |     300 |     300 |              5 |
| detached    | XGBoost      | positive_training_p90_tail |     10.0806 |    1.2512 |     5.7460 |     -3.7441 |      31 |      40 |              5 |
| detached    | XGBoost      | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | AlwaysZero   | above_32h                  |     46.1337 |    5.0888 |    43.9664 |    -43.9664 |       5 |      11 |              5 |
| semi        | AlwaysZero   | all                        |     18.8588 |    0.3525 |    17.5967 |    -17.5967 |     300 |     300 |              5 |
| semi        | AlwaysZero   | nonzero                    |     18.8588 |    0.3525 |    17.5967 |    -17.5967 |     300 |     300 |              5 |
| semi        | AlwaysZero   | positive_training_p90_tail |     34.4645 |    2.7528 |    32.7711 |    -32.7711 |      23 |      42 |              5 |
| semi        | AlwaysZero   | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | MLP          | above_32h                  |     13.1319 |    4.3191 |     9.4744 |     -8.7497 |       5 |      11 |              5 |
| semi        | MLP          | all                        |      2.8210 |    0.4515 |     1.4603 |     -0.0430 |     300 |     300 |              5 |
| semi        | MLP          | nonzero                    |      2.8210 |    0.4515 |     1.4603 |     -0.0430 |     300 |     300 |              5 |
| semi        | MLP          | positive_training_p90_tail |      7.9521 |    2.1892 |     5.0637 |     -2.5707 |      23 |      42 |              5 |
| semi        | MLP          | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | TrainingMean | above_32h                  |     29.6511 |    5.5938 |    26.2412 |    -26.2412 |       5 |      11 |              5 |
| semi        | TrainingMean | all                        |      6.7790 |    0.5367 |     4.4385 |      0.1285 |     300 |     300 |              5 |
| semi        | TrainingMean | nonzero                    |      6.7790 |    0.5367 |     4.4385 |      0.1285 |     300 |     300 |              5 |
| semi        | TrainingMean | positive_training_p90_tail |     18.3791 |    3.2826 |    15.0459 |    -15.0459 |      23 |      42 |              5 |
| semi        | TrainingMean | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | XGBoost      | above_32h                  |     14.0615 |    4.0032 |    10.5759 |    -10.2920 |       5 |      11 |              5 |
| semi        | XGBoost      | all                        |      2.9717 |    0.3136 |     1.5103 |     -0.0337 |     300 |     300 |              5 |
| semi        | XGBoost      | nonzero                    |      2.9717 |    0.3136 |     1.5103 |     -0.0337 |     300 |     300 |              5 |
| semi        | XGBoost      | positive_training_p90_tail |      8.1324 |    1.3297 |     5.1527 |     -3.7510 |      23 |      42 |              5 |
| semi        | XGBoost      | zero                       |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |

n_min/n_max are subgroup sizes per split; appearances across splits are not independent samples. Undefined empty/single-class metrics remain NA. Regression outputs are not clipped; negative-prediction diagnostics are retained separately.

| archetype   | status                                   |   model_split_count |
|:------------|:-----------------------------------------|--------------------:|
| detached    | not_identifiable_single_class_validation |                  15 |
| semi        | not_identifiable_single_class_validation |                  15 |

## Night-Time SHAP

| archetype   | feature   |   mean_abs_shap |   sd_abs_shap |   rank_of_mean |   first_rank_splits |
|:------------|:----------|----------------:|--------------:|---------------:|--------------------:|
| detached    | g_value   |          3.1798 |        0.1887 |         1.0000 |                   5 |
| detached    | wof       |          2.6975 |        0.1022 |         2.0000 |                   0 |
| detached    | u_windows |          2.1006 |        0.0977 |         3.0000 |                   0 |
| semi        | wof       |          2.8013 |        0.0972 |         1.0000 |                   5 |
| semi        | g_value   |          2.6172 |        0.1307 |         2.0000 |                   0 |
| semi        | u_windows |          1.4482 |        0.0616 |         3.0000 |                   0 |

Rankings are five-split averages of exact selected-XGBoost attributions, not MLP explanations or causal effects. Cross-model permutation rankings are provided separately. Beeswarm figures use the prespecified seed-42 held-out cases, ordered by the five-split mean ranking; other splits may differ. Orientation is cyclic and high versus low numeric angles do not imply a monotonic physical effect.

## Cross-Model Interpretation Check

| archetype   | target           |   rank_spearman | xgb_top_feature   | mlp_top_feature   |
|:------------|:-----------------|----------------:|:------------------|:------------------|
| detached    | He_worst         |          0.8813 | g_value           | g_value           |
| detached    | T_op_peak        |          0.9956 | wwr               | wwr               |
| detached    | We_max_worst     |          0.9868 | wwr               | wwr               |
| detached    | heat_kWh_m2      |          0.9780 | wwr               | wwr               |
| detached    | hours_gt26_night |          0.9516 | g_value           | g_value           |
| semi        | He_worst         |          0.9912 | wwr               | wwr               |
| semi        | T_op_peak        |          0.9868 | wwr               | wwr               |
| semi        | We_max_worst     |          0.9912 | wwr               | wwr               |
| semi        | heat_kWh_m2      |          0.9824 | wwr               | wwr               |
| semi        | hours_gt26_night |          0.9516 | g_value           | g_value           |

This comparison uses permutation importance for BOTH models, not SHAP for one model versus a different importance method for the other. A high whole-ranking Spearman correlation does not establish an identical leading feature. Where the two leading-feature columns differ, do not claim model-independent dominance.

### Method Dependence of the Leading Feature

| archetype   | target           | xgb_shap_leader   |   rank_spearman | xgb_permutation_leader   | mlp_permutation_leader   |
|:------------|:-----------------|:------------------|----------------:|:-------------------------|:-------------------------|
| detached    | He_worst         | wwr               |          0.8813 | g_value                  | g_value                  |
| detached    | T_op_peak        | wwr               |          0.9956 | wwr                      | wwr                      |
| detached    | We_max_worst     | wwr               |          0.9868 | wwr                      | wwr                      |
| detached    | heat_kWh_m2      | wwr               |          0.9780 | wwr                      | wwr                      |
| detached    | hours_gt26_night | g_value           |          0.9516 | g_value                  | g_value                  |
| semi        | He_worst         | wwr               |          0.9912 | wwr                      | wwr                      |
| semi        | T_op_peak        | wwr               |          0.9868 | wwr                      | wwr                      |
| semi        | We_max_worst     | wwr               |          0.9912 | wwr                      | wwr                      |
| semi        | heat_kWh_m2      | wwr               |          0.9824 | wwr                      | wwr                      |
| semi        | hours_gt26_night | wof               |          0.9516 | g_value                  | g_value                  |

SHAP here ranks mean absolute prediction contributions; permutation importance ranks the increase in held-out prediction loss. The same XGBoost model can therefore have different leading features under these two summaries. Report the named method, model and weather, rather than asserting a universal physical driver.

## Changes from Legacy Model

| archetype   | target                  |    n |   mean_old |   mean_new |   mean_change |   median_change |   mean_absolute_change |   p95_absolute_change |   maximum_absolute_change |   increased |   decreased |
|:------------|:------------------------|-----:|-----------:|-----------:|--------------:|----------------:|-----------------------:|----------------------:|--------------------------:|------------:|------------:|
| detached    | He_worst                | 2000 |     1.7258 |     1.5600 |       -0.1657 |         -0.1634 |                 0.1661 |                0.3812 |                    0.7353 |           7 |        1981 |
| detached    | We_max_worst            | 2000 |    49.3175 |    44.0465 |       -5.2710 |         -5.0000 |                 5.2710 |                8.0000 |                   10.0000 |           0 |        2000 |
| detached    | T_op_peak               | 2000 |    34.7708 |    34.2155 |       -0.5552 |         -0.5530 |                 0.5552 |                0.6451 |                    0.8330 |           0 |        2000 |
| detached    | hours_gt26_night        | 2000 |    15.1765 |    18.2575 |        3.0810 |          3.0000 |                 3.4090 |                7.0000 |                   27.0000 |        1818 |         110 |
| detached    | heat_kWh_m2             | 2000 |    94.2343 |    91.5137 |       -2.7206 |         -1.8494 |                 3.0362 |                9.8052 |                   34.2213 |         119 |        1881 |
| detached    | hours_C3_worst          | 2000 |    11.6065 |     6.7860 |       -4.8205 |         -3.0000 |                 4.8205 |               12.0000 |                   26.0000 |           0 |        1965 |
| detached    | hours_gt26_night_annual | 2000 |    15.9540 |    18.9910 |        3.0370 |          3.0000 |                 3.6160 |                7.0000 |                   60.0000 |        1769 |         154 |
| semi        | He_worst                | 2000 |     1.5913 |     1.4020 |       -0.1893 |         -0.1906 |                 0.1894 |                0.3540 |                    0.8170 |           1 |        1995 |
| semi        | We_max_worst            | 2000 |    45.7700 |    39.9360 |       -5.8340 |         -6.0000 |                 5.8350 |               10.0000 |                   16.0000 |           1 |        1992 |
| semi        | T_op_peak               | 2000 |    34.4911 |    33.8023 |       -0.6888 |         -0.5915 |                 0.6888 |                1.2333 |                    1.9030 |           0 |        2000 |
| semi        | hours_gt26_night        | 2000 |    14.7280 |    17.6590 |        2.9310 |          3.0000 |                 3.2470 |                7.0000 |                   28.0000 |        1808 |         103 |
| semi        | heat_kWh_m2             | 2000 |    65.4888 |    61.2345 |       -4.2543 |         -2.3362 |                 4.3522 |               16.0208 |                   57.3936 |         147 |        1853 |
| semi        | hours_C3_worst          | 2000 |     7.9340 |     4.2825 |       -3.6515 |         -3.0000 |                 3.6515 |               10.0000 |                   17.0000 |           0 |        1896 |
| semi        | hours_gt26_night_annual | 2000 |    15.3745 |    18.3275 |        2.9530 |          3.0000 |                 3.5230 |                7.0000 |                   77.0000 |        1782 |         137 |

Model-performance and SHAP comparisons are in evaluation/legacy_model_performance_comparison.csv and evaluation/legacy_shap_comparison.csv. A changed R2 can reflect changed target variance, not only learner quality.

## Remaining Boundaries

- This is internal validation against EnergyPlus, not monitored-building or benchmark physical validation.
- Intermediate-floor concrete-only and full-height adjoining attic are explicit assumptions; the overall reference model remains simplified.
- No DSY2/DSY3 or TRY control is added. DSY1 and TMYx differ in source/location representation and scenario period, not just severity.
- Occupancy/security/noise do not restrict openings; opening need not require outdoor temperature below indoor temperature.
- C3 remains diagnostic to retain the same five-target comparison.
- Legacy paper text, reviewer replies and supplementary package require coordinated updating before submission.

## Verification

4,000 outputs independently re-audited; 180 candidate trials; 45,000 held-out predictions; 150 trained-model metric rows and 50 SHAP arrays recomputed from saved models. Scalers fitted to training data only; split identities and validation selection verified.
