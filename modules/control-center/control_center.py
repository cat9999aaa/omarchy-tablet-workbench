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
from adapters import snapshot, read_touch_state, touch_field, thermal_values, field
import contract_host

ROOT=Path(__file__).resolve().parents[1]
NETWORK=ROOT/'network-center/network.py'
IME=ROOT/'omarchy-touch-ime/control.py'

def read_lock(reader=None):
    try:
        value=(reader(['omarchy-shell','lock','isLocked'],2) if reader else subprocess.check_output(['omarchy-shell','lock','isLocked'],text=True,timeout=2)).strip()
        return False if value=='false' else True if value=='true' else None
    except (OSError,subprocess.SubprocessError):return None

# Literal commands never inspect hardware. Dynamic commands are resolved only
# after the selected action's parameters and lock state have been validated.
_STATIC_COMMANDS = {
    **{name: ('omarchy-shell', 'omarchy.' + name, 'open')
       for name in ('network', 'power', 'audio', 'monitor', 'bluetooth')},
    'nightlight': ('omarchy', 'toggle', 'nightlight'),
    'screen-off': ('hyprctl', 'dispatch', 'hl.dsp.dpms({enabled=false})'),
    'lock': ('omarchy', 'system', 'lock'),
    'player': ('gtk-launch', 'io.github.celluloid_player.Celluloid'),
    'music': ('gtk-launch', 'io.github.quodlibet.QuodLibet'),
    'reader': ('gtk-launch', 'rocks.koreader.KOReader'),
    'games': ('gtk-launch', 'pcadmin-flight-arcade'),
}
_PRIVILEGED_ACTIONS = frozenset(('flight-on', 'flight-off', 'touch-glove',
                                 'touch-normal', 'touch-refresh'))
_PRIVILEGED_HELPER = '/usr/local/libexec/pcadmin-control-privileged.py'
_POWER_ACTIONS = frozenset(('power-saver', 'balanced'))
_CONFIRMATION_ACTIONS = frozenset(('proxy-off', 'flight-on', 'touch-normal'))


def _action_command(action, params):
    if action == 'brightness':
        return ['omarchy-shell', 'omarchy.monitor', 'brightness', str(params['percent'])]
    if action == 'volume':
        return ['pactl', 'set-sink-volume', audio_sink(), str(params['percent']) + '%']
    if action == 'mute':
        return ['pactl', 'set-sink-mute', audio_sink(), 'toggle']
    if action in _POWER_ACTIONS:
        return ['omarchy', 'powerprofiles', 'set', power_context(), action]
    if action in _PRIVILEGED_ACTIONS:
        return ['pkexec', '/usr/bin/python', _PRIVILEGED_HELPER, action]
    if action in ('proxy-on', 'proxy-off'):
        return ['python', str(NETWORK), action]
    if action == 'keyboard':
        return ['python', str(IME)]
    if action == 'windows':
        return ['python', str(ROOT / 'window-controls/physical_window_menu.py')]
    if action in _STATIC_COMMANDS:
        return list(_STATIC_COMMANDS[action])
    raise ValueError('未知操作')


def _action_resource(action):
    if action in ('volume', 'mute'):
        return 'audio-output'
    if action in _POWER_ACTIONS:
        return 'power-profile'
    if action in ('proxy-on', 'proxy-off', 'flight-on', 'flight-off'):
        return 'network'
    if action in ('touch-glove', 'touch-normal', 'touch-refresh'):
        return 'touch'
    return action


def prepare(action, params, locked):
    if locked is not False:
        raise PermissionError('锁屏中或无法确认锁屏状态')
    if not isinstance(params, dict):
        raise ValueError('参数无效')
    if action in ('brightness', 'volume'):
        if (set(params) != {'percent'} or type(params['percent']) is not int
                or not 0 <= params['percent'] <= 100):
            raise ValueError('亮度须为0–100整数')
    elif params:
        raise ValueError('该操作不接受参数')

    argv = _action_command(action, params)
    request_id = str(uuid.uuid4())
    if action in _PRIVILEGED_ACTIONS:
        argv.append(request_id)
    return {'request_id': request_id, 'action': action,
            'resource': _action_resource(action), 'argv': argv,
            'requires_confirmation': action in _CONFIRMATION_ACTIONS}

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

def nightlight_status(now=None, reader=None):
    now=time.time() if now is None else now
    temperature=None
    try:
        value=json.loads(reader(['omarchy','toggle','nightlight','--status'],3) if reader else subprocess.check_output(['omarchy','toggle','nightlight','--status'],text=True,timeout=3))
        temp=value.get('temperature')
        if type(temp) in (int,float) and 1000<=temp<=20000:
            temperature=temp
    except (OSError,ValueError,TypeError,AttributeError,subprocess.SubprocessError):pass
    # Native status reports false even when its IPC is unavailable; don't present that as off.
    state=field('nightlight',True,None if temperature is None else temperature<6000,now,15,'Omarchy nightlight / hyprsunset',now=now)
    state['temperature']=temperature
    return state

def collect_status(reader=None):
    def read(args, timeout):
        return reader(args, timeout) if reader else subprocess.check_output(args,text=True,timeout=timeout)
    now=time.time();network={};monitor={}
    try:network=json.loads(read(['python',str(NETWORK),'status'],12))
    except (OSError,ValueError,subprocess.SubprocessError):pass
    try:monitor=json.loads(read(['omarchy-shell','omarchy.monitor','state'],2))
    except (OSError,ValueError,subprocess.SubprocessError):pass
    if type(network) is not dict:network={}
    if type(monitor) is not dict:monitor={}
    network['flight_saved']=Path('/var/lib/pcadmin-network/flight.json').exists()
    cache,trusted=contract_host.read_touch_cache('/run/pcadmin-touch-mode/state.json')
    started=contract_host.boottime_ms()
    thermal=thermal_values()
    ended=contract_host.boottime_ms()
    if started is None or ended is None or ended<started:started=None
    d=snapshot(now,network,touch_field(cache,now),thermal)
    d['nightlight']=nightlight_status(reader=reader) if reader else nightlight_status()
    d['brightness']=None
    if monitor.get('brightnessAvailable'):
        for p in Path('/sys/class/backlight').glob('*'):
            try:
                maximum=int((p/'max_brightness').read_text());actual=int((p/'actual_brightness').read_text())
                if maximum>0:d['brightness']=round(actual/maximum*100);break
            except (OSError,ValueError):pass
    d['power_profile']='unknown'
    try:d['power_profile']=read(['powerprofilesctl','get'],2).strip()
    except (OSError,subprocess.SubprocessError):pass
    d['locked']=read_lock(reader=reader) if reader else read_lock()
    return contract_host.Sample(d,started,cache.get('observation'),trusted)

def status():
    return collect_status().legacy

def status_readonly():
    try:
        with contract_host.ReadBudget() as budget:
            sample=collect_status(reader=budget.run_read)
            budget.remaining_s()
            result=contract_host.response(sample)
            budget.remaining_s()
            return result
    except contract_host.ReadDeadline:
        return contract_host.failure('read_timeout')
    except Exception:
        return contract_host.failure('read_failed')

def main():
    op=sys.argv[1] if len(sys.argv)==2 else ''
    if op in ('mode-step','mode-preference-read','mode-preference-write','output-policy'):
        from device_session import command
        return command(op)
    if op=='device-evidence':
        from device_classifier import aggregate
        try:
            from device_evidence import collect_device_evidence
            return collect_device_evidence()
        except Exception:
            return aggregate([], False, 'read_failed', 0)
    if op=='status':return status()
    if op=='status-readonly':return status_readonly()
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
