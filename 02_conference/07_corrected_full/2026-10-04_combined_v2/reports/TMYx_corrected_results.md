# TMYx: Corrected Full Results (Combined V2)

This report replaces neither the preserved legacy data nor the existing Word manuscripts. Use corrected tables and figures together, not mixed with legacy values.

## Model and Simulation

Full original LHS: 2,000 detached + 2,000 semi-detached cases. Three IDF corrections: wind-opening bearings follow rotation; intermediate-floor construction no longer contains sampled loft insulation; semi attic east gable is adiabatic. Automatic interior shades at 26.5 C remain enabled. The semi Kiva exposed fraction remains 0.75. All schedules, weather files and proxy definitions otherwise remain fixed.

| archetype   |    n |   C1_gt3 |   C2_gt6 |   C3_nonzero |   same_zone_two_of_three_proxy |   night_zero_pct |   night_summer_gt32 |   night_annual_gt32 |   median_peak_C |   max_peak_C |   median_heating_kWh_m2 |   max_cooling_kWh |
|:------------|-----:|---------:|---------:|-------------:|-------------------------------:|-----------------:|--------------------:|--------------------:|----------------:|-------------:|------------------------:|------------------:|
| detached    | 2000 |        0 |      784 |            0 |                              0 |          44.8000 |                   5 |                  16 |         29.4650 |      31.9110 |                 76.0900 |            0.0000 |
| semi        | 2000 |        0 |      392 |            0 |                              0 |          55.3500 |                   0 |                  17 |         29.1220 |      31.8770 |                 52.5936 |            0.0000 |

C1 uses the verified positive-occupancy schedule; C2 is the stepped proxy with strict >6; joint flags require two criteria in the SAME zone. None are formal compliance outcomes. Annual-night counts are diagnostic only.

## Repeated Model Accuracy

| archetype   | target           | MLP             | RF              | XGBoost         |
|:------------|:-----------------|:----------------|:----------------|:----------------|
| detached    | He_worst         | 0.938 +/- 0.014 | 0.867 +/- 0.024 | 0.912 +/- 0.013 |
| detached    | T_op_peak        | 0.962 +/- 0.002 | 0.913 +/- 0.005 | 0.967 +/- 0.002 |
| detached    | We_max_worst     | 0.944 +/- 0.006 | 0.894 +/- 0.007 | 0.936 +/- 0.005 |
| detached    | heat_kWh_m2      | 0.968 +/- 0.008 | 0.874 +/- 0.019 | 0.928 +/- 0.018 |
| detached    | hours_gt26_night | 0.684 +/- 0.079 | 0.597 +/- 0.026 | 0.684 +/- 0.077 |
| semi        | He_worst         | 0.821 +/- 0.027 | 0.775 +/- 0.029 | 0.845 +/- 0.017 |
| semi        | T_op_peak        | 0.915 +/- 0.009 | 0.868 +/- 0.011 | 0.956 +/- 0.005 |
| semi        | We_max_worst     | 0.891 +/- 0.015 | 0.843 +/- 0.019 | 0.903 +/- 0.013 |
| semi        | heat_kWh_m2      | 0.917 +/- 0.010 | 0.815 +/- 0.034 | 0.892 +/- 0.011 |
| semi        | hours_gt26_night | 0.611 +/- 0.076 | 0.545 +/- 0.063 | 0.666 +/- 0.036 |

Five matched original 1400/300/300 splits; six candidate pipelines per model; validation-only selection. Equal configuration budget is not equal runtime. SD over overlapping splits is not an independent-sample confidence interval. Each weather dataset is retrained separately, not transferred.

## Night-Time Diagnostics

