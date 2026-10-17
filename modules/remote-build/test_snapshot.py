import io,json,tarfile,tempfile,unittest
from pathlib import Path
import snapshot
class SnapshotTests(unittest.TestCase):
 def test_only_source_files_no_build_userdb_or_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);s=p/'src';s.mkdir();(s/'CMakeLists.txt').write_text('project(test)');(s/'src').mkdir();(s/'src/a.cpp').write_text('code');(s/'build').mkdir();(s/'build/password').write_text('private');(s/'rime').mkdir();(s/'rime/personal.userdb.txt').write_text('private')
   (s/'rime/custom_phrase.txt').write_text('private');(s/'rime/personal.dict.yaml').write_text('private')
   manifest=snapshot.create_snapshot(s,p/'source.tar.gz')
   self.assertEqual(set(manifest),{'CMakeLists.txt','src/a.cpp'})
   (s/'src/leak.cpp').symlink_to(s/'build/password')
   with self.assertRaises(ValueError):snapshot.create_snapshot(s,p/'other.tar.gz')
 def test_verify_rejects_tamper_escape_and_links(self):
  for name,kind in [('../escape',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),('safe',tarfile.SYMTYPE)]:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    p=Path(d)/'bad.tar.gz'
    with tarfile.open(p,'w:gz') as t:
     m=tarfile.TarInfo(name);m.type=kind;m.linkname='/etc/passwd';t.addfile(m)
    with self.assertRaises(ValueError):snapshot.verify_archive(p,{})
 def test_changed_file_rejected_and_original_verified(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);s=p/'src';s.mkdir();(s/'CMakeLists.txt').write_text('source')
   manifest=snapshot.create_snapshot(s,p/'a.tar.gz');snapshot.verify_archive(p/'a.tar.gz',manifest)
   manifest['CMakeLists.txt']='0'*64
   with self.assertRaises(ValueError):snapshot.verify_archive(p/'a.tar.gz',manifest)
if __name__=='__main__':unittest.main()
