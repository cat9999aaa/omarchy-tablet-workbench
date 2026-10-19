"""A C2 candidate must carry every runtime import and independently hashed helpers."""
from pathlib import Path
import importlib.util
import shutil
import tempfile
import unittest

class CandidateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.source=self.root/'source'
  shutil.copytree(Path(__file__).parent,self.source,ignore=shutil.ignore_patterns('__pycache__'))
  spec=importlib.util.spec_from_file_location('navigation_candidate',Path(__file__).with_name('candidate.py'))
  self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
 def test_complete_candidate_and_helper_tamper(self):
  out=self.root/'candidate';self.module.build(self.source,out)
  receipt=self.module.verify(out)
  self.assertEqual(receipt['version'],'0.1.5')
  self.assertEqual(set(receipt['helpers']),{'navigation.py','navigation_read.py','task_model.py','task_source.py','tasks.py'})
  self.assertTrue((out/'bundle/files/NavigationSession.js').is_file())
  self.assertFalse((out/'bundle/files/test_navigation.py').exists())
  (out/'helpers/navigation_read.py').write_text('changed')
  with self.assertRaises(ValueError):self.module.verify(out)
 def test_missing_any_runtime_import_refuses_package(self):
  names=['TaskCenter.qml','TaskSession.js','tasks.py','task_source.py','task_model.py','NavigationSession.js','navigation_read.py',*['Workbench/'+n for n in self.module.SHARED]]
  for index,name in enumerate(names):
   with self.subTest(name=name):
    path=self.source/name;original=path.read_bytes();path.unlink()
    try:
     with self.assertRaises(ValueError):self.module.build(self.source,self.root/('bad'+str(index)))
    finally:path.write_bytes(original)
 def test_bundle_tamper_refused_and_existing_output_preserved(self):
  out=self.root/'candidate';self.module.build(self.source,out)
  with self.assertRaises(FileExistsError):self.module.build(self.source,out)
  (out/'bundle/files/Workbench/ThemeContext.qml').unlink()
  with self.assertRaises(ValueError):self.module.verify(out)
if __name__=='__main__':unittest.main()