| archetype   | model        | subgroup                   |   RMSE_mean |   RMSE_sd |   MAE_mean |   bias_mean |   n_min |   n_max |   valid_splits |
|:------------|:-------------|:---------------------------|------------:|----------:|-----------:|------------:|--------:|--------:|---------------:|
| detached    | AlwaysZero   | above_32h                  |     47.3333 |   11.5470 |    47.3333 |    -47.3333 |       0 |       1 |              3 |
| detached    | AlwaysZero   | all                        |      3.5857 |    0.5512 |     1.3553 |     -1.3553 |     300 |     300 |              5 |
| detached    | AlwaysZero   | nonzero                    |      4.8185 |    0.7589 |     2.4423 |     -2.4423 |     152 |     183 |              5 |
| detached    | AlwaysZero   | positive_training_p90_tail |     15.1828 |    3.4726 |    11.7876 |    -11.7876 |      13 |      19 |              5 |
| detached    | AlwaysZero   | zero                       |      0.0000 |    0.0000 |     0.0000 |      0.0000 |     117 |     148 |              5 |
| detached    | MLP          | above_32h                  |     27.3403 |    2.5288 |    27.3403 |    -27.3403 |       0 |       1 |              3 |
| detached    | MLP          | all                        |      1.8388 |    0.3039 |     0.6567 |      0.0069 |     300 |     300 |              5 |
| detached    | MLP          | nonzero                    |      2.4535 |    0.4298 |     0.9701 |     -0.1625 |     152 |     183 |              5 |
| detached    | MLP          | positive_training_p90_tail |      7.6522 |    1.9795 |     4.7938 |     -2.8459 |      13 |      19 |              5 |
| detached    | MLP          | zero                       |      0.3415 |    0.0178 |     0.2652 |      0.2098 |     117 |     148 |              5 |
| detached    | TrainingMean | above_32h                  |     45.9240 |   11.5804 |    45.9240 |    -45.9240 |       0 |       1 |              3 |
| detached    | TrainingMean | all                        |      3.3182 |    0.5710 |     1.4762 |      0.0428 |     300 |     300 |              5 |
| detached    | TrainingMean | nonzero                    |      4.2733 |    0.8254 |     1.5398 |     -1.0442 |     152 |     183 |              5 |
| detached    | TrainingMean | positive_training_p90_tail |     14.1128 |    3.5482 |    10.3894 |    -10.3894 |      13 |      19 |              5 |
| detached    | TrainingMean | zero                       |      1.3981 |    0.0324 |     1.3981 |      1.3981 |     117 |     148 |              5 |
| detached    | XGBoost      | above_32h                  |     24.6684 |    4.3889 |    24.6684 |    -24.6684 |       0 |       1 |              3 |
| detached    | XGBoost      | all                        |      1.8298 |    0.2011 |     0.6755 |     -0.0385 |     300 |     300 |              5 |
| detached    | XGBoost      | nonzero                    |      2.4222 |    0.3161 |     0.9796 |     -0.1808 |     152 |     183 |              5 |
| detached    | XGBoost      | positive_training_p90_tail |      7.1636 |    1.1082 |     4.3165 |     -3.7772 |      13 |      19 |              5 |
| detached    | XGBoost      | zero                       |      0.4734 |    0.1244 |     0.3004 |      0.1454 |     117 |     148 |              5 |
| semi        | AlwaysZero   | above_32h                  |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | AlwaysZero   | all                        |      2.4277 |    0.3678 |     0.9820 |     -0.9820 |     300 |     300 |              5 |
| semi        | AlwaysZero   | nonzero                    |      3.5801 |    0.6020 |     2.1256 |     -2.1256 |     123 |     152 |              5 |
| semi        | AlwaysZero   | positive_training_p90_tail |     10.3167 |    1.8168 |     8.7877 |     -8.7877 |      12 |      16 |              5 |
| semi        | AlwaysZero   | zero                       |      0.0000 |    0.0000 |     0.0000 |      0.0000 |     148 |     177 |              5 |
| semi        | MLP          | above_32h                  |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | MLP          | all                        |      1.3755 |    0.2569 |     0.5895 |     -0.0550 |     300 |     300 |              5 |
| semi        | MLP          | nonzero                    |      1.9848 |    0.4177 |     0.9916 |     -0.3443 |     123 |     152 |              5 |
| semi        | MLP          | positive_training_p90_tail |      5.5112 |    1.5989 |     4.0985 |     -3.1376 |      12 |      16 |              5 |
| semi        | MLP          | zero                       |      0.3712 |    0.0997 |     0.2465 |      0.1825 |     148 |     177 |              5 |
| semi        | TrainingMean | above_32h                  |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | TrainingMean | all                        |      2.2180 |    0.3864 |     1.0580 |      0.0134 |     300 |     300 |              5 |
| semi        | TrainingMean | nonzero                    |      3.0857 |    0.6581 |     1.1371 |     -1.1302 |     123 |     152 |              5 |
| semi        | TrainingMean | positive_training_p90_tail |      9.4736 |    1.8825 |     7.7923 |     -7.7923 |      12 |      16 |              5 |
| semi        | TrainingMean | zero                       |      0.9954 |    0.0191 |     0.9954 |      0.9954 |     148 |     177 |              5 |
| semi        | XGBoost      | above_32h                  |    nan      |  nan      |   nan      |    nan      |       0 |       0 |              0 |
| semi        | XGBoost      | all                        |      1.2723 |    0.1784 |     0.5467 |     -0.0483 |     300 |     300 |              5 |
| semi        | XGBoost      | nonzero                    |      1.8343 |    0.2925 |     0.9019 |     -0.2893 |     123 |     152 |              5 |
| semi        | XGBoost      | positive_training_p90_tail |      5.2102 |    0.8525 |     3.6898 |     -3.0548 |      12 |      16 |              5 |
| semi        | XGBoost      | zero                       |      0.3484 |    0.0533 |     0.2397 |      0.1548 |     148 |     177 |              5 |

