"""Small guard tests; no simulations or writes to production outputs."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import pandas as pd
import dsy_runner as runner
from dsy_runner import select_ids, weather_info, DEFAULT_WEATHER


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({'run_id': [f'run_{i:04d}' for i in range(100)]})
        for col in ('wwr', 'g_value', 'wof', 'orientation', 'u_windows'):
            self.frame[col] = range(100)

    def test_pilot_deterministic_and_contains_extremes(self):
        ids = select_ids(self.frame, 'pilot', 20)
        self.assertEqual(ids, select_ids(self.frame, 'pilot', 20))
        self.assertEqual(len(ids), 20)
        self.assertTrue({'run_0000', 'run_0099'} <= set(ids))

    def test_full_preserves_all_ids(self):
        self.assertEqual(select_ids(self.frame, 'full', 20), sorted(self.frame.run_id))

    def test_duplicate_and_unsafe_ids(self):
        for value in ('run_0001', '../outside'):
            changed = self.frame.copy()
            changed.loc[0, 'run_id'] = value
            with self.assertRaises(ValueError):
                select_ids(changed, 'pilot', 20)

    def test_invalid_pilot_size(self):
        with self.assertRaises(ValueError):
            select_ids(self.frame, 'pilot', 101)

    def test_actual_epw(self):
        info = weather_info(DEFAULT_WEATHER)
        self.assertEqual(info['hours'], 8760)
        self.assertEqual(info['max_drybulb_C'], 38.1)

    def test_cleanup_permission_error_keeps_successful_checkpoint(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'output/runs/detached/run_0000/sim.idf'
            src.parent.mkdir(parents=True)
            src.write_text('unchanged model')
            dest = root / 'experiment'
            folder = dest / 'runs/detached/run_0000'
            metrics = {t: 0.0 for t in runner.TARGETS + ['hours_C3_worst']}
            metrics['cooling_kWh'] = 0.0
            protocol = {'weather': {'sha256': 'test-weather'},
                        'source_idfs': {'detached/run_0000': runner.sha(src)}}
            def simulate(*args, **kwargs):
                (folder / 'eplusout.err').write_text('EnergyPlus Completed Successfully')
                (folder / 'eplusout.csv').write_text('test output')
                (folder / 'eplusout.rvaudit').write_text('keep on permission failure')
                return SimpleNamespace(returncode=0)
            unlink = Path.unlink
            def guarded_unlink(path, *args, **kwargs):
                if path.name == 'eplusout.rvaudit':
                    raise PermissionError('simulated cleanup permission failure')
                return unlink(path, *args, **kwargs)
            with patch.object(runner, 'ROOT', root), \
                 patch.object(runner.subprocess, 'run', side_effect=simulate), \
                 patch.object(runner.audit, 'occupancy_proof', return_value=.3), \
                 patch.object(runner.audit, 'calculate', return_value=metrics), \
                 patch.object(runner.baseline, 'compute_targets', return_value=metrics), \
                 patch.object(runner.pd, 'read_csv', return_value=pd.DataFrame()), \
                 patch.object(Path, 'unlink', guarded_unlink):
                result = runner.worker('detached', {'run_id':'run_0000','width':8,'length':9},
                                       dest, root / 'weather.epw', protocol)
            saved = json.loads((folder / 'result.json').read_text())
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(saved['status'], 'ok')
            self.assertEqual(len(saved['cleanup_warnings']), 1)
            self.assertTrue((folder / 'eplusout.rvaudit').exists())


if __name__ == '__main__':
    unittest.main()
