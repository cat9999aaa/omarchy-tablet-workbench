#!/usr/bin/python3
"""Accept a fixed root-observed gesture, then recheck the user session lock."""
import fcntl
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import time

def main():
    runtime=Path(os.environ['XDG_RUNTIME_DIR'])/'pcadmin-control-center';runtime.mkdir(mode=0o700,exist_ok=True)
    with open(runtime/'receiver.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=runtime/'gesture.sock'
        if path.exists():
            if not stat.S_ISSOCK(path.lstat().st_mode) or path.lstat().st_uid!=os.getuid():raise ValueError('Unexpected socket owner/type')
            path.unlink()
        sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);sock.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
        sock.bind(str(path));path.chmod(0o600)
        while True:
            data,ancillary,_,_=sock.recvmsg(128,socket.CMSG_SPACE(12))
            sender=[struct.unpack('3i',v)[1] for level,kind,v in ancillary if level==socket.SOL_SOCKET and kind==socket.SCM_CREDENTIALS]
            if data!=b'three-finger-down' or sender!=[0]:continue
            try:
                if subprocess.check_output(['omarchy-shell','lock','isLocked'],text=True,timeout=2).strip()!='false':continue
                (runtime/'last-gesture').write_text(str(time.monotonic()))
                subprocess.run(['omarchy-shell','pcadmin.controlCenter','gesture'],capture_output=True,timeout=3)
            except (OSError,subprocess.SubprocessError):pass

if __name__=='__main__':main()
