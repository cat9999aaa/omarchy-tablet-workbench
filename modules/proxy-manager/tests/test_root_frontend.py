import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
spec=importlib.util.spec_from_file_location('frontroot',Path(__file__).parents[1]/'integration/root_frontend.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FrontendTests(unittest.TestCase):
 def fixture(self,path):
  config=path/'tun.json';config.write_text('{"original":true}')
  adapter=Mock();adapter.check.return_value=True;adapter.arm.return_value=True;adapter.restart.return_value=True
  return config,adapter,m.Controller(path,adapter)
 def test_timer_armed_before_config_replacement(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);cfg,a,c=self.fixture(path);a.arm.return_value=False
   token=c.prepare(b'{"candidate":true}')['token']
   self.assertFalse(c.apply(token)['ok']);self.assertEqual(json.loads(cfg.read_text()),{'original':True});a.restart.assert_not_called()
 def test_failed_restart_restores_original(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);cfg,a,c=self.fixture(path);a.restart.side_effect=[False,True]
   token=c.prepare(b'{"candidate":true}')['token'];r=c.apply(token)
   self.assertFalse(r['ok']);self.assertTrue(r['restored']);self.assertEqual(json.loads(cfg.read_text()),{'original':True})
 def test_stale_timer_and_external_edit_never_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);cfg,a,c=self.fixture(path);token=c.prepare(b'{"candidate":true}')['token'];self.assertTrue(c.apply(token)['ok']);c.commit(token)
   self.assertTrue(c.rollback(token)['ignored']);self.assertEqual(json.loads(cfg.read_text()),{'candidate':True})
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);cfg,a,c=self.fixture(path);token=c.prepare(b'{"candidate":true}')['token'];c.apply(token);cfg.write_text('{"external":true}')
   self.assertFalse(c.rollback(token)['ok']);self.assertEqual(json.loads(cfg.read_text()),{'external':True})
 def test_boot_restore_does_not_start_or_restart_network(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);cfg,a,c=self.fixture(path);token=c.prepare(b'{"candidate":true}')['token'];c.apply(token);a.reset_mock()
   r=c.rollback(token,restart=False);self.assertTrue(r['restored']);a.restart.assert_not_called();self.assertEqual(json.loads(cfg.read_text()),{'original':True})
 def test_privileged_request_requires_live_token_and_unlocked_session(self):
  for unlocked,valid in ((False,True),(True,False),(None,True)):
   gate=Mock();gate.session_unlocked.return_value=unlocked;gate.request_active.return_value=valid
   with self.assertRaises(PermissionError):m.require_request(gate,1000,'a'*36,'apply')
  gate=Mock();gate.session_unlocked.return_value=True;gate.request_active.return_value=True
  m.require_request(gate,1000,'a'*36,'apply');gate.request_active.assert_called_with(1000,'a'*36,'proxy-front-apply')
if __name__=='__main__':unittest.main()
