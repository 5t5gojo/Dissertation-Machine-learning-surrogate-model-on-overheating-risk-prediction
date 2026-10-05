# Non-DSY revision results

Source of truth: `/Users/hlbao/Projects/dissertation/formal model file`. Original 4,000 simulation records are unchanged. All hourly records were audited before fitting. Five repeated splits are descriptive robustness checks on the same finite dataset, not five independent external validations.

## Repeated model accuracy

Mean +/- sample SD across seeds 42, 123, 202, 340 and 567. Six candidate configurations per model family per split; selected using joint normalized validation MSE only. RF/XGBoost each fit five estimators per candidate; MLP is multi-output. Equal configuration budget is not equal compute time or per-target tuning budget.

| archetype   | target           | RF              | XGBoost         | MLP             |
|:------------|:-----------------|:----------------|:----------------|:----------------|
| detached    | He_worst         | 0.886 +/- 0.014 | 0.929 +/- 0.011 | 0.945 +/- 0.006 |
| detached    | We_max_worst     | 0.904 +/- 0.006 | 0.946 +/- 0.003 | 0.946 +/- 0.005 |
| detached    | T_op_peak        | 0.914 +/- 0.006 | 0.970 +/- 0.002 | 0.959 +/- 0.004 |
| detached    | hours_gt26_night | 0.585 +/- 0.025 | 0.660 +/- 0.091 | 0.669 +/- 0.077 |
| detached    | heat_kWh_m2      | 0.883 +/- 0.015 | 0.938 +/- 0.016 | 0.972 +/- 0.003 |
| semi        | He_worst         | 0.819 +/- 0.013 | 0.896 +/- 0.010 | 0.870 +/- 0.029 |
| semi        | We_max_worst     | 0.858 +/- 0.012 | 0.929 +/- 0.003 | 0.898 +/- 0.019 |
| semi        | T_op_peak        | 0.862 +/- 0.009 | 0.960 +/- 0.003 | 0.914 +/- 0.017 |
| semi        | hours_gt26_night | 0.649 +/- 0.030 | 0.722 +/- 0.030 | 0.746 +/- 0.036 |
| semi        | heat_kWh_m2      | 0.832 +/- 0.027 | 0.906 +/- 0.015 | 0.939 +/- 0.010 |

Do not retain the old claims that MLP wins all three detached daytime targets, that XGBoost is best on night-time outcomes, or that RF defaults approach its achievable ceiling. The new experiment supersedes those single-split comparisons. No statistical-significance claim follows from the displayed mean/SD.

## Night-time errors

The tail is defined before testing from the 90th percentile of positive training outcomes. Predictions are not clipped or rounded. Empty or constant subgroups have undefined R-squared. The >32h subgroup is too sparse for a reliable compliance classifier.

