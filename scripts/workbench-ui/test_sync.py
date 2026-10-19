import importlib.util
from pathlib import Path
import tempfile
import unittest

class SyncTests(unittest.TestCase):
 def setUp(self):
  p=Path(__file__).with_name('sync.py')
  self.assertTrue(p.exists(),'controlled sync implementation missing')
  spec=importlib.util.spec_from_file_location('sync',p);self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
  self.source=self.root/'modules/workbench-ui';self.source.mkdir(parents=True)
  for n in ['TouchButton.qml','PanelHeader.qml','PanelBody.qml','Layout.js','State.js','Theme.js','ThemeContext.qml','StyledText.qml','ActionGrid.qml']:(self.source/n).write_text('source:'+n)
  for n in ['modules/control-center/Workbench','modules/network-center/Workbench','modules/battery-manager/panel/Workbench','modules/window-controls/Workbench']:(self.root/n).mkdir(parents=True)
 def test_write_check_and_drift(self):
  self.assertTrue(self.api.sync(self.root,False));self.assertEqual(self.api.sync(self.root,True),[]);self.assertEqual(self.api.sync(self.root,False),[])
  p=self.root/'modules/control-center/Workbench/Theme.js';p.write_text('stale');self.assertTrue(self.api.sync(self.root,False));self.assertEqual(self.api.sync(self.root,True),[])
 def test_presentation_imports_in_every_payload(self):
  self.assertEqual(self.api.sync(self.root,True),[])
  for target in self.api.DESTINATIONS:
   for name in ['ThemeContext.qml','StyledText.qml','ActionGrid.qml']:
    p=self.root/target/name
    self.assertTrue(p.is_file(),str(p))
    self.assertEqual(p.read_bytes(),(self.source/name).read_bytes())
 def test_unknown_file_prevents_any_write(self):
  p=self.root/'modules/window-controls/Workbench/private.txt';p.write_text('preserve')
  self.assertTrue(self.api.sync(self.root,True));self.assertEqual(p.read_text(),'preserve');self.assertFalse((self.root/'modules/control-center/Workbench/Theme.js').exists())
 def test_symlink_parent_and_source_rejected(self):
  p=self.source/'Theme.js';p.unlink();p.symlink_to(self.source/'State.js');self.assertTrue(self.api.sync(self.root,True))
  p.unlink();p.write_text('theme')
  p=self.root/'modules/control-center/Workbench';p.rmdir();p.symlink_to(self.source,target_is_directory=True);self.assertTrue(self.api.sync(self.root,True))
if __name__=='__main__':unittest.main()
