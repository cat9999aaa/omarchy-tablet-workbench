"""Cached health must not crash status or outlive its observation/interface."""
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import network


class HealthCacheTests(unittest.TestCase):
    def status_with_health(self, value):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            home = Path(temp)
            cache = home / '.local/state/pcadmin-network/health.json'
            cache.parent.mkdir(parents=True)
            cache.write_text(json.dumps(value))
            read_text = Path.read_text
            def isolated_read(path, *args, **kwargs):
                if path == Path('/run/pcadmin-network/status.json'):
                    return '{}'
                return read_text(path, *args, **kwargs)
            stack.enter_context(patch.object(network.Path, 'read_text', isolated_read))
            stack.enter_context(patch.object(network.Path, 'home', return_value=home))
            stack.enter_context(patch.object(network, 'route_status', return_value={'interface': 'wlan-test'}))
            stack.enter_context(patch.object(network, 'optional', side_effect=lambda args, default='', **kw: default))
            stack.enter_context(patch.object(network, 'call', return_value='{}'))
            stack.enter_context(patch.object(network.socket, 'create_connection', side_effect=OSError))
            stack.enter_context(patch.object(network.time, 'time', return_value=100))
            stack.enter_context(patch.object(network, 'flight_requested', return_value=False))
            stack.enter_context(patch.object(network, 'read_policy', return_value={}))
            stack.enter_context(patch.object(network, 'gps_status', return_value={}))
            return network.status()['health']

    def test_invalid_health_timestamp_is_discarded(self):
        for timestamp in [None, '99', True, float('nan'), float('inf'), -float('inf'), 10**400]:
            with self.subTest(timestamp=repr(timestamp)):
                self.assertEqual(self.status_with_health({'interface': 'wlan-test', 'observed_at': timestamp, 'internet': 'ok'}), {})

    def test_non_object_health_is_discarded(self):
        for value in [None, [], ['ok'], 'ok', True, 1]:
            with self.subTest(value=value):
                self.assertEqual(self.status_with_health(value), {})

    def test_timestamp_boundaries_and_interface_match(self):
        for timestamp, fresh in [(105, True), (106, False), (100, True), (35, True), (34, False)]:
            value = {'interface': 'wlan-test', 'observed_at': timestamp, 'internet': 'ok'}
            with self.subTest(timestamp=timestamp):
                self.assertEqual(self.status_with_health(value), value if fresh else {})
        self.assertEqual(self.status_with_health({'interface': 'old-link', 'observed_at': 99, 'internet': 'ok'}), {})
