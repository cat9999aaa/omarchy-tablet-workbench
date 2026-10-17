#!/usr/bin/python3
"""Explicit, key-only SSH dispatch. No installs and no local build fallback."""
import argparse,json,re,shlex,subprocess,tarfile
from pathlib import Path,PurePosixPath
from build_ime import ABI,verify_junit
from snapshot import create_snapshot,verify_archive,digest

def run(argv,**kwargs):
 return subprocess.run(argv,check=True,**kwargs)

def remote(host,argv,**kwargs):
 return run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,shlex.join(argv)],**kwargs)

def validate(host,root,job):
 if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*',host):raise ValueError('Use a configured SSH alias')
 if not root.startswith('/') or not re.fullmatch(r'[/a-zA-Z0-9_.-]+',root) or '..' in PurePosixPath(root).parts:raise ValueError('Use an explicit absolute build root without spaces')
 if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,63}',job):raise ValueError('Invalid job ID')
 return root.rstrip('/')+'/jobs/'+job

def prepare(source,destination):
 destination.mkdir(parents=True,exist_ok=False)
 manifest=create_snapshot(source,destination/'source.tar.gz')
 verify_archive(destination/'source.tar.gz',manifest)
 abi=subprocess.check_output(['pacman','-Q',*ABI],text=True).strip()
 (destination/'input.json').write_text(json.dumps({'source_files':manifest,'target_abi':abi,'target_packages':dict(line.split(' ',1) for line in subprocess.check_output(['pacman','-Q'],text=True).splitlines())},indent=2)+'\n')
 return manifest

def submit(host,root,job,inputs):
 target=validate(host,root,job)
 config=json.loads((inputs/'input.json').read_text())
 verify_archive(inputs/'source.tar.gz',config['source_files'])
 # Resolve scope on the host before creating anything. Existing job IDs fail closed.
 setup="""import sys,json
from pathlib import Path
root=Path(sys.argv[1]);job=root/'jobs'/sys.argv[2]
assert root.is_absolute() and root.resolve()==root and root.joinpath('build-scope.json').is_file(), 'Provisioned scope marker required'
assert job.resolve().is_relative_to(root), 'Job path escapes scope'
assert not any(p.is_symlink() for p in [job,*job.parents] if p!=root), 'Symlink in job path'
job.mkdir(parents=True,exist_ok=False)
(job/'runner').mkdir()
"""
 remote(host,['python','-c',setup,root,job])
 src=Path(__file__).resolve().parent
 run(['scp','-o','BatchMode=yes',str(inputs/'source.tar.gz'),str(inputs/'input.json'),host+':'+target+'/'])
 run(['scp','-o','BatchMode=yes',*[str(src/n) for n in ('build_ime.py','snapshot.py')],host+':'+target+'/runner/'])
 command=shlex.join(['python',target+'/runner/build_ime.py',root,job])+' > '+shlex.quote(target+'/runner.log')+' 2>&1'
 remote(host,['tmux','-L','pcadmin-build','-f','/dev/null','new-session','-d','-s',job,'-c',target,command])
 print(json.dumps({'job':job,'state':'submitted','note':'Use status; submission is not test success'}))

def status(host,root,job):
 target=validate(host,root,job)
 script="""import sys,json
from pathlib import Path
p=Path(sys.argv[1]);f=p/'result.json'
if not f.exists():f=p/'progress.json'
if not f.exists():print(json.dumps({'status':'not_started_or_interrupted'}))
else:
 d=json.loads(f.read_text());print(json.dumps({k:d[k] for k in ('job','status','stage','started_at','finished_at','tests','error') if k in d},indent=2))
"""
 remote(host,['python','-c',script,target])

def check_result(result,job,config,current_abi):
 if result.get('job')!=job or result.get('status')!='passed':raise ValueError('Build has not passed')
 if result.get('source_files')!=config['source_files']:raise ValueError('Returned source differs from submitted input')
 if result.get('target_abi')!=config['target_abi'] or current_abi!=config['target_abi']:raise ValueError('Tablet ABI changed; rebuild required')
 from build_ime import verify_test_inventory
 verify_test_inventory({'tests':[{'name':name} for name in result.get('tests',[])]})

def fetch(host,root,job,inputs,destination):
 target=validate(host,root,job)
 destination.mkdir(parents=True,exist_ok=False)
 run(['scp','-o','BatchMode=yes',host+':'+target+'/result.json',str(destination/'result.json')])
 result=json.loads((destination/'result.json').read_text())
 config=json.loads((inputs/'input.json').read_text())
 check_result(result,job,config,subprocess.check_output(['pacman','-Q',*ABI],text=True).strip())
 for name in ('artifacts.tar.gz','build.log','test.log','test-results.xml','packages.json'):
  run(['scp','-o','BatchMode=yes',host+':'+target+'/'+name,str(destination/name)])
 archive=destination/'artifacts.tar.gz'
 if digest(archive)!=result['artifact_sha256']:raise ValueError('Artifact checksum mismatch')
 verify_archive(archive,result['artifact_files'])
 verify_junit(destination/'test-results.xml')
 print(json.dumps({'job':job,'state':'download_verified','installed':False}))

def main():
 parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='action',required=True)
 p=subs.add_parser('prepare');p.add_argument('source',type=Path);p.add_argument('output',type=Path)
 for action in ('submit','status','fetch'):
  p=subs.add_parser(action);p.add_argument('--host',required=True);p.add_argument('--root',required=True);p.add_argument('--job',required=True)
  if action!='status':p.add_argument('--input',required=True,type=Path)
  if action=='fetch':p.add_argument('--output',required=True,type=Path)
 a=parser.parse_args()
 if a.action=='prepare':print(json.dumps({'source_files':len(prepare(a.source,a.output))}))
 elif a.action=='submit':submit(a.host,a.root,a.job,a.input)
 elif a.action=='status':status(a.host,a.root,a.job)
 elif a.action=='fetch':fetch(a.host,a.root,a.job,a.input,a.output)
if __name__=='__main__':main()
