#!/usr/bin/python3
"""Private compatibility bridge. Never accepts executable names from IPC clients."""
import importlib.util
import json
import fcntl
import os
import socket
import subprocess
import sys
from pathlib import Path


def ownership(unit='omt-proxy-core.service'):
    """All GUI/core processes must belong to the expected owner; unknown fails closed."""
    try:
        value = subprocess.check_output(['systemctl','--user','show',unit,'--property=ControlGroup','--value'],text=True,timeout=3).strip()
        running = []
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit() or proc.stat().st_uid != os.getuid(): continue
            try:
                exe = (proc/'exe').resolve(strict=True)
                if exe.name not in ('v2rayN','xray'): continue
                running.append((proc/'cgroup').read_text())
            except (FileNotFoundError,ProcessLookupError): continue
            except PermissionError: return False
        if not running:
            try:
                with socket.create_connection(('127.0.0.1',10808),timeout=.3): return False
            except OSError: return True
        return all(value and any(line.split(':',2)[-1]==value or line.split(':',2)[-1].startswith(value+'/') for line in groups.splitlines()) for groups in running)
    except (OSError,subprocess.SubprocessError): return False


def main():
    if len(sys.argv)!=3: raise ValueError('usage')
    root=Path(sys.argv[1]).resolve(strict=True)
    sys.path.insert(0,str(root/'control-center'))
    spec=importlib.util.spec_from_file_location('legacy_control',root/'control-center/control_center.py')
    control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
    op=sys.argv[2]
    if op=='observe':
        raw=json.loads(subprocess.check_output(['/usr/bin/python3',str(root/'network-center/network.py'),'status'],timeout=12))
        from client import native
        raw['locked']=control.read_lock();raw['ownership']=native() and ownership()
        print(json.dumps(raw));return
    if op!='action':raise ValueError('unsupported')
    data=sys.stdin.buffer.read(4097)
    if len(data)>4096:raise ValueError('large')
    request=json.loads(data)
    from client import native
    if not native() or not ownership():print(json.dumps({'stage':'conflict','error_code':'ownership_conflict'}));return
    if type(request.get('confirmed')) is not bool:raise ValueError('invalid')
    if request.get('action')=='apply':
        if set(request)!={'action','confirmed','candidate_hash'} or request['confirmed'] is not True:raise ValueError('invalid')
        from guarded_apply import execute,SystemdAdapter
        from importlib.machinery import SourceFileLoader
        owned=SourceFileLoader('owned_core',str(Path(__file__).with_name('owned-core.py'))).load_module()
        runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))
        with (runtime/'pcadmin-control-network.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:print('{"stage":"busy"}');return
            if not owned.policy_allows(*owned.policy_state()):print('{"stage":"conflict"}');return
            store=Path.home()/'.local/state/omt-proxy'
            journal=store/'transaction.json'
            generation=json.loads(journal.read_text())['generation'] if journal.exists() else 0
            result=execute(store,request['candidate_hash'],generation,SystemdAdapter())
        print(json.dumps({'stage':'submitted' if result.get('verified') is True else 'failed','error_code':result.get('error_code')}));return
    if set(request)!={'action','confirmed'} or request['action'] not in ('enable','disable'):raise ValueError('invalid')
    # Existing token/Polkit/lock cancellation remains authoritative. Mark only this child internal.
    os.environ['PCADMIN_PROXY_CONTROLLER']='1'
    prepared=control.prepare('proxy-on' if request['action']=='enable' else 'proxy-off',{},control.read_lock())
    print(json.dumps(control.execute(prepared,request['confirmed'],control.read_lock,control.run)))

if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'stage':'failed','error_code':'adapter_failed'}));sys.exit(1)
