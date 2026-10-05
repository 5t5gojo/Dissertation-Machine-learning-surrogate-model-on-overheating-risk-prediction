# Paired IDF Sensitivity Results

This is an isolated pilot, not a replacement dataset or revised surrogate evaluation.

## Verification

- 8020 original source paths unchanged; 4,000 original IDFs archived and hash-checked.
- 320 original hourly outputs re-audited before running; hourly source hashes unchanged.
- 12 unmodified controls reproduce every saved target; 1,440 variant runs completed.
- All 1,452 unique runs have zero severe errors and zero active cooling.
- Initial ReadVarsESO audit-file failures: 1; recovered with isolated working directories: 1. Initial runner, protocol and failed attempt are preserved in backup/.
- Additional warning instances relative to paired original logs: 0 (see additional_warning_instances.csv).
- Each new run was evaluated using both independent target implementations.
- Actual run IDFs, weather provenance and output hashes were checked after completion.

## Interpretation Boundaries

- Random64 and Stress16 cohorts are reported separately. Stress16 was partly selected using extreme outcomes.
- Means, counts and maximum differences describe this pilot only, not all 2,000 cases or housing-stock rates.
- Combined retains automatic interior shading. Shade-off is a separate diagnostic, not part of the proposed correction.
- No ML retraining or SHAP reranking is performed here; unchanged conclusions cannot be inferred from a small temperature difference alone.
- Single-change effects are not additive; no complete factorial or causal decomposition is claimed.
- Threshold counts are screening proxies, not regulatory compliance outcomes.
- Existing semi Kiva fraction remains 0.75. This experiment does not resolve all model simplifications.

## Variants

- `control`: Unmodified IDF rerun: environment/reproducibility control.
- `vent_rotation`: Rotate opening effective bearings with building and zone north.
- `interfloor`: Surface 6/7 use original 100 mm concrete only; loft insulation unchanged.
- `attic_party`: Semi Surface 16 becomes adiabatic/NoSun/NoWind; all else unchanged.
- `combined`: Vent rotation + interfloor; plus attic party for semi. Interior shades retained.
- `shade_off`: Diagnostic only: automatic interior shade controls AlwaysOff; other fields unchanged.

## Combined Correction: Random Cohort

Units: He in percentage points, We in stepped proxy units, peak in deg C, night in hours, heating in kWh/m2/year. Differences are modified minus original.

| weather   | archetype   | target           |   n |   mean_change |   mean_absolute_change |   max_absolute_change |
|:----------|:------------|:-----------------|----:|--------------:|-----------------------:|----------------------:|
| DSY1      | detached    | He_worst         |  64 |       -0.1842 |                 0.1842 |                0.7353 |
| DSY1      | detached    | We_max_worst     |  64 |       -5.0156 |                 5.0156 |                9.0000 |
| DSY1      | detached    | T_op_peak        |  64 |       -0.5631 |                 0.5631 |                0.7850 |
| DSY1      | detached    | hours_gt26_night |  64 |        2.5000 |                 3.0625 |                9.0000 |
| DSY1      | detached    | heat_kWh_m2      |  64 |       -2.7819 |                 2.8504 |               18.7384 |
| DSY1      | semi        | He_worst         |  64 |       -0.2123 |                 0.2123 |                0.5174 |
| DSY1      | semi        | We_max_worst     |  64 |       -6.4531 |                 6.4531 |               15.0000 |
| DSY1      | semi        | T_op_peak        |  64 |       -0.7568 |                 0.7568 |                1.6590 |
| DSY1      | semi        | hours_gt26_night |  64 |        2.2656 |                 3.0156 |                9.0000 |
| DSY1      | semi        | heat_kWh_m2      |  64 |       -5.6847 |                 5.6879 |               35.0334 |
| TMYx      | detached    | He_worst         |  64 |       -0.1217 |                 0.1226 |                0.3813 |
| TMYx      | detached    | We_max_worst     |  64 |       -2.8750 |                 2.8750 |                6.0000 |
| TMYx      | detached    | T_op_peak        |  64 |       -0.4547 |                 0.4547 |                0.6030 |
| TMYx      | detached    | hours_gt26_night |  64 |        0.3906 |                 0.7344 |               10.0000 |
| TMYx      | detached    | heat_kWh_m2      |  64 |       -3.3683 |                 3.9931 |               28.7231 |
| TMYx      | semi        | He_worst         |  64 |       -0.0923 |                 0.0923 |                0.5447 |
| TMYx      | semi        | We_max_worst     |  64 |       -2.6562 |                 2.6875 |                6.0000 |
| TMYx      | semi        | T_op_peak        |  64 |       -0.4628 |                 0.4628 |                0.7350 |
| TMYx      | semi        | hours_gt26_night |  64 |       -0.2969 |                 0.6406 |                4.0000 |
| TMYx      | semi        | heat_kWh_m2      |  64 |       -4.1472 |                 5.0193 |               32.3382 |

## Individual Changes: Random Cohort

