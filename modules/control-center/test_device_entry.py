import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import control_center
from device_classifier import aggregate


class DeviceEntryTests(unittest.TestCase):
    def test_device_entry_dispatch(self):
        expected = aggregate([], True, 'observed', 1)
        with patch.object(sys, 'argv', ['control_center.py', 'device-evidence']), \
             patch('device_evidence.collect_device_evidence', return_value=expected) as collect, \
             patch.object(control_center, 'collect_status', side_effect=AssertionError('unexpected status')), \
             patch.object(control_center, 'read_lock', side_effect=AssertionError('unexpected lock')), \
             patch.object(control_center, 'execute', side_effect=AssertionError('unexpected action')):
            self.assertEqual(control_center.main(), expected)
            collect.assert_called_once_with()

    def test_existing_status_does_not_probe_devices(self):
        for op in ('status', 'status-readonly'):
            with patch.object(sys, 'argv', ['control_center.py', op]), \
                 patch('device_evidence.collect_device_evidence', side_effect=AssertionError('probe forbidden')), \
                 patch.object(control_center, 'collect_status', return_value=SimpleNamespace(legacy={'original': True})), \
                 patch.object(control_center.contract_host, 'response', return_value={'original': True}):
                self.assertEqual(control_center.main(), {'original': True})

    def test_reject_extra_args(self):
        value = subprocess.run([sys.executable, str(Path(control_center.__file__)),
                                'device-evidence', '--sysfs=/tmp'], capture_output=True, text=True)
        self.assertNotEqual(value.returncode, 0)

    def test_response_allowlist(self):
        expected = aggregate([], False, 'read_failed', 0)
        with patch.object(sys, 'argv', ['control_center.py', 'device-evidence']), \
             patch('device_evidence.collect_device_evidence', side_effect=RuntimeError('PRIVATE_CANARY')):
            result = control_center.main()
        self.assertEqual(result, expected)
        self.assertLessEqual(len(json.dumps(result).encode()), 65536)
        self.assertNotIn('PRIVATE_CANARY', json.dumps(result))
