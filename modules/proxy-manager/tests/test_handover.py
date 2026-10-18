import importlib.util
from pathlib import Path
import unittest
import json
import tempfile
import os
import subprocess
import fcntl
import time
import sys
from unittest.mock import patch,Mock
spec=importlib.util.spec_from_file_location('handover',Path(__file__).parents[1]/'integration/handover.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Adapter:
 def __init__(self,failed=None):self.failed=failed;self.calls=[]
 def step(self,name):self.calls.append(name);return name!=self.failed
class HandoverTests(unittest.TestCase):
 def test_watchdog_precedes_old_owner_stop(self):
  a=Adapter('arm');r=m.sequence(a)
  self.assertFalse(r['verified']);self.assertNotIn('stop_old',a.calls)
 def test_failure_restores_previous_owner(self):
  a=Adapter('verify');r=m.sequence(a)
  self.assertFalse(r['verified']);self.assertTrue(r['restored']);self.assertEqual(a.calls[-1],'restore')
  self.assertLess(a.calls.index('arm'),a.calls.index('stop_old'))
 def test_only_verified_cutover_commits(self):
  a=Adapter();self.assertTrue(m.sequence(a)['verified']);self.assertEqual(a.calls[-2:],['verify','commit'])
 def test_boot_reverts_uncommitted_owner_without_starting_services(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);token='a'*32
   (root/'owner.json').write_text('{"owner":"omt-proxy"}')
   (root/'handover.json').write_text(json.dumps({'token':token,'stage':'switching','frontend_verified_with_legacy':True}))
   with patch.object(m.subprocess,'run',side_effect=AssertionError('boot recovery must not start services')):
    result=m.recover_boot(root)
   self.assertTrue(result['owner_restored']);self.assertFalse((root/'owner.json').exists());self.assertEqual(json.loads((root/'handover.json').read_text())['stage'],'restored')
 def test_restore_requires_live_old_owner_probe(self):
  a=m.System('b'*32);a.read=lambda:{'stage':'switching','watcher':False,'old_enabled':True,'frontend_verified_with_legacy':True};a.save=Mock();a.systemctl=Mock(return_value=True)
  owned=Mock();owned.policy_state.return_value=(False,False,True);owned.probe.return_value=False;a.owned=lambda:owned;a.ownership=lambda unit:True
  with tempfile.TemporaryDirectory() as d:
   a.root=Path(d);self.assertFalse(a.step('restore'))
  a.save.assert_not_called()
 def test_unknown_intent_does_not_restart_watcher(self):
  a=m.System('c'*32);a.read=lambda:{'stage':'switching','watcher':True,'old_enabled':True,'frontend_verified_with_legacy':True};a.save=Mock()
  calls=[]
  def systemctl(*args):calls.append(args);return args[0]!='is-active'
  a.systemctl=systemctl;owned=Mock();owned.policy_state.return_value=(False,False,None);a.owned=lambda:owned
  with tempfile.TemporaryDirectory() as d:
   a.root=Path(d);self.assertTrue(a.step('restore'))
  self.assertNotIn(('start','pcadmin-cell-proxy.service'),calls);self.assertNotIn(('start','v2rayn.service'),calls)
 def test_lock_during_authorization_revokes_request(self):
  a=m.System('d'*32);owned=Mock();owned.policy_allows.side_effect=[True,False];owned.policy_state.return_value=(False,False,True);a.owned=lambda:owned
  child=Mock();child.poll.return_value=None;child.pid=123456;child.wait.return_value=0
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'XDG_RUNTIME_DIR':d}),patch.object(m.subprocess,'Popen',return_value=child),patch.object(m.os,'killpg'):
   with self.assertRaises(ValueError):a.front('prepare')
   self.assertEqual(list(Path(d).rglob('request-*.json')),[])
  child.communicate.assert_not_called()
 def test_handover_recovery_waits_for_owned_lock_release(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'.local/state/omt-proxy';root.mkdir(parents=True);token='e'*32
   (root/'handover.json').write_text(json.dumps({'token':token,'stage':'committed'}))
   with (root/'handover.lock').open('w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    child=subprocess.Popen([sys.executable,str(Path(m.__file__)),'recover',token],env={**os.environ,'HOME':d},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
     time.sleep(.6);self.assertIsNone(child.poll());fcntl.flock(lock,fcntl.LOCK_UN)
     output,_=child.communicate(timeout=4);self.assertIn(b'"restored": false',output)
    finally:
     if child.poll() is None:child.kill();child.wait()
 def test_offline_owner_restore_is_not_network_success(self):
  a=m.System('f'*32);a.read=lambda:{'stage':'restored','network_verified':False,'recovery':'boot-owner-selection'}
  self.assertFalse(a.step('restore'))
if __name__=='__main__':unittest.main()