| weather   | archetype   | variant       | target           |   mean_change |   mean_absolute_change |   max_absolute_change |
|:----------|:------------|:--------------|:-----------------|--------------:|-----------------------:|----------------------:|
| DSY1      | detached    | combined      | T_op_peak        |       -0.5631 |                 0.5631 |                0.7850 |
| DSY1      | detached    | combined      | hours_gt26_night |        2.5000 |                 3.0625 |                9.0000 |
| DSY1      | detached    | interfloor    | T_op_peak        |       -0.5581 |                 0.5581 |                0.7260 |
| DSY1      | detached    | interfloor    | hours_gt26_night |        2.3594 |                 2.9531 |               10.0000 |
| DSY1      | detached    | shade_off     | T_op_peak        |        0.4237 |                 0.4237 |                1.2410 |
| DSY1      | detached    | shade_off     | hours_gt26_night |        2.5312 |                 2.5312 |                8.0000 |
| DSY1      | detached    | vent_rotation | T_op_peak        |       -0.0053 |                 0.0210 |                0.1050 |
| DSY1      | detached    | vent_rotation | hours_gt26_night |        0.0312 |                 0.3125 |                2.0000 |
| DSY1      | semi        | attic_party   | T_op_peak        |       -0.0013 |                 0.0035 |                0.0560 |
| DSY1      | semi        | attic_party   | hours_gt26_night |       -0.0781 |                 0.1406 |                1.0000 |
| DSY1      | semi        | combined      | T_op_peak        |       -0.7568 |                 0.7568 |                1.6590 |
| DSY1      | semi        | combined      | hours_gt26_night |        2.2656 |                 3.0156 |                9.0000 |
| DSY1      | semi        | interfloor    | T_op_peak        |       -0.5566 |                 0.5566 |                0.7550 |
| DSY1      | semi        | interfloor    | hours_gt26_night |        2.0625 |                 3.0312 |                9.0000 |
| DSY1      | semi        | shade_off     | T_op_peak        |        0.3281 |                 0.3281 |                1.1580 |
| DSY1      | semi        | shade_off     | hours_gt26_night |        2.2812 |                 2.3438 |               12.0000 |
| DSY1      | semi        | vent_rotation | T_op_peak        |       -0.1883 |                 0.2041 |                1.0180 |
| DSY1      | semi        | vent_rotation | hours_gt26_night |        0.1875 |                 0.9688 |                4.0000 |
| TMYx      | detached    | combined      | T_op_peak        |       -0.4547 |                 0.4547 |                0.6030 |
| TMYx      | detached    | combined      | hours_gt26_night |        0.3906 |                 0.7344 |               10.0000 |
| TMYx      | detached    | interfloor    | T_op_peak        |       -0.4540 |                 0.4540 |                0.5920 |
| TMYx      | detached    | interfloor    | hours_gt26_night |        0.4219 |                 0.7031 |               10.0000 |
| TMYx      | detached    | shade_off     | T_op_peak        |        0.5780 |                 0.5780 |                1.4680 |
| TMYx      | detached    | shade_off     | hours_gt26_night |        0.9531 |                 0.9844 |               11.0000 |
| TMYx      | detached    | vent_rotation | T_op_peak        |        0.0057 |                 0.0233 |                0.0890 |
| TMYx      | detached    | vent_rotation | hours_gt26_night |       -0.0156 |                 0.1094 |                2.0000 |
| TMYx      | semi        | attic_party   | T_op_peak        |        0.0014 |                 0.0184 |                0.0800 |
| TMYx      | semi        | attic_party   | hours_gt26_night |        0.0000 |                 0.1562 |                1.0000 |
| TMYx      | semi        | combined      | T_op_peak        |       -0.4628 |                 0.4628 |                0.7350 |
| TMYx      | semi        | combined      | hours_gt26_night |       -0.2969 |                 0.6406 |                4.0000 |
| TMYx      | semi        | interfloor    | T_op_peak        |       -0.4239 |                 0.4239 |                0.7340 |
| TMYx      | semi        | interfloor    | hours_gt26_night |        0.2969 |                 0.7031 |               13.0000 |
| TMYx      | semi        | shade_off     | T_op_peak        |        0.4350 |                 0.4350 |                1.4900 |
| TMYx      | semi        | shade_off     | hours_gt26_night |        1.0469 |                 1.0469 |               12.0000 |
| TMYx      | semi        | vent_rotation | T_op_peak        |       -0.0236 |                 0.0635 |                0.4330 |
| TMYx      | semi        | vent_rotation | hours_gt26_night |       -0.4688 |                 0.6250 |                4.0000 |

## Combined Correction: Stress Cohort

