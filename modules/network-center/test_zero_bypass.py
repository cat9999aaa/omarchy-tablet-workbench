import unittest
from zero_bypass import rule_change


class ZeroBypassTests(unittest.TestCase):
    def test_only_dedicated_daemon_uid_bypasses_tun(self):
        self.assertEqual(rule_change(957, [], '-4'),
                         ['ip', '-4', 'rule', 'add', 'priority', '8990',
                          'uidrange', '957-957', 'lookup', 'main'])

    def test_existing_owned_rule_is_not_duplicated(self):
        self.assertIsNone(rule_change(957, [{'priority': 8990, 'table': 'main',
                            'uidrange': {'start': 957, 'end': 957}}], '-6'))

    def test_iproute2_flat_uid_fields_are_recognized(self):
        self.assertIsNone(rule_change(957, [{'priority': 8990, 'table': 'main',
                            'uid_start': 957, 'uid_end': 957}], '-4'))

    def test_removal_uses_both_uid_and_table(self):
        self.assertEqual(rule_change(957, [{'priority': 8990, 'table': 'main',
                            'uid_start': 957, 'uid_end': 957}], '-4', remove=True),
                         ['ip', '-4', 'rule', 'del', 'priority', '8990',
                          'uidrange', '957-957', 'lookup', 'main'])

    def test_foreign_priority_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            rule_change(957, [{'priority': 8990, 'table': 100}], '-4')

    def test_root_uid_is_never_bypassed(self):
        with self.assertRaises(ValueError):
            rule_change(0, [], '-4')

    def test_removal_only_removes_our_rule(self):
        self.assertIsNone(rule_change(957, [{'priority': 8990, 'table': 100}], '-4', remove=True))


if __name__ == '__main__':
    unittest.main()
