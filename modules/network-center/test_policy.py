import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from policy import read_policy,update_policy
import network
class PolicyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'PCADMIN_NETWORK_POLICY':self.tmp.name+'/policy.json'});self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def test_defaults(self):self.assertEqual(read_policy(),{'mode':'auto','proxy_enabled':True})
 def test_off_survives_mode_change(self):
  update_policy(proxy_enabled=False);update_policy(mode='manual');self.assertEqual(read_policy(),{'mode':'manual','proxy_enabled':False})
 def test_manual_off_prevents_automatic_client_start(self):
  update_policy(proxy_enabled=False)
  with patch('network.start_proxy_client') as start:network.ensure_proxy();start.assert_not_called()
 def test_manual_on_clears_off_latch(self):
  update_policy(proxy_enabled=False)
  with patch('network.ensure_proxy'):network.action('proxy-on')
  self.assertTrue(read_policy()['proxy_enabled'])
 def test_proxy_off_latches_before_stopping(self):
  with patch('network.set_system_proxy'),patch('network.close_extra_clients'),patch('network.call',side_effect=lambda *a,**kw:self.assertFalse(read_policy()['proxy_enabled'])):network.action('proxy-off')
 def test_profile_types_priorities(self):
  self.assertEqual(network.auto_metric('802-3-ethernet'),100)
  self.assertEqual(network.auto_metric('802-11-wireless'),600)
  self.assertEqual(network.auto_metric('gsm'),700)
  self.assertIsNone(network.auto_metric('tun'))
if __name__=='__main__':unittest.main()
