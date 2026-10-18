#!/usr/bin/python3
"""Version existing Omarchy user plugins; no root services or private data migration."""
import argparse,contextlib,fcntl,hashlib,json,os,re,shutil,subprocess,tempfile,time,uuid
from pathlib import Path,PurePosixPath

class ReleaseError(RuntimeError):pass
PROFILES={
 'ime':('.touchime','omtInput','version',False),
 'network':('.network','omarchy.network','travelVersion',False),
 'battery':('.power','omarchy.power','workbenchState',True),
 'control':('pcadmin.control-center','pcadmin.controlCenter','state',True),
 'navigation':('pcadmin.navigation','pcadmin.navigation','state',True),
}
def sha(data):return hashlib.sha256(data).hexdigest()
def no_links(path):
 for p in [path,*path.parents]:
  if p.is_symlink():raise ReleaseError('Symlink paths are not accepted')
def relative(name):
 if not isinstance(name,str) or not name or '\\' in name or '\x00' in name:raise ReleaseError('Invalid relative path')
 p=PurePosixPath(name)
 if p.is_absolute() or any(x in ('','..','.') for x in name.split('/')):raise ReleaseError('Path escapes release')
 return name
def unique_pairs(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise ValueError('Duplicate JSON key')
  result[key]=value
 return result
def read_json(path):
 try:
  no_links(path);return json.loads(path.read_text(),object_pairs_hook=unique_pairs)
 except (OSError,ValueError) as e:raise ReleaseError('Cannot read valid JSON: '+path.name) from e
def manifest(path):return validate_manifest(read_json(path))
def validate_manifest(d):
 if not isinstance(d,dict) or type(d.get('schemaVersion')) is not int or d.get('schemaVersion')!=1:raise ReleaseError('Unsupported plugin manifest')
 if not isinstance(d.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',d.get('id','')) or '..' in d['id'] or d['id'].startswith('omarchy.'):raise ReleaseError('Invalid user plugin id')
 if not isinstance(d.get('version'),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}',d.get('version','')):raise ReleaseError('Invalid version')
 if not isinstance(d.get('entryPoints'),dict) or not d['entryPoints']:raise ReleaseError('Missing entry points')
 for value in d['entryPoints'].values():relative(value)
 if not isinstance(d.get('kinds'),list) or not d['kinds']:raise ReleaseError('Missing plugin kinds')
 return d
def scan(folder):
 no_links(folder)
 if not folder.is_dir():raise ReleaseError('Missing payload folder')
 found={};size=0
 for p in folder.rglob('*'):
  no_links(p)
  if p.is_dir():continue
  if not p.is_file():raise ReleaseError('Only regular release files are supported')
  name=relative(p.relative_to(folder).as_posix());size+=p.stat().st_size
  if len(found)>=1000 or size>100*1024*1024:raise ReleaseError('Release exceeds limits')
  found[name]=sha(p.read_bytes())
 if not found:raise ReleaseError('Empty release')
 return found
def bundle(path):
 path=Path(path).absolute();no_links(path);d=manifest(path/'manifest.json');index=read_json(path/'files.json')
 if not isinstance(index,dict) or type(index.get('schema')) is not int or index.get('schema')!=1 or not isinstance(index.get('sha256'),dict):raise ReleaseError('Invalid file index')
 for name,digest in index['sha256'].items():
  relative(name)
  if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ReleaseError('Invalid file digest')
 if scan(path/'files')!=index['sha256']:raise ReleaseError('Payload missing, extra or changed')
 if any(p not in index['sha256'] for p in d['entryPoints'].values()):raise ReleaseError('Entry point not in payload')
 return d,index['sha256']
def pack(source_manifest,payload,output):
 source_manifest=Path(source_manifest).absolute();payload=Path(payload).absolute();output=Path(output).absolute()
 d=manifest(source_manifest);hashes=scan(payload);no_links(output)
 payload=payload.resolve();output=output.resolve()
 watched=(Path.home()/'.config/omarchy/plugins').resolve()
 if output.is_relative_to(payload) or output.is_relative_to(watched):raise ReleaseError('Package output must be outside source and watched plugins')
 if output.exists():raise ReleaseError('Output already exists')
 if any(p not in hashes for p in d['entryPoints'].values()):raise ReleaseError('Entry point not in payload')
 output.mkdir(parents=True,mode=0o700);shutil.copytree(payload,output/'files')
 (output/'manifest.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 (output/'files.json').write_text(json.dumps({'schema':1,'sha256':hashes},indent=2)+'\n');bundle(output)
 return {'status':'packed','files':len(hashes)}
def command(args):
 try:return subprocess.run(args,check=True,capture_output=True,text=True,timeout=5).stdout.strip()
 except (OSError,subprocess.SubprocessError) as e:raise ReleaseError('Official command failed: '+args[0]) from e

class ReleaseManager:
 def __init__(self,plugins,state,runner=command,timeout=12):
  self.plugins=Path(plugins).absolute();self.state=Path(state).absolute();self.runner=runner;self.timeout=timeout
  no_links(self.plugins);no_links(self.state)
  self.plugins=self.plugins.resolve();self.state=self.state.resolve()
  if self.state==self.plugins or self.state.is_relative_to(self.plugins):raise ReleaseError('State must be outside watched plugins')
  self.staging=self.plugins.parent/'.workbench-release-staging'
 def identity(self,plugin_id,profile):
  if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',plugin_id) or '..' in plugin_id:raise ReleaseError('Invalid plugin id')
  if profile not in PROFILES:raise ReleaseError('Unknown runtime profile')
  suffix=PROFILES[profile][0]
  if (plugin_id!=suffix if profile in ('control','navigation') else not plugin_id.endswith(suffix)):raise ReleaseError('Profile does not match plugin')
  plug=self.plugins/plugin_id;no_links(plug)
  if not plug.is_dir():raise ReleaseError('Only existing installed plugins may be updated')
  no_links(plug/'manifest.json')
  try:
   original=(plug/'manifest.json').read_bytes()
   current=validate_manifest(json.loads(original,object_pairs_hook=unique_pairs))
  except (OSError,ValueError) as e:raise ReleaseError('Cannot read installed manifest') from e
  if current['id']!=plugin_id:raise ReleaseError('Installed identity mismatch')
  return plug,current,original
 def context(self,source,plugin_id,profile):
  plug,old,original=self.identity(plugin_id,profile);new,files=bundle(source)
  if new['id']!=plugin_id or new['kinds']!=old['kinds'] or set(new['entryPoints'])!=set(old['entryPoints']):raise ReleaseError('Candidate changes plugin identity or roles')
  return plug,old,new,files,original
 def plan(self,source,plugin_id,profile):
  plug,old,new,files,original=self.context(source,plugin_id,profile)
  return {'status':'checked','plugin':plugin_id,'from':old['version'],'to':new['version'],'files':len(files),'would_change':old['version']!=new['version'],'writes':False}
 @contextlib.contextmanager
 def locked(self,plugin_id):
  no_links(self.state);self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
  no_links(self.staging);self.staging.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.staging.is_relative_to(self.plugins):raise ReleaseError('Staging must be outside watched plugins')
  lock=self.state/(plugin_id+'.lock');no_links(lock)
  fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError as e:raise ReleaseError('Another release is running') from e
   yield
  finally:os.close(fd)
 def atomic(self,path,data,mode=0o600):
  no_links(path)
  # Stage outside the plugin watcher, then perform one same-filesystem rename.
  with tempfile.NamedTemporaryFile(dir=self.staging,delete=False) as f:
   temp=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),mode)
  try:os.replace(temp,path)
  finally:temp.unlink(missing_ok=True)
 def save(self,transaction,data):
  self.atomic(transaction/'transaction.json',(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
 def require_unlocked(self):
  # Omarchy owns this lock; logind LockedHint can disagree with its state.
  if self.runner(['omarchy-shell','lock','isLocked']).strip()!='false':
   raise ReleaseError('Omarchy session is locked or lock state is unknown')
 def wait_version(self,profile,version,require_control_ready=False):
  _,target,method,is_json=PROFILES[profile];end=time.monotonic()+self.timeout
  while True:
   try:
    value=self.runner(['omarchy-shell',target,method]).strip()
    actual=json.loads(value).get('version') if is_json else value
    needs_ready=profile=='ime' or (profile=='control' and require_control_ready)
    if actual==version and (not needs_ready or self.runner(['omarchy-shell',target,'ready']).strip()=='true'):return
   except (ReleaseError,ValueError,AttributeError):pass
   if time.monotonic()>=end:raise ReleaseError('Runtime version/readiness was not confirmed')
   time.sleep(min(.1,max(.001,self.timeout/4)))
 def restore(self,plug,transaction,data,profile):
  before=transaction/'before.json';no_links(before)
  try:original=before.read_bytes();current=(plug/'manifest.json').read_bytes()
  except OSError as e:raise ReleaseError('Recovery evidence unavailable') from e
  if sha(original)!=data['before_sha256'] or manifest(before)['id']!=data['plugin']:raise ReleaseError('Recovery backup does not match')
  if sha(current) not in (data['after_sha256'],data['before_sha256']):
   data['status']='conflict-preserved';self.save(transaction,data);raise ReleaseError('Concurrent edit preserved; recovery not applied')
  self.atomic(plug/'manifest.json',original,data['mode']);data['status']='rollback-unverified';self.save(transaction,data)
  self.runner(['omarchy-shell','shell','rescanPlugins']);self.wait_version(profile,data['from'])
  if sha((plug/'manifest.json').read_bytes())!=data['before_sha256']:
   data['status']='conflict-preserved';self.save(transaction,data);raise ReleaseError('Concurrent edit preserved during recovery probe')
  data['status']='rolled-back';self.save(transaction,data);return data
 def apply(self,source,plugin_id,profile):
  self.identity(plugin_id,profile)
  with self.locked(plugin_id):
   plug,old,new,files,original=self.context(source,plugin_id,profile)
   if new['version']==old['version']:raise ReleaseError('Same-version replacement is refused')
   self.require_unlocked()
   before_hash=sha(original);mode=(plug/'manifest.json').stat().st_mode&0o777
   self.wait_version(profile,old['version'],require_control_ready=True)
   if sha((plug/'manifest.json').read_bytes())!=before_hash:raise ReleaseError('Installed manifest changed during initial probe')
   token=uuid.uuid4().hex;release='workbench-releases/'+new['version']+'-'+token
   candidate={**new,'entryPoints':{k:release+'/'+v for k,v in new['entryPoints'].items()}}
   encoded=(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n').encode();transaction=None;data=None
   try:
    with tempfile.TemporaryDirectory(dir=self.staging,prefix='prepare-') as tmp:
     staged=Path(tmp)/'plugin';payload=staged/release;payload.parent.mkdir(parents=True)
     shutil.copytree(Path(source)/'files',payload)
     if scan(payload)!=files:raise ReleaseError('Payload changed while copying')
     (staged/'manifest.json').write_bytes(encoded);self.runner(['omarchy','plugin','validate',str(staged)])
     if sha((plug/'manifest.json').read_bytes())!=before_hash:raise ReleaseError('Installed manifest changed during preparation')
     transaction=self.state/plugin_id/token;no_links(transaction);transaction.mkdir(parents=True,mode=0o700)
     (transaction/'before.json').write_bytes(original);os.chmod(transaction/'before.json',0o600)
     data={'schema':1,'transaction':token,'plugin':plugin_id,'profile':profile,'from':old['version'],'to':new['version'],'before_sha256':before_hash,'after_sha256':sha(encoded),'mode':mode,'release':release,'status':'prepared','created_at':time.time()};self.save(transaction,data)
     destination=plug/release;no_links(destination);destination.parent.mkdir(exist_ok=True)
     os.replace(payload,destination)
     self.require_unlocked()
     if sha((plug/'manifest.json').read_bytes())!=before_hash:raise ReleaseError('Installed manifest changed before switch')
     self.atomic(plug/'manifest.json',encoded,mode);data['status']='pointer-written';self.save(transaction,data)
     self.runner(['omarchy-shell','shell','rescanPlugins']);self.wait_version(profile,new['version'],require_control_ready=True)
     self.require_unlocked()
     if sha((plug/'manifest.json').read_bytes())!=data['after_sha256']:raise ReleaseError('Installed manifest changed during new runtime probe')
     data['status']='applied';self.save(transaction,data);return data
   except BaseException as failure:
    if data is not None:
     try:
      current=sha((plug/'manifest.json').read_bytes())
      if current==data['after_sha256']:self.restore(plug,transaction,data,profile)
      elif current!=data['before_sha256']:data['status']='conflict-preserved';self.save(transaction,data)
      else:data['status']='not-applied';self.save(transaction,data)
     except Exception as recovery:
      raise ReleaseError('Release failed; recovery not verified; keep transaction evidence') from recovery
    if isinstance(failure,(KeyboardInterrupt,SystemExit)):raise
    raise ReleaseError('Release failed; inspect transaction status') from failure
 def rollback(self,plugin_id,token,profile):
  plug,_,_=self.identity(plugin_id,profile)
  if not re.fullmatch('[0-9a-f]{32}',token):raise ReleaseError('Invalid transaction id')
  with self.locked(plugin_id):
   transaction=self.state/plugin_id/token;no_links(transaction);data=read_json(transaction/'transaction.json')
   if not isinstance(data,dict) or data.get('schema')!=1 or data.get('transaction')!=token or data.get('plugin')!=plugin_id or data.get('profile')!=profile:raise ReleaseError('Transaction identity mismatch')
   if any(not isinstance(data.get(key),str) or not re.fullmatch('[0-9a-f]{64}',data[key]) for key in ('before_sha256','after_sha256')):raise ReleaseError('Invalid recovery checksums')
   if any(not isinstance(data.get(key),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}',data[key]) for key in ('from','to')):raise ReleaseError('Invalid recovery versions')
   if type(data.get('mode')) is not int or not 0<=data['mode']<=0o777:raise ReleaseError('Invalid recovery file mode')
   return self.restore(plug,transaction,data,profile)

def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='op',required=True)
 p=sub.add_parser('pack');p.add_argument('--manifest',required=True,type=Path);p.add_argument('--payload',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
 for name in ('plan','apply','rollback'):
  p=sub.add_parser(name);p.add_argument('--plugin-id',required=True);p.add_argument('--profile',choices=PROFILES,required=True)
  p.add_argument('--transaction',required=True) if name=='rollback' else p.add_argument('--bundle',required=True,type=Path)
 a=parser.parse_args()
 try:
  if a.op=='pack':result=pack(a.manifest,a.payload,a.output)
  else:
   manager=ReleaseManager(Path.home()/'.config/omarchy/plugins',Path.home()/'.local/state/omarchy-tablet-workbench/plugin-releases')
   result=manager.rollback(a.plugin_id,a.transaction,a.profile) if a.op=='rollback' else getattr(manager,a.op)(a.bundle,a.plugin_id,a.profile)
  print(json.dumps(result,ensure_ascii=False,indent=2))
 except (ReleaseError,OSError) as e:parser.exit(1,str(e)+'\n')
if __name__=='__main__':main()
