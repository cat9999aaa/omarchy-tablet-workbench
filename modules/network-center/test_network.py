import unittest
from network import classify, traffic_totals, action_command, consume_gps, preference, wired_command
from unittest.mock import patch
class NetworkTests(unittest.TestCase):
 def test_cellular_not_ethernet(self):
  self.assertEqual(classify('wwp0s20f0u2c2',{'cdc-wdm0':'gsm'},'wwp0s20f0u2c2'),'4g')
  self.assertEqual(classify('ztabc',{'ztabc':'tun'},'wwp0s20f0u2c2'),'virtual')
 def test_traffic_is_single_interface(self):
  data={'interfaces':[{'name':'wwan','traffic':{'day':[{'rx':10,'tx':20}],'month':[{'rx':30,'tx':40}]}},{'name':'ztabc','traffic':{'day':[{'rx':900,'tx':900}]}}]}
  self.assertEqual(traffic_totals(data,'wwan'),{'day':30,'month':70})
 def test_latest_date_not_array_order(self):
  d={'interfaces':[{'name':'wwan','traffic':{'day':[{'date':{'year':2026,'month':10,'day':15},'rx':1,'tx':1},{'date':{'year':2026,'month':10,'day':16},'rx':5,'tx':6}]}}]}
  self.assertEqual(traffic_totals(d,'wwan')['day'],11)
 def test_gps_summary_does_not_expose_coordinates(self):
  out={'mode':1};consume_gps({'class':'TPV','mode':3,'lat':12.3,'lon':45.6},out)
  consume_gps({'class':'SKY','satellites':[{'used':True},{'used':False}]},out)
  self.assertEqual(out,{'mode':3,'satellites':2,'used':1})
 def test_no_arbitrary_root_commands(self):
  with self.assertRaises(ValueError):action_command('zero; rm -rf /')
  self.assertEqual(action_command('zero-on'),['pkexec','/usr/bin/systemctl','start','zerotier-one.service'])
 def test_radio_and_connection_separate(self):
  self.assertIn('wwan',action_command('cell-radio-off'))
  self.assertIn('down',action_command('cell-off'))
 def test_selection_does_not_reconnect_active_cellular(self):
  calls=[]
  def fake(a,*args,**kwargs):
   calls.append(a)
   if a==['nmcli','-t','-f','DEVICE,TYPE,STATE','dev']:return 'wlp3s0:wifi:connected\ncdc-wdm0:gsm:connected'
   if a==['nmcli','-g','GENERAL.CONNECTION','dev','show','wlp3s0']:return 'test-wifi'
   if a[:2]==['nmcli','-g'] and 'ipv4.route-metric,ipv6.route-metric' in a:return '600\n50'
   return ''
  with patch('network.call',side_effect=fake),patch('network.optional',side_effect=fake):preference('prefer-wifi')
  self.assertIn(['nmcli','device','reapply','cdc-wdm0'],calls)
  self.assertFalse(any('up' in c for c in calls))
 def test_wired_action_targets_only_detected_ethernet(self):
  with patch('network.call',return_value='wlp3s0:wifi\nenp0s1:ethernet'):
   self.assertEqual(wired_command('wired-on'),['nmcli','--wait','25','device','connect','enp0s1'])
  with patch('network.call',return_value='wlp3s0:wifi'):
   with self.assertRaises(RuntimeError):wired_command('wired-off')
 def test_zero_shutdown_not_available(self):
  with self.assertRaises(ValueError):action_command('zero-off')
if __name__=='__main__':unittest.main()

