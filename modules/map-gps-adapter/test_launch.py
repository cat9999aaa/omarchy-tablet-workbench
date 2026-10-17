import hashlib,json,tempfile,unittest
from pathlib import Path
from launch import checked_environment
class Launcher(unittest.TestCase):
 def setUp(self):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);self.root=Path(d.name);self.binary=self.root/'plugins/position/libworkbench_gpsd.so';self.binary.parent.mkdir(parents=True);self.binary.write_bytes(b'fixture')
  self.meta={'schema':1,'qt_versions':['6.11.2','6.11.2'],'binary_sha256':hashlib.sha256(b'fixture').hexdigest()};self.save()
 def save(self):(self.root/'release.json').write_text(json.dumps(self.meta))
 def test_environment_is_application_local(self):
  original={'LANG':'zh_CN.UTF-8','QT_PLUGIN_PATH':'/existing'};out=checked_environment(self.root,original,['6.11.2','6.11.2']);self.assertEqual(original['QT_PLUGIN_PATH'],'/existing');self.assertEqual(out['QT_PLUGIN_PATH'],str(self.root/'plugins')+':/existing');self.assertEqual(out['LANG'],original['LANG'])
 def test_abi_mismatch_fails(self):
  with self.assertRaises(ValueError):checked_environment(self.root,{},['6.12','6.12'])
 def test_tampered_or_missing_binary_fails(self):
  self.binary.write_bytes(b'changed')
  with self.assertRaises(ValueError):checked_environment(self.root,{},self.meta['qt_versions'])
  self.binary.unlink()
  with self.assertRaises(ValueError):checked_environment(self.root,{},self.meta['qt_versions'])
 def test_link_and_bad_schema_fail(self):
  self.binary.unlink();target=self.root/'target';target.write_bytes(b'fixture');self.binary.symlink_to(target)
  with self.assertRaises(ValueError):checked_environment(self.root,{},self.meta['qt_versions'])
  self.binary.unlink();self.binary.write_bytes(b'fixture');self.meta['schema']=2;self.save()
  with self.assertRaises(ValueError):checked_environment(self.root,{},self.meta['qt_versions'])
if __name__=='__main__':unittest.main()
