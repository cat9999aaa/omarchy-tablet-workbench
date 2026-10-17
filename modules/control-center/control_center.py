#!/usr/bin/python3
"""Narrow local actions. No arbitrary command strings or network controllers."""
import fcntl
import json
import os
import subprocess
import sys
import time
import uuid
import re
import signal
from privileged_control import process_start
from pathlib import Path
from adapters import snapshot, read_touch_state, thermal_values

ROOT=Path(__file__).resolve().parents[1]
NETWORK=ROOT/'network-center/network.py'
IME=ROOT/'omarchy-touch-ime/control.py'

def read_lock():
    try:
        value=subprocess.check_output(['omarchy-shell','lock','isLocked'],text=True,timeout=2).strip()
        return False if value=='false' else True if value=='true' else None
    except (OSError,subprocess.SubprocessError):return None

def prepare(action, params, locked):
    if locked is not False:raise PermissionError('锁屏中或无法确认锁屏状态')
    if not isinstance(params,dict):raise ValueError('参数无效')
    if action in ('brightness','volume'):
        if set(params)!={'percent'} or type(params['percent']) is not int or not 0<=params['percent']<=100:raise ValueError('亮度须为0–100整数')
        argv=['omarchy-shell','omarchy.monitor','brightness',str(params['percent'])] if action=='brightness' else ['pactl','set-sink-volume',audio_sink(),str(params['percent'])+'%'];resource=action
    else:
        if params:raise ValueError('该操作不接受参数')
        details={x:['omarchy-shell','omarchy.'+x,'open'] for x in ['network','power','audio','monitor','bluetooth']}
        actions={**details,
          'keyboard':['python',str(IME)],
          'proxy-on':['python',str(NETWORK),'proxy-on'],'proxy-off':['python',str(NETWORK),'proxy-off'],
          **{a:['pkexec','/usr/bin/python','/usr/local/libexec/pcadmin-control-privileged.py',a] for a in ['flight-on','flight-off','touch-glove','touch-normal','touch-refresh']},
          'screen-off':['hyprctl','dispatch','hl.dsp.dpms({enabled=false})'],
          'lock':['omarchy','system','lock'],
          'windows':['python',str(ROOT/'window-controls/physical_window_menu.py')],
          'player':['gtk-launch','io.github.celluloid_player.Celluloid'],
          'reader':['gtk-launch','rocks.koreader.KOReader'],
          'games':['gtk-launch','pcadmin-flight-arcade'],
          'power-saver':['omarchy','powerprofiles','set',power_context(),'power-saver'],
          'balanced':['omarchy','powerprofiles','set',power_context(),'balanced']}
        if action=='mute':actions['mute']=['pactl','set-sink-mute',audio_sink(),'toggle']
        if action not in actions:raise ValueError('未知操作')
        argv=actions[action];resource='network' if action.startswith(('proxy','flight')) else 'touch' if action.startswith('touch') else action
    if action in ('volume','mute'):resource='audio-output'
    if action in ('power-saver','balanced'):resource='power-profile'
    request_id=str(uuid.uuid4())
    if '/usr/local/libexec/pcadmin-control-privileged.py' in argv:argv.append(request_id)
    return {'request_id':request_id,'action':action,'resource':resource,'argv':argv,
            'requires_confirmation':action in ('proxy-off','flight-on','touch-normal')}

def power_context():
    for p in Path('/sys/class/power_supply').glob('*/type'):
        try:
            if p.read_text().strip() in ('Mains','USB','USB_C') and (p.parent/'online').read_text().strip()=='1':return 'ac'
        except OSError:pass
    return 'battery'

def audio_sink():
    sink=subprocess.check_output(['omarchy','audio','output','sink'],text=True,timeout=3).strip()
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:-]*',sink):raise ValueError('没有有效输出设备')
    return sink

