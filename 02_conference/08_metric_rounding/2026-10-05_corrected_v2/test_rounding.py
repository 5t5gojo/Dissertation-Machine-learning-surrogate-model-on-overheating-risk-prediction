import unittest
import numpy as np
from audit_rounding import combine_zones, evaluate_zone


class RoundingTests(unittest.TestCase):
    def test_half_integer_boundaries(self):
        x = np.zeros(24)
        x[:8] = [.4999, .5, .5001, .9999, 1, 4, 4.5, 4.5001]
        r = evaluate_zone(x)
        self.assertEqual(r['C1_hours_raw'], 4)
        self.assertEqual(r['C1_hours_rounded'], 6)
        self.assertEqual(r['C1_hours_halfup'], 7)
        self.assertEqual(r['C3_hours_raw'], 2)
        self.assertEqual(r['C3_hours_rounded'], 1)
        self.assertEqual(r['C3_hours_halfup'], 2)
        self.assertEqual(r['ties_at_0_5'], 1)
        self.assertEqual(r['ties_at_4_5'], 1)

    def test_c1_strict_three_percent(self):
        x = np.zeros(2400)
        x[:72] = 1
        self.assertFalse(evaluate_zone(x)['C1_flag_raw'])
        x[72] = 1
        self.assertTrue(evaluate_zone(x)['C1_flag_raw'])

    def test_c2_strict_six_and_no_rerounding(self):
        x = np.zeros(24)
        x[0] = 6
        self.assertFalse(evaluate_zone(x)['C2_flag'])
        x[1] = 1
        r = evaluate_zone(x)
        self.assertTrue(r['C2_flag'])
        self.assertEqual(r['We_fixed'], 7)

    def test_same_zone_not_worst_metric_mix(self):
        c1_only = evaluate_zone(np.tile([1] + [0]*23, 153))
        c2_only_input = np.zeros(3672)
        c2_only_input[:7] = 1
        c2_only = evaluate_zone(c2_only_input)
        r = combine_zones([c1_only, c2_only])
        self.assertTrue(r['C1_flag_raw'])
        self.assertTrue(r['C2_flag'])
        self.assertFalse(r['joint_raw'])

    def test_joint_can_gain_or_lose(self):
        gain = evaluate_zone(np.full(3672, .8))
        self.assertFalse(gain['joint_raw'])
        self.assertTrue(gain['joint_rounded'])
        x = np.zeros(3672)
        x[:2] = 4.2
        loss = evaluate_zone(x)
        self.assertTrue(loss['joint_raw'])
        self.assertFalse(loss['joint_rounded'])

    def test_negative_and_zero(self):
        r = evaluate_zone(np.full(24, -.8))
        for mode in ['raw', 'rounded', 'halfup']:
            self.assertEqual(r[f'He_{mode}_pct'], 0)
            self.assertEqual(r[f'C3_hours_{mode}'], 0)
            self.assertFalse(r[f'joint_{mode}'])

    def test_invalid_hours_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_zone(np.zeros(23))
        with self.assertRaises(ValueError):
            evaluate_zone(np.full(24, np.nan))


if __name__ == '__main__':
    unittest.main()
