import unittest
from unittest.mock import patch
import network
import os,tempfile
class CellProxyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{"PCADMIN_NETWORK_POLICY":self.tmp.name+"/policy.json"});self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def test_already_connected_still_enables_proxy(self):
  with patch('network.call'),patch('network.status',return_value={'cell_connected':True}),patch('network.ensure_proxy') as proxy:
   network.action('cell-on');proxy.assert_called_once()
 def test_select_cell_enables_proxy_after_route_success(self):
  with patch('network.preference') as select,patch('network.ensure_proxy') as proxy:
   network.action('prefer-cell');select.assert_called_once_with('prefer-cell');proxy.assert_called_once()
 def test_failed_cell_connection_does_not_change_proxy(self):
  with patch('network.call',side_effect=RuntimeError('connect failed')),patch('network.ensure_proxy') as proxy:
   with self.assertRaises(RuntimeError):network.action('cell-on')
   proxy.assert_not_called()
 def test_select_wifi_does_not_disable_proxy(self):
  with patch('network.preference'),patch('network.ensure_proxy') as proxy:
   network.action('prefer-wifi');proxy.assert_not_called()
 def test_external_trigger_requires_active_cellular(self):
  with patch('network.cell_connected',return_value=False),patch('network.ensure_proxy') as proxy:
   network.action('cell-proxy-on');proxy.assert_not_called()
 def test_open_reuses_managed_instance(self):
  with patch('network.ensure_proxy') as start,patch('network.subprocess.Popen') as launch:
   network.action('proxy-open');start.assert_called_once();launch.assert_not_called()
 def test_off_stops_client_and_system_proxy(self):
  with patch('network.tun_control') as tun,patch('network.set_system_proxy') as settings,patch('network.call') as call,patch('network.close_extra_clients') as close:
   network.action('proxy-off');tun.assert_called_once_with('stop');settings.assert_called_once_with(False)
   call.assert_called_once_with(['systemctl','--user','stop','v2rayn.service'],25);close.assert_called_once_with(0)
if __name__=='__main__':unittest.main()

