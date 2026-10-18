"""Local-only host freshness, bounded reads and compatibility checks."""
import importlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def field(actual, stale=15):
    return {'available':True,'actual':actual,'health':'observed','observed_at':100,'stale_after':stale,'source':'synthetic'}


class HostTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).parent/'contract_host.py').is_file(), 'read-only host is not implemented')
        self.host=importlib.import_module('contract_host')
        self.marker='a'*64
        self.observation={'schema':1,'boot_marker':self.marker,'started_boottime_ms':100}
        self.legacy={'temperature':field(0),'touch':dict(field(0,45),boot_default=1),'locked':False}

    def sample(self, **kw):
        return self.host.Sample(**{'legacy':self.legacy,'temperature_started_ms':1000,'touch_observation':self.observation,'touch_cache_trusted':True,**kw})

    def response(self, sample=None, now=1600):
        with patch.object(self.host,'boottime_ms',return_value=now),patch.object(self.host,'boot_marker',return_value=self.marker):
            return self.host.response(sample or self.sample())

    def test_age_uses_start_and_final_boottime(self):
        result=self.response();states=result['contracts']['states']
        self.assertEqual([x['observation_context']['age_upper_bound_ms'] for x in states],[600,1500])
        self.assertEqual([x['state']['actual'] for x in states],[0,0])
        self.assertEqual([x['state']['health'] for x in states],['observed','observed'])
        self.assertEqual(result['legacy'],self.legacy)

    def test_boot_and_invalid_time_degrade(self):
        variants=[None,{},dict(self.observation,boot_marker='b'*64)]
        variants += [dict(self.observation,started_boottime_ms=x) for x in (1601,True,-1,float('nan'),float('inf'),10**1000,'100')]
        for obs in variants:
            with self.subTest(obs=repr(obs)[:80]):
                state=self.response(self.sample(touch_observation=obs))['contracts']['states'][1]['state']
                self.assertEqual(state['health'],'unknown');self.assertEqual(state['actual'],0);self.assertEqual(state['boot_default'],1)
        for start in (None,True,-1,1601,float('inf'),10**1000):
            self.assertEqual(self.response(self.sample(temperature_started_ms=start))['contracts']['states'][0]['state']['health'],'unknown')

    def test_suspend_and_wall_clock_jump(self):
        self.assertEqual(self.response(now=45100)['contracts']['states'][1]['state']['health'],'observed')
        self.assertEqual(self.response(now=45101)['contracts']['states'][1]['state']['health'],'stale')
        self.legacy['touch']['observed_at']=999999999
        self.assertEqual(self.response(now=45101)['contracts']['states'][1]['state']['health'],'stale')
        self.assertEqual(self.response(self.sample(touch_observation=None))['contracts']['states'][1]['state']['health'],'unknown')

    def test_dependency_error_preserves_legacy(self):
        from contracts_loader import ContractsUnavailable
        with patch.object(self.host,'load_contracts',side_effect=ContractsUnavailable('dependency_missing')):
            result=self.response()
        self.assertEqual(result['legacy'],self.legacy)
        self.assertEqual(result['contracts']['status'],'unavailable')
        self.assertEqual(result['contracts']['reason_code'],'dependency_missing')
        self.assertEqual(result['contracts']['states'],[])

    def test_no_context_injection_or_private_marker(self):
        self.legacy.update(device_id='injected',session_id='injected',output_id='remote',age=0)
        result=self.response();states=result['contracts']['states']
        for value in states:
            self.assertEqual(value['device_id'],'local-device');self.assertEqual(value['output_id'],'local')
            self.assertNotEqual(value['session_id'],'injected');self.assertEqual(value['sequence'],0)
        self.assertNotIn(self.marker,json.dumps(result));self.assertNotIn('boot_marker',json.dumps(result))
        self.assertEqual(self.response(self.sample(touch_cache_trusted=False))['contracts']['states'][1]['state']['health'],'unknown')
        self.legacy['touch']['admin']=True
        self.assertEqual(self.response()['contracts']['reason_code'],'invalid_snapshot')

    def test_output_is_bounded_and_errors_are_fixed(self):
        self.legacy['extra']='x'*65536
        result=self.response();self.assertLess(len(json.dumps(result).encode()),65536)
        self.assertEqual(result['contracts']['reason_code'],'output_too_large')
        with patch.object(self.host,'load_contracts',side_effect=RuntimeError('/private/path should not escape')):
            result=self.response()
        self.assertNotIn('/private/path',json.dumps(result))

    def test_untrusted_cache_not_fresh(self):
        root=SimpleNamespace(st_mode=stat.S_IFREG|0o644,st_uid=0)
        directory=SimpleNamespace(st_mode=stat.S_IFDIR|0o755,st_uid=0)
        self.assertTrue(self.host.trusted_metadata(root,[directory]))
        for info,parents in [(SimpleNamespace(st_mode=stat.S_IFREG|0o644,st_uid=1000),[directory]),(SimpleNamespace(st_mode=stat.S_IFREG|0o664,st_uid=0),[directory]),(SimpleNamespace(st_mode=stat.S_IFREG|0o646,st_uid=0),[directory]),(root,[SimpleNamespace(st_mode=stat.S_IFDIR|0o777,st_uid=0)]),(root,[SimpleNamespace(st_mode=stat.S_IFLNK|0o755,st_uid=0)])]:
            self.assertFalse(self.host.trusted_metadata(info,parents))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json'
            valid={'mode':0,'verified':True,'observed_at':100,'boot_default':1,'observation':self.observation}
            p.write_text(json.dumps(valid))
            with patch.object(self.host,'trusted_metadata',return_value=True):
                data,trusted=self.host.read_touch_cache(p)
            self.assertEqual(data,valid);self.assertTrue(trusted)
            for raw in (b'[]',b'{"mode":0,"mode":1}',b'\xff',b'x'*65537):
                p.write_bytes(raw);data,trusted=self.host.read_touch_cache(p);self.assertEqual(data,{});self.assertFalse(trusted)
            p.unlink();p.symlink_to(Path(d)/'target');self.assertEqual(self.host.read_touch_cache(p),({},False))
            p.unlink();os.mkfifo(p);start=time.monotonic();self.assertEqual(self.host.read_touch_cache(p),({},False));self.assertLess(time.monotonic()-start,1)

    def test_one_sample_shared_with_legacy(self):
        import control_center as cc
        calls=[]
        def read(args,**kwargs):
            if args[-1]=='status':calls.append('network');return '{"primary":"wifi"}'
            if args[-1]=='get':return 'balanced'
            return '{}'
        def thermal():calls.append('thermal');return [{'type':'cpu_thermal','celsius':0}]
        def touch(path):calls.append('touch');return ({'verified':True,'mode':0,'observed_at':100,'boot_default':1,'observation':self.observation},True)
        with patch.object(cc.subprocess,'check_output',side_effect=read),patch.object(cc,'thermal_values',side_effect=thermal),patch.object(self.host,'read_touch_cache',side_effect=touch),patch.object(cc.time,'time',return_value=100),patch.object(cc,'read_lock',return_value=False),patch.object(cc,'nightlight_status',return_value=field(False)),patch.object(cc.Path,'exists',return_value=False):
            sample=cc.collect_status()
        self.assertEqual(calls.count('network'),1);self.assertEqual(calls.count('touch'),1);self.assertEqual(calls.count('thermal'),1)
        self.assertEqual(sample.legacy['temperature']['actual'],0);self.assertEqual(sample.legacy['touch']['actual'],0)
        with patch.object(cc,'collect_status',return_value=sample):self.assertEqual(cc.status(),sample.legacy)
        self.assertNotIn('observation',json.dumps(sample.legacy));self.assertTrue(sample.touch_cache_trusted)

    def test_deadline_and_cancel_only_owned_read_children(self):
        controller=subprocess.Popen([sys.executable,'-c','import time;time.sleep(5)'])
        try:
            budget=self.host.ReadBudget(limit_ms=40)
            with self.assertRaises(self.host.ReadDeadline):
                budget.run_read([sys.executable,'-c','import time;time.sleep(5)'],2)
            self.assertIsNone(controller.poll())
            budget.cancel();self.assertIsNone(controller.poll())
            fake=self.host.ReadBudget(clock_ms=lambda:0)
            self.assertEqual(fake.limit_ms,20000)
            with patch.object(fake,'clock_ms',return_value=20001):
                with self.assertRaises(self.host.ReadDeadline):fake.run_read([sys.executable,'-c','pass'],1)
        finally:
            controller.terminate();controller.wait(timeout=2)

    def test_owned_command_failure_and_output_limits(self):
        budget=self.host.ReadBudget()
        self.assertEqual(budget.run_read([sys.executable,'-c','print("ok")'],1).strip(),'ok')
        with self.assertRaises(subprocess.CalledProcessError):budget.run_read([sys.executable,'-c','raise SystemExit(2)'],1)
        with self.assertRaises(self.host.ReadFailure):budget.run_read([sys.executable,'-c','print("x"*65537)'],1)

    def test_cli_rejects_extra_context(self):
        import control_center as cc
        with patch('sys.argv',['control_center.py','status-readonly','remote']),patch.object(cc,'collect_status',side_effect=AssertionError('must not sample')):
            with self.assertRaises(ValueError):cc.main()

    def test_sigterm_reaps_active_read_and_preserves_controller(self):
        controller=subprocess.Popen([sys.executable,'-c','import time;time.sleep(5)'])
        code="""import os, signal, sys
from contract_host import ReadBudget, ReadDeadline
class ReadyBudget(ReadBudget):
    def remaining_s(self):
        if self.process is not None:
            print(self.process.pid, flush=True)
        return super().remaining_s()
try:
    with ReadyBudget() as budget:
        budget.run_read([sys.executable, '-c', 'import time;time.sleep(5)'], 5)
except ReadDeadline:
    print('cancelled', flush=True)
"""
        proc=subprocess.Popen([sys.executable,'-u','-c',code],cwd=Path(__file__).parent,stdout=subprocess.PIPE,text=True)
        try:
            child=int(proc.stdout.readline().strip())
            proc.terminate();out,_=proc.communicate(timeout=2)
            self.assertEqual(proc.returncode,0);self.assertIn('cancelled',out)
            with self.assertRaises(ProcessLookupError):os.kill(child,0)
            self.assertIsNone(controller.poll())
        finally:
            if proc.poll() is None:proc.kill();proc.wait()
            controller.terminate();controller.wait(timeout=2)

    def test_readonly_entry_preserves_success_and_fixed_failures(self):
        import control_center as cc
        with patch.object(cc,'collect_status',return_value=self.sample()),patch.object(self.host,'boottime_ms',return_value=1600),patch.object(self.host,'boot_marker',return_value=self.marker):
            result=cc.status_readonly()
        self.assertEqual(result['legacy'],self.legacy)
        self.assertEqual(result['contracts']['status'],'ok')
        for error,code in [(self.host.ReadDeadline('private detail'),'read_timeout'),(RuntimeError('/private/path'),'read_failed')]:
            with patch.object(cc,'collect_status',side_effect=error):result=cc.status_readonly()
            self.assertEqual(result['contracts']['reason_code'],code)
            self.assertIsNone(result['legacy']['locked']);self.assertNotIn('private',json.dumps(result))
