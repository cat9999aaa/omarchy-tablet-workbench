"""Action scope validation; actual compositor behavior has a separate gate."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import navigation as n

class ActionScopeTests(unittest.TestCase):
 def test_legacy_window_and_desktop_requests_do_not_dispatch(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n,'run',return_value=True) as run:
   for name in ['switch','restore','close','maximize','move']:
    result=n.action({'action':name,'target':{'address':'0xab','pid':12},'workspace':1})
    self.assertFalse(result['ok']);self.assertEqual(result['reason_code'],'context-changed')
   run.assert_not_called()
 def test_missing_scope_does_not_launch_or_save(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n,'run') as run,patch.object(n,'save_bindings') as save:
   for name in ['browser','files','launcher','keyboard','voice','control-center','bindings','defaults']:
    self.assertFalse(n.action({'action':name})['ok'])
   run.assert_not_called();save.assert_not_called()
 def test_guard_precedes_window_check_and_dispatch(self):
  code=n.window_script('close',{'address':'0xab','pid':12},output='HEADLESS-1')
  self.assertLess(code.index('get_active_monitor'),code.index('get_active_window'))
  self.assertLess(code.index('w.pid==12'),code.index('hl.dispatch'))
 def test_output_quoted_and_control_chars_rejected(self):
  code=n.window_script('close',{'address':'0xab','pid':12},output='virtual"\\quoted')
  self.assertIn('"virtual\\"\\\\quoted"',code)
  for value in [None,'',True,'x\ny','x\x00y','x'*257]:
   with self.assertRaises(ValueError):n.window_script('close',{'address':'0xab','pid':12},output=value)
 def test_switch_and_restore_use_one_eval(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='ok')) as run:
   for name in ['switch','restore']:
    run.reset_mock();self.assertTrue(n.action({'action':name,'workspace':3,'context':{'output':'HEADLESS-2'}})['ok'])
    self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[0][:2],['hyprctl','eval'])
    self.assertIn('get_active_monitor',run.call_args.args[0][2])
 def test_missing_compositor_api_has_explicit_failure(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='error: capability-unavailable')):
   result=n.action({'action':'restore','context':{'output':'HEADLESS-2'}})
   self.assertFalse(result['ok']);self.assertEqual(result['reason_code'],'capability-unavailable')
 def test_cross_process_launch_checks_snapshot_context(self):
  with patch.object(n,'unlocked',return_value=True),patch.object(n,'read_json',side_effect=n.ReadError('context-changed')),patch.object(n,'run') as run:
   result=n.action({'action':'browser','context':{'output':'HEADLESS-2'},'target':None})
   self.assertFalse(result['ok']);run.assert_not_called()
if __name__=='__main__':unittest.main()
