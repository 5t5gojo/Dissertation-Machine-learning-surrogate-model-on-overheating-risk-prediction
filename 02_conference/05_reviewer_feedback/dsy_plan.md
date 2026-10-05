# DSY1 experiment: current scope (2026-10-03)

## Latest status

Full DSY1 simulation and independent recovery audit are complete: 4000/4000 cases passed, no physical simulations repeated. See `DSY1_recovery_notes.md` for the housekeeping PermissionError and recovery of eight checkpoints. The paired five-split model evaluation is also complete: 180 candidates and 45000 held-out prediction records, independently verified against the original partitions and recomputed metrics. See `DSY1_results_summary.md` for results and new figures. Launch-time notes below are experiment history, not current pending work. Word manuscript integration remains outstanding.

| Full-dataset diagnostic | Detached n=2000 | Semi n=2000 |
| --- | ---: | ---: |
| C1 proxy >3% | 28 | 8 |
| C2 stepped proxy >6 | 2000 | 2000 |
| Any C3 proxy hours | 1999 | 1994 |
| Same-zone two-of-three proxy flag | 1999 | 1994 |
| Zero summer night exceedance | 0 | 0 |
| Summer night >32 hours | 64 | 39 |
| Annual night >32 hours | 87 | 64 |
| Highest simulated summer peak (C) | 36.433 | 36.006 |

The DSY case activates the formerly sparse responses but nearly saturates C2/C3 proxy flags. Continuous severity and regression errors remain important; these are not measured-stock prevalence estimates or formal compliance outcomes.

The previous lack of a DSY file is resolved. The September no-DSY manuscript and reviewer response are preserved as historical drafts, not yet rewritten with full DSY results.

## Weather selected

- Local source: `CIBSE_weather_files_z1/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1.epw` under the project root.
- Header: Z1, 2030s (2019-2039), RCP 8.5, 50th probability percentile, v1.1.
- SHA256: `f31a17333556b5e7ac80078ae88c99f08af5269d75a4603c4f0b36336349361c`.
- 8760 ordered hourly records, maximum dry-bulb 38.1 C.
- EPW location: 51.5622, -0.414512, 33 m. This differs from the St James's Park baseline. Describe a paired building/weather-scenario comparison, not an isolated effect of weather-year severity.
- Licensed EPWs and ZIP are ignored by Git. Do not redistribute without permission.

## Completed pilot

Both archetypes used the same 20 original run IDs. Selection covers extrema of WWR, g-value, opening factor, orientation and window U-factor, then reproducible random cases (seed 20261003). This is not a prevalence sample.

- 40/40 passed, zero severe/fatal errors.
- Original generated IDFs copied byte-for-byte, not regenerated.
- Original 2025 simulation calendar retained, preserving occupancy weekdays. The scenario period does not change the IDF calendar; weather is not treated as actual.
- 8760 beginning-of-interval output hours, 3672 summer hours, 1377 summer-night hours and 3285 annual-night hours checked in each case.
- Independent audit reproduces the runner's targets at saved precision.
- Zero cooling energy throughout; original heating remains enabled, so this is not a formal free-running compliance assessment.
- Baseline LHS/result hashes unchanged.

| Diagnostic | Detached n=20 | Semi n=20 |
| --- | ---: | ---: |
| C1 proxy >3% | 1 | 1 |
| C2 stepped proxy >6 | 20 | 20 |
| Any C3 proxy hours | 20 | 20 |
| Same-zone two-of-three proxy flag | 20 | 20 |
| Zero summer night exceedance | 0 | 0 |
| Summer night >32 hours | 2 | 1 |
| Annual night >32 hours | 3 | 1 |
| Highest simulated summer peak (C) | 36.010 | 35.379 |

Warnings were inspected: EnergyPlus uses the EPW location instead of IDF Site:Location, a real geographic difference to disclose. Other warnings concern an unused construction, unused life-cycle cost resources, and ReadVarsESO overwriting native CSV output. Timestamp and metric checks passed on the final CSV actually used. IDFs were not changed to suppress warnings.

## Full run and progress

The 4000-case full run was launched on 2026-10-03 with eight workers after the passing pilot. This records launch, not completion. The output directory is:

```text
02_conference/03_data/weather_scenarios/
  Z1_DSY1_2030s_HIGH50_CIBSE_v1.1/
    pilot/  # 40 completed QA cases
    full/   # 2000 detached + 2000 semi
```

Each phase retains protocol.json, incremental results.csv, per-run result.json, original sim.idf, eplusout.csv, eplusout.err and logs. summary.csv, paired_comparison.csv and completion.json are written at the end. A missing completion marker means the run must not be described as finished.

```bash
# Read-only status, from the project root:
/opt/anaconda3/bin/python "formal model file/script/dsy_status.py"

# Only after the original process has stopped, if the full run is incomplete:
/opt/anaconda3/bin/python "formal model file/script/dsy_runner.py" --mode full --workers 8 --execute --resume
```

Resume checks weather, executable, scripts, LHS/results, original IDFs and successful saved output hashes. Do not start two executions against the same phase directory. Without --execute the runner performs read-only preflight.

## Next gates, not yet completed

1. Verify all 4000 cases and review additional warnings/failures; do not drop failed samples silently.
2. Audit full target coverage and paired changes, including proxy saturation and summer/annual night differences.
3. Keep the five-target comparison unchanged. Since C3 is active in the pilot, explicitly assess whether to add a supplementary C3 regression after the full audit. Annual-night regression is also a separate experiment.
4. Reuse five matched train/validation/test partitions and equal candidate-count budget for DSY-specific models. Frozen TMYx-model transfer performance is distinct from retraining on DSY.
5. Recompute DSY explanations, then update the conference paper and response with full results.
6. DSY2/DSY3 and matching CIBSE TRY are optional extensions, not claimed as tested. No 2050s/2080s work is planned in this phase.

The preserved September Word manuscript has not yet been integrated with DSY results. Physical reference-model validation and causal ablation remain outstanding. Current training completion is recorded separately in the evaluation markers and, when generated, DSY1_results_summary.md.
