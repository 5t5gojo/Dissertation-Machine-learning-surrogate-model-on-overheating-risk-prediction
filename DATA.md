# Data and Results

## Datasets

`data/{TMYx,DSY1}/{detached,semi}.csv` contains the final 2,000-row dataset for each weather/archetype combination. Numeric fields are copied without rounding or reformatting from the final experiment. Local paths and process bookkeeping are omitted.

`run_id` links a row to `data/samples/{archetype}.csv` and the corresponding saved partition in `data/splits/`. The same designs and partitions are used for both weather files.

The 14 inputs and their bounds are in `config/parameters.json`. Lengths and insulation thicknesses use metres, orientation uses degrees, window U-factor uses W/(m2 K), and ratios are dimensionless. `flowCoefficient` is the coefficient for EnergyPlus's FlowCoefficient infiltration model, not a measured constant airflow rate.

| Target | Meaning | Unit |
| --- | --- | --- |
| `He_worst` | Highest occupied-zone summer exceedance percentage, rounded temperature difference >=1 K | % |
| `We_max_worst` | Maximum stepped daily positive exceedance over occupied zones | K h |
| `T_op_peak` | Highest occupied-zone summer operative temperature | deg C |
| `hours_gt26_night` | Bedroom hours above 26 deg C, 22:00-07:00, May-September | h |
| `heat_kWh_m2` | Annual ideal heating demand per total occupied floor area | kWh/m2/year |

`hours_C3_worst`, `two_of_three_proxy_dwelling` and `hours_gt26_night_annual` are diagnostics, not model targets. Joint flags are evaluated within each zone before aggregation. All occupied schedules remain positive throughout the summer (3,672 hours). Temperature differences are rounded with NumPy `rint`; C1 uses >3%, C2 uses >6 K h, and C3 counts rounded differences >4 K. See `src/metrics.py` for the exact implementation and timestamp checks.

## Result Tables

Each weather folder in `results/` contains:

| File | Contents |
| --- | --- |
| `performance.csv` | R2, MAE, RMSE and bias by archetype, model, seed and target, including baselines |
| `performance_summary.csv` | Mean and sample SD across five splits |
| `predictions.csv` | Held-out predictions; key: archetype, seed, model, target, run_id |
| `search_trials.csv` | Six candidate configurations and validation loss per family/split |
| `night_subgroups.csv` | Zero, nonzero, training-positive P90 tail and >32 h subgroup errors |
| `night_event_detection.csv` | Nonzero-event diagnostics; undefined single-class results are NA |
| `shap_importance.csv` | XGBoost mean absolute SHAP values per split, in target units |
| `shap_mean_values_and_ranks.csv` | Aggregated SHAP values and rankings |
| `permutation_importance.csv` | Held-out normalized-MSE increases for XGBoost and MLP |
| `cross_model_importance_comparison.csv` | Cross-model permutation ranking comparison |

Test samples recur across the five splits; the prediction rows are not independent dwellings. The >32 h summer group is a diagnostic tail group, not a compliance label. SHAP and permutation importance measure different forms of predictive reliance, not causal retrofit benefits.

## Building Inputs

`config/templates/` contains substitution templates. Always use `src/simulate.py` (via `src/idf.py`), which applies the final ventilation bearing, occupied-floor slab and semi-detached attic party-wall settings after parameter substitution. The templates alone are not the final simulation IDFs. Automatic interior shading and the fixed semi-detached Kiva perimeter fraction are retained.

`config/training.json` records the exact candidate configurations, split seeds and main package versions used in the experiment. Package or hardware changes may affect refitted scores. The data and published output tables are checksummed in `config/checksums.json`; `src/verify.py` checks them.

## Figures

`figures/*.png` are drawn by `src/figures.py` from `results/` only.

## Models

`models/xgboost_seed42/{weather}_{archetype}_{target}.ubj` are XGBoost models (UBJSON format, XGBoost 3.0.5) refitted by `src/export_models.py` with the configuration selected on validation loss for split seed 42. They reproduce the published seed-42 XGBoost test predictions in `results/*/predictions.csv` (checked in `tests/`). Inputs are the 14 design columns in the order of `config/parameters.json`.

