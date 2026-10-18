import subprocess
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from device_evidence import collect_device_evidence


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'class/input').mkdir(parents=True)
        (self.root / 'devices').mkdir()
        (self.root / 'bus/usb').mkdir(parents=True)
        self.node = self.add_device(0)
        self.properties = 'ID_INPUT_KEYBOARD=1\nID_BUS=usb\nID_SERIAL=PRIVATE_CANARY\n'

    def add_device(self, index):
        parent = self.root / f'devices/usb{index}'
        parent.mkdir()
        (parent / 'subsystem').symlink_to(self.root / 'bus/usb')
        device = parent / f'input{index}'
        (device / 'capabilities').mkdir(parents=True)
        (device / 'id').mkdir()
        (device / 'capabilities/key').write_text('200100050010000')
        (device / 'capabilities/abs').write_text('60000000000000')
        (device / 'capabilities/sw').write_text('0')
        (device / 'id/bustype').write_text('0003')
        event = device / f'event{index}'
        event.mkdir()
        (event / 'device').symlink_to(device)
        (self.root / f'class/input/event{index}').symlink_to(event)
        return device

    def collect(self, runner=None, **kwargs):
        return collect_device_evidence(sysfs_root=self.root,
                                      runner=runner or (lambda argv, timeout: self.properties), **kwargs)

    def test_normal_and_privacy(self):
        value = self.collect()
        self.assertTrue(value['complete'])
        self.assertIs(value['physical_keyboard_present'], True)
        self.assertIs(value['touch_present'], True)
        self.assertIs(value['tablet_switch_capability'], False)
        for private in ('PRIVATE_CANARY', str(self.root), 'usb0', 'event0', 'ID_SERIAL'):
            self.assertNotIn(private, json.dumps(value))

    def test_collect_limits(self):
        for i in range(1, 129):
            self.add_device(i)
        self.assertEqual(self.collect()['reason_code'], 'limit_exceeded')

    def test_capability_limit_and_invalid(self):
        path = self.node / 'capabilities/key'
        for data, reason in [('f' * 16385, 'limit_exceeded'), ('not-hex', 'invalid_data')]:
            path.write_text(data)
            value = self.collect()
            self.assertEqual(value['reason_code'], reason)
            self.assertIsNone(value['physical_keyboard_present'])

    def test_udev_malformed(self):
        for output in ['ID_BUS=usb\nID_BUS=bluetooth', '\udcff', 'X' * 16385]:
            self.properties = output
            value = self.collect()
            self.assertFalse(value['complete'])
            self.assertNotIn(output, json.dumps(value))

    def test_read_races(self):
        def vanished(*args):
            shutil.rmtree(self.node)
            return self.properties
        self.assertEqual(self.collect(vanished)['reason_code'], 'device_changed')

    def test_changed_inventory_incomplete(self):
        def added(*args):
            self.add_device(1)
            return self.properties
        self.assertEqual(self.collect(added)['reason_code'], 'device_changed')

    def test_subquery_timeout_is_timeout(self):
        def timeout(*args):
            raise subprocess.TimeoutExpired(['udevadm'], 5)
        self.assertEqual(self.collect(timeout)['reason_code'], 'read_timeout')

    def test_read_denied(self):
        with patch('device_evidence.os.open', side_effect=PermissionError('PRIVATE_CANARY')):
            value = self.collect()
        self.assertEqual(value['reason_code'], 'read_denied')
        self.assertNotIn('PRIVATE_CANARY', json.dumps(value))

    def test_symlink_escape_rejected(self):
        path = self.node / 'capabilities/key'
        path.unlink()
        path.symlink_to('/etc/passwd')
        self.assertFalse(self.collect()['complete'])

    def test_fifo_not_blocking(self):
        path = self.node / 'capabilities/key'
        path.unlink()
        os.mkfifo(path)
        self.assertEqual(self.collect()['reason_code'], 'invalid_data')

    def test_shared_total_budget(self):
        clock = [0]
        def slow(*args):
            clock[0] = 5000
            return self.properties
        value = self.collect(slow, clock_ms=lambda: clock[0])
        self.assertEqual(value['reason_code'], 'read_timeout')
        self.assertFalse(value['complete'])

    def test_failed_udev_is_fixed_error(self):
        def failed(*args):
            raise RuntimeError('PRIVATE_CANARY')
        value = self.collect(failed)
        self.assertEqual(value['reason_code'], 'read_failed')
        self.assertNotIn('PRIVATE_CANARY', json.dumps(value))
