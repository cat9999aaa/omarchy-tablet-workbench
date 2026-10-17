"""Sanitized, read-only adapters for this tablet's existing controllers."""
import json
import time
from pathlib import Path


def field(capability, available, actual, observed_at, stale_after, source, reason='', now=None):
    now = time.time() if now is None else now
    return dict(capability=capability, available=available, desired=None, actual=actual,
                health='unavailable' if not available else 'stale' if now-observed_at>stale_after else 'unknown' if actual is None else 'observed',
                observed_at=observed_at, stale_after=stale_after, source=source, reason=reason)


def read_touch_state(path, now):
    try:
        d=json.loads(Path(path).read_text())
        f=field('touch_mode',d.get('verified') is True,d.get('mode'),d.get('observed_at',0),45,'TouchMode readback',d.get('error',''),now)
        f['boot_default']=d.get('boot_default',1)
        return f
    except (OSError,ValueError,TypeError):
        return field('touch_mode',False,None,0,45,'TouchMode','尚无有效读回',now)


def snapshot(now, network, touch, thermal):
    def live(k,v,available=True):return field(k,available,v,now,15,'existing network controller',now=now)
    health=network.get('health',{})
    temperatures=[x for x in thermal if isinstance(x.get('celsius'),(int,float)) and -20<=x['celsius']<=150]
    cpu=[x for x in temperatures if x.get('type') in ('x86_pkg_temp','cpu_thermal')]
    chosen=max(cpu or temperatures,key=lambda x:x['celsius'],default=None)
    return {'physical_uplink':live('physical_uplink',network.get('primary'),bool(network.get('primary'))),
            'proxy_core':live('proxy_core',network.get('proxy_available'), 'proxy_available' in network),
            'tun':live('tun',network.get('proxy_tun'),'proxy_tun' in network),
            'internet':field('internet',bool(health),health.get('internet'),health.get('observed_at',0),65,'network health cache',now=now),
            'temperature':field('temperature',bool(chosen),chosen['celsius'] if chosen else None,now,15,chosen['type'] if chosen else 'thermal',now=now),
            'touch':touch if 'capability' in touch else field('touch_mode',False,None,0,45,'TouchMode',now=now),
            'network_mode':network.get('policy',{}).get('mode','unknown'),
            'zero':live('zero',network.get('zero_online'),'zero_online' in network and not network.get('zero_error')),
            'zero_online':network.get('zero_online'), 'zero_peers':network.get('zero_peers',{}),
            'flight_saved':network.get('flight_saved'),'flight_active':network.get('flight_active') if 0<=now-network.get('flight_observed_at',0)<=45 else None,
            'flight_observed_at':network.get('flight_observed_at',0),'flight_error':network.get('flight_error',''),'flight_checks':network.get('flight_checks',{}),
            'observed_at':now}


def thermal_values():
    result=[]
    for p in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:result.append({'type':(p/'type').read_text().strip(),'celsius':int((p/'temp').read_text())/1000})
        except (OSError,ValueError):pass
    return result
