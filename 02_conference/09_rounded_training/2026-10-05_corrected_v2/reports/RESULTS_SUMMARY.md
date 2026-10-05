# Rounded C1 surrogate evaluation

Existing corrected V2 simulations were retained. Only the He training target changed to the audited rounded-temperature definition; C3 and same-zone flags were updated as diagnostics.

All models were freshly fit and selected using the original five matched splits and six candidates per family. Selection uses validation loss only. No EnergyPlus simulation was rerun.

C1 performance comparisons cross different target definitions and are not direct evidence that an algorithm improved. Other target values are unchanged, but MLP shared training and joint configuration selection can change their predictions.

## TMYx

| archetype   | target           | MLP             | RF              | XGBoost         |
|:------------|:-----------------|:----------------|:----------------|:----------------|
| detached    | He_worst         | 0.958 +/- 0.005 | 0.901 +/- 0.011 | 0.939 +/- 0.007 |
| detached    | T_op_peak        | 0.963 +/- 0.002 | 0.913 +/- 0.005 | 0.967 +/- 0.002 |
| detached    | We_max_worst     | 0.944 +/- 0.006 | 0.894 +/- 0.007 | 0.936 +/- 0.005 |
| detached    | heat_kWh_m2      | 0.967 +/- 0.007 | 0.872 +/- 0.018 | 0.928 +/- 0.018 |
| detached    | hours_gt26_night | 0.684 +/- 0.082 | 0.595 +/- 0.023 | 0.684 +/- 0.077 |
| semi        | He_worst         | 0.877 +/- 0.017 | 0.823 +/- 0.015 | 0.887 +/- 0.012 |
| semi        | T_op_peak        | 0.917 +/- 0.011 | 0.868 +/- 0.011 | 0.956 +/- 0.005 |
| semi        | We_max_worst     | 0.892 +/- 0.020 | 0.843 +/- 0.018 | 0.903 +/- 0.013 |
| semi        | heat_kWh_m2      | 0.924 +/- 0.017 | 0.815 +/- 0.035 | 0.892 +/- 0.011 |
| semi        | hours_gt26_night | 0.628 +/- 0.099 | 0.542 +/- 0.066 | 0.666 +/- 0.036 |

## DSY1

| archetype   | target           | MLP             | RF              | XGBoost         |
|:------------|:-----------------|:----------------|:----------------|:----------------|
| detached    | He_worst         | 0.901 +/- 0.013 | 0.847 +/- 0.027 | 0.889 +/- 0.016 |
| detached    | T_op_peak        | 0.977 +/- 0.004 | 0.919 +/- 0.004 | 0.977 +/- 0.003 |
| detached    | We_max_worst     | 0.956 +/- 0.006 | 0.894 +/- 0.009 | 0.945 +/- 0.004 |
| detached    | heat_kWh_m2      | 0.961 +/- 0.006 | 0.864 +/- 0.015 | 0.926 +/- 0.005 |
| detached    | hours_gt26_night | 0.798 +/- 0.057 | 0.703 +/- 0.026 | 0.799 +/- 0.052 |
| semi        | He_worst         | 0.855 +/- 0.030 | 0.788 +/- 0.027 | 0.854 +/- 0.027 |
| semi        | T_op_peak        | 0.944 +/- 0.008 | 0.889 +/- 0.004 | 0.965 +/- 0.003 |
| semi        | We_max_worst     | 0.924 +/- 0.012 | 0.861 +/- 0.009 | 0.933 +/- 0.005 |
| semi        | heat_kWh_m2      | 0.932 +/- 0.013 | 0.813 +/- 0.034 | 0.886 +/- 0.015 |
| semi        | hours_gt26_night | 0.812 +/- 0.030 | 0.686 +/- 0.032 | 0.806 +/- 0.027 |

## Scope

- Five overlapping split SDs are descriptive, not independent confidence intervals.
- No formal compliance, physical validation or frozen-model cross-weather transfer is established.
- Manuscripts and old figures were not overwritten. New publication figures require a separate update and visual check.
- Detailed predictions, selected models, SHAP arrays and permutation comparisons are in each weather evaluation folder.
