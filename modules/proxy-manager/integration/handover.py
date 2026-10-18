#!/usr/bin/python3
"""One controlled legacy-to-native owner transition and independent rollback."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import time
import signal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from root_frontend import atomic, safe


def sequence(adapter):
 for step in ('preflight','arm','frontend','stop_old','start_new','verify','commit'):
  try:ok=adapter.step(step)
  except Exception:ok=False
  if not ok:
   restored=False
   if step not in ('preflight','arm'):
    try:restored=adapter.step('restore')
    except Exception:pass
   return {'verified':False,'restored':bool(restored),'stage':step}
 return {'verified':True,'restored':False,'stage':'committed'}


def recover_boot(root):
 root=Path(root);record=root/'handover.json';owner=root/'owner.json'
 if not record.exists():return {'owner_restored':False,'network_verified':False,'stage':'not_needed'}
 value=json.loads(safe(record).read_bytes())
 if value.get('stage') in ('committed','restored'):return {'owner_restored':False,'network_verified':False,'stage':'not_needed'}
 if value.get('stage') not in ('prepared','switching'):raise ValueError('unknown_handover_stage')
 if owner.exists():
  if json.loads(safe(owner).read_bytes()).get('owner')!='omt-proxy':raise ValueError('owner_conflict')
  owner.unlink();fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 value['stage']='restored';value['network_verified']=False;value['recovery']='boot-owner-selection'
 atomic(record,json.dumps(value).encode())
 return {'owner_restored':True,'network_verified':False,'stage':'restored'}


class System:
 def __init__(self,token):
  if not re.fullmatch('[a-f0-9]{32}',token):raise ValueError('invalid_token')
  self.token=token;self.root=Path.home()/'.local/state/omt-proxy';self.record=self.root/'handover.json'
  self.lib=Path.home()/'.local/lib/omt-proxy';self.unit='omt-proxy-handover-'+token
 def run(self,args,timeout=20):return subprocess.run(args,capture_output=True,timeout=timeout)
 def systemctl(self,*args):return self.run(['systemctl','--user',*args]).returncode==0
 def read(self):
  value=json.loads(safe(self.record).read_bytes())
  if value.get('token')!=self.token:raise ValueError('handover_identity_conflict')
  return value
 def save(self,value):atomic(self.record,json.dumps(value).encode())
 def front(self,op,token=None):
  args=['pkexec','/usr/local/libexec/omt-proxy-frontend',op]+([token] if token else [])
  if op=='rollback':
   result=self.run(args,100)
   if result.returncode:raise ValueError('frontend_failed')
   return json.loads(result.stdout)
  if not self.owned().policy_allows(*self.owned().policy_state()):raise ValueError('locked_or_disabled')
  request=str(uuid.uuid4());directory=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/'pcadmin-control-center'
  directory.mkdir(mode=0o700,exist_ok=True);path=directory/('request-'+request+'.json')
  start=Path('/proc/'+str(os.getpid())+'/stat').read_text().rpartition(')')[2].split()[19]
  atomic(path,json.dumps({'active':True,'privileged_actions':['proxy-front-'+op],'expires_at':time.time()+95,'pid':os.getpid(),'process_start':start}).encode())
  child=None
  try:
   child=subprocess.Popen(args+['--request',request],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
   deadline=time.monotonic()+90
   while child.poll() is None:
    if time.monotonic()>deadline or not self.owned().policy_allows(*self.owned().policy_state()):raise ValueError('authorization_cancelled')
    time.sleep(.2)
   output,_=child.communicate(timeout=2)
   if child.returncode or len(output)>4096:raise ValueError('frontend_failed')
   return json.loads(output)
  finally:
   path.unlink(missing_ok=True)
   if child is not None and child.poll() is None:
    try:os.killpg(child.pid,signal.SIGTERM)
    except (ProcessLookupError,PermissionError):pass
    try:child.wait(timeout=2)
    except subprocess.TimeoutExpired:pass
 def owned(self):
  spec=importlib.util.spec_from_file_location('omt_owned',self.lib/'owned-core.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def ownership(self,unit):
  spec=importlib.util.spec_from_file_location('handover_ownership',self.lib/'legacy-control.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.ownership(unit)
 def step(self,step):
  return self._step(step)
 def _step(self,step):
  if step=='preflight':
   owned=self.owned()
   if not owned.policy_allows(*owned.policy_state()) or (self.root/'owner.json').exists():return False
   if not self.ownership('v2rayn.service') or not self.systemctl('is-active','v2rayn.service') or not owned.check(self.root/'active.json').get('ok') or not owned.probe():return False
   if self.record.exists() and json.loads(safe(self.record).read_bytes()).get('stage') not in ('restored','committed'):return False
   old_enabled=self.run(['systemctl','--user','is-enabled','v2rayn.service']).stdout.strip()==b'enabled'
   watcher=self.systemctl('is-active','pcadmin-cell-proxy.service')
   if not old_enabled:return False
   # Both boot entries exist before switching; one atomic owner marker selects one.
   if not self.systemctl('daemon-reload') or not self.systemctl('start','omt-proxy-handover-recovery.service') or not self.systemctl('enable','omt-proxy.service','omt-proxy-core.service'):return False
   prepared=self.front('prepare')
   self.save({'token':self.token,'stage':'prepared','frontend_token':prepared['token'],'old_enabled':old_enabled,'watcher':watcher})
   return True
  value=self.read()
  if step=='arm':
   result=self.run(['systemd-run','--user','--quiet','--collect','--unit='+self.unit,'--on-active=240s','--timer-property=AccuracySec=1s','/usr/bin/python3',str(self.lib/'handover.py'),'recover',self.token])
   return result.returncode==0
  if step=='frontend':
   if not self.front('apply',value['frontend_token']).get('ok') or not self.owned().probe():return False
   # Accept the transport-only frontend while the old core is STILL running.
   # Subsequent owner rollback keeps this separately verified compatible frontend.
   if not self.front('commit',value['frontend_token']).get('ok'):return False
   value['frontend_verified_with_legacy']=True;self.save(value);return True
  if step=='stop_old':
   if not self.owned().policy_allows(*self.owned().policy_state()):return False
   value['stage']='switching';self.save(value)
   return self.systemctl('stop','pcadmin-cell-proxy.service') and self.systemctl('stop','v2rayn.service')
  if step=='start_new':
   if not self.owned().policy_allows(*self.owned().policy_state()):return False
   atomic(self.root/'owner.json',b'{"owner":"omt-proxy","schema":1}')
   return self.systemctl('daemon-reload') and self.systemctl('enable','omt-proxy.service','omt-proxy-core.service') and self.systemctl('start','omt-proxy-core.service','omt-proxy.service') and (not value['watcher'] or self.systemctl('start','pcadmin-cell-proxy.service'))
  if step=='verify':
   return self.ownership('omt-proxy-core.service') and self.owned().probe() and self.systemctl('is-active','omt-proxy-core.service','omt-proxy.service') and not self.systemctl('is-active','v2rayn.service')
  if step=='commit':
   value['stage']='committed';self.save(value);self.systemctl('stop',self.unit+'.timer');return True
  if step=='restore':
   if value['stage'] in ('committed','restored'):return value['stage']=='restored' and (value.get('network_verified') is True or value.get('stopped_verified') is True)
   self.systemctl('stop','pcadmin-cell-proxy.service')
   if not self.systemctl('disable','--now','omt-proxy-core.service','omt-proxy.service'):return False
   self.systemctl('stop','omt-proxy-recovery.service')
   (self.root/'owner.json').unlink(missing_ok=True)
   # Root's independently armed timer restores TUN even when interactive Polkit is unavailable.
   restored_front=value.get('frontend_verified_with_legacy') is True
   if not restored_front:
    try:restored_front=self.front('rollback',value['frontend_token']).get('ok') is True
    except Exception:pass
   enabled_ok=not value['old_enabled'] or self.systemctl('enable','v2rayn.service')
   state=self.owned().policy_state();want=state[1] is False and state[2] is True
   running=self.systemctl('start','v2rayn.service') if want else self.systemctl('stop','v2rayn.service')
   if want:
    verified=running and self.systemctl('is-active','v2rayn.service') and self.ownership('v2rayn.service') and self.owned().probe()
   else:
    verified=running and not self.systemctl('is-active','v2rayn.service') and not self.systemctl('is-active','omt-proxy-core.service')
   # Unknown policy must not restart a watcher whose legacy default is enabled.
   if verified and value['watcher'] and state[2] is not None:verified=self.systemctl('start','pcadmin-cell-proxy.service')
   if enabled_ok and verified and restored_front:
    value['stage']='restored';value['network_verified']=bool(want);value['stopped_verified']=not want;self.save(value);self.systemctl('stop',self.unit+'.timer');return True
   return False
  raise ValueError('unsupported_step')


def main():
 root=Path.home()/'.local/state/omt-proxy';root.mkdir(parents=True,exist_ok=True,mode=0o700)
 boot=len(sys.argv)==2 and sys.argv[1]=='recover-boot'
 if not boot and (len(sys.argv)!=3 or sys.argv[1] not in ('apply','recover')):raise ValueError('unsupported')
 fd=os.open(root/'handover.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
 try:
  deadline=time.monotonic()+90
  while True:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:
    if not boot and sys.argv[1]=='apply' or time.monotonic()>deadline:raise
    time.sleep(.5)
  if boot:print(json.dumps(recover_boot(root)));return 0
  adapter=System(sys.argv[2])
  result=sequence(adapter) if sys.argv[1]=='apply' else {'restored':adapter.step('restore')}
  print(json.dumps(result));return 0 if result.get('verified') or result.get('restored') else 1
 finally:os.close(fd)

if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print('{"verified":false,"error_code":"handover_failed"}');sys.exit(1)