| archetype   | model        | subgroup                   |   mean_n |   MAE_mean |   MAE_sd |   RMSE_mean |   RMSE_sd |   bias_mean |
|:------------|:-------------|:---------------------------|---------:|-----------:|---------:|------------:|----------:|------------:|
| detached    | AlwaysZero   | nonzero                    | 131.2000 |     2.2214 |   0.2260 |      4.4767 |    0.7732 |     -2.2214 |
| detached    | AlwaysZero   | positive_training_p90_tail |  18.2000 |     8.6383 |   1.2283 |     11.6541 |    2.3894 |     -8.6383 |
| detached    | MLP          | nonzero                    | 131.2000 |     1.0310 |   0.0657 |      2.3678 |    0.4566 |     -0.2718 |
| detached    | MLP          | positive_training_p90_tail |  18.2000 |     3.8576 |   0.5825 |      5.9432 |    1.5337 |     -1.9820 |
| detached    | RF           | nonzero                    | 131.2000 |     1.0311 |   0.1606 |      2.6414 |    0.5938 |     -0.4091 |
| detached    | RF           | positive_training_p90_tail |  18.2000 |     4.2677 |   0.7105 |      6.7440 |    1.5241 |     -3.6264 |
| detached    | TrainingMean | nonzero                    | 131.2000 |     1.2851 |   0.2317 |      4.0874 |    0.8147 |     -1.2851 |
| detached    | TrainingMean | positive_training_p90_tail |  18.2000 |     7.7020 |   1.2381 |     10.9695 |    2.4431 |     -7.7020 |
| detached    | XGBoost      | nonzero                    | 131.2000 |     1.0301 |   0.1382 |      2.3579 |    0.3812 |     -0.3332 |
| detached    | XGBoost      | positive_training_p90_tail |  18.2000 |     3.6661 |   0.5370 |      5.5774 |    0.4798 |     -3.0021 |
| semi        | AlwaysZero   | nonzero                    | 127.4000 |     2.7474 |   0.2126 |      4.0086 |    0.4194 |     -2.7474 |
| semi        | AlwaysZero   | positive_training_p90_tail |  16.4000 |     9.0564 |   1.4281 |      9.9722 |    1.9518 |     -9.0564 |
| semi        | MLP          | nonzero                    | 127.4000 |     1.0281 |   0.0474 |      1.7382 |    0.2694 |     -0.3344 |
| semi        | MLP          | positive_training_p90_tail |  16.4000 |     3.1306 |   0.9244 |      4.0347 |    1.2671 |     -2.5022 |
| semi        | RF           | nonzero                    | 127.4000 |     1.0907 |   0.1172 |      2.0251 |    0.3687 |     -0.4360 |
| semi        | RF           | positive_training_p90_tail |  16.4000 |     3.9727 |   0.9325 |      5.1731 |    1.3571 |     -3.7154 |
| semi        | TrainingMean | nonzero                    | 127.4000 |     1.6961 |   0.1955 |      3.2991 |    0.4717 |     -1.5514 |
| semi        | TrainingMean | positive_training_p90_tail |  16.4000 |     7.8604 |   1.4385 |      8.8911 |    2.0104 |     -7.8604 |
| semi        | XGBoost      | nonzero                    | 127.4000 |     0.9813 |   0.0919 |      1.8157 |    0.3338 |     -0.3699 |
| semi        | XGBoost      | positive_training_p90_tail |  16.4000 |     3.3644 |   0.8243 |      4.5117 |    1.2297 |     -2.9808 |

Event detection uses regression output as a score, with a cut-off selected by validation balanced accuracy. It is exploratory discrimination of any nonzero summer hours, not calibrated probability or TM59 compliance.

| archetype   | model   |   precision_mean |   precision_std |   recall_mean |   recall_std |   f1_mean |   f1_std |   balanced_accuracy_mean |   balanced_accuracy_std |   roc_auc_mean |   roc_auc_std |   average_precision_mean |   average_precision_std |
|:------------|:--------|-----------------:|----------------:|--------------:|-------------:|----------:|---------:|-------------------------:|------------------------:|---------------:|--------------:|-------------------------:|------------------------:|
| detached    | MLP     |           0.8409 |          0.0504 |        0.8815 |       0.0599 |    0.8580 |   0.0145 |                   0.8763 |                  0.0132 |         0.9536 |        0.0119 |                   0.9433 |                  0.0173 |
| detached    | RF      |           0.8146 |          0.0676 |        0.8743 |       0.0494 |    0.8409 |   0.0318 |                   0.8598 |                  0.0269 |         0.9380 |        0.0198 |                   0.9134 |                  0.0246 |
| detached    | XGBoost |           0.8089 |          0.0555 |        0.8787 |       0.0740 |    0.8390 |   0.0258 |                   0.8591 |                  0.0177 |         0.9382 |        0.0112 |                   0.9184 |                  0.0189 |
| semi        | MLP     |           0.8609 |          0.0468 |        0.8634 |       0.0248 |    0.8612 |   0.0208 |                   0.8800 |                  0.0137 |         0.9569 |        0.0129 |                   0.9474 |                  0.0127 |
| semi        | RF      |           0.7873 |          0.0711 |        0.9089 |       0.0385 |    0.8411 |   0.0324 |                   0.8645 |                  0.0205 |         0.9478 |        0.0145 |                   0.9298 |                  0.0184 |
| semi        | XGBoost |           0.8290 |          0.0614 |        0.9186 |       0.0580 |    0.8687 |   0.0276 |                   0.8879 |                  0.0218 |         0.9618 |        0.0111 |                   0.9490 |                  0.0121 |

