import unittest
from control_center import prepare, execute

class ActionsTests(unittest.TestCase):
 def test_unknown_action_or_parameters_rejected(self):
  for a,p in [('bad;reboot',{}),('network',{'command':'sh'}),('brightness',{'percent':-1}),('brightness',{'percent':True}),('brightness',{'percent':101})]:
   with self.assertRaises(ValueError):prepare(a,p,False)
 def test_locked_or_unknown_fails_closed(self):
  for locked in (True,None):
   with self.assertRaises(PermissionError):prepare('network',{},locked)
 def test_close_proxy_requires_confirmation(self):
  r=prepare('proxy-off',{},False);calls=[]
  result=execute(r,False,lambda:False,lambda cmd:calls.append(cmd))
  self.assertEqual(result['stage'],'confirmation');self.assertEqual(calls,[])
 def test_recheck_after_prepare(self):
  r=prepare('network',{},False)
  result=execute(r,True,lambda:True,lambda cmd:0)
  self.assertEqual(result['stage'],'locked')
 def test_auth_cancel_is_not_success(self):
  r=prepare('touch-glove',{},False)
  result=execute(r,True,lambda:False,lambda cmd:126)
  self.assertFalse(result['ok']);self.assertEqual(result['stage'],'cancelled')
 def test_allowed_action_is_argument_list(self):
  self.assertEqual(prepare('brightness',{'percent':42},False)['argv'],['omarchy-shell','omarchy.monitor','brightness','42'])
 def test_duplicate_resource_is_busy(self):
  import tempfile,os,fcntl
  from unittest.mock import patch
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'XDG_RUNTIME_DIR':d}):
   with open(Path(d)/'pcadmin-control-network.lock','w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    self.assertEqual(execute(prepare('proxy-on',{},False),True,lambda:False,lambda cmd:0)['stage'],'busy')
