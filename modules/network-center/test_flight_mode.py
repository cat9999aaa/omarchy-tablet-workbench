"""Hardware boundary fixtures: never operate this tablet's radios in tests."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import radio_control as radio
import network

class Hardware:
 def __init__(self):
  self.wifi=True;self.wwan=True;self.bt=True;self.net=True;self.power='on';self.state='connected';self.calls=[];self.stuck=False
 def __call__(self,a):
  self.calls.append(a)
  if a==['nmcli','-t','-f','WIFI,WWAN','radio']:return ':'.join('enabled' if v else 'disabled' for v in (self.wifi,self.wwan))
  if a==['nmcli','networking']:return 'enabled' if self.net else 'disabled'
  if a==['rfkill','--json']:return json.dumps({'rfkilldevices':[{'id':0,'type':'bluetooth','device':'hci0','soft':'unblocked' if self.bt else 'blocked','hard':'unblocked'},{'id':1,'type':'wlan','device':'phy0','soft':'unblocked' if self.wifi else 'blocked','hard':'unblocked'}]})
  if a==['mmcli','-L','-J']:return json.dumps({'modem-list':['/org/freedesktop/ModemManager1/Modem/0']})
  if a==['mmcli','-m','/org/freedesktop/ModemManager1/Modem/0','-J']:return json.dumps({'modem':{'generic':{'state':self.state,'power-state':self.power}}})
  if a[:3]==['nmcli','radio','all']:self.wifi=self.wwan=a[3]=='on'
  elif a[:2]==['nmcli','radio']:setattr(self,a[2],a[3]=='on')
  elif a[:2]==['nmcli','networking']:self.net=a[2]=='on'
  elif a[0]=='rfkill':
   if a[2] in ('all','bluetooth','0'):self.bt=a[1]=='unblock'
   if a[2] in ('all','wlan','1'):self.wifi=a[1]=='unblock'
  elif a[0]=='mmcli':
   if a[-1]=='--disable':self.state='disabled'
   elif a[-1].startswith('--set-power-state-') and not self.stuck:self.power=a[-1].removeprefix('--set-power-state-')
   elif a[-1]=='--enable':self.state='enabled'
   else:raise RuntimeError('unsupported modem transition')
  else:raise AssertionError(a)
  return ''

class FlightTests(unittest.TestCase):
 def test_flight_disables_modem_radio_and_networking_before_verified(self):
  hw=Hardware()
  with tempfile.TemporaryDirectory() as d:
   radio.flight(True,Path(d)/'flight.json',hw)
   self.assertEqual(hw.power,'low');self.assertFalse(hw.net);self.assertFalse(hw.bt)
 def test_modem_stuck_on_is_failure_and_does_not_reenable_other_radios(self):
  hw=Hardware();hw.stuck=True
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json'
   with self.assertRaises(RuntimeError):radio.flight(True,p,hw)
   self.assertTrue(p.exists());self.assertFalse(hw.wifi);self.assertFalse(hw.bt)
 def test_restore_preserves_prior_disabled_wwan_and_repeated_enable_snapshot(self):
  hw=Hardware();hw.wwan=False;hw.power='low';hw.state='disabled'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';radio.flight(True,p,hw);before=p.read_text();radio.flight(True,p,hw)
   self.assertEqual(p.read_text(),before)
   radio.flight(False,p,hw)
   self.assertTrue(hw.wifi);self.assertTrue(hw.bt);self.assertTrue(hw.net);self.assertFalse(hw.wwan);self.assertEqual(hw.power,'low');self.assertFalse(p.exists())
 def test_unknown_nm_output_is_not_off(self):
  hw=Hardware()
  def invalid(a):return 'unknown:unknown' if a[0]=='nmcli' and 'WIFI,WWAN' in a else hw(a)
  with self.assertRaises(ValueError):radio.radio_state(invalid)
 def test_lock_guard_rechecked_between_radio_writes(self):
  hw=Hardware();checks=[]
  def guard():
   checks.append(1)
   if len(checks)>2:raise PermissionError('locked')
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(PermissionError):radio.flight(True,Path(d)/'flight.json',hw,guard)
 def test_proxy_health_and_auto_start_paused_during_flight(self):
  with patch.object(network,'flight_requested',return_value=True,create=True),patch.object(network,'call',side_effect=AssertionError('must not change network')),patch.object(network,'optional',side_effect=AssertionError('must not probe')),patch.object(network,'ensure_proxy',side_effect=AssertionError('must not start proxy')):
   network.action('proxy-auto-on')
   self.assertEqual(network.health_check()['internet'],'flight')
   with self.assertRaises(RuntimeError):network.action('wifi-on')
 def test_disappeared_rfkill_device_is_not_confirmed_off(self):
  hw=Hardware()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';radio.flight(True,p,hw)
   def missing(a):return '{"rfkilldevices":[]}' if a==['rfkill','--json'] else hw(a)
   self.assertIsNot(radio.flight_status(json.loads(p.read_text()),missing)['flight_active'],True)
 def test_restore_power_readback_failure_keeps_recovery(self):
  hw=Hardware()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flight.json';radio.flight(True,p,hw);hw.stuck=True
   # Firmware acknowledges power-on but still reports low.
   def lies(a):
    if a[-1]=='--set-power-state-on':return ''
    return hw(a)
   with self.assertRaises(RuntimeError):radio.flight(False,p,lies)
   self.assertTrue(p.exists())
 def test_client_exit_wait_does_not_change_proxy_intent_after_flight_starts(self):
  with patch.object(network,'flight_requested',side_effect=[False,True]),patch.object(network,'optional',return_value='inactive'),patch.object(network,'update_policy') as update:
   network.action('proxy-user-exit');update.assert_not_called()
 def test_flight_started_while_reading_route_prevents_http_probe(self):
  with patch.object(network,'flight_requested',side_effect=[False,True]),patch.object(network,'route_status',return_value={'interface':'wwan0'}),patch.object(network,'optional',side_effect=AssertionError('no new HTTP probe')):
   self.assertEqual(network.health_check()['internet'],'flight')
 def test_tun_does_not_start_if_flight_begins_during_status_wait(self):
  with patch.object(network,'flight_requested',side_effect=[False,True]),patch.object(network,'optional',return_value='inactive'),patch.object(network,'call',side_effect=AssertionError('must not start TUN')):
   network.tun_control('start')
if __name__=='__main__':unittest.main()
