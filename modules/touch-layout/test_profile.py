import importlib.util
import json
import subprocess
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('touch_profile', Path(__file__).with_name('profile.py'))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

class Host:
    def __init__(self):
        self.context_value = {'theme':'dashen-overdrive', 'position':'bottom', 'output':'test', 'layout_hash':'fixed'}
        self.fits = True
        self.reload_ok = True
        self.callback = None
    def context(self): return dict(self.context_value)
    def measure(self, profile, theme_text=None): return {'fits':self.fits, 'reason':'ok' if self.fits else 'layout-overflow', 'targets':[{'id':'device','width':48,'height':56}]}
    def reload(self):
        if self.callback: self.callback()
        return self.reload_ok
    def verify(self, profile): return self.fits

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.host=Host()
        self.manager=api.Manager(self.root,self.host)
        self.original='# retain comment\n[bar]\nsize-horizontal = 30 # old\nicon-slot = 31\ntext = "#ffffff"\n[controls]\nnormal-color = "#123456"\n'
        for path in self.manager.targets:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(self.original)
    def apply(self,profile='touch'):
        planned=self.manager.plan(profile)
        self.assertEqual(planned['health'],'ready',planned)
        return self.manager.apply(planned['plan_id'])
    def test_transaction_history_is_bounded(self):
        for i in range(16):
            self.assertEqual(self.apply('touch' if i%2==0 else 'compact')['health'],'applied')
        self.assertLess(self.manager.state_path.stat().st_size,12000)
    def test_reload_timeout_restores_files(self):
        def timeout():raise subprocess.TimeoutExpired('fixed-reload',4)
        self.host.reload=timeout
        result=self.apply()
        self.assertEqual(result['health'],'unverified')
        for path in self.manager.targets:self.assertEqual(path.read_text(),self.original)

    def test_original_tokens_roundtrip(self):
        result=self.apply();self.assertEqual(result['health'],'applied',result)
        for path in self.manager.targets:
            self.assertIn('size-horizontal = 56 # old',path.read_text())
            self.assertIn('normal-color = "#123456"',path.read_text())
        self.assertEqual(self.apply('compact')['health'],'applied')
        for path in self.manager.targets:self.assertEqual(path.read_text(),self.original)
    def test_plan_is_read_only_and_apply_is_idempotent(self):
        planned=self.manager.plan('touch');self.assertFalse(self.manager.state_dir.exists())
        first=self.manager.apply(planned['plan_id']);self.assertEqual(first['health'],'applied')
        self.assertEqual(self.apply()['transaction_id'],first['transaction_id'])
    def test_concurrent_edit_preserved(self):
        planned=self.manager.plan('touch');path=self.manager.targets[0]
        path.write_text(self.original+'# concurrent\n')
        self.assertEqual(self.manager.apply(planned['plan_id'])['health'],'conflict')
        self.assertTrue(path.read_text().endswith('# concurrent\n'))
    def test_rollback_conflict_preserves_edit(self):
        result=self.apply();path=self.manager.targets[1];path.write_text(path.read_text()+'# concurrent\n')
        self.assertEqual(self.manager.rollback(result['transaction_id'])['health'],'conflict')
        self.assertTrue(path.read_text().endswith('# concurrent\n'))
    def test_rollback_and_private_state(self):
        result=self.apply()
        for path in self.manager.state_dir.iterdir():self.assertEqual(path.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.manager.rollback(result['transaction_id'])['health'],'rolled-back')
        for path in self.manager.targets:self.assertEqual(path.read_text(),self.original)
    def test_invalid_theme_or_position_rejected(self):
        for field,value in [('theme','other'),('position','top'),('position',None),('output',None)]:
            with self.subTest(field=field,value=value):
                old=self.host.context_value[field];self.host.context_value[field]=value
                self.assertEqual(self.manager.plan('touch')['health'],'unverified')
                self.host.context_value[field]=old
    def test_overflow_rejected(self):
        self.host.fits=False;self.assertEqual(self.manager.plan('touch')['health'],'unverified')
        self.assertEqual(self.manager.targets[0].read_text(),self.original)
    def test_reload_failure_restores_original(self):
        self.host.reload_ok=False
        self.assertEqual(self.apply()['health'],'unverified')
        for path in self.manager.targets:self.assertEqual(path.read_text(),self.original)
    def test_reload_failure_does_not_overwrite_concurrent_edit(self):
        self.host.reload_ok=False
        self.host.callback=lambda:self.manager.targets[0].write_text('# user edit\n')
        self.assertEqual(self.apply()['health'],'conflict')
        self.assertEqual(self.manager.targets[0].read_text(),'# user edit\n')
    def test_absent_keys_roundtrip_and_reject_ambiguous_toml(self):
        original='[bar]\ntext = "#ffffff" # keep\n'
        for path in self.manager.targets:path.write_text(original)
        self.assertEqual(self.apply()['health'],'applied');self.assertEqual(self.apply('compact')['health'],'applied')
        for path in self.manager.targets:self.assertEqual(path.read_text(),original)
        for text in ['[bar]\nsize-horizontal=30\nsize-horizontal=31\n','bar = { size-horizontal=30 }\n','[bar]\nsize-horizontal=true\n']:
            self.manager.targets[0].write_text(text)
            self.assertIn(self.manager.plan('touch')['health'],('unverified','conflict'))

if __name__=='__main__':unittest.main()
