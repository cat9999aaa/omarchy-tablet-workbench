#!/usr/bin/env python3
"""Run fixed operations in an explicitly provisioned, private remote build root.

Provision the signed Arch overlay first; this runner never installs host packages.
The scope marker is an operational guard, not a sandboxed SSH account.
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def checked(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError('scope: path escapes root')
    current = root
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink(): raise ValueError('scope: symlink rejected')
    return path


def execute(root, job_id, phase):
    root = Path(root).absolute()
    if root != root.resolve() or not (root/'build-scope.json').is_file():
        raise ValueError('scope: explicit non-symlink build root required')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,63}', job_id):
        raise ValueError('job: invalid identifier')
    if phase not in ('fetch', 'test', 'build', 'baseline', 'format'):
        raise ValueError('phase: unsupported operation')
    job = checked(root, 'jobs/'+job_id)
    source = checked(root, 'jobs/'+job_id+'/source')
    overlay = checked(root, 'jobs/'+job_id+'/overlay')
    home = checked(root, 'jobs/'+job_id+'/home')
    runtime = checked(root, 'jobs/'+job_id+'/runtime')
    for path in (source, overlay/'usr', home, runtime):
        if not path.is_dir(): raise ValueError('scope: incomplete provisioned job')
    packages = json.loads(checked(root, 'jobs/'+job_id+'/packages.json').read_text())
    if not packages or not any(p['name']=='rust' for p in packages) or not all(p.get('signature_verified') is True for p in packages):
        raise ValueError('scope: verified package manifest required')
    sandbox = ['bwrap','--unshare-all','--uid','0','--gid','0','--new-session','--clearenv',
        '--overlay-src','/usr','--overlay-src',str(overlay/'usr'),'--ro-overlay','/usr',
        '--symlink','usr/bin','/bin','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64',
        '--proc','/proc','--dev','/dev','--tmpfs','/tmp',
        '--ro-bind-try','/etc/ld.so.cache','/etc/ld.so.cache',
        '--ro-bind-try','/etc/fonts','/etc/fonts','--ro-bind-try','/etc/ca-certificates','/etc/ca-certificates',
        '--ro-bind-try','/etc/ssl','/etc/ssl','--ro-bind-try','/etc/resolv.conf','/etc/resolv.conf',
        '--ro-bind-try','/etc/hosts','/etc/hosts','--bind',str(source),'/work',
        '--bind',str(home),'/home/build','--bind',str(runtime),'/run/user/0',
        '--setenv','PATH','/usr/bin','--setenv','HOME','/home/build',
        '--setenv','CARGO_HOME','/home/build/cargo','--setenv','XDG_RUNTIME_DIR','/run/user/0',
        '--setenv','QT_QPA_PLATFORM','offscreen','--setenv','QT_QUICK_BACKEND','software',
        '--setenv','LC_ALL','C.UTF-8']
    commands = {
        'fetch': [['--share-net','--chdir','/work/modules/proxy-manager','cargo','fetch','--locked']],
        'test': [['--chdir','/work/modules/proxy-manager','cargo','test','--locked','--offline','-j2'],
                 ['--chdir','/work','python','scripts/remote-build/test_proxy_build.py']],
        'build': [['--chdir','/work/modules/proxy-manager','cargo','build','--release','--locked','--offline','-j2']],
        'format': [['--chdir','/work/modules/proxy-manager','cargo','fmt','--check']],
        'baseline': [['--chdir','/work','python','scripts/acceptance/run.py','--output','/work/report-'+str(time.time_ns())]],
    }
    stamp = str(time.time_ns())
    hashes = {}
    for p in (source/'modules/proxy-manager').rglob('*'):
        if p.is_file() and 'target' not in p.parts and p.suffix in ('.rs','.toml','.lock','.qml','.py','.js'):
            if p.is_symlink(): raise ValueError('scope: source symlink rejected')
            hashes[str(p.relative_to(source))] = hashlib.sha256(p.read_bytes()).hexdigest()
    result = {'phase':phase,'source_files':hashes,'status':'failed'}
    code = 1
    try:
        with (job/(phase+'-'+stamp+'.log')).open('x') as log:
            for cmd in commands[phase]:
                code = subprocess.run(sandbox+cmd,stdout=log,stderr=subprocess.STDOUT).returncode
                if code: break
        result['status'] = 'passed' if code==0 else 'failed'
        result['returncode'] = code
    finally:
        (job/(phase+'-'+stamp+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'phase':phase,'status':result['status'],'evidence':phase+'-'+stamp}))
    return code


if __name__ == '__main__':
    try:
        if len(sys.argv)!=4: raise ValueError('usage: proxy-build.py ROOT JOB PHASE')
        sys.exit(execute(*sys.argv[1:]))
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'failed','reason':str(error)}));sys.exit(1)
