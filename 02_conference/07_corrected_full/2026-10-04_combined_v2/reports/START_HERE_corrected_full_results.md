# Combined V2: Full Corrected Experiment

**Status: full corrected simulations, repeated model training, verification and new figures completed. Existing Word manuscripts and submission ZIP are still legacy versions and must not be submitted with these new numbers until updated.**

## Scope

8,000 successful paired weather/archetype simulations: 7,680 newly executed and 320 hash-matched pilot results reused. Original IDFs, data, models and manuscripts were preserved. The same 14-dimensional LHS and five original splits were retained.

Changes: ventilation bearings, intermediate-floor insulation separation and full-height semi attic party wall. Automatic interior shades at 26.5 C remain; Kiva fraction stays 0.75. No physical validation or compliance claim is added.

## How Much Did the IDF Corrections Change Results?

| weather   | archetype   |   mean_delta_peak_C |   mean_delta_night_hours |   mean_delta_heating_kWh_m2 |
|:----------|:------------|--------------------:|-------------------------:|----------------------------:|
| DSY1      | detached    |             -0.5552 |                   3.0810 |                     -2.7206 |
| DSY1      | semi        |             -0.6888 |                   2.9310 |                     -4.2543 |
| TMYx      | detached    |             -0.4571 |                   0.4475 |                     -3.1399 |
| TMYx      | semi        |             -0.4765 |                  -0.1935 |                     -3.2466 |

Each delta is corrected minus legacy, for the same weather and same 2,000 LHS samples per archetype. These are NOT DSY1-minus-TMYx changes. A lower peak temperature does not necessarily mean fewer night-time exceedance hours.

## Full Simulation Coverage

| archetype   |    n |   C1_gt3 |   C2_gt6 |   C3_nonzero |   same_zone_two_of_three_proxy |   night_zero_pct |   night_summer_gt32 |   night_annual_gt32 |   median_peak_C |   max_peak_C |   median_heating_kWh_m2 |   max_cooling_kWh | weather   |
|:------------|-----:|---------:|---------:|-------------:|-------------------------------:|-----------------:|--------------------:|--------------------:|----------------:|-------------:|------------------------:|------------------:|:----------|
| detached    | 2000 |        0 |      784 |            0 |                              0 |          44.8000 |                   5 |                  16 |         29.4650 |      31.9110 |                 76.0900 |            0.0000 | TMYx      |
| semi        | 2000 |        0 |      392 |            0 |                              0 |          55.3500 |                   0 |                  17 |         29.1220 |      31.8770 |                 52.5936 |            0.0000 | TMYx      |
| detached    | 2000 |       15 |     2000 |         1969 |                           1969 |           0.0000 |                  71 |                  82 |         34.2070 |      35.8350 |                 69.8306 |            0.0000 | DSY1      |
| semi        | 2000 |        3 |     2000 |         1822 |                           1822 |           0.0000 |                  62 |                  74 |         33.8560 |      35.4670 |                 48.4870 |            0.0000 | DSY1      |

## Corrected Model Accuracy

