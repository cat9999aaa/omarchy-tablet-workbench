#!/usr/bin/python3
"""Screen-edge navigation via Omarchy menus; fail closed during lock."""
import sys,subprocess,os,time
from pathlib import Path

def recent_three_finger():
    try:
        stamp=float((Path(os.environ['XDG_RUNTIME_DIR'])/'pcadmin-control-center/last-gesture').read_text())
        return 0<=time.monotonic()-stamp<.8
    except (KeyError,OSError,ValueError):return False

def dispatch(args):
    if not args:return 2
    try:
        if subprocess.check_output(['omarchy-shell','lock','isLocked'],text=True,timeout=3).strip()!='false':return 0
        if args==['quickstatus']:
            if recent_three_finger():return 0
            try:
                ready=subprocess.check_output(['omarchy-shell','pcadmin.controlCenter','ready'],text=True,stderr=subprocess.DEVNULL,timeout=2).strip()
                if ready=='true' and subprocess.run(['omarchy-shell','pcadmin.controlCenter','toggle'],timeout=3).returncode==0:return 0
            except (OSError,subprocess.SubprocessError):pass
        if args[0] in ('desktops','quickstatus') and len(args)==1:
            return subprocess.run(['omarchy','menu','summon',args[0]],timeout=5).returncode
        if args[0]=='switch' and len(args)==2 and args[1].isdigit() and 1<=int(args[1])<=10:
            return subprocess.run(['hyprctl','dispatch','hl.dsp.focus({workspace="'+str(int(args[1]))+'"})'],timeout=3).returncode
        return 2
    except (OSError,subprocess.SubprocessError):return 1
def main():return dispatch(sys.argv[1:])
if __name__=='__main__':raise SystemExit(main())
