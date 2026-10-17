#!/usr/bin/python3
"""Run returned IME binaries in an isolated temporary tree; never install."""
import argparse,json,subprocess,tarfile,tempfile
from datetime import datetime,timezone
from pathlib import Path
from build_ime import ABI,verify_junit
from client import check_result
from snapshot import verify_archive,digest

def check(inputs,download):
 result=json.loads((download/'result.json').read_text());config=json.loads((inputs/'input.json').read_text())
 check_result(result,result['job'],config,subprocess.check_output(['pacman','-Q',*ABI],text=True).strip())
 verify_junit(download/'test-results.xml')
 if digest(download/'artifacts.tar.gz')!=result['artifact_sha256']:raise ValueError('Artifact hash mismatch')
 verify_archive(download/'artifacts.tar.gz',result['artifact_files']);verify_archive(inputs/'source.tar.gz',config['source_files'])
 evidence={'job':result['job'],'artifact_sha256':result['artifact_sha256'],'target_abi':result['target_abi'],'observed_at':datetime.now(timezone.utc).isoformat(),'installed':False,'checks':[]}
 with tempfile.TemporaryDirectory(prefix='omt-abi-') as directory:
  work=Path(directory);source=work/'source';source.mkdir()
  with tarfile.open(inputs/'source.tar.gz') as t:t.extractall(source,filter='data')
  build=source/'build';build.mkdir()
  with tarfile.open(download/'artifacts.tar.gz') as t:t.extractall(build,filter='data')
  for name in ('home','runtime','etc'):(work/name).mkdir(mode=0o700)
  (work/'etc/passwd').write_text('root:x:0:0:Test sandbox:/work/home:/bin/sh\n');(work/'etc/group').write_text('root:x:0:\n')
  sandbox=['bwrap','--unshare-all','--uid','0','--gid','0','--new-session','--clearenv','--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/etc','--ro-bind',str(work/'etc/passwd'),'/etc/passwd','--ro-bind',str(work/'etc/group'),'/etc/group','--ro-bind-try','/etc/ld.so.cache','/etc/ld.so.cache','--ro-bind-try','/etc/fonts','/etc/fonts','--dir','/work','--ro-bind',str(source),'/work/source','--bind',str(build),'/work/source/build','--bind',str(work/'home'),'/work/home','--bind',str(work/'runtime'),'/work/runtime','--chdir','/work/source','--setenv','PATH','/usr/bin','--setenv','HOME','/work/home','--setenv','XDG_RUNTIME_DIR','/work/runtime','--setenv','QT_QPA_PLATFORM','offscreen','--setenv','LC_ALL','C.UTF-8']
  tests=[('engine',['./build/test_engine','./rime','./build/local-test-rime']),('bridge',['dbus-run-session','--','./build/test_bridge','--disable','all','--enable','dbus,keyboard']),('backend',['dbus-run-session','--','python','tests/test_backend.py']),('module_load',['python','-c',"import ctypes;ctypes.CDLL('./build/libomtbridge.so');print('PASS module load')"])]
  with (download/'local-check.log').open('x') as log:
   for name,command in tests:
    log.write(name+'\n');log.flush()
    subprocess.run([*sandbox,*command],check=True,timeout=120,stdout=log,stderr=subprocess.STDOUT)
    evidence['checks'].append({'name':name,'status':'passed'})
 evidence['status']='passed';(download/'local-check.json').write_text(json.dumps(evidence,indent=2)+'\n');return evidence
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True,type=Path);parser.add_argument('--download',required=True,type=Path);a=parser.parse_args();print(json.dumps(check(a.input,a.download)))
