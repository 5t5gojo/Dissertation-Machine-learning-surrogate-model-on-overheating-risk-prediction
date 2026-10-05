# Non-DSY reviewer revision

This directory contains a separate revision experiment based on the canonical local project at `/Users/hlbao/Projects/dissertation`. It does not use the old OneDrive project. Original simulation targets, trained artifacts and published results are preserved.

## Start here

- `paper/p129v1_revised_no_DSY.docx`: revised conference manuscript, generated from the supplied paper without replacing the original.
- `reports/results_summary.md`: repeated model performance and diagnostic results.
- `reports/metric_audit.md`: metric definitions, exact discrepancies and scope decisions.
- `reports/response_to_reviewers.md`: point-by-point reply draft with evidence paths relative to this directory.
- `reports/reviewer_checklist.md`: completed work and limitations still outstanding.
- `reports/model_eval_plan.md`: executed search and repeated-evaluation protocol.
- `reports/dsy_plan.md`: explicit deferred scope.

## Evidence

- `audit/`: all 4,000 hourly audit records, strict-threshold summaries, C3 cases and hashes.
- `evaluation/`: 180 candidate search records, 10 split assignments, selected models, predictions, subgroup/event diagnostics, permutation comparisons, SHAP values/ranks and summary tables.
- `figures/`: paired archetype SHAP, full beeswarms, repeated performance, night errors and summer/annual comparison, in PNG and vector PDF.

The original saved notebook outputs document the earlier experiment. Use this directory's results for the revised paper; do not mix revised means/ranks with old single-split scores. The new experiment does not train a surrogate for annual night hours. It validates the original summer target and separately audits the annual diagnostic.

The new outputs and manuscript are local only. No Git commit or push was performed for this revision. Supply the relevant tables and figures as supplementary material with the revised paper; do not claim they are already published online.

No DSY simulation, monitored validation, reference-building benchmark or controlled causal ablation was performed. These limitations remain visible in the revised abstract/discussion and reviewer response.