| weather   | archetype   | target           | MLP             | RF              | XGBoost         |
|:----------|:------------|:-----------------|:----------------|:----------------|:----------------|
| DSY1      | detached    | He_worst         | 0.899 +/- 0.023 | 0.854 +/- 0.021 | 0.908 +/- 0.011 |
| DSY1      | detached    | T_op_peak        | 0.977 +/- 0.004 | 0.919 +/- 0.004 | 0.977 +/- 0.003 |
| DSY1      | detached    | We_max_worst     | 0.957 +/- 0.007 | 0.894 +/- 0.009 | 0.945 +/- 0.004 |
| DSY1      | detached    | heat_kWh_m2      | 0.960 +/- 0.009 | 0.864 +/- 0.015 | 0.926 +/- 0.005 |
| DSY1      | detached    | hours_gt26_night | 0.799 +/- 0.068 | 0.703 +/- 0.026 | 0.799 +/- 0.052 |
| DSY1      | semi        | He_worst         | 0.908 +/- 0.011 | 0.839 +/- 0.020 | 0.908 +/- 0.022 |
| DSY1      | semi        | T_op_peak        | 0.951 +/- 0.011 | 0.889 +/- 0.004 | 0.965 +/- 0.003 |
| DSY1      | semi        | We_max_worst     | 0.930 +/- 0.014 | 0.861 +/- 0.009 | 0.933 +/- 0.005 |
| DSY1      | semi        | heat_kWh_m2      | 0.933 +/- 0.016 | 0.813 +/- 0.034 | 0.886 +/- 0.015 |
| DSY1      | semi        | hours_gt26_night | 0.826 +/- 0.035 | 0.686 +/- 0.032 | 0.806 +/- 0.027 |
| TMYx      | detached    | He_worst         | 0.938 +/- 0.014 | 0.867 +/- 0.024 | 0.912 +/- 0.013 |
| TMYx      | detached    | T_op_peak        | 0.962 +/- 0.002 | 0.913 +/- 0.005 | 0.967 +/- 0.002 |
| TMYx      | detached    | We_max_worst     | 0.944 +/- 0.006 | 0.894 +/- 0.007 | 0.936 +/- 0.005 |
| TMYx      | detached    | heat_kWh_m2      | 0.968 +/- 0.008 | 0.874 +/- 0.019 | 0.928 +/- 0.018 |
| TMYx      | detached    | hours_gt26_night | 0.684 +/- 0.079 | 0.597 +/- 0.026 | 0.684 +/- 0.077 |
| TMYx      | semi        | He_worst         | 0.821 +/- 0.027 | 0.775 +/- 0.029 | 0.845 +/- 0.017 |
| TMYx      | semi        | T_op_peak        | 0.915 +/- 0.009 | 0.868 +/- 0.011 | 0.956 +/- 0.005 |
| TMYx      | semi        | We_max_worst     | 0.891 +/- 0.015 | 0.843 +/- 0.019 | 0.903 +/- 0.013 |
| TMYx      | semi        | heat_kWh_m2      | 0.917 +/- 0.010 | 0.815 +/- 0.034 | 0.892 +/- 0.011 |
| TMYx      | semi        | hours_gt26_night | 0.611 +/- 0.076 | 0.545 +/- 0.063 | 0.666 +/- 0.036 |

## Corrected Night-Time SHAP

| weather   | archetype   | feature   |   rank_of_mean |   mean_abs_shap |   first_rank_splits |
|:----------|:------------|:----------|---------------:|----------------:|--------------------:|
| DSY1      | detached    | g_value   |         1.0000 |          3.1798 |                   5 |
| DSY1      | detached    | wof       |         2.0000 |          2.6975 |                   0 |
| DSY1      | detached    | u_windows |         3.0000 |          2.1006 |                   0 |
| DSY1      | semi        | wof       |         1.0000 |          2.8013 |                   5 |
| DSY1      | semi        | g_value   |         2.0000 |          2.6172 |                   0 |
| DSY1      | semi        | u_windows |         3.0000 |          1.4482 |                   0 |
| TMYx      | detached    | g_value   |         1.0000 |          0.9788 |                   5 |
| TMYx      | detached    | wof       |         2.0000 |          0.7419 |                   0 |
| TMYx      | detached    | u_windows |         3.0000 |          0.5134 |                   0 |
| TMYx      | semi        | wof       |         1.0000 |          0.7000 |                   5 |
| TMYx      | semi        | g_value   |         2.0000 |          0.6629 |                   0 |
| TMYx      | semi        | u_windows |         3.0000 |          0.2516 |                   0 |

These are XGBoost predictive attributions. Consult permutation agreement before generalising to MLP. No causal mechanism or ranking stability is assumed from the legacy results.

### Do the Leading Features Agree Across Methods?

| weather   | archetype   | xgb_shap_leader   | xgb_permutation_leader   | mlp_permutation_leader   |
|:----------|:------------|:------------------|:-------------------------|:-------------------------|
| TMYx      | detached    | g_value           | g_value                  | g_value                  |
| TMYx      | semi        | wof               | wof                      | g_value                  |
| DSY1      | detached    | g_value           | g_value                  | g_value                  |
| DSY1      | semi        | wof               | g_value                  | g_value                  |

Differences in this table must be retained in the interpretation. SHAP contribution magnitude and permutation-induced prediction loss do not define the same quantity; neither demonstrates a unique physical cause.

## Paired Weather Changes

