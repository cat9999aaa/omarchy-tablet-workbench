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
 def test_exit_zero_only_means_submitted_not_verified(self):
  r=execute(prepare('brightness',{'percent':42},False),True,lambda:False,lambda cmd:0)
  self.assertEqual(r['stage'],'submitted');self.assertFalse(r['verified'])
 def test_audio_and_power_actions_share_resource(self):
  from unittest.mock import patch
  with patch('control_center.audio_sink',return_value='alsa_test'):
   self.assertEqual(prepare('volume',{'percent':50},False)['resource'],prepare('mute',{},False)['resource'])
  self.assertEqual(prepare('power-saver',{},False)['resource'],prepare('balanced',{},False)['resource'])
 def test_lock_while_process_pending_cancels_request(self):
  from unittest.mock import patch
  from control_center import run
  import sys,time
  start=time.monotonic()
  with patch('control_center.read_lock',return_value=True):
   self.assertEqual(run([sys.executable,'-c','import time; time.sleep(30)']),126)
  self.assertLess(time.monotonic()-start,4)

 def test_nightlight_uses_native_toggle_and_shared_guard(self):
  r=prepare('nightlight',{},False)
  self.assertEqual(r['argv'],['omarchy','toggle','nightlight'])
  self.assertFalse(r['requires_confirmation'])
  for locked in (True,None):
   with self.assertRaises(PermissionError):prepare('nightlight',{},locked)
  calls=[]
  self.assertEqual(execute(r,False,lambda:True,lambda cmd:calls.append(cmd))['stage'],'locked')
  self.assertEqual(calls,[])
 def test_nightlight_readback_does_not_guess_off(self):
  from control_center import nightlight_status
  from unittest.mock import patch
  import json
  for temp,expected in [(4000,True),(6500,False),(6000,False),(None,None),('4000',None),(False,None)]:
   with patch('control_center.subprocess.check_output',return_value=json.dumps({'enabled':False,'temperature':temp})):
    self.assertIs(nightlight_status(100)['actual'],expected)
  with patch('control_center.subprocess.check_output',side_effect=OSError()):
   self.assertIsNone(nightlight_status(100)['actual'])
