"""Persistent user intent, atomic writes; contains no credentials."""
import json,os,tempfile,fcntl
from pathlib import Path
DEFAULTS={'mode':'auto','proxy_enabled':True}
def policy_path():return Path(os.environ.get('PCADMIN_NETWORK_POLICY',str(Path.home()/'.config/pcadmin-network/policy.json')))
def read_policy():
 try:
  data=json.loads(policy_path().read_text())
  return {'mode':data['mode'] if data.get('mode') in ('auto','manual') else 'auto','proxy_enabled':data.get('proxy_enabled',True) is not False}
 except (OSError,ValueError):return DEFAULTS.copy()
def update_policy(**values):
 p=policy_path();p.parent.mkdir(parents=True,exist_ok=True)
 with p.with_suffix('.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);data=read_policy();data.update(values)
  fd,name=tempfile.mkstemp(dir=p.parent,prefix='.policy-')
  try:
   os.fchmod(fd,0o600)
   with os.fdopen(fd,'w') as f:json.dump(data,f)
   os.replace(name,p)
  finally:
   if os.path.exists(name):os.unlink(name)
 return data
