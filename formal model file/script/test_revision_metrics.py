"""Boundary tests for the supplementary metric audit."""
import unittest
import numpy as np
import pandas as pd
from revision_metric_audit import calculate, occupancy_proof
from revision_common import ROOT

def frame():
    r = pd.DataFrame({'Date/Time': pd.date_range('2025-01-01', periods=8760, freq='h').astype(str),
                      'Environment:Site Outdoor Air Drybulb Temperature': 20.})
    for z in ['101','102']:
        r[f'{z}:Zone Operative Temperature'] = 20.
        r[f'{z}:Zone Ideal Loads Supply Air Total Heating Energy'] = 0.
        r[f'{z}:Zone Ideal Loads Supply Air Total Cooling Energy'] = 0.
    return r

class MetricTests(unittest.TestCase):
    def test_same_zone_rule_and_strict_threshold(self):
        r=frame()
        start=120*24
        # A 4.1 K event triggers C3 but contributes only 4 to C2 in zone 101.
        r.loc[start,'101:Zone Operative Temperature']=28.4+4.1
        r.loc[start:start+5,'102:Zone Operative Temperature']=28.4+1.1
        a=calculate(r,8,10)
        self.assertEqual(a['We_102'],6)
        self.assertFalse(a['two_of_three_proxy_dwelling'])
        r.loc[start:start+6,'102:Zone Operative Temperature']=28.4+1.1
        a=calculate(r,8,10)
        self.assertEqual(a['We_102'],7)
        self.assertFalse(a['two_of_three_proxy_dwelling'])
        r.loc[start+1,'101:Zone Operative Temperature']=28.4+4.1
        self.assertTrue(calculate(r,8,10)['two_of_three_proxy_dwelling'])

    def test_start_timestamp_night_edges(self):
        r=frame()
        start=120*24
        for h in [6,7,21,22,23]:
            r.loc[start+h,'102:Zone Operative Temperature']=27.
        r.loc[22,'102:Zone Operative Temperature']=27.
        a=calculate(r,8,10)
        self.assertEqual(a['hours_gt26_night'],3)
        self.assertEqual(a['hours_gt26_night_annual'],4)
        self.assertEqual(a['summer_hours'],3672)
        self.assertEqual(a['summer_night_hours'],1377)

    def test_temperature_threshold_is_strict(self):
        r=frame()
        r.loc[120*24+22,'102:Zone Operative Temperature']=26.
        self.assertEqual(calculate(r,8,10)['hours_gt26_night'],0)

    def test_missing_hour_rejected(self):
        with self.assertRaises(AssertionError):
            calculate(frame().iloc[:-1],8,10)

    def test_actual_occupancy(self):
        for arch in ['detached','semi']:
            p=ROOT/'output/runs'/arch/'run_0000/sim.idf'
            self.assertEqual(occupancy_proof(p.read_text()),.3)

if __name__=='__main__':
    unittest.main()
