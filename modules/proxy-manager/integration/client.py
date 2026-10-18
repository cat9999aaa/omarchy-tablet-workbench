"""Shared native controller client for existing local entry points."""
import json
import os
from pathlib import Path
import subprocess
import uuid

def native(home=None):
 home=Path.home() if home is None else Path(home)
 p=home/'.local/state/omt-proxy/owner.json'
 try:
  if p.resolve()!=p or not p.is_file():return False
  st=p.stat()
  return st.st_uid==os.getuid() and not st.st_mode&0o077 and st.st_nlink==1 and st.st_size<=4096 and json.loads(p.read_text()).get('owner')=='omt-proxy'
 except (OSError,ValueError,AttributeError):return False

def dispatch(home,action,confirmed,runner=subprocess.run,candidate_hash=None):
 failure={'verified':False,'stage':'failed','error_code':'controller_unavailable'}
 if action not in ('enable','disable','apply'):return failure
 if action in ('disable','apply') and confirmed is not True:return {'verified':False,'stage':'confirmation','error_code':'confirmation_required'}
 binary=str(Path(home)/'.local/lib/omt-proxy/omt-proxy')
 socket=str(Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'omt-proxy/control.sock')
 argv=[binary,'request',socket];request_id='entry-'+uuid.uuid4().hex
 def call(data):
  p=runner(argv,input=json.dumps(data).encode(),capture_output=True,timeout=125)
  if p.returncode:raise ValueError('request_failed')
  return json.loads(p.stdout)
 try:
  snapshot=call({'id':'read-'+request_id,'action':'status','expected_revision':0,'confirmed':False})['snapshot']
  request={'id':request_id,'action':action,'expected_revision':snapshot['revision'],'confirmed':bool(confirmed)}
  if candidate_hash is not None:request['candidate_hash']=candidate_hash
  result=call(request)['outcome']
  return {'verified':result.get('verified') is True,'stage':result.get('stage','failed'),'error_code':result.get('error_code')}
 except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):return failure


def active_client():
 """Absence permits legacy mode; malformed ownership fails closed."""
 owner=Path.home()/'.local/state/omt-proxy/owner.json'
 if not owner.exists() and not owner.is_symlink():return None
 if not native():raise RuntimeError('代理控制归属异常，请使用恢复入口')
 import sys
 return sys.modules[__name__]
