# Executed model evaluation protocol

## Data and scope

Use the unchanged 2,000 successful samples per archetype and five original targets. The hourly audit reproduces all five targets and confirms that an occupied-hours mask does not alter C1 under the implemented schedules. Annual night hours are a separate diagnostic, not silently substituted for the summer target. No DSY data are included.

## Search and evaluation

1. Use split seeds 42, 123, 202, 340 and 567. Each seed creates 1,400 training, 300 validation and 300 test records. The three algorithms receive identical records within each archetype/split.
2. Use six configurations per family: the original configuration plus five candidates sampled reproducibly using search seed 20260917. Search spaces and actual candidates are saved in `evaluation/protocol.json`.
3. Score every candidate by the mean, across five targets, of validation MSE divided by that target's training variance. Select one joint configuration per family/split, not the best test-set result. This also prevents the large numerical scale of heating from dominating selection.
4. RF and XGBoost each train five independent regressors under that candidate configuration. MLP trains one multi-output model. Six pipeline candidates is an equal configuration budget, not equal training time, estimator count or independent per-target searches. Report this distinction and the recorded runtimes.
5. Fit MLP scalers on training rows only. Use CPU PyTorch, Adam, up to 300 epochs, patience 30, ReduceLROnPlateau patience 10/factor 0.5/minimum lr 1e-5, retaining the best validation checkpoint. Architecture, dropout, learning rate, weight decay and batch size are searched. Validation participates in early stopping and selection; test does not.
6. Evaluate selected models without refitting on test data. Report test R2, MAE, RMSE and signed bias for every target; show mean and sample SD across splits, plus paired R2 differences and win counts. Retain per-run split assignments and predictions.

The revised search comprises 180 pipeline candidate evaluations: two archetypes times five seeds times three families times six candidates. Search is deliberately modest, not exhaustive. Repeated splits overlap, so SD is descriptive, not an independent-sample confidence interval or significance test. The original dataset/test split has been examined before this revision; the new experiment is not a previously unseen external validation.

## Night-time diagnostics

- Report zero and nonzero prevalence, all-zero and training-mean baselines, subgroup MAE/RMSE/bias and sample counts.
- Define the high tail using the 90th percentile of positive TRAINING values, then evaluate held-out test values above that cut-off.
- Report the >32h subgroup count and errors, without claiming reliable rare-event compliance classification.
- Treat the regressor output as a continuous score for any nonzero summer overheating. Select its decision cut-off only on validation balanced accuracy; report test precision/recall/F1, balanced accuracy, AUROC, average precision and confusion counts. Scores are not calibrated probabilities.
- Retain negative predictions for honest comparison; no post-hoc clipping or rounding.

## Interpretation

Compute exact XGBoost TreeSHAP contributions using the native `pred_contribs` interface and verify their sum against predictions. Report mean absolute values, mean/SD across splits, rank ranges and a fixed split-42 beeswarm. Do not pick the most persuasive split after seeing results.

For XGBoost and MLP, independently calculate held-out permutation importance using five permutations per feature. Use increase in MSE normalized by training variance; compare Spearman ranks and top-three overlap per target and split. This compares model reliance, not causal effects, and does not claim to be MLP SHAP.

## Re-run

From `formal model file/script/` in a compatible Python environment:

```bash
python revision_metric_audit.py --workers 4
python test_revision_metrics.py
python revision_model_eval.py --workers 3
python revision_report.py
python revision_manuscript.py
```

Use `--resume` only with an unchanged protocol after an interrupted evaluation. All generated files are under `output/reviewer_revision/`. Canonical original results and model artifacts are preserved. The original notebook's saved cell outputs remain historical; the revision reports, not those saved images, describe the new experiment.