| weather   | archetype   | target           |   n |   mean_change |   mean_absolute_change |   max_absolute_change |
|:----------|:------------|:-----------------|----:|--------------:|-----------------------:|----------------------:|
| DSY1      | detached    | He_worst         |  16 |       -0.2723 |                 0.2723 |                0.6536 |
| DSY1      | detached    | We_max_worst     |  16 |       -4.8750 |                 4.8750 |                8.0000 |
| DSY1      | detached    | T_op_peak        |  16 |       -0.5549 |                 0.5549 |                0.6820 |
| DSY1      | detached    | hours_gt26_night |  16 |        7.5625 |                 7.9375 |               27.0000 |
| DSY1      | detached    | heat_kWh_m2      |  16 |        5.2874 |                 8.1389 |               34.2213 |
| DSY1      | semi        | He_worst         |  16 |       -0.2485 |                 0.2485 |                0.5175 |
| DSY1      | semi        | We_max_worst     |  16 |       -5.9375 |                 5.9375 |               11.0000 |
| DSY1      | semi        | T_op_peak        |  16 |       -0.6892 |                 0.6892 |                1.2460 |
| DSY1      | semi        | hours_gt26_night |  16 |        3.5000 |                 6.1250 |               16.0000 |
| DSY1      | semi        | heat_kWh_m2      |  16 |       -7.8470 |                 8.4962 |               57.3936 |
| TMYx      | detached    | He_worst         |  16 |       -0.2145 |                 0.2145 |                0.4902 |
| TMYx      | detached    | We_max_worst     |  16 |       -3.0625 |                 3.0625 |                6.0000 |
| TMYx      | detached    | T_op_peak        |  16 |       -0.4644 |                 0.4644 |                0.6580 |
| TMYx      | detached    | hours_gt26_night |  16 |        2.7500 |                 3.2500 |               11.0000 |
| TMYx      | detached    | heat_kWh_m2      |  16 |        5.8733 |                10.1480 |               37.4210 |
| TMYx      | semi        | He_worst         |  16 |       -0.2672 |                 0.2672 |                0.6809 |
| TMYx      | semi        | We_max_worst     |  16 |       -3.0625 |                 3.0625 |                6.0000 |
| TMYx      | semi        | T_op_peak        |  16 |       -0.4745 |                 0.4745 |                0.7670 |
| TMYx      | semi        | hours_gt26_night |  16 |        0.4375 |                 3.8125 |               13.0000 |
| TMYx      | semi        | heat_kWh_m2      |  16 |       -1.8576 |                 8.6190 |               25.9995 |

## Combined Threshold Changes: Random Cohort

| weather   | archetype   | flag                         |   n |   old_count |   new_count |   newly_exceeding |   no_longer_exceeding |
|:----------|:------------|:-----------------------------|----:|------------:|------------:|------------------:|----------------------:|
| DSY1      | detached    | C1_gt3                       |  64 |           0 |           0 |                 0 |                     0 |
| DSY1      | detached    | C2_gt6                       |  64 |          64 |          64 |                 0 |                     0 |
| DSY1      | detached    | C3_nonzero                   |  64 |          64 |          63 |                 0 |                     1 |
| DSY1      | detached    | night_summer_gt32            |  64 |           2 |           2 |                 0 |                     0 |
| DSY1      | detached    | night_annual_gt32            |  64 |           3 |           2 |                 0 |                     1 |
| DSY1      | detached    | same_zone_two_of_three_proxy |  64 |          64 |          63 |                 0 |                     1 |
| DSY1      | semi        | C1_gt3                       |  64 |           0 |           0 |                 0 |                     0 |
| DSY1      | semi        | C2_gt6                       |  64 |          64 |          64 |                 0 |                     0 |
| DSY1      | semi        | C3_nonzero                   |  64 |          63 |          55 |                 0 |                     8 |
| DSY1      | semi        | night_summer_gt32            |  64 |           1 |           1 |                 0 |                     0 |
| DSY1      | semi        | night_annual_gt32            |  64 |           2 |           1 |                 0 |                     1 |
| DSY1      | semi        | same_zone_two_of_three_proxy |  64 |          63 |          55 |                 0 |                     8 |
| TMYx      | detached    | C1_gt3                       |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | detached    | C2_gt6                       |  64 |          37 |          26 |                 0 |                    11 |
| TMYx      | detached    | C3_nonzero                   |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | detached    | night_summer_gt32            |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | detached    | night_annual_gt32            |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | detached    | same_zone_two_of_three_proxy |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | semi        | C1_gt3                       |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | semi        | C2_gt6                       |  64 |          29 |          13 |                 0 |                    16 |
| TMYx      | semi        | C3_nonzero                   |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | semi        | night_summer_gt32            |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | semi        | night_annual_gt32            |  64 |           0 |           0 |                 0 |                     0 |
| TMYx      | semi        | same_zone_two_of_three_proxy |  64 |           0 |           0 |                 0 |                     0 |

## Files

- `results/change_summary.csv`: all target differences by variant/cohort.
- `results/paired_changes.csv`: per-building paired targets and changes.
- `results/threshold_changes.csv`: old/new proxy counts and both crossing directions.
- `results/archetype_contrasts.csv`: matched semi-minus-detached differences.
- `inputs/idf_change_log.json`: every modified IDF field.
- `figures/variant_effects_random.png` and `figures/combined_random_parity.png`.

Original manuscripts, model checkpoints and result tables remain unchanged. Decisions about full reruns and paper updates require reviewing these pilot differences.