def execute(request, confirmed, read_lock, run):
    def result(stage,ok=False):return {'request_id':request['request_id'],'stage':stage,'ok':ok,'verified':False}
    if request['requires_confirmation'] and confirmed is not True:return result('confirmation')
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))
    path=runtime/('pcadmin-control-'+request['resource']+'.lock')
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    request_file=None
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return result('busy')
        if read_lock() is not False:return result('locked')
        directory=runtime/'pcadmin-control-center';directory.mkdir(mode=0o700,exist_ok=True)
        request_file=directory/('request-'+request['request_id']+'.json')
        token_fd=os.open(request_file,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        privileged={'proxy-on':['tun-start'],'proxy-off':['tun-stop']}.get(request['action'],[request['action']])
        with os.fdopen(token_fd,'w') as stream:json.dump({'active':True,'privileged_actions':privileged,'expires_at':time.time()+95,'pid':os.getpid(),'process_start':process_start(os.getpid())},stream)
        code=run(['/usr/bin/env','PCADMIN_CONTROL_REQUEST='+request['request_id'],*request['argv']])
        return result('submitted' if code==0 else 'cancelled' if code in (126,127) else 'failed',code==0)
    finally:
        if request_file is not None:request_file.unlink(missing_ok=True)
        os.close(fd)

def run(args):
    env=os.environ.copy();env['PCADMIN_NETWORK_GUARDED']='1'
    p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,env=env)
    end=time.monotonic()+90
    while p.poll() is None:
        if read_lock() is not False or time.monotonic()>end:
            if len(args)>1 and args[0]=='/usr/bin/env' and args[1].startswith('PCADMIN_CONTROL_REQUEST='):
                token=args[1].split('=',1)[1]
                (Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'pcadmin-control-center'/('request-'+token+'.json')).unlink(missing_ok=True)
            try:os.killpg(p.pid,signal.SIGTERM)
            except (ProcessLookupError,PermissionError):pass
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:p.kill();p.wait(timeout=1)
                except (PermissionError,subprocess.TimeoutExpired):pass
            return 126
        time.sleep(.2)
    return p.returncode

def prepare_open():
    if read_lock() is not False:return False
    # Hide both implementations, then verify neither layer is still mapped.
    for cmd in [['omarchy-shell','omtInput','hide'],[str(Path.home()/'.local/bin/pcadmin-keyboard'),'hide']]:
        try:subprocess.run(cmd,capture_output=True,timeout=3)
        except (OSError,subprocess.SubprocessError):pass
    for _ in range(8):
        try:
            data=json.loads(subprocess.check_output(['hyprctl','layers','-j'],text=True,timeout=2))
            layers=[s for m in data.values() for group in m['levels'].values() for s in group]
            if not any(s.get('namespace') in ('pcadmin-touch-ime','wvkbd') for s in layers):return read_lock() is False
        except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError):return False
        time.sleep(.05)
    return False

def status():
    now=time.time();network={};monitor={}
    try:network=json.loads(subprocess.check_output(['python',str(NETWORK),'status'],text=True,timeout=12))
    except (OSError,ValueError,subprocess.SubprocessError):pass
    try:monitor=json.loads(subprocess.check_output(['omarchy-shell','omarchy.monitor','state'],text=True,timeout=2))
    except (OSError,ValueError,subprocess.SubprocessError):pass
    d=snapshot(now,network,read_touch_state('/run/pcadmin-touch-mode/state.json',now),thermal_values())
    d['brightness']=None
    if monitor.get('brightnessAvailable'):
        for p in Path('/sys/class/backlight').glob('*'):
            try:
                maximum=int((p/'max_brightness').read_text());actual=int((p/'actual_brightness').read_text())
                if maximum>0:d['brightness']=round(actual/maximum*100);break
            except (OSError,ValueError):pass
    d['power_profile']='unknown'
    try:d['power_profile']=subprocess.check_output(['powerprofilesctl','get'],text=True,timeout=2).strip()
    except (OSError,subprocess.SubprocessError):pass
    d['locked']=read_lock()
    return d

def main():
    op=sys.argv[1] if len(sys.argv)==2 else ''
    if op=='status':return status()
    if op=='lock-state':return {'locked':read_lock()}
    if op=='prepare-open':return {'ok':prepare_open()}
    if op!='action':raise ValueError('未知请求')
    raw=sys.stdin.buffer.read(4097)
    if len(raw)>4096:raise ValueError('请求过大')
    d=json.loads(raw)
    if set(d)-{'action','params','confirmed'}:raise ValueError('未知字段')
    r=prepare(d['action'],d.get('params',{}),read_lock())
    return execute(r,d.get('confirmed',False),read_lock,run)

if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as e:print(json.dumps({'ok':False,'stage':'failed','reason':str(e)[:120]},ensure_ascii=False));sys.exit(1)
