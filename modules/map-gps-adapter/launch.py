#!/usr/bin/python3
"""Load the private GPS adapter for Marble only; never start GPS or change Qt globally."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path

def checked_environment(release,environment,qt_versions):
 release=Path(release).resolve()
 manifest=json.loads((release/'release.json').read_text())
 binary=release/'plugins/position/libworkbench_gpsd.so'
 if manifest.get('schema')!=1 or manifest.get('qt_versions')!=qt_versions:raise ValueError('Qt version changed; rebuild the map adapter before use')
 if not binary.is_file() or binary.is_symlink() or hashlib.sha256(binary.read_bytes()).hexdigest()!=manifest.get('binary_sha256'):raise ValueError('Map adapter missing or changed')
 result=dict(environment)
 result['QT_PLUGIN_PATH']=str(release/'plugins')+(os.pathsep+result['QT_PLUGIN_PATH'] if result.get('QT_PLUGIN_PATH') else '')
 return result

def localized_environment(environment,library=Path('/usr/lib/libKirigami.so.6')):
 # Load the packaged translation initializer before QML creates SearchField.
 # This environment is passed only to Marble, never exported to the session.
 library=Path(library)
 if not library.is_file():raise ValueError('地图中文界面依赖缺失，请检查系统 Kirigami 软件包')
 result=dict(environment);previous=result.get('LD_PRELOAD','');name=str(library)
 if name not in re.split(r'[:\s]+',previous):result['LD_PRELOAD']=name+(' '+previous if previous else '')
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--release',required=True,type=Path);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 try:
  versions=subprocess.check_output(['/usr/bin/pkg-config','--modversion','Qt6Core','Qt6Positioning'],text=True,timeout=5).splitlines()
  environment=localized_environment(checked_environment(args.release,os.environ,versions))
  if args.check:print(json.dumps({'ready':True,'scope':'Marble process only','gps_service_changed':False}));return
  os.execve('/usr/bin/marble-maps',['marble-maps'],environment)
 except (OSError,ValueError,subprocess.SubprocessError) as error:parser.exit(1,str(error)+'\n')
if __name__=='__main__':main()
