# Raw versus rounded temperature-difference audit

Source: corrected combined V2, 2026-10-04. This is post-processing only. No EnergyPlus runs, model training, manuscript edits or canonical-result replacements were performed.

## Scope and definitions

- Cases: 8,000; occupied-zone series: 16,000; 8,760 hourly records per case.
- Summer is May-September, with 3,672 hourly bins. Every checked occupied-zone schedule remains positive (minimum 0.3), so its occupied mask equals the summer mask. This is not a validation of realistic occupancy.
- Delta T = operative temperature minus adaptive limit. The adaptive limit and outdoor running mean are identical to the frozen corrected V2 implementation.
- Raw: C1 counts Delta T >= 1 K; C3 counts Delta T > 4 K.
- Rounded: round Delta T to the nearest integer (NumPy rint, ties to even), then use >=1 and >4. This is equivalent to raw Delta T >0.5 K for C1 and >4.5 K for C3, including the specified tie behaviour.
- A secondary half-away-from-zero calculation checks the unspecified half-integer convention. No tolerance snapping was applied to hourly differences.
- C1 is a percentage of occupied summer hours; changes are percentage points (pp), not relative percent. Flag: C1 >3%, evaluated before display rounding.
- C2 is deliberately held fixed: sum rint(max(Delta T,0)) over each summer day, take the maximum; flag is strictly >6. The half-up C2 calculation is a diagnostic only.
- C3 flag means at least one qualifying summer hour. The joint flag requires two criteria in the SAME zone, then any qualifying habitable zone at dwelling level.
- Motivation: [UK government overheating research, printed pp. 7-8](https://assets.publishing.service.gov.uk/media/5d91ca2ded915d556d8e7b64/Research_into_overheating_in_new_homes_-_phase_1.pdf) describes nearest-integer temperature differences. This audit isolates rounding; it does not establish full TM52/TM59 compliance.

## C1 continuous-value sensitivity

| weather   | archetype   |    n |   He_raw_mean_pct |   He_rounded_mean_pct |   He_change_mean_pp |   He_change_median_pp |   He_change_p95_pp |   He_change_max_pp |   He_changed_cases |
|:----------|:------------|-----:|------------------:|----------------------:|--------------------:|----------------------:|-------------------:|-------------------:|-------------------:|
| DSY1      | detached    | 2000 |            1.5600 |                1.8319 |              0.2719 |                0.2451 |             0.5447 |             1.9336 |               2000 |
| DSY1      | semi        | 2000 |            1.4020 |                1.6706 |              0.2686 |                0.2451 |             0.4085 |             1.3889 |               2000 |
| TMYx      | detached    | 2000 |            0.1676 |                0.3776 |              0.2100 |                0.1634 |             0.6536 |             1.1438 |               1846 |
| TMYx      | semi        | 2000 |            0.0778 |                0.2113 |              0.1336 |                0.0817 |             0.4630 |             0.9259 |               1573 |

## Threshold counts (each group has 2,000 cases)

| weather   | archetype   |   C1_raw_count |   C1_rounded_count |   C2_fixed_count |   C3_raw_count |   C3_rounded_count |   joint_raw_count |   joint_rounded_count |
|:----------|:------------|---------------:|-------------------:|-----------------:|---------------:|-------------------:|------------------:|----------------------:|
| DSY1      | detached    |             15 |                 46 |             2000 |           1969 |               1851 |              1969 |                  1851 |
| DSY1      | semi        |              3 |                 18 |             2000 |           1822 |               1508 |              1822 |                  1508 |
| TMYx      | detached    |              0 |                  1 |              784 |              0 |                  0 |                 0 |                     1 |
| TMYx      | semi        |              0 |                  0 |              392 |              0 |                  0 |                 0 |                     0 |

## All flag transitions

| weather   | archetype   | metric                 |    n |   false_to_false |   false_to_true |   true_to_false |   true_to_true |   changed |
|:----------|:------------|:-----------------------|-----:|-----------------:|----------------:|----------------:|---------------:|----------:|
| DSY1      | detached    | C1_gt3                 | 2000 |             1954 |              31 |               0 |             15 |        31 |
| DSY1      | detached    | C3_nonzero             | 2000 |               31 |               0 |             118 |           1851 |       118 |
| DSY1      | detached    | same_zone_two_of_three | 2000 |               31 |               0 |             118 |           1851 |       118 |
| DSY1      | semi        | C1_gt3                 | 2000 |             1982 |              15 |               0 |              3 |        15 |
| DSY1      | semi        | C3_nonzero             | 2000 |              178 |               0 |             314 |           1508 |       314 |
| DSY1      | semi        | same_zone_two_of_three | 2000 |              178 |               0 |             314 |           1508 |       314 |
| TMYx      | detached    | C1_gt3                 | 2000 |             1999 |               1 |               0 |              0 |         1 |
| TMYx      | detached    | C3_nonzero             | 2000 |             2000 |               0 |               0 |              0 |         0 |
| TMYx      | detached    | same_zone_two_of_three | 2000 |             1999 |               1 |               0 |              0 |         1 |
| TMYx      | semi        | C1_gt3                 | 2000 |             2000 |               0 |               0 |              0 |         0 |
| TMYx      | semi        | C3_nonzero             | 2000 |             2000 |               0 |               0 |              0 |         0 |
| TMYx      | semi        | same_zone_two_of_three | 2000 |             2000 |               0 |               0 |              0 |         0 |

## Paired weather comparison

| archetype   | metric                     |    n |   TMYx_mean |   DSY1_mean |   mean_DSY1_minus_TMYx |   median_DSY1_minus_TMYx |   increased |   unchanged |   decreased |
|:------------|:---------------------------|-----:|------------:|------------:|-----------------------:|-------------------------:|------------:|------------:|------------:|
| detached    | He_raw_pct                 | 2000 |      0.1676 |      1.5600 |                 1.3924 |                   1.3889 |        2000 |           0 |           0 |
| detached    | He_rounded_pct             | 2000 |      0.3776 |      1.8319 |                 1.4543 |                   1.4706 |        2000 |           0 |           0 |
| detached    | C3_hours_raw               | 2000 |      0.0000 |      6.7860 |                 6.7860 |                   5.0000 |        1969 |          31 |           0 |
| detached    | C3_hours_rounded           | 2000 |      0.0000 |      3.7715 |                 3.7715 |                   3.0000 |        1851 |         149 |           0 |
| detached    | T_op_peak_unchanged        | 2000 |     29.5524 |     34.2155 |                 4.6631 |                   4.7150 |        2000 |           0 |           0 |
| detached    | hours_gt26_night_unchanged | 2000 |      1.3810 |     18.2575 |                16.8765 |                  16.0000 |        2000 |           0 |           0 |
| semi        | He_raw_pct                 | 2000 |      0.0778 |      1.4020 |                 1.3242 |                   1.3344 |        2000 |           0 |           0 |
| semi        | He_rounded_pct             | 2000 |      0.2113 |      1.6706 |                 1.4593 |                   1.4706 |        2000 |           0 |           0 |
| semi        | C3_hours_raw               | 2000 |      0.0000 |      4.2825 |                 4.2825 |                   4.0000 |        1822 |         178 |           0 |
| semi        | C3_hours_rounded           | 2000 |      0.0000 |      2.2155 |                 2.2155 |                   2.0000 |        1508 |         492 |           0 |
| semi        | T_op_peak_unchanged        | 2000 |     29.1870 |     33.8023 |                 4.6153 |                   4.6765 |        2000 |           0 |           0 |
| semi        | hours_gt26_night_unchanged | 2000 |      0.9815 |     17.6590 |                16.6775 |                  16.0000 |        2000 |           0 |           0 |

## Half-integer check

| weather   | archetype   |   exact_half_integer_zone_hours |   tie_sensitive_cases |   C2_halfup_changed_zones |
|:----------|:------------|--------------------------------:|----------------------:|--------------------------:|
| DSY1      | detached    |                               0 |                     0 |                         0 |
| DSY1      | semi        |                               0 |                     0 |                         0 |
| TMYx      | detached    |                               0 |                     0 |                         0 |
| TMYx      | semi        |                               0 |                     0 |                         0 |

## Interpretation boundaries

- Threshold claims about C1, C3 and same-zone joint flags must name the rounding convention. The raw counts remain the preserved original proxy results; the rounded counts are a separate sensitivity analysis.
- Peak operative temperature, summer/annual night hours and heating demand do not involve this Delta T rounding. Their saved values were reproduced, not changed. C2 is unchanged by design.
- Existing He surrogate accuracy and SHAP results apply only to the original raw He target. A changed C1 target would require separate retraining/evaluation; no rounded-target model performance is inferred here.
- C3 remains diagnostic. Recomputing its counts and joint flags does not by itself require retraining the five existing target models.
- Weather pairing holds building inputs fixed, but the two weather files differ in source/location/scenario. Differences are not isolated climate-change or heat-severity effects.

## Verification

- 8,000 cases reproduce all frozen audit metrics before the change.
- 16,000 occupied-zone series pass independent interval-count checks and monotonicity checks.
- All 4,725 frozen input/result/model/figure files match their pre-existing hashes, before and after this audit.
- All 8,000 hourly CSVs and their run IDFs match recorded hashes on input and a separate final preservation pass.
- No existing result, model, IDF, weather, manuscript or figure was written.

## Outputs

- `case_comparison.csv`: all 8,000 dwellings/weather cases, continuous metrics and flags for each convention.
- `zone_comparison.csv`: all 16,000 occupied-zone series; reconstructs same-zone logic.
- `group_summary.csv`: four weather/archetype groups and C1 distributions.
- `flag_transitions.csv`: full false/true transitions, including both directions.
- `paired_weather_comparison.csv`: paired DSY1 minus TMYx values under each convention.
- `changed_flag_cases.csv`: IDs and values for cases with any C1/C3/joint flip.
- `verification.json`: scope, preservation checks, software versions and completion status.
