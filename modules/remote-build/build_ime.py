#!/usr/bin/python3
"""Run an IME build in an explicitly provisioned project root, never install globally."""
import fcntl,json,os,re,subprocess,sys,tarfile,time
import xml.etree.ElementTree as ET
import tempfile,shutil
from pathlib import Path
from urllib.parse import urlparse
from snapshot import digest,verify_archive
PACKAGES=['cmake','ninja','librime','rime-luna-pinyin','rime-prelude','rime-essay']
EXPECTED_TESTS={'engine','backend','control','layout','preview','bridge','touchkey','learning','MetasequoiaHandwritingTests'}
ABI=['qt6-base','qt6-declarative','fcitx5','glibc','gcc-libs','python']

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def output(args):return subprocess.check_output(args,text=True).strip()
def save(path,data):
 with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix='.state-',delete=False) as f:
  f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp=Path(f.name)
 try:temp.replace(path)
 finally:temp.unlink(missing_ok=True)
def scoped(root,*parts):
 p=root.joinpath(*parts)
 if not p.resolve().is_relative_to(root) or any(x.is_symlink() for x in [p,*p.parents] if x!=root):raise ValueError('Path outside build scope')
 return p

def verify_test_inventory(data):
 names=[t['name'] for t in data['tests']]
 if len(names)!=len(EXPECTED_TESTS) or set(names)!=EXPECTED_TESTS:raise ValueError('Incomplete or unexpected CTest inventory')
 return names

def verify_junit(path):
 tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
 verify_test_inventory({'tests':[{'name':c.get('name')} for c in cases]})
 if any(c.find('skipped') is not None or c.find('failure') is not None or c.find('error') is not None or c.get('status') not in (None,'run') for c in cases):raise ValueError('CTest skipped or failed a required case')
 for key in ('failures','errors','disabled','skipped'):
  if int(tree.get(key,'0')):raise ValueError('Nonzero CTest '+key)
 return True

def verify_signature_status(status,revoked):
 valid=[]
 for line in status.splitlines():
  fields=line.split()
  if len(fields)<2 or fields[0]!='[GNUPG:]':continue
  if fields[1] in {'BADSIG','ERRSIG','EXPSIG','EXPKEYSIG','REVKEYSIG'}:raise ValueError('Rejected package signature status')
  if fields[1]=='VALIDSIG':
   fingerprints={fields[2],fields[-1]}
   if fingerprints & revoked:raise ValueError('Revoked package signer')
   valid.append(fields[2])
 if not valid:raise ValueError('No valid package signature')
 return valid

