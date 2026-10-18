#!/usr/bin/python3
"""Install only two reviewed root helpers; do not mutate network configuration."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile

def install():
 if os.geteuid()!=0:raise ValueError('root_required')
 source=Path(__file__).resolve().parent
 if (source/'root_frontend.py').exists():base=source
 else:base=source.parent/'integration'
 targets={'root_frontend.py':('omt-proxy-frontend',0o755),'frontend.py':('omt_proxy_frontend.py',0o644)}
 destination=Path('/usr/local/libexec');backup=Path('/var/lib/pcadmin-network/native-proxy-helpers')
 if destination.resolve()!=destination or backup.resolve()!=backup:raise ValueError('unsafe_path')
 destination.mkdir(parents=True,exist_ok=True);backup.mkdir(parents=True,exist_ok=True,mode=0o700)
 for name,(target,mode) in targets.items():
  data=(base/name).read_bytes();path=destination/target
  if path.is_symlink():raise ValueError('symlink_target')
  if path.exists():
   old=path.read_bytes();copy=backup/(target+'-'+hashlib.sha256(old).hexdigest())
   if not copy.exists():
    with copy.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(old);f.flush();os.fsync(f.fileno())
  fd,tmp=tempfile.mkstemp(prefix='.omt-',dir=destination)
  try:
   with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),mode);os.fchown(f.fileno(),0,0)
   os.replace(tmp,path)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 # Once per boot, before the root TUN starts. Running it now establishes the
 # initial successful state so a deliberate tested restart does not undo itself.
 unit=Path('/etc/systemd/system/omt-proxy-front-recovery.service')
 dropin=Path('/etc/systemd/system/pcadmin-v2ray-tun.service.d/90-omt-recovery.conf')
 texts={unit:"[Unit]\nDescription=Recover interrupted proxy frontend before initial TUN start\nBefore=pcadmin-v2ray-tun.service\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/local/libexec/omt-proxy-frontend recover-config\n",dropin:"[Unit]\nRequires=omt-proxy-front-recovery.service\nAfter=omt-proxy-front-recovery.service\n"}
 for path,text in texts.items():
  if path.resolve()!=path:raise ValueError('unsafe_unit_path')
  path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists() and path.read_text()!=text:raise ValueError('foreign_unit_conflict')
  with path.open('w') as f:f.write(text);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),0o644)
 import subprocess
 subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=15)
 subprocess.run(['systemctl','start','omt-proxy-front-recovery.service'],check=True,capture_output=True,timeout=20)
 print('{"ok":true,"network_changed":false}')
if __name__=='__main__':
 try:install()
 except Exception:print('{"ok":false,"error_code":"helper_install_failed"}');sys.exit(1)
