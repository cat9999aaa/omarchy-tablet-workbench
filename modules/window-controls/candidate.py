"""Build/verify a complete navigation candidate; never install or run desktop commands."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[2]
SHARED=runpy.run_path(str(ROOT/'scripts/workbench-ui/sync.py'))['FILES']
HELPERS=('navigation.py','navigation_read.py','task_model.py','task_source.py','tasks.py')
UI=('Navigation.qml','NavigationSession.js','TaskCenter.qml','TaskSession.js',*('Workbench/'+name for name in SHARED))
spec=importlib.util.spec_from_file_location('navigation_plugin_release',ROOT/'modules/plugin-release/release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify(output):
 output=Path(output)
 try:
  receipt=release.read_json(output/'candidate.json')
  manifest,files=release.bundle(output/'bundle')
  if manifest['id']!='pcadmin.navigation' or manifest['version']!='0.1.5':raise ValueError('candidate identity mismatch')
  if receipt.get('version')!=manifest['version'] or receipt.get('ui')!=files or set(files)!=set(UI):raise ValueError('candidate UI mismatch')
  helpers=release.scan(output/'helpers')
  if set(helpers)!=set(HELPERS) or receipt.get('helpers')!=helpers:raise ValueError('candidate helpers mismatch')
  return receipt
 except (OSError,release.ReleaseError,KeyError,TypeError) as exc:raise ValueError('invalid navigation candidate') from exc

def build(source,output):
 source=Path(source).absolute();output=Path(output).absolute()
 if output.exists():raise FileExistsError(output)
 release.no_links(source);release.no_links(output)
 for name in (*UI,*HELPERS,'manifest.json'):
  file=source/name
  if not file.is_file() or file.is_symlink():raise ValueError('missing or linked runtime file: '+name)
  release.no_links(file)
 manifest=release.manifest(source/'manifest.json')
 if manifest['id']!='pcadmin.navigation' or manifest['version']!='0.1.5':raise ValueError('candidate version mismatch')
 output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='.navigation-candidate-',dir=output.parent) as temp:
  stage=Path(temp);payload=stage/'payload';payload.mkdir()
  for name in UI:
   dest=payload/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,dest)
  candidate=stage/'candidate';candidate.mkdir();(candidate/'helpers').mkdir()
  release.pack(source/'manifest.json',payload,candidate/'bundle')
  for name in HELPERS:shutil.copy2(source/name,candidate/'helpers'/name)
  receipt={'schema':1,'version':'0.1.5','kind':'software-candidate-not-installed',
           'ui':release.scan(candidate/'bundle/files'),'helpers':release.scan(candidate/'helpers'),
           'required_gates':['matching-compositor','official-handoff','helper-ui-recovery','independent-review','unlocked-live-acceptance']}
  (candidate/'candidate.json').write_text(json.dumps(receipt,indent=2)+'\n')
  verify(candidate);candidate.rename(output)
 return verify(output)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','verify']);parser.add_argument('output',type=Path);parser.add_argument('--source',type=Path,default=Path(__file__).parent)
 args=parser.parse_args();result=build(args.source,args.output) if args.command=='build' else verify(args.output)
 print(json.dumps(result,indent=2))
