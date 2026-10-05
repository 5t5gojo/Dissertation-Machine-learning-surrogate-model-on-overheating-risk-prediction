# Rounded C1 Retraining

This isolated experiment uses the completed corrected V2 temperature-rounding
audit. No EnergyPlus simulations are run and no old model or result is replaced.

Only the `He_worst` training target changes. C3 and same-zone joint flags are
updated as diagnostics. All 14 features and the other four training targets keep
their original CSV values. C1 retains the original four-decimal storage precision.

The original five matched 1400/300/300 splits and six candidate configurations per
family are reused. RF and XGBoost fit one regressor per target; MLP is multi-output.
Joint validation-loss selection is rerun for every family. This totals 360
candidate pipeline evaluations across both weather datasets, followed by 90,000
held-out predictions and 300 trained-model metric-row checks. Configuration count
does not imply equal runtime or estimator count.

Start with `status.json` for progress. Training logs are in
`logs/training_TMYx.log` and `logs/training_DSY1.log`. A `complete.json` file is
created only after both evaluations, model reload checks and source-preservation
checks succeed. The final summary will be `reports/RESULTS_SUMMARY.md`.

Training is background work; keep the computer awake until it completes.
Manuscripts and publication figures are not automatically updated by this task.

Entry points, from this directory:

```sh
python -B scripts/prepare.py
python -B -u scripts/rounded_pipeline.py --workers-per-weather 3
```

Preparation refuses to overwrite existing datasets. A resumed training run must
match the frozen protocol and input hashes. Comparisons of old and new C1 model
accuracy use different targets and must not be described as direct improvements.
