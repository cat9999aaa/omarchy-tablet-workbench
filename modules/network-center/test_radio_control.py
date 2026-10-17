import unittest,tempfile
from pathlib import Path
from radio_control import zero_summary,flight,radio_state
class RadioTests(unittest.TestCase):
 def test_post_auth_guard_blocks_flight_before_any_write(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';calls=[]
   def runner(a):
    calls.append(a)
    if a==['nmcli','-t','-f','WIFI,WWAN','radio']:return 'enabled:enabled'
    if a==['rfkill','--json']:return '{"rfkilldevices":[]}'
    return ''
   def guard():raise PermissionError('locked')
   with self.assertRaises(PermissionError):flight(True,p,runner,guard)
   self.assertFalse(p.exists());self.assertNotIn(['nmcli','radio','all','off'],calls)
 def test_authorization_is_not_service_running(self):
  self.assertEqual(zero_summary([{'status':'ACCESS_DENIED','name':'test','assignedAddresses':[]}])[0]['state'],'未授权')
  self.assertEqual(zero_summary([{'status':'OK','name':'test','assignedAddresses':['10.0.0.2/24'],'authToken':'secret'}])[0],{'name':'test','state':'已连接／已授权','status':'OK','addresses':['10.0.0.2/24']})
 def test_airplane_preserves_previously_disabled_cellular(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';calls=[]
   def run(a):
    calls.append(a)
    if a==['nmcli','-t','-f','WIFI,WWAN','radio']:return 'enabled:disabled'
    if a==['rfkill','--json']:return '{"rfkilldevices":[{"type":"bluetooth","soft":"unblocked"}]}'
    return ''
   flight(True,p,run);self.assertTrue(p.exists());flight(False,p,run)
   self.assertIn(['nmcli','radio','wifi','on'],calls);self.assertIn(['nmcli','radio','wwan','off'],calls)
   self.assertNotIn(['nmcli','radio','wwan','on'],calls);self.assertFalse(p.exists())
 def test_repeated_enable_keeps_original_snapshot(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';p.write_text('{"wifi":true,"wwan":false,"bluetooth":true}')
   flight(True,p,lambda a:'');self.assertIn('"wifi":true',p.read_text())
 def test_failure_restores_radios(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';calls=[]
   def run(a):
    calls.append(a)
    if a[0]=='rfkill' and a[1]=='block':raise RuntimeError('denied')
    if a==['nmcli','-t','-f','WIFI,WWAN','radio']:return 'enabled:disabled'
    if a==['rfkill','--json']:return '{"rfkilldevices":[]}'
    return ''
   with self.assertRaises(RuntimeError):flight(True,p,run)
   self.assertIn(['nmcli','radio','wifi','on'],calls)
if __name__=='__main__':unittest.main()
