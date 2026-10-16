import unittest
from network import parse_probe
from radio_control import peer_summary


class DiagnosticsTests(unittest.TestCase):
    def test_discarded_body_survives_command_whitespace_normalization(self):
        self.assertEqual(parse_probe('204\t1.025', ('204',)), {'state':'ok','latency_ms':1025})
    def test_domestic_requires_expected_body_not_captive_portal(self):
        self.assertEqual(parse_probe('NetworkManager is online\n200\t0.123', ('200',), 'NetworkManager is online'), {'state':'ok','latency_ms':123})
        self.assertEqual(parse_probe('login required\n200\t0.200', ('200',), 'NetworkManager is online')['state'], 'failed')

    def test_http_failure_is_not_success_despite_low_latency(self):
        self.assertEqual(parse_probe('\n503\t0.050', ('204',)), {'state':'failed','latency_ms':50})

    def test_timeout_missing_or_invalid_timing_is_not_zero_latency(self):
        for raw in ('', '\n204\tnan', '\n204\t-1', '\n000\t5.0'):
            result = parse_probe(raw, ('204',))
            self.assertEqual(result['state'], 'failed')
        self.assertIsNone(parse_probe('', ('204',))['latency_ms'])

    def test_root_servers_are_not_counted_as_connected_devices(self):
        peers=[{'role':'PLANET','latency':20,'paths':[{'active':True}]},
               {'role':'LEAF','latency':46,'paths':[{'active':True}], 'address':'private-id'},
               {'role':'LEAF','latency':-1,'paths':[]}]
        self.assertEqual(peer_summary(peers), {'active_devices':1,'best_latency_ms':46,'unconfirmed_devices':1})

    def test_unknown_peer_latency_is_not_presented_as_measured(self):
        self.assertEqual(peer_summary([{'role':'LEAF','latency':-1,'paths':[{'active':True}]}]),
                         {'active_devices':1,'best_latency_ms':None,'unconfirmed_devices':0})


if __name__=='__main__':unittest.main()
