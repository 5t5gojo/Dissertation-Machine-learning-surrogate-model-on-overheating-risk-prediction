# Manuscript and Submission Update Checklist

The corrected V2 experiment is complete; this is NOT a declaration that the existing Word manuscript or submission ZIP has been updated.

## Methods and Model Definition

- Describe the corrected wind-opening bearings as local facade bearing plus building/zone rotation, modulo 360 degrees.
- Separate the occupied-storey interface (100 mm reinforced concrete only) from the loft interface (sampled insulation plus concrete). Do not state that sampled loft insulation also belongs between occupied storeys.
- State that the semi-detached attic east gable is adiabatic: the adjoining dwelling is assumed to extend to the full gable height.
- Disclose retained automatic interior shades, activated above 26.5 C zone air temperature, in addition to sampled exterior overhang depth.
- Retain the caveat that the semi Kiva exposed-perimeter fraction is fixed at 0.75, rather than derived separately for every sampled width/length.
- Do not claim occupancy/security-controlled window operation, formal TM52/TM59 compliance, or monitored physical validation.

## Results, Figures and Conclusions

- Update BOTH TMYx and DSY1 distributions, threshold-proxy counts, heating statistics and paired weather differences from corrected_simulation_coverage.csv and the per-weather datasets.
- Replace model comparison values with corrected_model_accuracy.csv: five overlapping splits, mean +/- SD, six configurations per family and validation-only selection. Do not reuse single-split legacy headlines.
- Replace every SHAP figure and ranking from corrected_shap_rankings.csv. Do not carry forward a legacy orientation or night-time hierarchy without checking the new table.
- In corrected V2, the semi-detached night-time XGBoost SHAP leader is window opening factor in BOTH weather datasets. The old statement that DSY1 makes g-value first in both archetypes no longer describes these corrected results. Separately, DSY1 permutation importance has g-value first for both XGBoost and MLP; do not suppress this method dependence.
- Separate XGBoost SHAP from MLP predictive accuracy. Use cross_model_importance_comparison.csv to report the actual degree of permutation-ranking agreement.
- Report sparse-night subgroup errors and single-class limitations; do not present undefined event discrimination as perfect performance.
- Keep the DSY1 experiment framed as separate training under a specified weather scenario, not frozen-model transfer or a controlled isolation of climate severity.

## Response Letter and Supplement

- Explain that a subsequent IDF audit led to three transparent modelling corrections; include the new-versus-legacy paired comparison rather than silently replacing numbers.
- Update all reviewer response references, table/figure numbers and supplementary data links in the same revision.
- Retain the old package for provenance. Label a new submission package corrected V2 and exclude licensed weather files from public distribution.
- Check final Word/PDF layout and conference requirements after coordinated text changes. No submission-format compliance is asserted by this simulation report.

## Evidence Location

- reports/START_HERE_corrected_full_results.md: numerical overview and remaining boundaries.
- reports/idf_verification.json: independent 4,000-IDF geometry, construction and control checks.
- datasets/<weather>/legacy_change_summary.csv: magnitude of all paired IDF-correction effects.
- datasets/<weather>/evaluation/verification.json: saved-model, split, selection, metric and SHAP checks.
- backup/original_backup_reference.json: verified original archive location and checksum.
