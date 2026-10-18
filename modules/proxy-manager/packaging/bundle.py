#!/usr/bin/python3
"""Build a user-scoped install payload from reviewed source and a verified binary."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from install import Installer

def payload(source,binary,expected):
 source=Path(source).resolve();binary=Path(binary)
 data=binary.read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected or not data.startswith(b'\x7fELF'):raise ValueError('binary_integrity_failed')
 module=source/'modules/proxy-manager';out={'.local/lib/omt-proxy/omt-proxy':(data,0o755)}
 out['.config/systemd/user/v2rayn.service.d/90-omt-owner.conf']=(b'[Unit]\nConditionPathExists=!%h/.local/state/omt-proxy/owner.json\n',0o644)
 def add(src,dest,mode=0o644):
  if src.is_symlink():raise ValueError('symlink_source')
  out[dest]=(src.read_bytes(),mode)
 for p in (module/'integration').glob('*.py'):add(p,'.local/lib/omt-proxy/'+p.name)
 add(module/'packaging/install-root.py','.local/lib/omt-proxy/install-root.py')
 add(source/'scripts/proxy-upstream.py','.local/lib/omt-proxy/proxy-upstream.py')
 for p in (module/'packaging').glob('*.service'):add(p,'.config/systemd/user/'+p.name)
 add(module/'packaging/launcher.py','.local/bin/omt-proxy',0o755)
 add(module/'packaging/omt-proxy.desktop','.local/share/applications/omt-proxy.desktop')
 add(source/'modules/ProxyShell.qml','.local/share/omt-proxy/modules/ProxyShell.qml')
 for folder in ('proxy-manager/ui','workbench-ui'):
  for p in (source/'modules'/folder).rglob('*'):
   if p.is_file() and p.suffix in ('.qml','.js'):add(p,'.local/share/omt-proxy/modules/'+str(p.relative_to(source/'modules')))
 for relative in ('network-center/network.py','network-center/cell_proxy_watch.py','control-center/control_center.py'):
  add(source/'modules'/relative,'Projects/pcadmin/tools/'+relative,0o755)
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--sha256',required=True)
 p.add_argument('--apply',action='store_true');args=p.parse_args();files=payload(args.source,args.binary,args.sha256);installer=Installer(Path.home())
 print(json.dumps(installer.apply(files) if args.apply else installer.plan(files)))
if __name__=='__main__':
 try:main()
 except Exception:print('{"status":"failed","error_code":"bundle_failed"}');sys.exit(1)
