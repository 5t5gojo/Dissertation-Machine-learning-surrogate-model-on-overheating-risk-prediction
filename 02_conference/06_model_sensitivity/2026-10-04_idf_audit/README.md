# Isolated IDF Sensitivity Audit

This folder is a new experiment, not a replacement for the dissertation or
conference results. Original IDFs, source scripts, canonical CSVs, weather and
manuscripts are not edited. No trained models are overwritten or retrained here.

## Layout

- `backup/original_inputs.zip`: original templates, configuration, scripts,
  sampling/result tables, two weather files, manuscript snapshots and all 4,000
  distinct original building IDFs. DSY used the same IDFs; hashes are verified.
- `backup/source_hashes.json`: original-file hashes for preservation checks.
- `inputs/`: fixed sample list, original re-audited metrics, copied weather,
  variant IDFs and exact changed-field log.
- `runs/`: separate EnergyPlus runs by weather, variant, archetype and run ID.
- `results/`: execution checks and paired comparison CSVs.
- `reports/` and `figures/`: interpretation and comparisons produced after runs.
- `scripts/`: dedicated runner, tests and reporting code for this experiment.

The backup contains licensed CIBSE weather. Keep it local; do not upload this
directory or backup archive to a public repository.

## Design

The same 64 randomly selected building vectors plus 16 targeted stress cases
are used for both archetypes under TMYx and DSY1. Seed: 20261004. Stress cases
include observed output extremes and must not be pooled with the random cohort
to estimate rates. This is an initial sensitivity experiment, not a population
estimate, complete factorial design or external physical validation.

Five variants are compared against their original output, with only four
applicable to detached buildings:

1. `vent_rotation`: effective opening angle follows building/zone rotation.
2. `interfloor`: the intermediate floor retains the original 100 mm concrete
   slab but no longer contains the sampled loft-insulation layer. The
   bedroom/attic interface and its sampled insulation are unchanged.
3. `attic_party`: semi-detached east attic gable is adiabatic, NoSun, NoWind.
4. `combined`: the above three, or first two for detached; internal shades stay.
5. `shade_off`: an additional diagnostic, not a mandatory correction. Existing
   internal shade controls become AlwaysOff; external overhangs stay unchanged.

Three unmodified cases per weather/archetype provide 12 environmental controls.
All controls must reproduce saved targets before variant simulations proceed.
A further 18-run smoke test validates each variant before the full pilot.
The full pilot is 1,440 variant runs (including the 18 smoke cases), plus 12
controls: 1,452 unique simulations. The original 2,000-case datasets remain intact.

The semi-detached fixed Kiva exposed fraction remains 0.75. No other geometry,
ventilation temperature controls, schedules, target definitions or weather
changes occur within a paired comparison. Full-height party wall and concrete
intermediate floor are explicit test assumptions, not validated constructions.

## Execution

Use the project's Anaconda Python environment (EnergyPlus 25.1 is required).
Run `scripts/test_sensitivity.py` first. Then execute the stages of
`scripts/run_sensitivity.py`: `prepare`, `controls`, `smoke`, `full`.
`prepare` refuses to overwrite an existing experiment. Execution resumes only
successful outputs whose IDF and CSV hashes match. Failed runs require inspection.
The full stage requires passing controls and smoke tests. Default: 8 workers.

The initial run had one ReadVarsESO `readvars.audit` race caused by a shared
working directory. It was not silently dropped: the initial execution version,
protocol, aggregate results and failed run are preserved under `backup/`.
The runner now uses each run's own working directory. `scripts/recover_csv_race.py`
documents the exact recovery; all successful initial outputs are retained.
The protocol records both execution versions. No scientific input changed.

References for the changed EnergyPlus fields:

- Effective opening angle is independent of GlobalGeometryRules:
  https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-airflow.html#field-effective-angle
- Interior shade `AlwaysOff` control:
  https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-thermal-zone-description-geometry.html#field-shading-control-type
