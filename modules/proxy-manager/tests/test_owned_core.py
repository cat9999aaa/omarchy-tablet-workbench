import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('owned',Path(__file__).parents[1]/'integration/owned-core.py')
owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
class OwnedTests(unittest.TestCase):
 def test_checker_uses_fixed_core_and_hides_output(self):
  calls=[]
  def runner(argv,**kw):
   calls.append(argv)
   return subprocess.CompletedProcess(argv,0,b'Xray 26.10.10 example' if 'version' in argv else b'private-server-credential',b'')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'candidate.json';p.write_text('{}');p.chmod(0o600)
   out=owned.check(p,runner)
   self.assertTrue(out['ok']);self.assertNotIn('private',str(out));self.assertEqual(calls[1][0],str(owned.CORE));self.assertIn('-test',calls[1])
 def test_unsafe_file_and_unknown_core_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'candidate.json';p.write_text('{}');p.chmod(0o644)
   with self.assertRaises(ValueError):owned.check(p,lambda *a,**k: self.fail('invoked core'))
   p.chmod(0o600)
   out=owned.check(p,lambda argv,**kw:subprocess.CompletedProcess(argv,0,b'Xray 99.0.0',b''))
   self.assertFalse(out['ok']);self.assertEqual(out['error_code'],'unverified_core_version')
 def test_restart_only_owned_unit_and_probe_is_fresh(self):
  calls=[]
  def runner(argv,**kw):
   calls.append(argv)
   return subprocess.CompletedProcess(argv,0,b'204',b'')
  self.assertTrue(owned.restart(runner))
  self.assertEqual(calls,[['systemctl','--user','restart','omt-proxy-core.service']])
  self.assertTrue(owned.probe(runner))
  self.assertEqual(len(calls),3)
  self.assertIn('socks5h://127.0.0.1:10808',calls[1])
  self.assertNotIn('--proxy',calls[2])
 def test_probe_failure_not_healthy(self):
  self.assertFalse(owned.probe(lambda argv,**kw:subprocess.CompletedProcess(argv,7,b'',b'secret')))
 def test_activation_respects_lock_flight_and_manual_off(self):
  for locked,flight,enabled in [(None,False,True),(True,False,True),(False,True,True),(False,False,False),(False,None,True)]:
   self.assertFalse(owned.policy_allows(locked,flight,enabled))
  self.assertTrue(owned.policy_allows(False,False,True))
if __name__=='__main__':unittest.main()
