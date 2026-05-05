# Machine Learning Surrogate Models for Predicting Summertime Overheating Risk in UK Detached and Semi-Detached Dwellings
This repository contains the reproducible modelling workflow, simulation outputs, trained surrogate artefacts and publication figures for a UCL undergraduate dissertation on overheating-risk surrogate modelling.

The final dissertation PDF is submitted separately through the university submission system. This repository is intended to document the computational workflow and supporting outputs.

## Repository structure
- `formal model file/`
  - EnergyPlus IDF templates
  - parameter configuration files
  - Python batch runner
  - surrogate-training notebook
  - publication-figure scripts
  - canonical result tables
  - trained model artefacts
  - final in-text and appendix figures

## Active workflow files
- `formal model file/script/batch_runner_v7.py`
  - Generates LHS samples, substitutes IDF placeholders, runs EnergyPlus and post-processes outputs.
- `formal model file/script/03_surrogate_v7.ipynb`
  - Trains RF, XGBoost and MLP surrogate models and exports intermediate result tables.
- `formal model file/script/figure_config.py`
  - Defines target ordering, labels, paths and figure settings.
- `formal model file/script/make_publication_figures.py`
  - Generates publication figures from fixed CSV outputs.

## Canonical outputs
- `formal model file/output/results/results_v7.csv`
- `formal model file/output/results/results_v7_semi.csv`
- `formal model file/output/results/model_performance.csv`
- `formal model file/output/results/model_performance_semi.csv`
- `formal model file/output/figures/in_text/`
- `formal model file/output/figures/appendix/`

## Notes
- Raw EnergyPlus run directories are intentionally excluded because they are large and can be regenerated from the runner, templates and LHS files.
- The London St James's Park TMYx 2009--2023 EPW file is included under `formal model file/weather file/` for reproducibility and is sourced from Climate.OneBuilding / OneBuilding weather data.
- `hours_C3_worst` is retained in the results as a diagnostic variable only. It is not used as a surrogate training target and should not appear in model-performance, parity, SHAP or RF-importance figures.
