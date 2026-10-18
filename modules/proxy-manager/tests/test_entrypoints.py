import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
root=Path(__file__).parents[2]
sys.path.insert(0,str(root/'network-center'))
spec=importlib.util.spec_from_file_location('net_entry',root/'network-center/network.py')
net=importlib.util.module_from_spec(spec);spec.loader.exec_module(net)
class Native:
 def __init__(self):self.calls=[]
 def dispatch(self,home,action,confirmed):self.calls.append((action,confirmed));return {'verified':True,'stage':'verified'}
class EntryTests(unittest.TestCase):
 def test_existing_switches_use_one_controller(self):
  native=Native()
  with patch.object(net,'native_client',return_value=native),patch.object(net,'flight_requested',return_value=False),patch.object(net,'call',side_effect=AssertionError('legacy control called')):
   net.action('proxy-on');net.action('proxy-off-confirmed')
  self.assertEqual(native.calls,[('enable',True),('disable',True)])
 def test_auto_entry_respects_manual_off(self):
  native=Native()
  with patch.object(net,'native_client',return_value=native),patch.object(net,'read_policy',return_value={'proxy_enabled':False}):net.ensure_proxy()
  self.assertEqual(native.calls,[])
 def test_old_exit_notification_does_not_disable_native_core(self):
  native=Native()
  with patch.object(net,'native_client',return_value=native),patch.object(net,'flight_requested',return_value=False),patch.object(net,'update_policy',side_effect=AssertionError('changed intent')):net.action('proxy-user-exit')
 def test_opening_ui_does_not_enable_proxy(self):
  native=Native()
  with patch.object(net,'native_client',return_value=native),patch.object(net,'flight_requested',return_value=False),patch.object(net.subprocess,'Popen') as popen:
   net.action('proxy-open');popen.assert_called_once()
  self.assertEqual(native.calls,[])
if __name__=='__main__':unittest.main()
