"""Read minimal local battery and activity facts; never read argv or serials."""
import datetime,json,os,subprocess,time
from pathlib import Path

def read_text(path):
    try:return path.read_text().strip()
    except (OSError,UnicodeError):return None

def number(path):
    try:return int(read_text(path))
    except (TypeError,ValueError):return None

def parse_stat(text):
    end=text.rfind(')');start=text.find('(');f=text[end+2:].split()
    return {'pid':int(text[:start].strip()),'name':text[start+1:end],
            'cpu_ticks':int(f[11])+int(f[12]),'start_ticks':int(f[19])}

def clock_snapshot():
    return {'wall_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            'boot_id':read_text(Path('/proc/sys/kernel/random/boot_id')),
            'boottime_s':time.clock_gettime(time.CLOCK_BOOTTIME),'monotonic_s':time.monotonic()}

def display_snapshot():
    try:
        def query(cmd):
            r=subprocess.run(['hyprctl','-j',cmd],capture_output=True,text=True,timeout=2,check=True)
            return json.loads(r.stdout)
        clients=query('clients');monitors=query('monitors')
        states=[m['dpmsStatus'] for m in monitors if isinstance(m.get('dpmsStatus'),bool)]
        return {'visible_pids':{c['pid'] for c in clients if c.get('mapped',True) and not c.get('hidden',False)},
                'screen_on':any(states) if states else None}
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):return None

def collect_snapshot(sysfs=Path('/sys/class/power_supply'),procfs=Path('/proc'),clocks=None,display=None):
    result={'schema':1,**(clocks or clock_snapshot()),'external_power':None,
            'screen_on':display.get('screen_on') if display else None,'clock_ticks':os.sysconf('SC_CLK_TCK'),
            'batteries':{},'processes':[]}
    online=[]
    for p in sysfs.iterdir():
        if read_text(p/'type')!='Battery' and not p.name.startswith('BAT'):
            v=number(p/'online')
            if v in [0,1]:online.append(bool(v))
    if online:result['external_power']=any(online)
    for bay in ['BAT0','BAT1']:
        p=sysfs/bay;present=p.exists() and number(p/'present')!=0
        d={'present':present,'status':read_text(p/'status') if present else None}
        for output,key in [('percent','capacity'),('charge_uah','charge_now'),('full_charge_uah','charge_full'),('energy_uwh','energy_now'),('full_energy_uwh','energy_full'),('charge_end_threshold','charge_control_end_threshold')]:
            d[output]=number(p/key) if present else None
        if d['percent'] is not None and not 0<=d['percent']<=100:d['percent']=None
        w=number(p/'power_now');v=number(p/'voltage_now');i=number(p/'current_now')
        d['power_w']=abs(w)/1e6 if w is not None else abs(v*i)/1e12 if v is not None and i is not None else None
        result['batteries'][bay]=d
    for p in procfs.iterdir():
        if not p.name.isdigit():continue
        try:
            d=parse_stat((p/'stat').read_text());d['visible']=d['pid'] in display['visible_pids'] if display is not None else None
            result['processes'].append(d)
        except (OSError,ValueError,IndexError,KeyError,UnicodeError):continue
    return result
