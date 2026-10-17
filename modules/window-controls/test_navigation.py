import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('navigation',Path(__file__).with_name('navigation.py'))
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
class NavigationTests(unittest.TestCase):
 def test_rotation_opens_window_actions_directly(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n,'load_bindings',return_value=n.DEFAULTS),patch.object(n,'run',return_value=True) as run:
   self.assertTrue(n.key_action('rotation'))
   self.assertEqual(run.call_args.args[0], ['omarchy-shell','pcadmin.navigation','toggle','窗口'])
 def test_defaults(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(n.load_bindings(Path(d)/'keys.json'),n.DEFAULTS)
 def test_roundtrip_and_reset(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'keys.json';v=dict(n.DEFAULTS,P1='desktops');n.save_bindings(p,v);self.assertEqual(n.load_bindings(p),v)
   n.save_bindings(p,n.DEFAULTS);self.assertEqual(n.load_bindings(p),n.DEFAULTS)
 def test_arbitrary_commands_rejected(self):
  for bad in [dict(n.DEFAULTS,P1='sh -c bad'),dict(n.DEFAULTS,P1='authorize'),dict(n.DEFAULTS,P3='voice'),dict(n.DEFAULTS,POWER='close')]:
   with self.assertRaises(ValueError):n.validate_bindings(bad)
 def test_invalid_saved_config_not_executed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'keys.json';p.write_text('{bad');self.assertEqual(n.load_bindings(p),n.DEFAULTS)
 def test_lock_unknown_refuses(self):
  for state in ['true','','error']:
   with patch.object(n,'output',return_value=state):self.assertFalse(n.unlocked())
 def test_window_injection_refused(self):
  for v in [{'address':'0x12;evil','pid':1},{'address':'0x0','pid':1},{'address':'0x12','pid':0}]:
   with self.assertRaises(ValueError):n.window_script('close',v)
 def test_window_script_bound_and_allowlisted(self):
  script=n.window_script('maximize',{'address':'0xab','pid':12})
  self.assertIn('w.pid==12',script);self.assertIn('w.address=="0xab"',script)
  self.assertIn('maximized',script)
  with self.assertRaises(ValueError):n.window_script('eval',{'address':'0xab','pid':12})
 def test_workspace_validation(self):
  for bad in [0,11,'1;bad',True]:
   with self.assertRaises(ValueError):n.workspace_id(bad)
  self.assertEqual(n.workspace_id(10),10)
 def test_key_routes_only_one_action(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n,'load_bindings',return_value=n.DEFAULTS),patch.object(n,'run',return_value=True) as run:
   self.assertTrue(n.key_action('P1'));self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[0],['omarchy-shell','omtInput','toggle'])
 def test_locked_key_does_not_run(self):
  with patch.object(n,'unlocked',return_value=False),patch.object(n,'run') as run:
   self.assertFalse(n.key_action('P3'));run.assert_not_called()
if __name__=='__main__':unittest.main()
