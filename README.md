# Machine Learning Surrogate Models for Predicting Summertime Overheating Risk in UK Detached and Semi-Detached Dwellings

## Latest Conference Results

The latest evaluated dataset is **corrected V2 with rounded C1**, dated 2026-10-05.
Start with [the rounded-training summary](02_conference/09_rounded_training/2026-10-05_corrected_v2/reports/RESULTS_SUMMARY.md).
It covers 8,000 existing corrected simulations across TMYx/DSY1 and detached/semi-detached houses,
with five matched splits and six candidate configurations per model family.
Only the C1 training target changed in this step; C3 and same-zone flags are diagnostics.
These are simulation-based screening proxies, not formal compliance or physical validation.

- [Metric-rounding audit](02_conference/08_metric_rounding/2026-10-05_corrected_v2/FINDINGS_zh.md).
- [Corrected physical-model experiment](02_conference/07_corrected_full/2026-10-04_combined_v2/README.md).
- [Conference experiment navigation](02_conference/README.md).

Earlier experiment folders and the original dissertation results are retained as historical
evidence. Their metric definitions and model scores must not be mixed with the latest results.

## Publication Layout

- [Dissertation](01_dissertation/README.md): original-workflow entry points; manuscripts remain local.
- [Conference paper](02_conference/README.md): versioned experiments, derived data and reports.
- `formal model file/` remains the shared executable workflow. Original paths are preserved; revision outputs are accessed through compatibility links to `02_conference/`.
- Folder links must be resolved when preparing a standalone supplementary archive. Local manuscript links are not downloadable paper releases.

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
- `formal model file/script/work.ipynb`
  - Preserved sampling/setup notebook for the original dissertation workflow; not the rounded-C1 training entry point.
- `formal model file/script/batch_runner_v7.py`
  - Generates LHS samples, substitutes IDF placeholders, runs EnergyPlus and post-processes outputs.
- `formal model file/script/03_surrogate_v7.ipynb`
  - Trains RF, XGBoost and MLP surrogate models and exports intermediate result tables.
- `formal model file/script/figure_config.py`
  - Defines target ordering, labels, paths and figure settings.
- `formal model file/script/make_publication_figures.py`
  - Generates publication figures from fixed CSV outputs.

## Original Dissertation Outputs
- `formal model file/output/results/results_v7.csv`
- `formal model file/output/results/results_v7_semi.csv`
- `formal model file/output/results/model_performance.csv`
- `formal model file/output/results/model_performance_semi.csv`
- `formal model file/output/figures/in_text/`
- `formal model file/output/figures/appendix/`

## Notes
- Current conference CSVs include predictions, performance summaries, selected configurations, split assignments, SHAP values and permutation comparisons under `02_conference/09_rounded_training/2026-10-05_corrected_v2/datasets/{TMYx,DSY1}/evaluation/`.
- Conference raw hourly runs, generated per-case IDFs and repeated-fit model binaries remain local. Code, input tables, protocols and derived results are included; source-preservation manifests also refer to excluded local files. A fresh clone is not a complete simulation cache and cannot pass every local reload/hash check without restoring or regenerating those files.
- Licensed CIBSE weather files are excluded from every conference experiment directory. DSY reproduction requires a separately obtained licensed file. The original public TMYx EPW remains included.
- Word/PDF manuscripts, reviewer correspondence, supplementary ZIPs and submission snapshots remain local and are not uploaded by this update. This repository does not claim that older publication figures have been refreshed for rounded C1.
- Raw EnergyPlus run directories are intentionally excluded because they are large and can be regenerated from the runner, templates and LHS files.
- The London St James's Park TMYx 2009--2023 EPW file is included under `formal model file/weather file/` for reproducibility and is sourced from Climate.OneBuilding / OneBuilding weather data.
- `hours_C3_worst` is retained in the results as a diagnostic variable only. It is not used as a surrogate training target and should not appear in model-performance, parity, SHAP or RF-importance figures.
