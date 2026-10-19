import importlib,json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ID='00000000-0000-4000-8000-000000000001'
class ProcessTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(Path(__file__).with_name('tasks.py').exists(),'task helper missing')
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.project=self.root/'a project';self.project.mkdir();self.bin=self.root/'bin';self.bin.mkdir();self.config=self.root/'config/omarchy-tablet-workbench';self.config.mkdir(parents=True)
  (self.config/'task-center.json').write_text(json.dumps({'schema':1,'project_root':str(self.project)}))
  self.env=dict(os.environ,HOME=str(self.root),XDG_CONFIG_HOME=str(self.root/'config'),PATH=str(self.bin)+':'+os.environ['PATH'])
  code='''#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
r=Path(os.environ['HOME']);name=Path(sys.argv[0]).name
with (r/'calls').open('a') as f:f.write(name+' '+' '.join(sys.argv[1:])+'\\n')
if name=='omarchy-shell':print('false' if sys.argv[1]=='lock' else 'off')
elif name=='hyprctl':print('[{"name":"TEST","focused":true}]')
elif name=='paseo':
 if (r/'slow').exists():
  (r/'pid').write_text(str(os.getpid()));time.sleep(8)
 if (r/'bad').exists():print('PRIVATE',file=sys.stderr);print('{bad');sys.exit(1)
 if sys.argv[1]=='inspect':print(json.dumps({'Id':sys.argv[2],'Cwd':str(r/'a project'),'Status':'idle','PendingPermissions':[]}));sys.exit(0)
 print(json.dumps([{'id':'00000000-0000-4000-8000-000000000001','status':'idle','cwd':str(r/'a project'),'name':'PRIVATE'}]))
'''
  for name in ['paseo','hyprctl','omarchy-shell','gtk-launch']:
   p=self.bin/name;p.write_text(code);p.chmod(0o755)
 def run_helper(self,command='snapshot',request=None):
  return subprocess.run([sys.executable,str(Path(__file__).with_name('tasks.py')),command],input=json.dumps(request or {'generation':1}),env=self.env,capture_output=True,text=True,timeout=11)
 def test_real_snapshot_and_no_notification_replay(self):
  p=self.run_helper();r=json.loads(p.stdout);self.assertEqual(p.returncode,0,p.stdout);self.assertTrue(r['ok']);self.assertEqual(r['rows'][0]['status'],'idle');self.assertNotIn('PRIVATE',p.stdout+p.stderr);self.assertNotIn('showHistory',(self.root/'calls').read_text())
 def test_config_missing_and_failure_redacted(self):
  (self.config/'task-center.json').unlink();r=json.loads(self.run_helper().stdout);self.assertIsNone(r['rows']);self.assertEqual(r['source_reason'],'invalid-project')
  self.assertNotIn('paseo',(self.root/'calls').read_text())
 def test_invalid_requests_no_actions(self):
  for req in [{'action':'send','output':'TEST'},{'action':'notification-history','output':'OTHER'},{'action':'open-paseo','output':'TEST','host':'remote'}]:
   p=self.run_helper('action',req);self.assertFalse(json.loads(p.stdout)['ok'])
  self.assertNotIn('gtk-launch',(self.root/'calls').read_text());self.assertNotIn('showHistory',(self.root/'calls').read_text())
 def test_source_error_and_timeout(self):
  (self.root/'bad').touch();p=self.run_helper();r=json.loads(p.stdout);self.assertIsNone(r['rows']);self.assertNotIn('PRIVATE',p.stdout+p.stderr)
  (self.root/'bad').unlink();(self.root/'slow').touch();start=time.monotonic();r=json.loads(self.run_helper().stdout);self.assertLess(time.monotonic()-start,6);self.assertEqual(r['source_reason'],'timeout')
  pid=int((self.root/'pid').read_text());self.assertFalse(Path('/proc',str(pid)).exists())
 def test_snapshot_detail_scope_is_carried_through_cli(self):
  snapshot=json.loads(self.run_helper().stdout)
  request={'generation':2,'agent_id':ID,'remaining_ms':4000,'output':'TEST','scope':snapshot['scope']}
  r=json.loads(self.run_helper('detail',request).stdout);self.assertTrue(r['ok']);self.assertEqual(r['detail']['pending_permission_count'],0)
  other=self.root/'other';other.mkdir();(self.config/'task-center.json').write_text(json.dumps({'schema':1,'project_root':str(other)}))
  r=json.loads(self.run_helper('detail',request).stdout);self.assertFalse(r['ok']);self.assertEqual(r['reason_code'],'scope-changed')
 def test_guard_is_fresh_without_paseo(self):
  r=json.loads(self.run_helper('guard',{'output':'TEST'}).stdout)
  self.assertTrue(r['ok']);self.assertGreater(r['sampled_boottime_ms'],0)
  self.assertNotIn('paseo',(self.root/'calls').read_text())
 def test_cancel_reaps_reader(self):
  (self.root/'slow').touch();p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('tasks.py')),'snapshot'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=self.env)
  try:
   p.stdin.write('{"generation":1}');p.stdin.close();end=time.monotonic()+4
   while not (self.root/'pid').exists() and time.monotonic()<end:time.sleep(.02)
   self.assertTrue((self.root/'pid').exists());pid=int((self.root/'pid').read_text());p.terminate();p.wait(timeout=2);self.assertFalse(Path('/proc',str(pid)).exists())
  finally:
   if p.poll() is None:p.kill();p.wait()
   p.stdout.close();p.stderr.close()
if __name__=='__main__':unittest.main()
