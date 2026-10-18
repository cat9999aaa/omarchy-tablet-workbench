"""Action preparation must not probe unrelated hardware or relax guards."""
import unittest
from unittest.mock import patch
import control_center as control


class ActionPreparationTests(unittest.TestCase):
    def test_static_actions_do_not_depend_on_power_or_audio(self):
        cases = {
            'network': (['omarchy-shell', 'omarchy.network', 'open'], 'network'),
            'lock': (['omarchy', 'system', 'lock'], 'lock'),
            'reader': (['gtk-launch', 'rocks.koreader.KOReader'], 'reader'),
            'nightlight': (['omarchy', 'toggle', 'nightlight'], 'nightlight'),
        }
        with patch.object(control, 'power_context', side_effect=AssertionError('unrelated power probe')), \
             patch.object(control, 'audio_sink', side_effect=AssertionError('unrelated audio probe')):
            for action, (argv, resource) in cases.items():
                with self.subTest(action=action):
                    result = control.prepare(action, {}, False)
                    self.assertEqual(result['argv'], argv)
                    self.assertEqual(result['resource'], resource)

    def test_power_action_uses_one_consistent_observation(self):
        for action in ('power-saver', 'balanced'):
            with self.subTest(action=action), patch.object(control, 'power_context', side_effect=['ac', AssertionError('duplicate power probe')]):
                result = control.prepare(action, {}, False)
                self.assertEqual(result['argv'], ['omarchy', 'powerprofiles', 'set', 'ac', action])
                self.assertEqual(result['resource'], 'power-profile')

    def test_invalid_requests_are_rejected_before_hardware_reads(self):
        with patch.object(control, 'power_context', side_effect=AssertionError('power probe before validation')), \
             patch.object(control, 'audio_sink', side_effect=AssertionError('audio probe before validation')):
            for action, params in [('bad;reboot', {}), ('mute', {'percent': 10}), ('volume', {'percent': True})]:
                with self.subTest(action=action), self.assertRaises(ValueError):
                    control.prepare(action, params, False)
            for locked in (True, None):
                with self.assertRaises(PermissionError):
                    control.prepare('balanced', {}, locked)

    def test_privileged_requests_keep_confirmation_and_request_identity(self):
        for action, resource, confirmation in [('flight-on', 'network', True), ('flight-off', 'network', False), ('touch-normal', 'touch', True), ('touch-refresh', 'touch', False)]:
            with self.subTest(action=action):
                result = control.prepare(action, {}, False)
                self.assertEqual(result['argv'], ['pkexec', '/usr/bin/python', '/usr/local/libexec/pcadmin-control-privileged.py', action, result['request_id']])
                self.assertEqual(result['resource'], resource)
                self.assertIs(result['requires_confirmation'], confirmation)

    def test_audio_uses_resolved_sink_and_shared_resource(self):
        cases = [
            ('volume', {'percent': 0}, ['pactl', 'set-sink-volume', 'alsa_test', '0%']),
            ('mute', {}, ['pactl', 'set-sink-mute', 'alsa_test', 'toggle']),
        ]
        for action, params, expected in cases:
            with self.subTest(action=action), \
                 patch.object(control, 'audio_sink', side_effect=['alsa_test', AssertionError('duplicate audio probe')]), \
                 patch.object(control, 'power_context', side_effect=AssertionError('unrelated power probe')):
                result = control.prepare(action, params, False)
                self.assertEqual(result['argv'], expected)
                self.assertEqual(result['resource'], 'audio-output')
