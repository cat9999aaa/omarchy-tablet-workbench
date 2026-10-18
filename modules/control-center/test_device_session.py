import select
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from test_device_mode import evidence
from device_session import mode_step, parse_request, read_preference, write_preference, output_policy

class SessionTests(unittest.TestCase):
    def request(self, **extra):
        return dict(choice='auto',last_effective='tablet',pending=None,**extra)
    def test_manual_never_collects(self):
        def fail(): raise AssertionError('manual probe')
        value=mode_step(dict(choice='desktop',last_effective='tablet',pending=None),collect=fail)
        self.assertEqual(value['mode']['effective'],'desktop')
        self.assertEqual(value['mode']['reason_code'],'manual')
        self.assertIsNone(value['evidence']['physical_keyboard_present'])
    def test_host_time_confirmation_and_slow_invalidates(self):
        times=iter([0,100]);v=mode_step(self.request(),collect=evidence,clock_ms=lambda:next(times))
        self.assertEqual(v['confirm_after_ms'],400)
        times=iter([0,2001]);v=mode_step(self.request(),collect=evidence,clock_ms=lambda:next(times))
        self.assertIsNone(v['mode']['pending']);self.assertEqual(v['mode']['health'],'unknown')
        self.assertIsNone(v['confirm_after_ms'])
    def test_strict_input(self):
        bad=[b'{"choice":"auto","last_effective":null,"pending":{"target":"desktop","since_ms":1e999,"last_seen_ms":1e999}}',b'x'*4097,b'{"choice":"auto","choice":"desktop"}',b'{"choice":NaN}',b'[]',b'{}',
             json.dumps(self.request(now_ms=0)).encode(),json.dumps({**self.request(),'pending':{'target':'desktop','since_ms':0,'last_seen_ms':0,'extra':1}}).encode()]
        for raw in bad:
            with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):parse_request('mode-step',raw)
        self.assertEqual(parse_request('mode-step',json.dumps(self.request()).encode()),self.request())

