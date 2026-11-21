"""Build EnergyPlus inputs from the saved samples and, optionally, simulate them.

Examples
--------
Generate the 2,000 IDFs for one archetype without simulating::

    python src/simulate.py detached --output output/idfs_detached

Simulate (EnergyPlus 25.1 and a user-supplied weather file are required)::

    python src/simulate.py semi --output output/sim_semi \\
        --energyplus /path/to/energyplus --weather /path/to/weather.epw
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import pandas as pd

from common import ROOT, load_samples, sha256
from geometry import placeholder_values
from idf import apply_final_settings
from metrics import calculate, check_occupancy


def render(design: dict, archetype: str) -> str:
    """Complete simulation input for one sampled design."""
    text = (ROOT / "config" / "templates" / f"{archetype}.idf").read_text()
    for placeholder, value in placeholder_values(design).items():
        text = text.replace(placeholder, value)
    if re.search(r"@[\w/]+@", text):
        raise ValueError("Unresolved IDF placeholders")
    text = apply_final_settings(text, archetype)
    check_occupancy(text)
    return text


def run_energyplus(executable: Path, weather: Path, folder: Path, idf: Path) -> None:
    """Run one simulation and fail on any severe or fatal EnergyPlus error."""
    with (folder / "console.log").open("w") as log:
        subprocess.run(
            [str(executable), "-w", str(weather), "-d", str(folder), "-r", str(idf)],
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    errors = (folder / "eplusout.err").read_text()
    if "** Severe **" in errors or "**  Fatal  **" in errors:
        raise RuntimeError(f"EnergyPlus errors: {folder}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archetype", choices=["detached", "semi"])
    parser.add_argument("--output", type=Path, required=True, help="new folder to create")
    parser.add_argument("--energyplus", type=Path, help="EnergyPlus 25.1 executable")
    parser.add_argument("--weather", type=Path, help="EPW weather file")
    parser.add_argument("--limit", type=int, help="only the first N samples")
    args = parser.parse_args()

    if bool(args.energyplus) != bool(args.weather):
        parser.error("--energyplus and --weather must be given together")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    output = args.output.resolve()
    if output.exists():
        parser.error("--output must be a new folder; existing results are never overwritten")
    if output.is_relative_to(ROOT / "data") or output.is_relative_to(ROOT / "results"):
        parser.error("Do not write into the published data/ or results/ folders")

    samples = load_samples(args.archetype)
    if args.limit:
        samples = samples.head(args.limit)
    simulate = args.energyplus is not None
    if simulate:
        executable = args.energyplus.resolve(strict=True)
        weather = args.weather.resolve(strict=True)
        version = subprocess.check_output([str(executable), "--version"], text=True)
        if "25.1" not in version:
            parser.error("The recorded experiment used EnergyPlus 25.1")

    output.mkdir(parents=True)
    records = []
    for design in samples.to_dict("records"):
        folder = output / design["run_id"]
        folder.mkdir()
        idf = folder / "sim.idf"
        idf.write_text(render(design, args.archetype))
        if simulate:
            run_energyplus(executable, weather, folder, idf)
            targets = calculate(pd.read_csv(folder / "eplusout.csv"), design["width"], design["length"])
            records.append(design | targets | {"idf_sha256": sha256(idf), "weather_sha256": sha256(weather)})
            pd.DataFrame(records).to_csv(output / "results.csv", index=False)
        print(design["run_id"], flush=True)


if __name__ == "__main__":
    main()
