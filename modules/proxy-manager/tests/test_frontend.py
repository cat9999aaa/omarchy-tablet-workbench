import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('frontend',Path(__file__).parents[1]/'integration/frontend.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fixture():return {'inbounds':[{'type':'tun','interface_name':'existing','auto_route':True}],'outbounds':[{'type':'socks','tag':'proxy','server':'127.0.0.1','server_port':10808},{'type':'direct','tag':'direct'}],'route':{'auto_detect_interface':True,'final':'proxy','rules':[{'network':'udp','port':[443],'action':'reject'},{'process_path':['/opt/v2rayn-bin/bin/xray/xray'],'outbound':'direct'},{'protocol':'dns','action':'hijack-dns'},{'ip_is_private':True,'outbound':'direct'},{'rule_set':['china'],'outbound':'direct'},{'domain_suffix':['example.cn'],'outbound':'direct'},{'clash_mode':'Global','outbound':'proxy'}],'rule_set':[{'tag':'china','type':'local','path':'/rules/china.srs'}]},'dns':{'rules':[{'rule_set':['china'],'server':'local'}]}}
class FrontendTests(unittest.TestCase):
 def test_business_rules_removed_and_transport_preserved(self):
  old=fixture();new=m.build(old)
  self.assertEqual(len(new['route']['rules']),4);self.assertEqual(len(old['route']['rules']),7)
  self.assertEqual(new['inbounds'],old['inbounds']);self.assertEqual(new['dns'],old['dns']);self.assertEqual(new['route']['rule_set'],old['route']['rule_set'])
  self.assertEqual(new['route']['final'],'proxy');self.assertTrue(any(r.get('process_path') for r in new['route']['rules']))
 def test_wrong_listener_or_missing_bypass_refused(self):
  c=fixture();c['outbounds'][0]['server']='example.org'
  with self.assertRaises(ValueError):m.build(c)
  c=fixture();c['route']['rules']=[{'domain_suffix':['example.cn'],'outbound':'direct'}]
  with self.assertRaises(ValueError):m.build(c)
 def test_unknown_route_action_not_silently_migrated(self):
  c=fixture();c['route']['rules'].append({'action':'new-custom-action'})
  with self.assertRaises(ValueError):m.build(c)
if __name__=='__main__':unittest.main()
