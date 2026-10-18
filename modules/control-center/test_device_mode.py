import copy
import unittest
from device_mode import reduce_mode


def evidence(keyboard=True, touch=True):
    return {'schema_version': 1, 'complete': True, 'health': 'observed',
            'physical_keyboard_present': keyboard, 'touch_present': touch,
            'tablet_switch_capability': False}


class ModeTests(unittest.TestCase):
    def boundary(self, source, target, data, limit):
        r = reduce_mode('auto', source, data, 0, None)
        self.assertEqual(r['effective'], source)
        r = reduce_mode('auto', source, data, limit-1, r['pending'])
        self.assertEqual(r['effective'], source)
        r = reduce_mode('auto', source, data, limit, r['pending'])
        self.assertEqual(r['effective'], target)
        self.assertEqual(r['reason_code'], 'stable')

    def test_desktop_boundary(self):
        self.boundary('tablet', 'desktop', evidence(), 500)

    def test_tablet_boundary(self):
        self.boundary('desktop', 'tablet', evidence(False), 1000)

    def test_unknown_resets_pending(self):
        p = reduce_mode('auto', 'tablet', evidence(), 0, None)['pending']
        for delta in ({'complete': False}, {'health': 'error'}, {'physical_keyboard_present': None},
                      {'schema_version': True}, {'physical_keyboard_present': 1}):
            r = reduce_mode('auto', 'tablet', evidence() | delta, 500, p)
            self.assertEqual(r['effective'], 'tablet')
            self.assertIsNone(r['pending'])
            self.assertEqual(r['health'], 'unknown')

    def test_manual_ignores_unknown(self):
        r = reduce_mode('desktop', 'tablet', {}, float('nan'), None)
        self.assertEqual(r, {'effective': 'desktop', 'health': 'observed',
                             'reason_code': 'manual', 'pending': None})

    def test_gap_and_reverse_time(self):
        p = reduce_mode('auto', 'tablet', evidence(), 100, None)['pending']
        for now, reason in [(2101, 'observation_gap'), (99, 'time_invalid')]:
            r = reduce_mode('auto', 'tablet', evidence(), now, p)
            self.assertEqual(r['effective'], 'tablet')
            self.assertIsNone(r['pending'])
            self.assertEqual(r['reason_code'], reason)

    def test_manual_then_auto_restarts(self):
        p = reduce_mode('auto', 'tablet', evidence(), 0, None)['pending']
        manual = reduce_mode('tablet', 'tablet', evidence(), 500, p)
        r = reduce_mode('auto', 'tablet', evidence(), 600, manual['pending'])
        self.assertEqual(r['effective'], 'tablet')
        self.assertEqual(r['pending']['since_ms'], 600)

    def test_flapping_restarts(self):
        r = reduce_mode('auto', None, evidence(), 0, None)
        r = reduce_mode('auto', None, evidence(False), 400, r['pending'])
        r = reduce_mode('auto', None, evidence(), 500, r['pending'])
        self.assertIsNone(r['effective'])
        self.assertEqual(r['pending']['since_ms'], 500)

    def test_invalid_time(self):
        for now in [10**1000, True, -1, float('nan'), float('inf'), '1']:
            r = reduce_mode('auto', None, evidence(), now, None)
            self.assertIsNone(r['effective'])
            self.assertEqual(r['reason_code'], 'time_invalid')
        for pending in [{'target':'desktop','since_ms':10**1000,'last_seen_ms':10**1000}, {}, {'target': 'desktop', 'since_ms': 2, 'last_seen_ms': 1}]:
            self.assertEqual(reduce_mode('auto', None, evidence(), 10, pending)['reason_code'], 'time_invalid')

    def test_missing_last_effective(self):
        self.assertIsNone(reduce_mode('auto', None, {}, 0, None)['effective'])

    def test_no_touch_no_keyboard(self):
        self.assertEqual(reduce_mode('auto', 'tablet', evidence(False, False), 0, None)['reason_code'],
                         'no_supported_mode')

    def test_invalid_choice_no_mutation(self):
        e = evidence(); original = copy.deepcopy(e)
        for choice, last in [('bad', 'tablet'), ('auto', 'bad')]:
            with self.assertRaises(ValueError):
                reduce_mode(choice, last, e, 0, None)
        self.assertEqual(e, original)
