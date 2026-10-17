import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from release import ReleaseManager,ReleaseError,pack
from unittest.mock import patch

class Releases(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  home=patch('release.Path.home',return_value=self.root/'home');home.start();self.addCleanup(home.stop)
  self.plugins=self.root/'plugins';self.plugin=self.plugins/'test.touchime';self.plugin.mkdir(parents=True)
  self.old={'schemaVersion':1,'id':'test.touchime','name':'Test','version':'1.0','kinds':['overlay'],'entryPoints':{'overlay':'old.qml'}}
  (self.plugin/'manifest.json').write_text(json.dumps(self.old));(self.plugin/'old.qml').write_text('old release')
  self.bundle=self.root/'bundle';(self.bundle/'files/qml').mkdir(parents=True)
  (self.bundle/'files/qml/Main.qml').write_text('new release')
  self.new={**self.old,'version':'2.0','entryPoints':{'overlay':'qml/Main.qml'}}
  (self.bundle/'manifest.json').write_text(json.dumps(self.new));self.hashes()
  self.calls=[];self.live='1.0';self.fail_new=False;self.fail_old=False;self.validation_fails=False;self.concurrent=None
  self.manager=ReleaseManager(self.plugins,self.root/'state',self.run_command,timeout=.02)
 def hashes(self):
  files={str(p.relative_to(self.bundle/'files')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.bundle/'files').rglob('*') if p.is_file()}
  (self.bundle/'files.json').write_text(json.dumps({'schema':1,'sha256':files}))
 def run_command(self,args):
  self.calls.append(args)
  if args[:3]==['omarchy','plugin','validate']:
   if self.concurrent=='validate':(self.plugin/'manifest.json').write_text(json.dumps({**self.old,'description':'user edit'}))
   if self.validation_fails:raise ReleaseError('validation rejected')
   candidate=Path(args[3]);d=json.loads((candidate/'manifest.json').read_text())
   self.assertTrue(all((candidate/p).is_file() for p in d['entryPoints'].values()))
   return ''
  if args==['omarchy-shell','shell','rescanPlugins']:
   self.live=json.loads((self.plugin/'manifest.json').read_text())['version']
   if self.concurrent=='rescan' and self.live=='2.0':(self.plugin/'manifest.json').write_text(json.dumps({**self.new,'description':'concurrent user edit'}))
   if self.concurrent=='rollback-rescan' and self.live=='1.0':(self.plugin/'manifest.json').write_text(json.dumps({**self.old,'description':'concurrent rollback edit'}))
   return ''
  if args==['omarchy-shell','omtInput','version']:
   if self.fail_new and self.live=='2.0':return 'unready'
   if self.fail_old and self.live=='1.0':return 'unready'
   return self.live
  if args==['omarchy-shell','omtInput','ready']:
   if self.concurrent=='ready':(self.plugin/'manifest.json').write_text(json.dumps({**self.old,'description':'initial probe edit'}))
   return 'true'
  raise AssertionError('Unexpected command: '+repr(args))
 def apply(self):return self.manager.apply(self.bundle,'test.touchime','ime')
 def test_apply_and_explicit_rollback_keep_old_files(self):
  result=self.apply();self.assertEqual(result['status'],'applied')
  self.assertEqual(self.live,'2.0');self.assertEqual((self.plugin/'old.qml').read_text(),'old release')
  current=json.loads((self.plugin/'manifest.json').read_text());self.assertTrue(current['entryPoints']['overlay'].startswith('workbench-releases/'))
  release=self.plugin/current['entryPoints']['overlay'];self.assertTrue(release.exists())
  rolled=self.manager.rollback('test.touchime',result['transaction'],'ime');self.assertEqual(rolled['status'],'rolled-back')
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text()),self.old);self.assertTrue(release.exists())
 def test_pack_and_refuse_recursive_output(self):
  result=pack(self.bundle/'manifest.json',self.bundle/'files',self.root/'packed')
  self.assertEqual(result['status'],'packed')
  self.assertTrue(self.manager.plan(self.root/'packed','test.touchime','ime')['would_change'])
  with patch('release.shutil.copytree',side_effect=AssertionError('Must reject before copying')):
   with self.assertRaises(ReleaseError):pack(self.bundle/'manifest.json',self.bundle/'files',self.bundle/'files/nested')
 def test_malformed_recovery_record_is_rejected(self):
  result=self.apply();journal=self.root/'state/test.touchime'/result['transaction']/'transaction.json'
  data=json.loads(journal.read_text());del data['before_sha256'];journal.write_text(json.dumps(data))
  with self.assertRaises(ReleaseError):self.manager.rollback('test.touchime',result['transaction'],'ime')
 def test_concurrent_publisher_is_refused(self):
  with self.manager.locked('test.touchime'):
   with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(self.calls,[])
 def test_dry_run_does_not_write_or_call_mutators(self):
  before={str(p.relative_to(self.root)) for p in self.root.rglob('*')}
  self.assertTrue(self.manager.plan(self.bundle,'test.touchime','ime')['would_change'])
  self.assertEqual(before,{str(p.relative_to(self.root)) for p in self.root.rglob('*')});self.assertEqual(self.calls,[])
 def test_tampered_missing_extra_files_fail(self):
  p=self.bundle/'files/qml/Main.qml';p.write_text('tampered')
  with self.assertRaises(ReleaseError):self.apply()
  p.unlink()
  with self.assertRaises(ReleaseError):self.apply()
  p.write_text('new release');(p.parent/'extra.qml').write_text('extra')
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(self.calls,[])
 def test_symlink_and_escape_fail(self):
  (self.bundle/'files/qml/link.qml').symlink_to(self.plugin/'old.qml')
  with self.assertRaises(ReleaseError):self.apply()
  (self.bundle/'files/qml/link.qml').unlink()
  d=json.loads((self.bundle/'files.json').read_text());d['sha256']['../outside']='0'*64;(self.bundle/'files.json').write_text(json.dumps(d))
  with self.assertRaises(ReleaseError):self.apply()
 def test_wrong_id_profile_same_version_refused(self):
  with self.assertRaises(ReleaseError):self.manager.apply(self.bundle,'../test.touchime','ime')
  with self.assertRaises(ReleaseError):self.manager.apply(self.bundle,'test.touchime','network')
  d={**self.new,'id':'other.touchime'};(self.bundle/'manifest.json').write_text(json.dumps(d))
  with self.assertRaises(ReleaseError):self.apply()
  (self.bundle/'manifest.json').write_text(json.dumps({**self.new,'version':'1.0'}))
  with self.assertRaises(ReleaseError):self.apply()
 def test_duplicate_json_and_invalid_types_fail(self):
  (self.bundle/'files.json').write_text('{"schema":1,"schema":1,"sha256":{}}')
  with self.assertRaises(ReleaseError):self.apply()
  self.hashes()
  for change in ({'version':2},{'id':12},{'schemaVersion':True}):
   (self.bundle/'manifest.json').write_text(json.dumps({**self.new,**change}))
   with self.assertRaises(ReleaseError):self.apply()
 def test_state_cannot_be_inside_watched_directory(self):
  with self.assertRaises(ReleaseError):ReleaseManager(self.plugins,self.root/'unused/../plugins/state',self.run_command)
 def test_validation_failure_does_not_change_current(self):
  self.validation_fails=True
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text()),self.old)
  self.assertFalse(any(c==['omarchy-shell','shell','rescanPlugins'] for c in self.calls))
 def test_precommit_concurrent_edit_preserved(self):
  self.concurrent='validate'
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text())['description'],'user edit')
 def test_failed_new_probe_restores_old_and_verifies(self):
  self.fail_new=True
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(self.live,'1.0');self.assertEqual(json.loads((self.plugin/'manifest.json').read_text()),self.old)
  journals=list((self.root/'state').rglob('transaction.json'));self.assertEqual(len(journals),1)
  self.assertEqual(json.loads(journals[0].read_text())['status'],'rolled-back')
 def test_postcommit_concurrent_edit_is_not_overwritten(self):
  self.fail_new=True;self.concurrent='rescan'
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text())['description'],'concurrent user edit')
 def test_initial_probe_concurrent_edit_preserved(self):
  self.concurrent='ready'
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text())['description'],'initial probe edit')
  self.assertFalse(any(c[:3]==['omarchy','plugin','validate'] for c in self.calls))
 def test_successful_probe_cannot_hide_concurrent_edit(self):
  self.concurrent='rescan'
  with self.assertRaises(ReleaseError):self.apply()
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text())['description'],'concurrent user edit')
  journal=next((self.root/'state').rglob('transaction.json'))
  self.assertEqual(json.loads(journal.read_text())['status'],'conflict-preserved')
 def test_successful_rollback_probe_cannot_hide_concurrent_edit(self):
  result=self.apply();self.concurrent='rollback-rescan'
  with self.assertRaises(ReleaseError):self.manager.rollback('test.touchime',result['transaction'],'ime')
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text())['description'],'concurrent rollback edit')
  journal=next((self.root/'state').rglob('transaction.json'))
  self.assertEqual(json.loads(journal.read_text())['status'],'conflict-preserved')
 def test_rollback_current_changed_refused(self):
  result=self.apply();(self.plugin/'manifest.json').write_text(json.dumps({**self.new,'description':'user'}))
  with self.assertRaises(ReleaseError):self.manager.rollback('test.touchime',result['transaction'],'ime')
  self.assertEqual(json.loads((self.plugin/'manifest.json').read_text())['description'],'user')
 def test_missing_backup_and_bad_transaction_refused(self):
  result=self.apply()
  with self.assertRaises(ReleaseError):self.manager.rollback('test.touchime','../bad','ime')
  (self.root/'state/test.touchime'/result['transaction']/'before.json').unlink()
  with self.assertRaises(ReleaseError):self.manager.rollback('test.touchime',result['transaction'],'ime')
 def test_probe_failed_recovery_is_not_success(self):
  result=self.apply();self.fail_old=True
  with self.assertRaises(ReleaseError):self.manager.rollback('test.touchime',result['transaction'],'ime')
  journal=self.root/'state/test.touchime'/result['transaction']/'transaction.json'
  self.assertEqual(json.loads(journal.read_text())['status'],'rollback-unverified')

if __name__=='__main__':unittest.main()
