"""Sanitized, read-only adapters for this tablet's existing controllers."""
import json
import math
import time
from pathlib import Path


def _finite_number(value):
    # bool is an int in Python, but is not a timestamp in the JSON contract.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _age(now, observed_at):
    now, observed_at = _finite_number(now), _finite_number(observed_at)
    if now is None or observed_at is None:
        return None
    return _finite_number(now - observed_at)


def field(capability, available, actual, observed_at, stale_after, source, reason='', now=None):
    now = time.time() if now is None else now
    observed_at = _finite_number(observed_at)
    stale_after = _finite_number(stale_after)
    if stale_after is not None and stale_after < 0:
        stale_after = None
    age = _age(now, observed_at)
    if not available:
        health = 'unavailable'
    elif age is None or stale_after is None or age < -5:
        health = 'unknown'
    elif age > stale_after:
        health = 'stale'
    else:
        health = 'unknown' if actual is None else 'observed'
    return dict(capability=capability, available=available, desired=None, actual=actual,
                health=health, observed_at=observed_at, stale_after=stale_after,
                source=source, reason=reason)


def touch_field(data, now):
    if type(data) is not dict:
        data = {}
    f=field('touch_mode',data.get('verified') is True,data.get('mode'),data.get('observed_at',0),45,'TouchMode readback',data.get('error',''),now)
    f['boot_default']=data.get('boot_default',1)
    return f


def read_touch_state(path, now):
    try:
        return touch_field(json.loads(Path(path).read_text()), now)
    except (OSError,ValueError,TypeError):
        return field('touch_mode',False,None,0,45,'TouchMode','尚无有效读回',now)


def snapshot(now, network, touch, thermal):
    def live(k,v,available=True):return field(k,available,v,now,15,'existing network controller',now=now)
    health=network.get('health',{})
    flight_observed_at = _finite_number(network.get('flight_observed_at', 0))
    flight_age = _age(now, flight_observed_at)
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
            'flight_saved':network.get('flight_saved'),'flight_active':network.get('flight_active') if flight_age is not None and 0<=flight_age<=45 else None,
            'flight_observed_at':flight_observed_at,'flight_error':network.get('flight_error',''),'flight_checks':network.get('flight_checks',{}),
            'observed_at':now}


def thermal_values():
    result=[]
    for p in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:result.append({'type':(p/'type').read_text().strip(),'celsius':int((p/'temp').read_text())/1000})
        except (OSError,ValueError):pass
    return result
