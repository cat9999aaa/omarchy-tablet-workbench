#!/usr/bin/python3
"""One UI process; opening/closing never changes proxy intent."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))
fd=os.open(runtime/'omt-proxy-ui.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:sys.exit(0)
config=Path.home()/'.local/share/omt-proxy/modules/ProxyShell.qml'
sys.exit(subprocess.run(['quickshell','--path',str(config)],pass_fds=(fd,)).returncode)
