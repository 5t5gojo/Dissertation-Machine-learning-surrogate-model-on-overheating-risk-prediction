# Completed verification

- Audited 4,000 generated IDFs and hourly CSVs; all statuses are successful.
- Reproduced all five canonical targets and the C3 diagnostic; all saved rounded differences are zero.
- Verified canonical data SHA256 values remain unchanged after the revision work.
- Confirmed detached and semi-detached use matching sampled feature vectors.
- Confirmed 180 trial records and six candidate pipelines per archetype/model/split.
- Confirmed selected candidates minimize saved validation scores, not test scores.
- Verified ten partitions, each with 1,400 train / 300 validation / 300 test rows; each partition is internally disjoint. Partitions across repeated seeds are allowed to overlap.
- Checked all 45,000 saved model-target test prediction records against canonical run IDs and target values.
- Independently recomputed all 150 trained-model R2/MAE/RMSE rows from saved predictions.
- Confirmed 140 feature/target/archetype rows in the complete mean-SHAP table.
- Five boundary tests pass: strict C2 threshold, same-zone joint flags, night-hour boundaries, strict 26 C threshold, missing-hour rejection and actual occupancy proof (some share a test case).
- All added Python scripts and original notebook code cells parse successfully; `git diff --check` passes.
- All nine final Word pages were rendered with the bundled LibreOffice renderer and visually inspected. Paired figures, captions, numeric tables and references fit; the initially overlapping beeswarm heading was removed and the final pairs display left/right as captioned.
- The original `p129v1.docx` SHA256 remains unchanged. Canonical original models and result CSVs were not replaced.

The source manuscript and simulated reference buildings have not received a fresh literature-wide or independent physical validation. These checks establish computational consistency and local artifact quality, not DSY validity, causal identification or regulatory compliance.
