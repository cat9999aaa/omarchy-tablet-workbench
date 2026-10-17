import json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_ime
class BuildScopeTests(unittest.TestCase):
 def test_scope_marker_and_valid_job_name_required(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   with self.assertRaises(ValueError):build_ime.execute(p,'job')
   (p/'build-scope.json').write_text('{}')
   with self.assertRaises(ValueError):build_ime.execute(p,'../outside')
 def test_missing_or_duplicate_ctest_cases_rejected(self):
  for names in [[],['engine'],list(build_ime.EXPECTED_TESTS)+['engine']]:
   with self.assertRaises(ValueError):build_ime.verify_test_inventory({'tests':[{'name':n} for n in names]})
  self.assertEqual(len(build_ime.verify_test_inventory({'tests':[{'name':n} for n in build_ime.EXPECTED_TESTS]})),9)
 def test_state_write_does_not_follow_existing_temp_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);outside=p/'outside';outside.write_text('preserve');job=p/'job';job.mkdir();(job/'result.tmp').symlink_to(outside);(job/'result.json').symlink_to(outside)
   build_ime.save(job/'result.json',{'status':'passed'})
   self.assertEqual(outside.read_text(),'preserve');self.assertFalse((job/'result.json').is_symlink())
 def test_child_symlink_cannot_escape_build_root(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);root=p/'root';root.mkdir();(root/'jobs').symlink_to(p,target_is_directory=True)
   with self.assertRaises(ValueError):build_ime.scoped(root,'jobs','other')
 def test_signature_failure_records_failure_without_artifact(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'build-scope.json').write_text('{}');job=root/'jobs/test';job.mkdir(parents=True);(job/'input.json').write_text(json.dumps({'target_abi':'matching','source_files':{}}))
   cache=root/'toolchain/ime-v1/packages';cache.mkdir(parents=True)
   for n in ('cmake.pkg.tar.zst','cmake.pkg.tar.zst.sig'):(cache/n).write_bytes(b'untrusted')
   def output(a):return 'cmake\t1\thttps://example.invalid/cmake.pkg.tar.zst' if '-Sp' in a else 'matching'
   def reject(a,**kw):
    if a[0]=='gpg':return
    if a[0]=='gpgv':raise subprocess.CalledProcessError(1,a)
    raise AssertionError('Unexpected external command')
   with patch.object(build_ime,'output',side_effect=output),patch.object(build_ime,'run',side_effect=reject):
    with self.assertRaises(subprocess.CalledProcessError):build_ime.execute(root,'test')
   self.assertEqual(json.loads((job/'result.json').read_text())['status'],'failed');self.assertFalse((job/'artifacts.tar.gz').exists());self.assertFalse((job/'source').exists())
if __name__=='__main__':unittest.main()

class EvidenceTests(unittest.TestCase):
 def test_skipped_test_does_not_count_as_passed(self):
  import xml.etree.ElementTree as ET
  with tempfile.TemporaryDirectory() as d:
   root=ET.Element('testsuite',{'failures':'0'});p=Path(d)/'results.xml'
   for name in build_ime.EXPECTED_TESTS:ET.SubElement(root,'testcase',{'name':name,'status':'run'})
   ET.ElementTree(root).write(p);self.assertTrue(build_ime.verify_junit(p))
   ET.SubElement(root[0],'skipped');ET.ElementTree(root).write(p)
   with self.assertRaises(ValueError):build_ime.verify_junit(p)
 def test_revoked_or_expired_signer_rejected(self):
  fingerprint='A'*40;status='[GNUPG:] VALIDSIG '+fingerprint+' 2026-01-01 1 0 4 0 1 10 00 '+fingerprint
  self.assertEqual(build_ime.verify_signature_status(status,set()),[fingerprint])
  with self.assertRaises(ValueError):build_ime.verify_signature_status(status,{fingerprint})
  with self.assertRaises(ValueError):build_ime.verify_signature_status(status+'\n[GNUPG:] EXPKEYSIG abc name',set())
  with self.assertRaises(ValueError):build_ime.verify_signature_status('',set())
