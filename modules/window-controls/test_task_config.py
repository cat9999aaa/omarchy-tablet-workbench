import importlib,tempfile,unittest
from pathlib import Path
class ConfigTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(Path(__file__).with_name('task_config.py').exists(),'config transaction missing')
  self.m=importlib.import_module('task_config');self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.r=Path(self.t.name);self.p=self.r/'config/tasks.json';self.project=self.r/'project';self.project.mkdir()
 def test_new_config_restores_absence(self):
  receipt=self.m.prepare(self.p,self.project);self.assertTrue(receipt['created']);self.assertEqual(self.p.stat().st_mode&0o777,0o600)
  self.assertTrue(self.m.restore(self.p,receipt));self.assertFalse(self.p.exists())
 def test_existing_and_concurrent_edits_preserved(self):
  receipt=self.m.prepare(self.p,self.project);self.p.write_text('user edit');self.assertFalse(self.m.restore(self.p,receipt));self.assertEqual(self.p.read_text(),'user edit')
  receipt=self.m.prepare(self.p,self.project);self.assertFalse(receipt['created']);self.assertTrue(self.m.restore(self.p,receipt));self.assertEqual(self.p.read_text(),'user edit')
 def test_link_destination_refused(self):
  self.p.parent.mkdir();target=self.r/'other';target.write_text('unchanged');self.p.symlink_to(target)
  with self.assertRaises(ValueError):self.m.prepare(self.p,self.project)
  self.assertEqual(target.read_text(),'unchanged')
if __name__=='__main__':unittest.main()
