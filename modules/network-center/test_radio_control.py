import unittest,tempfile
from pathlib import Path
from radio_control import zero_summary,flight
from test_flight_mode import Hardware
class RadioTests(unittest.TestCase):
 def test_post_auth_guard_blocks_flight_before_any_write(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';hw=Hardware()
   def guard():raise PermissionError('locked')
   with self.assertRaises(PermissionError):flight(True,p,hw,guard)
   self.assertFalse(p.exists());self.assertEqual(hw.calls,[])
 def test_authorization_is_not_service_running(self):
  self.assertEqual(zero_summary([{'status':'ACCESS_DENIED','name':'test','assignedAddresses':[]}])[0]['state'],'未授权')
  self.assertEqual(zero_summary([{'status':'OK','name':'test','assignedAddresses':['10.0.0.2/24'],'authToken':'secret'}])[0],{'name':'test','state':'已连接／已授权','status':'OK','addresses':['10.0.0.2/24']})
 def test_block_failure_keeps_recovery_and_never_reconnects(self):
  hw=Hardware()
  def denied(a):
   if a==['rfkill','block','all']:raise RuntimeError('denied')
   return hw(a)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json'
   with self.assertRaises(RuntimeError):flight(True,p,denied)
   self.assertTrue(p.exists());self.assertFalse(hw.net);self.assertFalse(hw.wifi)
if __name__=='__main__':unittest.main()
