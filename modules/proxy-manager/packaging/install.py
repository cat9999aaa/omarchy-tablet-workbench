#!/usr/bin/python3
"""User-scoped file publication. Reuse the existing plugin release path guards."""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

spec=importlib.util.spec_from_file_location('workbench_release',Path(__file__).resolve().parents[2]/'plugin-release/release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
def digest(data):return hashlib.sha256(data).hexdigest()
class Installer:
 def __init__(self,home):
  self.home=Path(home).absolute();self.state=self.home/'.local/state/omt-proxy-install'
 def target(self,name):
  try:release.relative(name)
  except Exception:raise ValueError('invalid_target') from None
  prefixes=('.local/lib/omt-proxy/','.local/share/omt-proxy/','.config/systemd/user/omt-proxy')
  exact={'.config/systemd/user/v2rayn.service.d/90-omt-owner.conf','.local/share/applications/omt-proxy.desktop','.local/bin/omt-proxy',
   'Projects/pcadmin/tools/network-center/network.py','Projects/pcadmin/tools/network-center/cell_proxy_watch.py',
   'Projects/pcadmin/tools/control-center/control_center.py'}
  if not name.startswith(prefixes) and name not in exact:raise ValueError('target_outside_scope')
  path=self.home/name
  try:release.no_links(path)
  except Exception:raise ValueError('symlink_target') from None
  if path.exists():
   st=path.stat()
   if not path.is_file() or st.st_uid!=os.getuid() or st.st_nlink!=1:raise ValueError('unsafe_target')
  return path
 def plan(self,payload):
  if not payload or len(payload)>1000:raise ValueError('invalid_payload')
  total=0;changed=False;hashes={}
  for name,(data,mode) in payload.items():
   if not isinstance(data,bytes) or mode not in (0o600,0o644,0o755):raise ValueError('invalid_payload')
   total+=len(data)
   if total>100*1024*1024:raise ValueError('payload_too_large')
   path=self.target(name);hashes[name]=digest(data)
   changed|=not path.exists() or path.read_bytes()!=data or path.stat().st_mode&0o777!=mode
  return {'would_change':changed,'files':len(payload),'sha256':digest(json.dumps(hashes,sort_keys=True).encode()),'writes':False}
 @contextlib.contextmanager
 def lock(self):
  try:release.no_links(self.state)
  except Exception:raise ValueError('unsafe_state') from None
  self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.state.stat().st_mode&0o077:raise ValueError('unsafe_state')
  fd=os.open(self.state/'install.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
  finally:os.close(fd)
 def atomic(self,path,data,mode):
  release.no_links(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  fd,tmp=tempfile.mkstemp(prefix='.omt-',dir=path.parent)
  try:
   with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),mode)
   os.replace(tmp,path)
   dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
   try:os.fsync(dfd)
   finally:os.close(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 def save(self,folder,record):self.atomic(folder/'transaction.json',json.dumps(record,sort_keys=True).encode(),0o600)
 def apply(self,payload):
  self.plan(payload)
  with self.lock():
   info=self.plan(payload)
   if not info['would_change']:return {'status':'unchanged','sha256':info['sha256']}
   transaction=uuid.uuid4().hex;folder=self.state/transaction;folder.mkdir(mode=0o700)
   record={'schema':1,'stage':'prepared','entries':[],'sha256':info['sha256']}
   for index,(name,(data,mode)) in enumerate(payload.items()):
    path=self.target(name);old=path.read_bytes() if path.exists() else None
    old_mode=path.stat().st_mode&0o777 if old is not None else None
    backup='original-'+str(index)
    if old is not None:self.atomic(folder/backup,old,0o600)
    record['entries'].append({'path':name,'old_hash':digest(old) if old is not None else None,'old_mode':old_mode,'backup':backup,'new_hash':digest(data),'mode':mode})
   self.save(folder,record)
   try:
    record['stage']='applying';self.save(folder,record)
    for entry in record['entries']:
     path=self.target(entry['path']);current=digest(path.read_bytes()) if path.exists() else None
     if current!=entry['old_hash']:raise ValueError('concurrent_file_change')
     data,mode=payload[entry['path']];self.atomic(path,data,mode)
    if self.plan(payload)['would_change']:raise ValueError('install_readback_failed')
    record['stage']='installed';self.save(folder,record)
   except Exception:
    self._rollback(folder,record);raise
   return {'status':'installed','transaction':transaction,'sha256':info['sha256'],'files':len(payload)}
 def _rollback(self,folder,record):
  # Validate every target before restoring any; unrelated external edits are preserved.
  for entry in record['entries']:
   if not re.fullmatch('original-[0-9]+',entry['backup']):raise ValueError('invalid_backup')
   path=self.target(entry['path']);current=digest(path.read_bytes()) if path.exists() else None
   if current not in (entry['old_hash'],entry['new_hash']):raise ValueError('rollback_conflict')
   if entry['old_hash'] is not None:
    backup=folder/entry['backup'];release.no_links(backup)
    if digest(backup.read_bytes())!=entry['old_hash']:raise ValueError('backup_integrity_failed')
  for entry in reversed(record['entries']):
   path=self.target(entry['path'])
   if entry['old_hash'] is None:path.unlink(missing_ok=True)
   elif not path.exists() or digest(path.read_bytes())!=entry['old_hash'] or path.stat().st_mode&0o777!=entry['old_mode']:
    self.atomic(path,(folder/entry['backup']).read_bytes(),entry['old_mode'])
  record['stage']='restored';self.save(folder,record)
  return {'status':'restored'}
 def rollback(self,transaction):
  if not re.fullmatch('[0-9a-f]{32}',transaction):raise ValueError('invalid_transaction')
  with self.lock():
   folder=self.state/transaction;release.no_links(folder);record=json.loads((folder/'transaction.json').read_text())
   if record.get('schema')!=1 or not isinstance(record.get('entries'),list):raise ValueError('invalid_transaction')
   return self._rollback(folder,record)
