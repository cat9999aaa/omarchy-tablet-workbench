#!/usr/bin/python3
"""Independent, transaction-bound systemd recovery timer for candidate activation."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid
import time


def execute(root, candidate_hash, generation, adapter):
    if not re.fullmatch('[a-f0-9]{64}',candidate_hash) or type(generation) is not int or generation<0:
        return {'verified':False,'stage':'invalid'}
    token='omt-proxy-recover-'+uuid.uuid4().hex
    if not adapter.arm(token,root,candidate_hash,generation):
        return {'verified':False,'stage':'watchdog_unavailable'}
    try: result=adapter.apply(root,candidate_hash,generation)
    except Exception: return {'verified':False,'stage':'interrupted','restored':False}
    if result.get('verified') is True or result.get('restored') is True:
        adapter.cancel(token)
    return result


class SystemdAdapter:
    def __init__(self,runner=subprocess.run):
        self.runner=runner
        self.binary=Path.home()/'.local/lib/omt-proxy/omt-proxy'
        self.helper=Path.home()/'.local/lib/omt-proxy/guarded_apply.py'
    def arm(self,token,root,candidate_hash,generation):
        # core-recovery-hash performs the same canonical port conversion as activation.
        result=self.runner([str(self.binary),'core-recovery-hash',str(root),candidate_hash],capture_output=True,timeout=5)
        if result.returncode:return False
        digest=json.loads(result.stdout).get('sha256','')
        if not re.fullmatch('[a-f0-9]{64}',digest):return False
        cmd=['systemd-run','--user','--quiet','--collect','--unit='+token,'--on-active=150s',
             '--timer-property=AccuracySec=1s','/usr/bin/python3',str(self.helper),'recover',str(generation+1),digest]
        return self.runner(cmd,capture_output=True,timeout=5).returncode==0
    def apply(self,root,candidate_hash,generation):
        # Bound and reap the entire owned group; the independent timer survives this process.
        child=subprocess.Popen([str(self.binary),'core-activate',str(root),str(generation),candidate_hash],
                               stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
        try:
            out,_=child.communicate(timeout=120)
            return json.loads(out) if len(out)<=4096 else {'verified':False,'stage':'oversize'}
        finally:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
    def cancel(self,token):
        # Unique unit names prevent an old request cancelling a later recovery.
        self.runner(['systemctl','--user','stop',token+'.timer'],capture_output=True,timeout=5)


def recover_with_retry(args,runner=subprocess.run,sleep=time.sleep,clock=time.monotonic):
    deadline=clock()+90
    while True:
        result=runner(args,capture_output=True,timeout=65)
        try:code=json.loads(result.stdout).get('error_code')
        except (ValueError,TypeError,AttributeError):return result
        if code!='catalog_busy' or clock()>=deadline:return result
        sleep(.5)

def main():
    root=Path.home()/'.local/state/omt-proxy'
    if len(sys.argv)!=4 or sys.argv[1]!='recover':raise ValueError('unsupported')
    generation=int(sys.argv[2]);digest=sys.argv[3]
    if generation<1 or not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('invalid')
    binary=Path.home()/'.local/lib/omt-proxy/omt-proxy'
    # Store's exclusive lock makes the identity check and recovery one atomic operation.
    result=recover_with_retry([str(binary),'core-recover',str(root),str(generation),digest])
    print(json.dumps({'recovery_attempted':True,'ok':result.returncode==0}))
    return result.returncode

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:print('{"ok":false,"error_code":"recovery_failed"}');sys.exit(1)
