"""Small regression tests for corrected-data comparisons and sparse diagnostics."""
import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frozen_code'))
from dsy_model_eval import night_diagnostics
from revision_common import TARGETS
from report import change_stats


class AnalysisChecks(unittest.TestCase):
    def test_case_pairing_uses_ids_not_position(self):
        old = pd.DataFrame({'archetype': ['detached'] * 2, 'run_id': ['a', 'b']})
        for metric in TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']:
            old[metric] = [10., 20.]
        new = old.iloc[::-1].copy()
        new.loc[new.run_id.eq('a'), TARGETS] += 2
        new.loc[new.run_id.eq('b'), TARGETS] -= 2
        pairs, summary = change_stats(old, new, ['archetype', 'run_id'])
        self.assertEqual(pairs.set_index('run_id').loc['a', 'delta_He_worst'], 2)
        row = summary.set_index('target').loc['He_worst']
        self.assertEqual(row.mean_change, 0)
        self.assertEqual(row.mean_absolute_change, 2)
        self.assertEqual(row.increased, 1)
        self.assertEqual(row.decreased, 1)

    def test_duplicate_case_ids_rejected(self):
        data = pd.DataFrame({'archetype': ['detached'] * 2, 'run_id': ['a', 'a']})
        for metric in TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']:
            data[metric] = [1., 2.]
        with self.assertRaises(pd.errors.MergeError):
            change_stats(data, data, ['archetype', 'run_id'])

    def test_single_class_is_not_perfect_discrimination(self):
        y = np.array([1., 2., 3., 4.])
        rows, event = night_diagnostics(y, y, y, y, y)
        self.assertEqual(event['status'], 'not_identifiable_single_class_validation')
        self.assertTrue(np.isnan(event['roc_auc']))
        self.assertTrue(np.isnan(event['balanced_accuracy']))
        empty = next(r for r in rows if r['subgroup'] == 'zero')
        self.assertEqual(empty['n'], 0)
        self.assertTrue(np.isnan(empty['RMSE']))

    def test_tail_cutoff_uses_training_not_test(self):
        ytr = np.array([0., 1., 2., 3., 4.])
        yval = np.array([0., 0., 2., 4.])
        test = np.array([0., 1., 4., 100.])
        rows, event = night_diagnostics(ytr, yval, yval, test, test)
        tail = next(r for r in rows if r['subgroup'] == 'positive_training_p90_tail')
        self.assertAlmostEqual(tail['tail_threshold'], 3.7)
        self.assertEqual(tail['n'], 2)
        self.assertEqual(tail['RMSE'], 0)
        self.assertEqual(event['status'], 'ok')

    def test_all_zero_training_handles_empty_positive_tail(self):
        y = np.zeros(4)
        rows, event = night_diagnostics(y, y, y, y, y)
        tail = next(r for r in rows if r['subgroup'] == 'positive_training_p90_tail')
        self.assertEqual(tail['n'], 0)
        self.assertTrue(np.isnan(tail['tail_threshold']))
        self.assertTrue(np.isnan(tail['MAE']))
        self.assertEqual(event['status'], 'not_identifiable_single_class_validation')


if __name__ == '__main__':
    unittest.main(verbosity=2)
