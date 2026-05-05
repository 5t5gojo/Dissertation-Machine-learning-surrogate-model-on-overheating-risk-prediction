# Formal Model Workspace Structure
This directory is the source of truth for the EnergyPlus-surrogate modelling workflow.

## Active code
- `script/batch_runner_v7.py`
  - LHS generation, IDF substitution, EnergyPlus execution and target post-processing.
- `script/03_surrogate_v7.ipynb`
  - Surrogate training, evaluation and export of fixed intermediate CSV files.
- `script/figure_config.py`
  - Target ordering, labels, paths and plotting configuration.
- `script/make_publication_figures.py`
  - Final publication figure generation.

## EnergyPlus templates and configuration
- `detachedhouse0.idf`
- `semidetached_template.idf`
- `parameter_config_v7.json`
- `parameter_config_v7_semi.json`
- `weather file/GBR_ENG_London.Wea.Ctr-St.James.Park.037700_TMYx.2009-2023.epw`

## Active outputs
- `output/lhs/`
  - LHS sample matrices and metadata.
- `output/results/`
  - Canonical simulation results, model-performance tables and fixed intermediate CSV files for plotting.
- `output/figures/in_text/`
  - Figures intended for the dissertation main text.
- `output/figures/appendix/`
  - Supporting figures retained for appendix evidence.
- `output/models/detached/`
  - Detached surrogate model artefacts.
- `output/models/semi/`
  - Semi-detached surrogate model artefacts.

## Excluded from Git
Raw EnergyPlus run directories are excluded because they are large and can be regenerated. Archive and legacy files are also excluded to keep the repository focused on the final workflow.