| archetype   | target                  |    n |   mean_TMYx |   mean_DSY1 |   mean_DSY1_minus_TMYx |   median_DSY1_minus_TMYx |   mean_absolute_change |   p95_absolute_change |   maximum_absolute_change |   increased |   decreased |
|:------------|:------------------------|-----:|------------:|------------:|-----------------------:|-------------------------:|-----------------------:|----------------------:|--------------------------:|------------:|------------:|
| detached    | He_worst                | 2000 |      0.1676 |      1.5600 |                 1.3924 |                   1.3889 |                 1.3924 |                1.5523 |                    2.9412 |        2000 |           0 |
| detached    | We_max_worst            | 2000 |      6.9620 |     44.0465 |                37.0845 |                  37.0000 |                37.0845 |               40.0000 |                   43.0000 |        2000 |           0 |
| detached    | T_op_peak               | 2000 |     29.5524 |     34.2155 |                 4.6631 |                   4.7150 |                 4.6631 |                4.9911 |                    5.1080 |        2000 |           0 |
| detached    | hours_gt26_night        | 2000 |      1.3810 |     18.2575 |                16.8765 |                  16.0000 |                16.8765 |               25.0000 |                   84.0000 |        2000 |           0 |
| detached    | heat_kWh_m2             | 2000 |    104.1622 |     91.5137 |               -12.6485 |                  -7.2097 |                13.2823 |               46.7761 |                  100.3015 |         350 |        1650 |
| detached    | hours_C3_worst          | 2000 |      0.0000 |      6.7860 |                 6.7860 |                   5.0000 |                 6.7860 |               17.0000 |                   39.0000 |        1969 |           0 |
| detached    | hours_gt26_night_annual | 2000 |      2.2395 |     18.9910 |                16.7515 |                  16.0000 |                16.7515 |               25.0000 |                   64.0000 |        2000 |           0 |
| semi        | He_worst                | 2000 |      0.0778 |      1.4020 |                 1.3242 |                   1.3344 |                 1.3242 |                1.5523 |                    2.6688 |        2000 |           0 |
| semi        | We_max_worst            | 2000 |      4.3855 |     39.9360 |                35.5505 |                  36.0000 |                35.5505 |               41.0000 |                   44.0000 |        2000 |           0 |
| semi        | T_op_peak               | 2000 |     29.1870 |     33.8023 |                 4.6153 |                   4.6765 |                 4.6153 |                5.1201 |                    5.2800 |        2000 |           0 |
| semi        | hours_gt26_night        | 2000 |      0.9815 |     17.6590 |                16.6775 |                  16.0000 |                16.6775 |               26.0000 |                   61.0000 |        2000 |           0 |
| semi        | heat_kWh_m2             | 2000 |     70.3064 |     61.2345 |                -9.0719 |                  -4.9804 |                 9.4880 |               33.5421 |                  109.4510 |         307 |        1693 |
| semi        | hours_C3_worst          | 2000 |      0.0000 |      4.2825 |                 4.2825 |                   4.0000 |                 4.2825 |                9.0000 |                   29.0000 |        1822 |           0 |
| semi        | hours_gt26_night_annual | 2000 |      1.9005 |     18.3275 |                16.4270 |                  16.0000 |                16.4390 |               25.0000 |                   52.0000 |        1999 |           1 |

This compares two specified weather datasets using identical corrected buildings, not an isolated climate-severity effect.

## Where to Read

- `TMYx_corrected_results.md` and `DSY1_corrected_results.md`: full counts, error diagnostics, differences and limitations.
- `datasets/<weather>/evaluation/`: models, splits, candidate trials, metrics, SHAP values and permutation results.
- `figures/<weather>/in_text/`: corrected model accuracy, peak/night SHAP and seed-42 directional figures.
- `figures/<weather>/appendix/`: other targets, parity plots and selected MLP loss curves.
- `datasets/<weather>/legacy_change_summary.csv`: full-data effect of the IDF corrections.

## Verification

360 candidate trials; 20 matched partitions; 90,000 held-out predictions; 300 trained-model metric rows and 100 SHAP arrays independently recomputed. All protected source hashes still match. All 8,000 error logs were checked: no severe/fatal errors or additional warning lines compared with their corresponding legacy case. Existing unused-construction/cost and CSV-processing warnings are retained in the audit, not described as zero warnings. Full source/target checks and verification manifests are retained.
