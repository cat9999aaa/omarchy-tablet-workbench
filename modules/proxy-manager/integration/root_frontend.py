#!/usr/bin/python3
"""Root-only transport-front-end transaction; fixed paths, service and core."""
import fcntl
import hashlib
import json
import os
import pwd
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

def sha(data):return hashlib.sha256(data).hexdigest()
def safe(path):
 if path.absolute()!=path.resolve():raise ValueError('unsafe_path')
 if path.exists() and (not path.is_file() or path.stat().st_nlink!=1):raise ValueError('unsafe_file')
 return path

def atomic(path,data):
 safe(path);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.native-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),0o600)
  os.replace(tmp,path)
  d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(d)
  finally:os.close(d)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

class Controller:
 def __init__(self,root,adapter):
  self.root=Path(root).absolute();self.adapter=adapter;self.config=self.root/'tun.json';self.state=self.root/'native-proxy'
  if self.root.resolve()!=self.root or self.state.is_symlink():raise ValueError('unsafe_root')
 def folder(self,token):
  if not re.fullmatch('[a-f0-9]{32}',token):raise ValueError('invalid_token')
  folder=self.state/token
  if folder.resolve()!=folder:raise ValueError('unsafe_transaction')
  return folder
 def record(self,folder):return json.loads(safe(folder/'transaction.json').read_bytes())
 def save(self,folder,record):atomic(folder/'transaction.json',json.dumps(record).encode())
 def prepare(self,data):
  if not isinstance(data,bytes) or len(data)>8*1024*1024:raise ValueError('invalid_candidate')
  original=safe(self.config).read_bytes()
  self.state.mkdir(mode=0o700,exist_ok=True)
  for item in self.state.iterdir():
   if item.is_dir() and self.record(item).get('stage') not in ('committed','restored'):raise ValueError('pending_frontend_transaction')
  token=uuid.uuid4().hex;folder=self.folder(token);folder.mkdir(mode=0o700)
  atomic(folder/'original.json',original);atomic(folder/'candidate.json',data)
  if not self.adapter.check(folder/'candidate.json'):
   self.save(folder,{'stage':'restored'});raise ValueError('frontend_native_check_failed')
  uid=getattr(self.adapter,'uid',None)
  self.save(folder,{'stage':'prepared','original':sha(original),'candidate':sha(data),'owner_uid':uid if type(uid) is int else None})
  return {'ok':True,'token':token,'sha256':sha(data),'applied':False}
 def apply(self,token):
  folder=self.folder(token);record=self.record(folder)
  if record['stage']!='prepared' or sha(safe(self.config).read_bytes())!=record['original']:raise ValueError('frontend_conflict')
  data=safe(folder/'candidate.json').read_bytes()
  if sha(data)!=record['candidate']:raise ValueError('candidate_changed')
  if not self.adapter.arm(token):return {'ok':False,'stage':'watchdog_unavailable'}
  record['stage']='activating';self.save(folder,record)
  try:
   atomic(self.config,data)
   if not self.adapter.restart():raise RuntimeError('restart_failed')
   record['stage']='applied';self.save(folder,record);return {'ok':True,'stage':'applied','token':token}
  except Exception:
   result=self.rollback(token);return {'ok':False,'restored':result.get('restored',False)}
 def commit(self,token):
  folder=self.folder(token);record=self.record(folder)
  if record['stage']!='applied' or sha(safe(self.config).read_bytes())!=record['candidate']:raise ValueError('frontend_conflict')
  record['stage']='committed';self.save(folder,record);self.adapter.cancel(token)
  return {'ok':True,'stage':'committed'}
 def rollback(self,token,restart=True):
  folder=self.folder(token);record=self.record(folder)
  if record['stage'] in ('committed','restored'):return {'ok':True,'ignored':True,'restored':record['stage']=='restored'}
  if sha(safe(self.config).read_bytes()) not in (record['original'],record['candidate']):return {'ok':False,'error_code':'external_config_change'}
  data=safe(folder/'original.json').read_bytes()
  if sha(data)!=record['original']:return {'ok':False,'error_code':'backup_changed'}
  atomic(self.config,data)
  if record['stage']=='prepared':
   record['stage']='restored';self.save(folder,record);return {'ok':True,'restored':True}
  if restart and not self.adapter.restart():return {'ok':False,'restored':False}
  record['stage']='restored';self.save(folder,record);self.adapter.cancel(token)
  return {'ok':True,'restored':True}

class System:
 core='/opt/v2rayn-bin/bin/sing_box/sing-box'
 def __init__(self,uid):self.uid=uid
 def call(self,args,timeout=15):return subprocess.run(args,capture_output=True,timeout=timeout)
 def check(self,path):
  version=self.call([self.core,'version']).stdout.decode(errors='replace').splitlines()
  return bool(version and version[0]=='sing-box version 1.14.3' and self.call([self.core,'check','-c',str(path)]).returncode==0)
 def arm(self,token):
  return self.call(['systemd-run','--quiet','--collect','--unit=omt-proxy-front-'+token,'--on-active=180s','--timer-property=AccuracySec=1s','/usr/local/libexec/omt-proxy-frontend','rollback',token]).returncode==0
 def cancel(self,token):self.call(['systemctl','stop','omt-proxy-front-'+token+'.timer'])
 def intent(self):
  if Path('/var/lib/pcadmin-network/flight.json').exists():return False
  try:
   p=Path(pwd.getpwuid(self.uid).pw_dir)/'.config/pcadmin-network/policy.json'
   return safe(p).stat().st_uid==self.uid and json.loads(p.read_bytes()).get('proxy_enabled') is True
  except (OSError,ValueError,KeyError,TypeError):return False
 def restart(self):
  op='restart' if self.intent() else 'stop'
  result=self.call(['systemctl',op,'pcadmin-v2ray-tun.service']).returncode==0
  if op=='restart' and not self.intent():return self.call(['systemctl','stop','pcadmin-v2ray-tun.service']).returncode==0
  return result

def main():
 if os.geteuid()!=0 or len(sys.argv) not in (2,3):raise ValueError('root_action_required')
 root=Path('/etc/pcadmin-network');safe(root/'native-frontend.lock')
 with (root/'native-frontend.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  op=sys.argv[1];uid=int(os.environ.get('PKEXEC_UID',os.getuid()))
  system=System(uid);control=Controller(root,system)
  if len(sys.argv)==3:system.uid=control.record(control.folder(sys.argv[2])).get('owner_uid')
  if op=='recover-config' and len(sys.argv)==2:
   results=[]
   if control.state.exists():
    for folder in control.state.iterdir():
     if folder.is_dir():results.append(control.rollback(folder.name,restart=False))
   result={'ok':all(r.get('ok') for r in results),'network_started':False}
  elif op in ('prepare','check') and len(sys.argv)==2:
   # This module is copied beside this helper as a root-owned file during installation.
   from omt_proxy_frontend import build
   config=json.loads(safe(root/'tun.json').read_bytes());data=json.dumps(build(config)).encode()
   if op=='check':
    with tempfile.TemporaryDirectory(prefix='omt-front-') as d:
     p=Path(d)/'candidate.json';atomic(p,data);result={'ok':control.adapter.check(p),'applied':False}
   else:result=control.prepare(data)
  elif op in ('apply','commit','rollback') and len(sys.argv)==3:result=getattr(control,op)(sys.argv[2])
  else:raise ValueError('unsupported_action')
  print(json.dumps(result));return 0 if result.get('ok') else 1

if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print('{"ok":false,"error_code":"frontend_action_failed"}');sys.exit(1)
