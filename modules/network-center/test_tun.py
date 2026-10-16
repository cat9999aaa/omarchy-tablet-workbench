import unittest
from unittest.mock import patch
import network
class TunTests(unittest.TestCase):
 def test_tun_does_not_replace_physical_network_label(self):
  def answer(a,*args,**kwargs):
   if a==['ip','-j','route','get','1.1.1.1']:return '[{"dev":"singbox_tun"}]'
   if a==['ip','-j','route','show','table','main','default']:return '[{"dev":"wwp0s20f0u2c2","metric":700},{"dev":"wlp3s0","metric":600}]'
   return ''
  with patch('network.optional',side_effect=answer):self.assertEqual(network.route_status()['interface'],'wlp3s0')
 def test_tun_stop_happens_before_client_stop(self):
  order=[]
  with patch('network.update_policy'),patch('network.set_system_proxy'),patch('network.tun_control',side_effect=lambda x:order.append(x)),patch('network.call',side_effect=lambda *x:order.append('client')),patch('network.close_extra_clients'):
   network.action('proxy-off')
  self.assertEqual(order,['stop','client'])
 def test_tun_start_reuses_existing_service(self):
  with patch('network.optional',return_value='active'),patch('network.call') as call:
   network.tun_control('start');call.assert_not_called()
 def test_unknown_tun_action_rejected(self):
  with self.assertRaises(ValueError):network.tun_control('restart;true')
if __name__=='__main__':unittest.main()
