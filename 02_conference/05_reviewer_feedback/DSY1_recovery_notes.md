# DSY1 simulation aggregation recovery

## Cause

The original full-run collector stopped updating its aggregate CSV after 673 records because a worker raised PermissionError while deleting the nonessential EnergyPlus file eplusout.rvaudit. This exception occurred after the physical simulation and metric checks, outside the worker's protected simulation block. ThreadPoolExecutor waited for its remaining workers before surfacing the exception, so simulations continued while the aggregate appeared stalled.

This was a runner housekeeping defect, not evidence of an EnergyPlus model failure. The original runner exited with code 1. Its original protocol and hashes remain preserved; the code was fixed only after that process exited.

## Recovery actually performed

- The recovery process waited for the original simulation process to exit, avoiding concurrent writes.
- All 4000 saved IDFs were matched against baseline copies and protocol hashes.
- All hourly files were independently re-read, timestamp checked and metrics recomputed with both the audit and canonical implementation.
- EnergyPlus success, absence of severe/fatal errors, positive occupancy schedules and zero cooling were checked.
- Eight missing result.json checkpoints were rebuilt: detached run_0673, run_1146, run_1414, run_1759, run_1961; semi run_0703, run_0756, run_0903.
- Existing successful checkpoint output hashes and target values were verified. The stalled aggregate was preserved as results_before_recovery.csv.
- The full aggregate, paired comparison, summary, training datasets and completion marker were rebuilt only after all 4000 passed.
- No physical simulation was repeated. Timing for recovered checkpoints is left missing, not invented.

Evidence: `../03_data/weather_scenarios/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1/full/finalization.json`, finalization_errors.json (empty), finalization.log and completion.json.

## Fix and provenance

The runner now writes a successful checkpoint before optional cleanup. Cleanup OSError is recorded as a warning and does not invalidate scientific results. A regression test injecting PermissionError verifies that the checkpoint survives and the worker returns status=ok; all six runner tests pass.

The simulation protocol deliberately keeps the pre-fix runner hash, because that was the code used. The finalization manifest records the independent audit script hash. Do not rewrite either provenance record to pretend the simulation used the patched runner. A new weather experiment needs a new pilot; do not resume the already-completed full run with modified code.

Model evaluation is a separate process and is gated on successful independent finalization. Training keeps the original five output targets and matched splits; single-class night event metrics are marked not identifiable instead of perfect discrimination.
