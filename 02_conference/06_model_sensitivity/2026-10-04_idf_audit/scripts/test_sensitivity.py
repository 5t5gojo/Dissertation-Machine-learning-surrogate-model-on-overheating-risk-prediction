import unittest

import pandas as pd

from run_sensitivity import FORMAL, TARGETS, modify, parsed, original_frames, select_cases


def objects(text):
    return {(o['fields'][0].lower(), o['fields'][1]): o['fields']
            for o in parsed(text) if len(o['fields']) > 1}


class IDFChanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = {a: (FORMAL / 'output/runs' / a / 'run_0000/sim.idf').read_text()
                    for a in ['detached', 'semi']}

    def test_parser_preserves_empty_fields_and_comments(self):
        text = 'Thing, ! a comma, and ; comment\n Name, , 5;\n'
        self.assertEqual(parsed(text)[0]['fields'], ['Thing', 'Name', '', '5'])

    def test_controls_unchanged(self):
        for arch, text in self.text.items():
            new, changes = modify(text, 'control', arch)
            self.assertEqual(new, text)
            self.assertEqual(changes, [])

    def test_vent_bearings(self):
        for arch, text in self.text.items():
            new, changes = modify(text, 'vent_rotation', arch)
            old = objects(text)
            north = float(old['building', 'Building 1'][2])
            self.assertEqual(len(changes), 8 if arch == 'detached' else 6)
            for c in changes:
                self.assertEqual(c['field_index'], 6)
                self.assertAlmostEqual(float(c['new']), (float(c['old']) + north) % 360, places=9)
            self.assertEqual(objects(new)['building', 'Building 1'], old['building', 'Building 1'])

    def test_wrap_angle_and_zone_rotation(self):
        text = 'Building,B,350; Zone,Z,20;\n'
        text += ''.join(f'ZoneVentilation:WindandStackOpenArea,V{i},Z,1,,autocalculate,270;' for i in range(8))
        _, changes = modify(text, 'vent_rotation', 'detached')
        self.assertTrue(all(float(c['new']) == 280 for c in changes))

    def test_interfloor_only(self):
        for arch, text in self.text.items():
            new, changes = modify(text, 'interfloor', arch)
            old, changed = objects(text), objects(new)
            self.assertEqual({c['name'] for c in changes}, {'Surface 6', 'Surface 7'})
            for surface in ['Surface 12', 'Surface 13']:
                self.assertEqual(old['buildingsurface:detailed', surface], changed['buildingsurface:detailed', surface])
            self.assertEqual(changed['construction', 'Audit_Interfloor_RC_100mm'][2:], ['RC_Slab_100mm'])
            self.assertEqual(old['material', 'Roof Insulation'], changed['material', 'Roof Insulation'])

    def test_party_only(self):
        new, changes = modify(self.text['semi'], 'attic_party', 'semi')
        self.assertEqual(len(changes), 3)
        self.assertTrue(all(c['name'] == 'Surface 16' for c in changes))
        wall = objects(new)['buildingsurface:detailed', 'Surface 16']
        self.assertEqual(wall[6:10], ['Adiabatic', '', 'NoSun', 'NoWind'])
        with self.assertRaises(ValueError):
            modify(self.text['detached'], 'attic_party', 'detached')

    def test_combined_equals_sequential(self):
        for arch, text in self.text.items():
            first, _ = modify(text, 'vent_rotation', arch)
            second, _ = modify(first, 'interfloor', arch)
            if arch == 'semi':
                second, _ = modify(second, 'attic_party', arch)
            combined, _ = modify(text, 'combined', arch)
            self.assertEqual(objects(second), objects(combined))
            original_shades = [o for k, o in objects(text).items() if k[0] == 'windowshadingcontrol']
            new_shades = [o for k, o in objects(combined).items() if k[0] == 'windowshadingcontrol']
            self.assertEqual(original_shades, new_shades)

    def test_shade_off_only(self):
        for arch, text in self.text.items():
            _, changes = modify(text, 'shade_off', arch)
            self.assertEqual(len(changes), 2)
            self.assertTrue(all(c['new'] == 'AlwaysOff' and c['field_index'] == 6 for c in changes))

    def test_unknown_variant_rejected(self):
        with self.assertRaises(ValueError):
            modify(self.text['detached'], 'typo', 'detached')


class AnalysisChecks(unittest.TestCase):
    def test_random_cohort_independent_of_outputs(self):
        frames = original_frames()
        a = select_cases(frames)
        self.assertEqual(a.cohort.value_counts().to_dict(), {'random64': 64, 'stress16': 16})
        self.assertTrue(a.run_id.is_unique)
        for frame in frames.values():
            for target in TARGETS:
                frame[target] = -frame[target]
        b = select_cases(frames)
        self.assertEqual(set(a[a.cohort.eq('random64')].run_id), set(b[b.cohort.eq('random64')].run_id))

    def test_signed_cancellation_and_flag_directions(self):
        from report_sensitivity import summarize, flag_tables
        rows = []
        for rid, old, new in [('a', 0, 1), ('b', 1, 0)]:
            d = dict(weather='TMYx', archetype='detached', variant='combined', cohort='random64', run_id=rid)
            for target in TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']:
                d['old_' + target] = old
                d['new_' + target] = new
            d['old_two_of_three_proxy_dwelling'] = bool(old)
            d['new_two_of_three_proxy_dwelling'] = bool(new)
            rows.append(d)
        frame = pd.DataFrame(rows)
        stats = summarize(frame, ['weather', 'archetype', 'variant', 'cohort'])
        self.assertTrue(stats.mean_change.eq(0).all())
        self.assertTrue(stats.mean_absolute_change.eq(1).all())
        self.assertTrue(stats.paired_rmse.eq(1).all())
        flags = flag_tables(frame)
        joint = flags[flags.flag.eq('same_zone_two_of_three_proxy')].iloc[0]
        self.assertEqual((joint.old_count, joint.new_count, joint.newly_exceeding, joint.no_longer_exceeding), (1, 1, 1, 1))


if __name__ == '__main__':
    unittest.main()
