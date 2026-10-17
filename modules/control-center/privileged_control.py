#!/usr/bin/python3
"""Root-owned post-Polkit lock gate for fixed existing device controllers."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import pwd
import subprocess
import sys
import json
import time
import re

def process_start(pid):
    return Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()[19]

def request_active(uid,token,action):
    if not isinstance(token,str) or not re.fullmatch(r'[0-9a-f-]{36}',token):return False
    path=f'/run/user/{uid}/pcadmin-control-center/request-{token}.json'
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd) as stream:
            if os.fstat(stream.fileno()).st_uid!=uid:return False
            d=json.loads(stream.read(4096))
        pid=d['pid']
        return d.get('active') is True and action in d.get('privileged_actions',[]) and time.time()<d['expires_at'] and type(pid) is int and pid>0 and Path(f'/proc/{pid}').stat().st_uid==uid and d['process_start']==process_start(pid)
    except (OSError,ValueError,KeyError,TypeError):return False

def session_unlocked(uid):
    account=pwd.getpwuid(uid)
    args=['/usr/bin/runuser','-u',account.pw_name,'--','/usr/bin/env','-i',
          'PATH=/usr/bin:/bin','HOME='+account.pw_dir,'XDG_RUNTIME_DIR=/run/user/'+str(uid),
          'OMARCHY_PATH=/usr/share/omarchy','/usr/bin/omarchy-shell','lock','isLocked']
    try:return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=4).strip()=='false'
    except (OSError,subprocess.SubprocessError):return False

def load_owned(path,name):
    s=Path(path).stat()
    if s.st_uid!=0 or s.st_mode&0o022:raise PermissionError('Controller must be root-owned and not writable by other accounts')
    loader=importlib.machinery.SourceFileLoader(name,path)
    spec=importlib.util.spec_from_loader(name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module);return module

def dispatch_guarded(action,uid,is_unlocked,runner,token=None,request_valid=None):
    if uid<=0:raise PermissionError('Non-root authenticated session required')
    if action not in ('tun-start','tun-stop','touch-refresh','touch-glove','touch-normal','flight-on','flight-off'):raise ValueError('Unknown privileged action')
    def guard():
        valid=request_valid() if request_valid is not None else request_active(uid,token,action)
        if is_unlocked(uid) is not True or valid is not True:raise PermissionError('Session locked or original request cancelled; operation denied')
    guard()
    commands={'tun-start':['/usr/bin/systemctl','start','pcadmin-v2ray-tun.service'],
              'tun-stop':['/usr/bin/systemctl','stop','pcadmin-v2ray-tun.service'],
              'touch-refresh':['/usr/bin/systemctl','start','pcadmin-touch-state.service']}
    if action in commands:return runner(commands[action])
    if action in ('touch-glove','touch-normal'):
        tool=load_owned('/usr/local/libexec/pcadmin-touch-mode.py','touch_controller')
        try:
            r=tool.read_apply(action.removeprefix('touch-'),guard=guard)
            tool.export_state(r['actual'],True);return 0
        except Exception:
            tool.export_state(None,False,'Authorized operation cancelled or readback failed');raise
    if action in ('flight-on','flight-off'):
        tool=load_owned('/usr/local/libexec/pcadmin-radio-control','radio_controller')
        tool.flight(action=='flight-on',Path('/var/lib/pcadmin-network/flight.json'),guard=guard)
        tool.export_status();return 0
    raise ValueError('Unknown privileged action')

if __name__=='__main__':
    if os.geteuid()!=0 or len(sys.argv)!=3 or not os.environ.get('PKEXEC_UID','').isdigit():raise SystemExit(1)
    try:raise SystemExit(dispatch_guarded(sys.argv[1],int(os.environ['PKEXEC_UID']),session_unlocked,lambda cmd:subprocess.run(cmd,timeout=30).returncode,token=sys.argv[2]))
    except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
