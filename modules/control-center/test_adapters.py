import unittest
from adapters import snapshot, field, read_touch_state

class StateTests(unittest.TestCase):
 def test_virtual_tun_does_not_replace_physical_or_internet_health(self):
  s=snapshot(100,{'primary':'4g','proxy_available':True,'proxy_tun':True,'health':{'observed_at':99,'internet':'failed','tun':'failed'}},{},[])
  self.assertEqual(s['physical_uplink']['actual'],'4g');self.assertTrue(s['tun']['actual']);self.assertEqual(s['internet']['actual'],'failed')
 def test_missing_temperature_is_unknown(self):
  self.assertIsNone(snapshot(100,{}, {},[])['temperature']['actual'])
 def test_missing_touch_is_not_normal(self):
  self.assertFalse(read_touch_state('/nonexistent',100)['available'])
 def test_field_stale_not_normal(self):
  self.assertEqual(field('x',True,1,10,45,'test',now=100)['health'],'stale')
 def test_touch_mode_preserves_boot_default(self):
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'state';p.write_text(json.dumps({'mode':0,'verified':True,'observed_at':90,'boot_default':1}))
   self.assertEqual(read_touch_state(p,100)['actual'],0)
   self.assertEqual(read_touch_state(p,100)['boot_default'],1)
   self.assertEqual(read_touch_state(p,200)['health'],'stale')

 def test_expired_radio_confirmation_does_not_show_flight_success(self):
  s=snapshot(100,{'flight_saved':True,'flight_active':True,'flight_observed_at':10},{},[])
  self.assertIsNone(s['flight_active']);self.assertTrue(s['flight_saved'])
 def test_network_timeout_keeps_entertainment_and_restore_entry(self):
  import control_center as cc
  from unittest.mock import patch
  with patch.object(cc.subprocess,'check_output',side_effect=OSError('unavailable')),patch.object(cc.Path,'exists',return_value=True):
   s=cc.status()
  self.assertIs(s['flight_saved'],True);self.assertIsNone(s['flight_active'])