n_min/n_max are subgroup sizes per split; appearances across splits are not independent samples. Undefined empty/single-class metrics remain NA. Regression outputs are not clipped; negative-prediction diagnostics are retained separately.

| archetype   | status   |   model_split_count |
|:------------|:---------|--------------------:|
| detached    | ok       |                  15 |
| semi        | ok       |                  15 |

## Night-Time SHAP

| archetype   | feature   |   mean_abs_shap |   sd_abs_shap |   rank_of_mean |   first_rank_splits |
|:------------|:----------|----------------:|--------------:|---------------:|--------------------:|
| detached    | g_value   |          0.9788 |        0.0951 |         1.0000 |                   5 |
| detached    | wof       |          0.7419 |        0.0461 |         2.0000 |                   0 |
| detached    | u_windows |          0.5134 |        0.0275 |         3.0000 |                   0 |
| semi        | wof       |          0.7000 |        0.0501 |         1.0000 |                   5 |
| semi        | g_value   |          0.6629 |        0.0709 |         2.0000 |                   0 |
| semi        | u_windows |          0.2516 |        0.0128 |         3.0000 |                   0 |

Rankings are five-split averages of exact selected-XGBoost attributions, not MLP explanations or causal effects. Cross-model permutation rankings are provided separately. Beeswarm figures use the prespecified seed-42 held-out cases, ordered by the five-split mean ranking; other splits may differ. Orientation is cyclic and high versus low numeric angles do not imply a monotonic physical effect.

## Cross-Model Interpretation Check

| archetype   | target           |   rank_spearman | xgb_top_feature   | mlp_top_feature   |
|:------------|:-----------------|----------------:|:------------------|:------------------|
| detached    | He_worst         |          0.9473 | g_value           | g_value           |
| detached    | T_op_peak        |          0.9912 | wwr               | wwr               |
| detached    | We_max_worst     |          0.9604 | wwr               | wwr               |
| detached    | heat_kWh_m2      |          0.9868 | wwr               | wwr               |
| detached    | hours_gt26_night |          0.9297 | g_value           | g_value           |
| semi        | He_worst         |          0.9165 | wwr               | g_value           |
| semi        | T_op_peak        |          0.9692 | wwr               | wwr               |
| semi        | We_max_worst     |          0.9692 | wwr               | wwr               |
| semi        | heat_kWh_m2      |          1.0000 | wwr               | wwr               |
| semi        | hours_gt26_night |          0.9692 | wof               | g_value           |

This comparison uses permutation importance for BOTH models, not SHAP for one model versus a different importance method for the other. A high whole-ranking Spearman correlation does not establish an identical leading feature. Where the two leading-feature columns differ, do not claim model-independent dominance.

### Method Dependence of the Leading Feature