## XGBoost and MLP interpretation agreement

Both models use the same held-out permutation-MSE measure for this comparison. This is not MLP SHAP and does not establish matching directions. Feature dependence and the sampled distribution affect both methods.

| archetype   | target           |   mean_spearman |   min_spearman |   mean_top3_overlap |
|:------------|:-----------------|----------------:|---------------:|--------------------:|
| detached    | He_worst         |          0.9525 |         0.9385 |              3.0000 |
| detached    | T_op_peak        |          0.9587 |         0.9429 |              3.0000 |
| detached    | We_max_worst     |          0.9666 |         0.9429 |              3.0000 |
| detached    | heat_kWh_m2      |          0.9613 |         0.8945 |              3.0000 |
| detached    | hours_gt26_night |          0.8338 |         0.6220 |              2.8000 |
| semi        | He_worst         |          0.9420 |         0.8989 |              2.0000 |
| semi        | T_op_peak        |          0.9895 |         0.9824 |              2.4000 |
| semi        | We_max_worst     |          0.9692 |         0.9560 |              2.2000 |
| semi        | heat_kWh_m2      |          0.9877 |         0.9780 |              3.0000 |
| semi        | hours_gt26_night |          0.9218 |         0.8593 |              3.0000 |

Full SHAP values, ranks and cross-split ranges: `../evaluation/shap_mean_values_and_ranks.csv`. Every SHAP figure uses explicit target units. Split-42 beeswarms are prespecified examples; global conclusions use all five splits. Individual panels should be placed at readable full-column/full-page width, not compressed into five tiny subplots.

## Audit results

| archetype   |    n |   C1_gt3 |   C2_gt6 |   C2_ge6 |   C2_gt6_pct |   C2_ge6_pct |   C3_nonzero |   two_of_three_proxy |   occupied_offset_max |   night_zero_pct |   night_mean |   night_median |   night_max |   night_gt32 |   night_annual_changed |   night_annual_gt32 |   rounding_changed |   cooling_kWh_max |
|:------------|-----:|---------:|---------:|---------:|-------------:|-------------:|-------------:|---------------------:|----------------------:|-----------------:|-------------:|---------------:|------------:|-------------:|-----------------------:|--------------------:|-------------------:|------------------:|
| detached    | 2000 |        0 |     1343 |     1456 |      67.1500 |      72.8000 |            2 |                    2 |                0.0000 |          56.6000 |       0.9335 |         0.0000 |          45 |            3 |                     99 |                  15 |                  0 |            0.0000 |
| semi        | 2000 |        0 |      942 |     1058 |      47.1000 |      52.9000 |            0 |                    0 |                0.0000 |          56.6000 |       1.1750 |         0.0000 |          29 |            0 |                     93 |                  16 |                  0 |            0.0000 |

Annual bedroom night diagnostic (not a newly trained target):

| archetype   |   mean |   median |   max |
|:------------|-------:|---------:|------:|
| detached    | 1.5820 |   0.0000 |   164 |
| semi        | 1.8660 |   0.0000 |   194 |

## Reproducibility

Hardware for the new experiment: Apple M5 Pro; macOS-26.6.2-arm64-arm-64bit. Versions, search spaces, sampled candidates and input hashes are in `../evaluation/protocol.json`. All 180 trials have recorded durations and selection scores. This hardware report does not prove which machine ran the original EnergyPlus campaign. Single-sample timings are exploratory CPU timings during concurrent training, not a controlled speed benchmark.
