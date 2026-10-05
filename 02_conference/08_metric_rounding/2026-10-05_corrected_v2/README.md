# Corrected V2 Temperature-Rounding Audit

This directory is separate from the completed corrected V2 experiment. It only
reads saved hourly outputs. It never launches EnergyPlus or trains models.

Source: `../../07_corrected_full/2026-10-04_combined_v2/`.

Run from this directory with a scientific Python environment:

```sh
python -B -m unittest -v test_rounding.py
python -B audit_rounding.py --workers 6
```

An existing output directory is never overwritten. Use `--output NEW_PATH` for
another audit. The source experiment cannot be used as an output directory.

The main comparison changes only C1/C3 temperature rounding. C2 remains fixed.
Nearest-integer, ties-to-even rounding is paired with a half-away-from-zero
sensitivity check. Occupancy, weather, running mean and same-zone joint logic
are held constant. This is not a formal compliance certification.

For the completed audit, start with `FINDINGS_zh.md` for the conclusions and
manuscript implications, or `results/REPORT.md` for the full method and tables.
The six result CSVs
retain per-case/per-zone data and transitions; verification and hash manifests
document complete coverage and preservation of source files.
