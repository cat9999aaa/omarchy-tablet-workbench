#!/usr/bin/python3
"""Owned Xray adapter. Fixed executable/unit; private configs never enter output."""
from pathlib import Path
import json
import os
import subprocess
import sys

CORE = Path('/opt/v2rayn-bin/bin/xray/xray')
UNIT = 'omt-proxy-core.service'


def check(path, runner=subprocess.run):
    path=Path(path).absolute()
    if path != path.resolve() or not path.is_file():raise ValueError('unsafe_candidate')
    st=path.stat()
    if st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_nlink != 1 or st.st_size>8*1024*1024:
        raise ValueError('unsafe_candidate')
    env={'PATH':'/usr/bin','HOME':str(Path.home()),'XRAY_LOCATION_ASSET':str(Path.home()/'.local/share/v2rayN/bin')}
    version=runner([str(CORE),'version'],capture_output=True,timeout=5,env=env)
    if version.returncode or version.stdout.decode(errors='replace').split()[:2]!=['Xray','26.10.10']:
        return {'ok':False,'error_code':'unverified_core_version'}
    result=runner([str(CORE),'run','-test','-c',str(path)],capture_output=True,timeout=15,env=env)
    return {'ok':result.returncode==0,'error_code':None if result.returncode==0 else 'native_validation_failed'}


def restart(runner=subprocess.run):
    return runner(['systemctl','--user','restart',UNIT],capture_output=True,timeout=12).returncode==0


def probe(runner=subprocess.run):
    # Separate new connections: explicit local proxy, then ordinary routing through TUN.
    base=['curl','--silent','--show-error','--fail','--output','/dev/null','--write-out','%{http_code}',
          '--connect-timeout','4','--max-time','10']
    env={'PATH':'/usr/bin','HOME':str(Path.home())}
    for args in [['--proxy','socks5h://127.0.0.1:10808','--noproxy','','https://www.gstatic.com/generate_204'],
                 ['--noproxy','*','https://www.google.com/generate_204']]:
        result=runner(base+args,capture_output=True,timeout=12,env=env)
        if result.returncode or result.stdout.strip()!=b'204':return False
    return True


def policy_allows(locked,flight,enabled):
    return locked is False and flight is False and enabled is True


def policy_state():
    try:
        value=subprocess.check_output(['omarchy-shell','lock','isLocked'],text=True,timeout=2).strip()
        locked=False if value=='false' else True if value=='true' else None
    except (OSError,subprocess.SubprocessError):locked=None
    try:
        policy=json.loads((Path.home()/'.config/pcadmin-network/policy.json').read_text())
        enabled=policy.get('proxy_enabled')
    except (OSError,ValueError):enabled=None
    return locked,Path('/var/lib/pcadmin-network/flight.json').exists(),enabled


def main():
    if len(sys.argv) != 3:raise ValueError('unsupported_core_action')
    op=sys.argv[1];path=Path(sys.argv[2]).absolute()
    if op=='check':result=check(path)
    elif op in ('activate','restore','probe'):
        expected=Path.home()/'.local/state/omt-proxy/active.json'
        if path!=expected:raise ValueError('unexpected_active_path')
        state=policy_state()
        if op=='activate':
            ok=policy_allows(*state) and check(path).get('ok') and restart() and policy_allows(*policy_state())
        elif op=='restore' and (state[1] is True or state[2] is not True):
            # A concurrent manual-off/flight decision wins over recovery's old running state.
            stopped=subprocess.run(['systemctl','--user','stop',UNIT],capture_output=True,timeout=12)
            active=subprocess.run(['systemctl','--user','is-active',UNIT],capture_output=True,timeout=3)
            ok=stopped.returncode==0 and active.stdout.strip() in (b'inactive',b'failed')
        else:
            ok=probe() if op=='probe' else check(path).get('ok') and restart() and probe()
        result={'ok':bool(ok),'error_code':None if ok else 'core_action_failed'}
    else:raise ValueError('unsupported_core_action')
    print(json.dumps(result))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        print(json.dumps({'ok':False,'error_code':'core_check_failed'}));sys.exit(1)