def execute(root,jobid):
 root=Path(root).absolute()
 if root!=root.resolve() or not (root/'build-scope.json').is_file():raise ValueError('Explicit build-scope.json marker required')
 if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,63}',jobid):raise ValueError('Invalid job id')
 job=scoped(root,'jobs',jobid)
 if (job/'result.json').exists():raise ValueError('Job already finished; choose a new ID')
 config=json.loads((job/'input.json').read_text());result={'job':jobid,'started_at':time.time(),'status':'running'};save(job/'progress.json',result)
 try:
  actual=output(['pacman','-Q',*ABI]);expected=config['target_abi']
  if actual!=expected:raise RuntimeError('Target/host ABI package versions differ; refuse build')
  result['target_abi']=actual
  result['host_packages']=output(['pacman','-Q'])
  toolchain=scoped(root,'toolchain','ime-v1');toolchain.mkdir(parents=True,exist_ok=True)
  with (toolchain/'build.lock').open('w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   overlay=scoped(root,'jobs',jobid,'overlay');cache=scoped(root,'toolchain','ime-v1','packages')
   overlay.mkdir(exist_ok=False);cache.mkdir(exist_ok=True)
   gnupg=scoped(root,'toolchain','ime-v1','gnupg');gnupg.mkdir(mode=0o700,exist_ok=True)
   keyring=scoped(root,'toolchain','ime-v1','archlinux.gpg')
   run(['gpg','--no-options','--batch','--yes','--homedir',str(gnupg),'--dearmor','--output',str(keyring),'/usr/share/pacman/keyrings/archlinux.gpg'])
   packages=[]
   for line in output(['pacman','-Sp','--print-format','%n\t%v\t%l',*PACKAGES]).splitlines():
    name,version,url=line.split('\t');u=urlparse(url)
    if u.scheme!='https' or u.username or u.password:raise ValueError('Package URL must use credential-free HTTPS')
    target_version=config.get('target_packages',{}).get(name)
    if target_version is not None and version!=target_version:raise ValueError('Overlay/target package mismatch: '+name)
    filename=Path(u.path).name
    if not filename.endswith('.pkg.tar.zst') or '/' in filename:raise ValueError('Unexpected package format')
    package=cache/filename;signature=cache/(filename+'.sig')
    for target,link in [(package,url),(signature,url+'.sig')]:
     if not target.exists():
      partial=target.with_suffix(target.suffix+'.partial')
      run(['curl','--silent','--show-error','--fail','--location','--retry','2','--connect-timeout','15','--max-time','180','--output',str(partial),link]);partial.replace(target)
    checked=run(['gpgv','--status-fd','1','--homedir',str(gnupg),'--keyring',str(keyring),str(signature),str(package)],stdout=subprocess.PIPE,text=True)
    revoked=set(Path('/usr/share/pacman/keyrings/archlinux-revoked').read_text().split())
    verify_signature_status(checked.stdout,revoked)
    run(['bsdtar','--no-same-owner','-xf',str(package),'-C',str(overlay)])
    packages.append({'name':name,'version':version,'url':url,'sha256':digest(package),'signature_verified':True})
   save(job/'packages.json',packages)
   source=scoped(root,'jobs',jobid,'source');source.mkdir(exist_ok=False)
   verify_archive(job/'source.tar.gz',config['source_files'])
   with tarfile.open(job/'source.tar.gz') as t:t.extractall(source,filter='data')
   (source/'build').mkdir();(job/'home').mkdir();(job/'runtime').mkdir(mode=0o700)
   (job/'etc').mkdir()
   (job/'etc/passwd').write_text('root:x:0:0:Build sandbox:/work/home:/bin/sh\n')
   (job/'etc/group').write_text('root:x:0:\n')
   # No host HOME, /run, D-Bus, devices, display or network inside the build.
   sandbox=['bwrap','--unshare-all','--uid','0','--gid','0','--new-session','--clearenv','--overlay-src','/usr','--overlay-src',str(overlay/'usr'),'--ro-overlay','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/etc','--ro-bind',str(job/'etc/passwd'),'/etc/passwd','--ro-bind',str(job/'etc/group'),'/etc/group','--ro-bind-try','/etc/ld.so.cache','/etc/ld.so.cache','--ro-bind-try','/etc/fonts','/etc/fonts','--dir','/work','--ro-bind',str(source),'/work/source','--bind',str(source/'build'),'/work/source/build','--bind',str(job/'home'),'/work/home','--bind',str(job/'runtime'),'/work/runtime','--chdir','/work/source','--setenv','PATH','/usr/bin','--setenv','HOME','/work/home','--setenv','XDG_RUNTIME_DIR','/work/runtime','--setenv','QT_QPA_PLATFORM','offscreen','--setenv','LC_ALL','C.UTF-8']
   # The environment variables describe the child sandbox, not the host shell.
   result['isolation']='read-only host usr plus signed package overlay; private home/runtime/bus; no network'
   result['packages']=packages
   save(job/'progress.json',{**result,'stage':'compile'})
   with (job/'build.log').open('x') as log:
    run([*sandbox,'cmake','-S','.','-B','build','-G','Ninja','-DCMAKE_BUILD_TYPE=Debug','-DCMAKE_CXX_FLAGS=-ffile-prefix-map=/work=.'],stdout=log,stderr=subprocess.STDOUT)
    run([*sandbox,'cmake','--build','build','--parallel','2'],stdout=log,stderr=subprocess.STDOUT)
   save(job/'progress.json',{**result,'stage':'test'})
   tests=verify_test_inventory(json.loads(output([*sandbox,'ctest','--test-dir','build','--show-only=json-v1'])))
   with (job/'test.log').open('x') as log:run([*sandbox,'ctest','--test-dir','build','--output-on-failure','--timeout','120','--output-junit','/work/source/build/test-results.xml'],stdout=log,stderr=subprocess.STDOUT)
   junit=scoped(root,'jobs',jobid,'source','build','test-results.xml')
   verify_junit(junit)
   with (job/'test-results.xml').open('xb') as f:f.write(junit.read_bytes())
   binaries=['omt-backend','omt-handwriting','libomtbridge.so','test_engine','test_bridge','test_learning']
   manifest={name:digest(scoped(root,'jobs',jobid,'source','build',name)) for name in binaries}
   with tarfile.open(job/'artifacts.tar.gz','x:gz') as t:
    for name in binaries:t.add(source/'build'/name,arcname=name,recursive=False)
   verify_archive(job/'artifacts.tar.gz',manifest)
   result.update(status='passed',artifact_sha256=digest(job/'artifacts.tar.gz'),artifact_files=manifest,source_files=config['source_files'],tests=tests,jobs=2)
 except Exception as error:
  result.update(status='failed',error=str(error))
  raise
 finally:
  result['finished_at']=time.time();save(job/'result.json',result)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: build_ime.py ROOT JOB_ID')
 execute(sys.argv[1],sys.argv[2])
