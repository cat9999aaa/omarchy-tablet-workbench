import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('install',Path(__file__).parents[1]/'packaging/install.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class InstallTests(unittest.TestCase):
 def test_idempotent_and_exact_rollback(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);target=home/'.local/lib/omt-proxy/a';target.parent.mkdir(parents=True);target.write_bytes(b'old');target.chmod(0o700)
   installer=m.Installer(home);payload={'.local/lib/omt-proxy/a':(b'new',0o755),'.config/systemd/user/omt-proxy.service':(b'unit',0o644)}
   check=installer.plan(payload);self.assertEqual(target.read_bytes(),b'old');self.assertTrue(check['would_change'])
   result=installer.apply(payload);self.assertEqual(target.read_bytes(),b'new')
   again=installer.apply(payload);self.assertEqual(again['status'],'unchanged')
   installer.rollback(result['transaction']);self.assertEqual(target.read_bytes(),b'old');self.assertEqual(target.stat().st_mode&0o777,0o700);self.assertFalse((home/'.config/systemd/user/omt-proxy.service').exists())
 def test_symlink_and_unrelated_paths_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);other=home/'other';other.mkdir();(home/'.local').symlink_to(other)
   with self.assertRaises(ValueError):m.Installer(home).plan({'.local/lib/omt-proxy/a':(b'x',0o755)})
   with self.assertRaises(ValueError):m.Installer(home).plan({'Documents/personal':(b'x',0o600)})
 def test_write_failure_restores_prior_files(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);a=home/'.local/lib/omt-proxy/a';a.parent.mkdir(parents=True);a.write_bytes(b'old')
   class Broken(m.Installer):
    count=0
    def atomic(self,path,data,mode):
     if str(path).endswith('/b'):raise PermissionError('injected')
     return super().atomic(path,data,mode)
   with self.assertRaises(PermissionError):Broken(home).apply({'.local/lib/omt-proxy/a':(b'new',0o755),'.local/lib/omt-proxy/b':(b'new',0o755)})
   self.assertEqual(a.read_bytes(),b'old')
 def test_external_edit_not_overwritten_on_rollback(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);installer=m.Installer(home);r=installer.apply({'.local/lib/omt-proxy/a':(b'new',0o755)})
   p=home/'.local/lib/omt-proxy/a';p.write_bytes(b'external')
   with self.assertRaises(ValueError):installer.rollback(r['transaction'])
   self.assertEqual(p.read_bytes(),b'external')
if __name__=='__main__':unittest.main()
