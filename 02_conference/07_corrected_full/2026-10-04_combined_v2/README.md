# Corrected Full Experiment: Combined V2

This is an isolated replacement experiment, not an overwrite of legacy results.
The original dissertation and conference manuscripts, datasets and trained models
remain preserved. Do not combine tables from the legacy and corrected models.

## Frozen Physical Specification

- Opening wind bearings rotate with building and zone north.
- Only the intermediate ground/first-floor interface loses the sampled loft
  insulation; the original 100 mm concrete layer remains. Loft insulation remains
  sampled at the first-floor/attic interface.
- The semi-detached east attic gable becomes adiabatic/NoSun/NoWind, representing
  full-height attachment.
- Automatic interior shades controlled at 26.5 deg C remain enabled. Shade-off
  was a diagnostic experiment and is not included in this corrected dataset.
- Everything else remains fixed, including schedules, proxy metrics, 14 input
  ranges, original 2,000-case LHS matrices, and semi Kiva exposed fraction 0.75.

These corrections improve internal modelling consistency; they are not external
validation or proof of realism of the simplified constructions/operation.

## Workflow and Locations

1. `inputs/`: all 4,000 corrected IDFs, exact changed-field log, original LHS
   samples and original comparison metrics.
2. `backup/`: protected-source hashes and reference to the independently
   verified original-input ZIP in the preceding sensitivity experiment.
3. `weather/`: local copied weather. Licensed DSY files must not be published.
4. `frozen_code/`: snapshot of the original metric and model-evaluation code.
5. `datasets/TMYx/` and `datasets/DSY1/`: corrected hourly runs, audited training
   tables and independent corrected-model evaluation outputs.
6. `figures/` and `reports/`: corrected results, old-versus-new comparisons and
   explicitly versioned interpretation, not silently refreshed legacy figures.

Eight thousand cases cover two weather files, two archetypes and 2,000 paired
building vectors. The 320 successful combined sensitivity cases are reused only
after IDF, weather and output hashes match; 7,680 cases are newly simulated.
Every output is recomputed by both target implementations and re-audited before
training. EnergyPlus subprocesses use individual working directories.

Model evaluation retains five original split assignments and six candidate
configurations per family, selected solely by normalized validation loss. This
is 180 pipeline trials per weather, not equal runtime or independent confidence
intervals. C3 remains a diagnostic, not a sixth trained target.

Existing Word manuscripts and reviewer replies are not automatically made valid
by these runs. They require a separate, complete numerical and narrative update
using the corrected reports, figures and limitations.
