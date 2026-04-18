# Dissertation Repository

UCL undergraduate dissertation project:

`Machine Learning Surrogate Models for Predicting Summertime Overheating Risk in UK Residential Buildings`

## Main directories

- `formal model file/`
  - Active EnergyPlus templates, runner, results, figures, and trained surrogate outputs.
- `latex_project/`
  - Dissertation writing assets.

## Active workflow files

- `formal model file/script/batch_runner_v7.py`
- `formal model file/script/03_surrogate_v7.ipynb`
- `formal model file/script/figure_config.py`
- `formal model file/script/make_publication_figures.py`

## Canonical outputs

- `formal model file/output/results/results_v7.csv`
- `formal model file/output/results/results_v7_semi.csv`
- `formal model file/output/results/model_performance.csv`
- `formal model file/output/results/model_performance_semi.csv`
- `formal model file/output/figures/in_text/`
- `formal model file/output/figures/appendix/`

## Notes

- Raw EnergyPlus run directories are intentionally excluded from Git because they are large.
- The active EPW weather file is stored under `formal model file/weather file/`.
- `hours_C3_worst` is retained in results as a diagnostic variable, not as a surrogate training target.
