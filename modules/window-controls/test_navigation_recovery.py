"""Rehearse the documented helper/UI file sequence in temporary HOME.

The real publisher and candidate bytes are used; official shell probes are synthetic.
This is filesystem recovery evidence, not desktop handoff or a production installer.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


class RecoveryRehearsal(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.home=Path(self.tmp.name)
  env=patch.dict(os.environ,{'HOME':str(self.home)});env.start();self.addCleanup(env.stop)
  spec=importlib.util.spec_from_file_location('recovery_candidate',Path(__file__).with_name('candidate.py'))
  self.candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.candidate)
  self.release=self.candidate.release
  self.package=self.home/'candidate';self.candidate.build(Path(__file__).parent,self.package)
  self.receipt=self.candidate.verify(self.package)
  self.plugins=self.home/'.config/omarchy/plugins';self.plugin=self.plugins/'pcadmin.navigation'
  self.plugin.mkdir(parents=True)
  self.old={**self.release.manifest(self.package/'bundle/manifest.json'),'version':'0.1.3'}
  (self.plugin/'manifest.json').write_text(json.dumps(self.old))
  (self.plugin/'Navigation.qml').write_text('import QtQuick\nItem {}\n')
  self.old_manifest=(self.plugin/'manifest.json').read_bytes()
  self.helpers=self.home/'tools/window-controls';self.helpers.mkdir(parents=True)
  (self.helpers/'navigation.py').write_bytes(b'# prior helper\n');(self.helpers/'navigation.py').chmod(0o750)
  self.preference=self.home/'.config/omarchy-tablet-workbench/buttons.json';self.preference.parent.mkdir(parents=True);self.preference.write_bytes(b'{"rotation":"windows"}\n')
  self.backup={name:((self.helpers/name).read_bytes(),(self.helpers/name).stat().st_mode&0o777) if (self.helpers/name).exists() else None for name in self.candidate.HELPERS}
  self.events=[];self.ui_restored=False
  self.manager=self.release.ReleaseManager(self.plugins,self.home/'transactions',self.shell,timeout=.02)
 def shell(self,args):
  if args==['omarchy-shell','lock','isLocked']:return 'false'
  if args[:3]==['omarchy','plugin','validate']:
   staged=Path(args[3]);manifest=self.release.manifest(staged/'manifest.json')
   self.assertTrue(all((staged/name).is_file() for name in manifest['entryPoints'].values()));return ''
  if args==['omarchy-shell','shell','rescanPlugins']:
   version=self.release.manifest(self.plugin/'manifest.json')['version']
   # Both switches happen before helper restoration, including inverse recovery.
   for name,digest in self.receipt['helpers'].items():self.assertEqual(self.candidate.digest(self.helpers/name),digest)
   self.events.append('ui-'+version);return ''
  if args==['omarchy-shell','pcadmin.navigation','state']:
   return json.dumps({'version':self.release.manifest(self.plugin/'manifest.json')['version']})
  raise AssertionError('Unexpected external operation: '+repr(args))
 def prepare(self):
  self.assertFalse(self.manager.plan(self.package/'bundle','pcadmin.navigation','navigation')['writes'])
  for name in self.candidate.HELPERS:
   shutil.copy2(self.package/'helpers'/name,self.helpers/name)
   self.assertEqual(self.candidate.digest(self.helpers/name),self.receipt['helpers'][name])
  self.events.append('helpers-prepared')
  result=self.manager.apply(self.package/'bundle','pcadmin.navigation','navigation')
  self.assertEqual(result['status'],'applied');return result['transaction']
 def restore_helpers(self):
  self.assertTrue(self.ui_restored,'restore UI before helpers')
  statuses={}
  for name,before in self.backup.items():
   path=self.helpers/name
   if not path.is_file() or path.is_symlink() or self.candidate.digest(path)!=self.receipt['helpers'][name]:
    statuses[name]='conflict-preserved';continue
   if before is None:path.unlink()
   else:path.write_bytes(before[0]);path.chmod(before[1])
   statuses[name]='restored'
  self.events.append('helpers-restored');return statuses
 def rollback_ui(self,transaction):
  result=self.manager.rollback('pcadmin.navigation',transaction,'navigation')
  self.assertEqual(result['status'],'rolled-back');self.ui_restored=True
 def test_upgrade_and_inverse_recovery_preserve_preferences_modes_and_absence(self):
  transaction=self.prepare();self.rollback_ui(transaction)
  self.assertEqual(set(self.restore_helpers().values()),{'restored'})
  self.assertEqual(self.events,['helpers-prepared','ui-0.1.6','ui-0.1.3','helpers-restored'])
  self.assertEqual((self.plugin/'manifest.json').read_bytes(),self.old_manifest)
  self.assertEqual((self.helpers/'navigation.py').read_bytes(),self.backup['navigation.py'][0])
  self.assertEqual((self.helpers/'navigation.py').stat().st_mode&0o777,0o750)
  self.assertFalse((self.helpers/'navigation_read.py').exists())
  self.assertEqual(self.preference.read_bytes(),b'{"rotation":"windows"}\n')
 def test_recovery_from_014_with_new_task_config(self):
  import task_config
  self.old['version']='0.1.4';(self.plugin/'manifest.json').write_text(json.dumps(self.old));self.old_manifest=(self.plugin/'manifest.json').read_bytes()
  path=self.home/'.config/omarchy-tablet-workbench/task-center.json';project=self.home/'project';project.mkdir()
  receipt=task_config.prepare(path,project)
  transaction=self.prepare();self.rollback_ui(transaction);self.restore_helpers()
  self.assertTrue(task_config.restore(path,receipt));self.assertFalse(path.exists())
  self.assertEqual((self.plugin/'manifest.json').read_bytes(),self.old_manifest)
 def test_config_restore_after_publisher_rejects_candidate(self):
  import task_config
  path=self.home/'.config/omarchy-tablet-workbench/task-center.json';project=self.home/'project';project.mkdir();receipt=task_config.prepare(path,project)
  (self.package/'bundle/files/TaskCenter.qml').write_text('tampered')
  with self.assertRaises(self.release.ReleaseError):self.manager.apply(self.package/'bundle','pcadmin.navigation','navigation')
  self.assertTrue(task_config.restore(path,receipt));self.assertFalse(path.exists());self.assertEqual((self.plugin/'manifest.json').read_bytes(),self.old_manifest)
 def test_helper_edit_after_ui_rollback_is_preserved(self):
  transaction=self.prepare();self.rollback_ui(transaction)
  (self.helpers/'navigation_read.py').write_bytes(b'# concurrent user edit\n')
  statuses=self.restore_helpers()
  self.assertEqual(statuses['navigation_read.py'],'conflict-preserved')
  self.assertEqual((self.helpers/'navigation_read.py').read_bytes(),b'# concurrent user edit\n')
  self.assertEqual(statuses['navigation.py'],'restored')
 def test_ui_conflict_blocks_helper_restoration(self):
  transaction=self.prepare();edited={**self.release.manifest(self.plugin/'manifest.json'),'description':'concurrent edit'}
  (self.plugin/'manifest.json').write_text(json.dumps(edited))
  with self.assertRaises(self.release.ReleaseError):self.rollback_ui(transaction)
  self.assertFalse(self.ui_restored)
  for name,digest in self.receipt['helpers'].items():self.assertEqual(self.candidate.digest(self.helpers/name),digest)
  self.assertEqual(self.release.manifest(self.plugin/'manifest.json'),edited)

if __name__=='__main__':unittest.main()
