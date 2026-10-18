import unittest
from dataclasses import replace
from device_classifier import DeviceFacts, parse_bitmap, classify, aggregate


class ClassifierTests(unittest.TestCase):
    def facts(self, **changes):
        value = DeviceFacts(frozenset({16, 30, 44, 28, 57}), frozenset(),
                            frozenset(), False, True, False, 3,
                            {'ID_INPUT_KEYBOARD': '1', 'ID_BUS': 'usb'})
        return replace(value, **changes)

    def test_bitmap_words(self):
        self.assertEqual(parse_bitmap('1 0', 64), {64})
        self.assertEqual(parse_bitmap('1 0', 32), {32})
        self.assertEqual(parse_bitmap('0 80000001', 32), {0, 31})
        for text, width in [('-1', 64), ('xx', 64), ('100000000', 32), ('', 64), ('1', 16)]:
            with self.subTest(text=text, width=width), self.assertRaises(ValueError):
                parse_bitmap(text, width)

    def test_keyboard_sources(self):
        cases = [(self.facts(), 'physical'),
                 (self.facts(input_bus=5, usb_parent=False, bluetooth_parent=True,
                             properties={'ID_INPUT_KEYBOARD': '1', 'ID_BUS': 'bluetooth'}), 'physical'),
                 (self.facts(virtual=True), 'virtual'),
                 (self.facts(usb_parent=False), 'unclassified'),
                 (self.facts(input_bus=1), 'unclassified'),
                 (self.facts(properties={'ID_BUS': 'usb'}), 'unclassified'),
                 (self.facts(properties={'ID_INPUT_KEYBOARD': '1', 'ID_BUS': 'pogo'}), 'unclassified')]
        for facts, want in cases:
            with self.subTest(want=want, facts=facts):
                self.assertEqual(classify(facts)['keyboard'], want)

    def test_consumer_mouse_switch_not_keyboard(self):
        item = classify(self.facts(key_bits=frozenset({115, 116, 272}),
                                  abs_bits=frozenset({53, 54}), sw_bits=frozenset({1})))
        self.assertEqual(item, {'keyboard': 'none', 'touch': True, 'tablet_switch': True})
        self.assertIs(aggregate([item], True, 'observed', 1)['physical_keyboard_present'], False)

    def test_mixed_unknown_and_physical(self):
        items = [classify(self.facts()), classify(self.facts(usb_parent=False))]
        result = aggregate(items, True, 'observed', 2)
        self.assertIs(result['physical_keyboard_present'], True)
        self.assertEqual(result['unclassified_keyboard_count'], 1)

    def test_unknown_prevents_absence(self):
        result = aggregate([classify(self.facts(usb_parent=False))], True, 'observed', 2)
        self.assertIsNone(result['physical_keyboard_present'])
        self.assertEqual(result['health'], 'unknown')
        self.assertEqual(result['reason_code'], 'unclassified_keyboard')

    def test_incomplete_never_absent(self):
        result = aggregate([], False, 'device_changed', 2)
        for key in ('physical_keyboard_present', 'touch_present', 'tablet_switch_capability'):
            self.assertIsNone(result[key])
        self.assertFalse(result['complete'])

    def test_virtual_excluded_and_empty_complete(self):
        result = aggregate([classify(self.facts(virtual=True))], True, 'observed', 0)
        self.assertIs(result['physical_keyboard_present'], False)
        self.assertEqual(result['excluded_virtual_count'], 1)
        self.assertIs(aggregate([], True, 'observed', 0)['touch_present'], False)
