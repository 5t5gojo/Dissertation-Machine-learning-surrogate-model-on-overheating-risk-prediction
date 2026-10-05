import json
import unittest
from pathlib import Path
import sys

from prepare import ROOT, SOURCE, AUDIT, UPDATED, rounded_record, read_csv


class PreparationTests(unittest.TestCase):
    def test_all_groups_match_rounding_audit(self):
        audit = {(r['weather'],r['archetype']):r for r in read_csv(AUDIT/'group_summary.csv')[1]}
        for r in json.loads((ROOT/'preparation.json').read_text())['group_checks']:
            expected = audit[(r['weather'],r['archetype'])]
            self.assertEqual(r['n'],2000)
            for name, column in [('C1_gt3','C1_rounded_count'),('C3_nonzero','C3_rounded_count'),('same_zone_joint','joint_rounded_count')]:
                self.assertEqual(r[name],int(expected[column]))

    def test_every_unmodified_csv_value_is_preserved(self):
        for weather in ['TMYx','DSY1']:
            fields, raw = read_csv(SOURCE/'datasets'/weather/'results.csv')
            new = read_csv(ROOT/'datasets'/weather/'results.csv')[1]
            self.assertEqual(len(raw),4000)
            self.assertEqual(len(new),4000)
            self.assertEqual([{k:r[k] for k in fields if k not in UPDATED} for r in raw],
                             [{k:r[k] for k in fields if k not in UPDATED} for r in new])

    def test_c1_target_is_rounded_audit_at_original_storage_precision(self):
        cases = {(r['weather'],r['archetype'],r['run_id']):r for r in read_csv(AUDIT/'case_comparison.csv')[1]}
        for weather in ['TMYx','DSY1']:
            for r in read_csv(ROOT/'datasets'/weather/'results.csv')[1]:
                expected=cases[(weather,r['archetype'],r['run_id'])]
                self.assertEqual(float(r['He_worst']),round(float(expected['He_rounded_pct']),4))

    def test_corrupt_hourly_provenance_is_rejected(self):
        row = read_csv(SOURCE/'datasets/TMYx/results.csv')[1][0]
        cases = read_csv(AUDIT/'case_comparison.csv')[1]
        c = next(r for r in cases if r['weather']=='TMYx' and r['archetype']==row['archetype'] and r['run_id']==row['run_id'])
        c = dict(c, source_csv_sha256='invalid')
        with self.assertRaises(ValueError):
            rounded_record(row,c,{})

    def test_evaluator_paths_and_versions(self):
        import train_rounded as t
        self.assertEqual(t.adapter.ROOT, ROOT)
        self.assertEqual(t.adapter.OLD,ROOT/'inputs/splits')
        original=json.loads((ROOT/'inputs/original_model_protocol.json').read_text())
        self.assertEqual(t.base.candidates(6),original['candidates'])
        self.assertEqual(t.base.SEEDS,original['seeds'])
        self.assertEqual({m:__import__(m).__version__ for m in original['versions']},original['versions'])


if __name__ == '__main__':
    unittest.main()