class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);p=patch.dict(os.environ,{'XDG_STATE_HOME':str(self.base)})
        p.start();self.addCleanup(p.stop)
        self.file=self.base/'pcadmin-control-center/modes.json'
    def test_roundtrip_and_distinct_outputs(self):
        self.assertEqual(read_preference('eDP-1')['choice'],'auto')
        self.assertTrue(write_preference('eDP-1','desktop')['saved'])
        self.assertTrue(write_preference('HDMI-A-1','tablet')['saved'])
        self.assertEqual(read_preference('eDP-1')['choice'],'desktop')
        self.assertEqual(read_preference('HDMI-A-1')['choice'],'tablet')
        self.assertEqual(self.file.stat().st_mode & 0o777,0o600)
    def test_bad_file_not_overwritten(self):
        self.assertTrue(write_preference('eDP-1','tablet')['saved'])
        for raw in [b'{',b'x'*4097,b'{"schema_version":2,"outputs":{}}']:
            self.file.write_bytes(raw)
            self.assertEqual(read_preference('eDP-1')['choice'],'auto')
            self.assertNotEqual(read_preference('eDP-1')['reason_code'],'ok')
            self.assertFalse(write_preference('eDP-1','desktop')['saved'])
            self.assertEqual(self.file.read_bytes(),raw)
    def test_unsafe_files_and_parent(self):
        self.assertTrue(write_preference('eDP-1','tablet')['saved'])
        self.file.unlink();target=self.base/'elsewhere';target.write_text('private')
        self.file.symlink_to(target)
        self.assertFalse(write_preference('eDP-1','desktop')['saved']);self.assertEqual(target.read_text(),'private')
        self.file.unlink();os.mkfifo(self.file,0o600)
        self.assertFalse(write_preference('eDP-1','desktop')['saved'])
        self.file.unlink();self.file.parent.rename(self.base/'old');self.file.parent.symlink_to(self.base/'old',target_is_directory=True)
        self.assertFalse(write_preference('eDP-1','desktop')['saved'])
    def test_owner_permissions_limits_and_failures_preserve(self):
        self.assertTrue(write_preference('eDP-1','tablet')['saved']);old=self.file.read_bytes()
        self.file.chmod(0o644);self.assertFalse(write_preference('eDP-1','desktop')['saved']);self.file.chmod(0o600)
        with patch('device_session.os.getuid',return_value=os.getuid()+1):self.assertFalse(write_preference('eDP-1','desktop')['saved'])
        for call in ['os.write','os.replace','os.fsync']:
            with patch('device_session.'+call,side_effect=OSError('disk failure')):
                self.assertFalse(write_preference('eDP-1','desktop')['saved'])
            self.assertEqual(self.file.read_bytes(),old)
        for i in range(15):self.assertTrue(write_preference('DP-'+str(i),'auto')['saved'])
        old=self.file.read_bytes();self.assertFalse(write_preference('DP-new','desktop')['saved']);self.assertEqual(self.file.read_bytes(),old)
    def test_killed_writer_does_not_make_old_preference_unreadable(self):
        self.assertTrue(write_preference('eDP-1','tablet')['saved'])
        code="import device_session as d,time;d.os.replace=lambda *a,**k:(print('READY',flush=True),time.sleep(30));d.write_preference('eDP-1','desktop')"
        p=subprocess.Popen([sys.executable,'-c',code],cwd=Path(__file__).parent,stdout=subprocess.PIPE)
        try:
            self.assertTrue(select.select([p.stdout],[],[],3)[0])
            self.assertEqual(p.stdout.readline(),b'READY\n');p.kill();p.wait(timeout=2)
        finally:
            if p.poll() is None:p.kill();p.wait()
            p.stdout.close()
        self.assertEqual(read_preference('eDP-1')['choice'],'tablet')

    def test_directory_sync_failure_restores_old_file(self):
        self.assertTrue(write_preference('eDP-1','tablet')['saved']);old=self.file.read_bytes()
        original=os.fsync
        calls=0
        def fail_directory_once(fd):
            nonlocal calls
            calls+=1
            if calls==3:raise OSError('directory sync failed')
            return original(fd)
        with patch('device_session.os.fsync',side_effect=fail_directory_once):
            self.assertFalse(write_preference('eDP-1','desktop')['saved'])
        self.assertEqual(self.file.read_bytes(),old)

    def test_concurrent_writers_preserve_both_choices(self):
        helper=str(Path(__file__).with_name('control_center.py'))
        children=[]
        for key,choice in [('eDP-1','desktop'),('DP-1','tablet')]:
            p=subprocess.Popen([sys.executable,helper,'mode-preference-write'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
            p.stdin.write(json.dumps(dict(output_key=key,choice=choice)).encode());p.stdin.close();children.append(p)
        for p in children:
            p.wait(timeout=3);self.assertTrue(json.loads(p.stdout.read())['saved']);p.stdout.close()
        self.assertEqual(read_preference('eDP-1')['choice'],'desktop')
        self.assertEqual(read_preference('DP-1')['choice'],'tablet')

    def test_key_rejection(self):
        for key in ['','../x','a/b','a'*129,'中']:
            with self.assertRaises(ValueError):parse_request('output-policy',json.dumps({'output_key':key}).encode())

class OutputPolicyTests(unittest.TestCase):
    def test_unique_connected_physical_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);drm=root/'class/drm';drm.mkdir(parents=True)
            target=root/'devices/pci/drm/card0-eDP-1';target.mkdir(parents=True);(target/'status').write_text('connected\n')
            (drm/'card0-eDP-1').symlink_to(target)
            self.assertTrue(output_policy('eDP-1',sysfs_root=root)['eligible'])
            self.assertFalse(output_policy('eDP-2',sysfs_root=root)['eligible'])
            (drm/'card1-eDP-1').symlink_to(target)
            self.assertFalse(output_policy('eDP-1',sysfs_root=root)['eligible'])
            (drm/'card1-eDP-1').unlink();(target/'status').write_text('x'*16385)
            self.assertFalse(output_policy('eDP-1',sysfs_root=root)['eligible'])
            (target/'status').write_text('disconnected')
            self.assertFalse(output_policy('eDP-1',sysfs_root=root)['eligible'])
            (target/'status').write_text('connected')
            times=iter([0,2]);self.assertFalse(output_policy('eDP-1',sysfs_root=root,clock=lambda:next(times))['eligible'])
            virtual=root/'devices/virtual/card';virtual.mkdir(parents=True);(virtual/'status').write_text('connected')
            (drm/'card0-eDP-1').unlink();(drm/'card0-eDP-1').symlink_to(virtual)
            self.assertFalse(output_policy('eDP-1',sysfs_root=root)['eligible'])

class CommandTests(unittest.TestCase):
    def test_bounded_open_stdin_and_fixed_errors(self):
        helper=str(Path(__file__).with_name('control_center.py'))
        for payload in [b'x'*4097,b'{"private":"DO_NOT_ECHO"}']:
            p=subprocess.run([sys.executable,helper,'mode-step'],input=payload,capture_output=True,timeout=4)
            self.assertNotEqual(p.returncode,0);self.assertNotIn(b'DO_NOT_ECHO',p.stdout)
        p=subprocess.Popen([sys.executable,helper,'mode-step'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        try:
            p.wait(timeout=3)
            self.assertNotEqual(p.returncode,0)
        finally:
            if p.poll() is None:p.kill();p.wait()
            p.stdin.close();p.stdout.close()
    def test_manual_cli_success_and_extra_argument_denied(self):
        helper=str(Path(__file__).with_name('control_center.py'))
        data=json.dumps(dict(choice='desktop',last_effective=None,pending=None)).encode()
        p=subprocess.run([sys.executable,helper,'mode-step'],input=data,capture_output=True,timeout=3)
        self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['mode']['reason_code'],'manual')
        p=subprocess.run([sys.executable,helper,'mode-step','extra'],input=data,capture_output=True,timeout=3)
        self.assertNotEqual(p.returncode,0)
