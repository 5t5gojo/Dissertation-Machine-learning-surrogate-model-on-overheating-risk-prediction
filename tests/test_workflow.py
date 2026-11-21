"""Fast regression tests: python -m unittest discover -s tests -v"""

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import FEATURES, ROOT, TARGETS, load_samples, read_json  # noqa: E402
from evaluation import night_diagnostics  # noqa: E402
from idf import parse  # noqa: E402
from metrics import calculate  # noqa: E402
from simulate import render  # noqa: E402

# SHA-256 of IDFs that were actually simulated for the published dataset.
SIMULATED_IDF_SHA256 = {
    ("detached", "run_0000"): "1b43650cb95183181500a2afc61f87312d1d509a504ce855987d306320a6cf80",
    ("detached", "run_1999"): "8a89c5bcc0eb218cfa75714aaa1f5b6ac406776ffa3a8b08ee4aaa19517434cc",
    ("semi", "run_0000"): "13f3813340826b9ac355e61fc32465edc2014b070dada062e5dd4bf2497b8e6c",
    ("semi", "run_1999"): "cdf10df2320eb008f1429a3c54f80556c3669d00701e604b69b7b855b067ade9",
}


class SimulationInputs(unittest.TestCase):
    def test_rendered_idf_is_byte_identical_to_simulated(self):
        for (archetype, run_id), digest in SIMULATED_IDF_SHA256.items():
            design = load_samples(archetype).set_index("run_id").loc[run_id].to_dict()
            text = render(design, archetype)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), digest, (archetype, run_id))

    def test_final_idf_settings(self):
        for archetype in ["detached", "semi"]:
            text = render(load_samples(archetype).iloc[0].to_dict(), archetype)
            self.assertNotIn("@", text)
            objects = [o["fields"] for o in parse(text)]
            by_name = {(o[0].lower(), o[1]): o for o in objects}
            for surface in ["Surface 6", "Surface 7"]:
                self.assertEqual(by_name["buildingsurface:detailed", surface][3], "Audit_Interfloor_RC_100mm")
            if archetype == "semi":
                self.assertEqual(by_name["buildingsurface:detailed", "Surface 16"][6], "Adiabatic")
            vents = [o for o in objects if o[0].lower() == "zoneventilation:windandstackopenarea"]
            self.assertEqual(len(vents), 8 if archetype == "detached" else 6)


class Targets(unittest.TestCase):
    def test_rounded_thresholds(self):
        """With outdoor 20 C the adaptive limit is 28.4 C; dT is rounded before thresholds."""
        time = pd.date_range("2025-01-01", periods=8760, freq="h")
        frame = pd.DataFrame({"Date/Time": time.astype(str), "Outdoor Drybulb": np.full(8760, 20.0)})
        for zone in ["101", "102"]:
            frame[f"{zone} Ideal Loads Supply Air Total Heating Energy"] = 0.0
        for difference, he, c3 in [(0.49, 0, 0), (0.51, 100, 0), (4.49, 100, 0), (4.51, 100, 3672)]:
            for zone in ["101", "102"]:
                frame[f"{zone} Operative Temperature"] = 28.4 + difference
            result = calculate(frame, 8.0, 10.0)
            self.assertEqual(result["He_worst"], he)
            self.assertEqual(result["hours_C3_worst"], c3)

    def test_single_class_event_detection_is_undefined(self):
        _, event = night_diagnostics(np.ones(20), np.ones(10), np.ones(10), np.ones(10), np.ones(10))
        self.assertEqual(event["status"], "not_identifiable_single_class_validation")
        self.assertTrue(np.isnan(event["roc_auc"]))


class Models(unittest.TestCase):
    def test_every_family_fits_and_predicts(self):
        from models import fit_model, predict

        candidates = read_json(ROOT / "config" / "training.json")["candidates"]
        rng = np.random.default_rng(42)
        x, y = rng.normal(size=(40, len(FEATURES))), rng.normal(size=(40, len(TARGETS)))
        for family, configs in candidates.items():
            config = dict(configs[0])
            if family in ["RF", "XGBoost"]:
                config["n_estimators"] = 2
            bundle, _ = fit_model(family, config, x[:30], y[:30], x[30:], y[30:], 42, 2)
            prediction = predict(bundle, x[30:])
            self.assertEqual(prediction.shape, (10, len(TARGETS)))
            self.assertTrue(np.isfinite(prediction).all())


if __name__ == "__main__":
    unittest.main()