| archetype   | target           | xgb_shap_leader   |   rank_spearman | xgb_permutation_leader   | mlp_permutation_leader   |
|:------------|:-----------------|:------------------|----------------:|:-------------------------|:-------------------------|
| detached    | He_worst         | g_value           |          0.9473 | g_value                  | g_value                  |
| detached    | T_op_peak        | wwr               |          0.9912 | wwr                      | wwr                      |
| detached    | We_max_worst     | wwr               |          0.9604 | wwr                      | wwr                      |
| detached    | heat_kWh_m2      | wwr               |          0.9868 | wwr                      | wwr                      |
| detached    | hours_gt26_night | g_value           |          0.9297 | g_value                  | g_value                  |
| semi        | He_worst         | wwr               |          0.9165 | wwr                      | g_value                  |
| semi        | T_op_peak        | wwr               |          0.9692 | wwr                      | wwr                      |
| semi        | We_max_worst     | wwr               |          0.9692 | wwr                      | wwr                      |
| semi        | heat_kWh_m2      | wwr               |          1.0000 | wwr                      | wwr                      |
| semi        | hours_gt26_night | wof               |          0.9692 | wof                      | g_value                  |

SHAP here ranks mean absolute prediction contributions; permutation importance ranks the increase in held-out prediction loss. The same XGBoost model can therefore have different leading features under these two summaries. Report the named method, model and weather, rather than asserting a universal physical driver.

## Changes from Legacy Model

| archetype   | target                  |    n |   mean_old |   mean_new |   mean_change |   median_change |   mean_absolute_change |   p95_absolute_change |   maximum_absolute_change |   increased |   decreased |
|:------------|:------------------------|-----:|-----------:|-----------:|--------------:|----------------:|-----------------------:|----------------------:|--------------------------:|------------:|------------:|
| detached    | He_worst                | 2000 |     0.2914 |     0.1676 |       -0.1238 |         -0.1089 |                 0.1242 |                0.2724 |                    0.5446 |           4 |        1807 |
| detached    | We_max_worst            | 2000 |     9.9855 |     6.9620 |       -3.0235 |         -3.0000 |                 3.0235 |                5.0000 |                    8.0000 |           0 |        1937 |
| detached    | T_op_peak               | 2000 |    30.0095 |    29.5524 |       -0.4571 |         -0.4560 |                 0.4571 |                0.5850 |                    0.7440 |           0 |        2000 |
| detached    | hours_gt26_night        | 2000 |     0.9335 |     1.3810 |        0.4475 |          0.0000 |                 0.6025 |                3.0000 |                   11.0000 |         608 |          69 |
| detached    | heat_kWh_m2             | 2000 |   107.3021 |   104.1622 |       -3.1399 |         -1.6284 |                 3.6550 |               13.6874 |                   39.4285 |         236 |        1763 |
| detached    | hours_C3_worst          | 2000 |     0.0015 |     0.0000 |       -0.0015 |          0.0000 |                 0.0015 |                0.0000 |                    2.0000 |           0 |           2 |
| detached    | hours_gt26_night_annual | 2000 |     1.5820 |     2.2395 |        0.6575 |          0.0000 |                 0.8775 |                3.0000 |                   57.0000 |         622 |          70 |
| semi        | He_worst                | 2000 |     0.1819 |     0.0778 |       -0.1042 |         -0.0817 |                 0.1042 |                0.3268 |                    0.7897 |           0 |        1564 |
| semi        | We_max_worst            | 2000 |     7.3740 |     4.3855 |       -2.9885 |         -3.0000 |                 2.9945 |                5.0000 |                    8.0000 |           6 |        1889 |
| semi        | T_op_peak               | 2000 |    29.6635 |    29.1870 |       -0.4765 |         -0.4760 |                 0.4765 |                0.6250 |                    0.8150 |           0 |        2000 |
| semi        | hours_gt26_night        | 2000 |     1.1750 |     0.9815 |       -0.1935 |          0.0000 |                 0.5925 |                3.0000 |                   13.0000 |         258 |         421 |
| semi        | heat_kWh_m2             | 2000 |    73.5530 |    70.3064 |       -3.2466 |         -1.7743 |                 3.8955 |               14.8406 |                   33.5848 |         314 |        1686 |
| semi        | hours_C3_worst          | 2000 |     0.0000 |     0.0000 |        0.0000 |          0.0000 |                 0.0000 |                0.0000 |                    0.0000 |           0 |           0 |
| semi        | hours_gt26_night_annual | 2000 |     1.8660 |     1.9005 |        0.0345 |          0.0000 |                 0.9355 |                3.0000 |                   78.0000 |         269 |         430 |

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
