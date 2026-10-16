"""Conservative session derivation from observed facts, not guessed plug times."""
import datetime
BAYS=('BAT0','BAT1')

def kind(s):return 'charge' if s['external_power'] is True else 'discharge' if s['external_power'] is False else 'unknown'
def delta(a,b):
    if a['boot_id']!=b['boot_id']:return None
    total=b['boottime_s']-a['boottime_s'];awake=b['monotonic_s']-a['monotonic_s']
    if total<0 or awake<0:return None
    return total,min(total,awake),max(0,total-awake)
def bad_bay(a,b,bay):
    x=a['batteries'].get(bay,{});y=b['batteries'].get(bay,{})
    if x.get('present')!=y.get('present'):return True
    dt=delta(a,b);xp=x.get('percent');yp=y.get('percent')
    return bool(dt and xp is not None and yp is not None and abs(yp-xp)>20*max(dt[0],1)/60)
def net_discharge(s):
    if kind(s)!='discharge':return None
    total=0
    for d in s['batteries'].values():
        if not d.get('present'):continue
        if d.get('status') not in ('Discharging','Not charging','Full'):return None
        if d.get('status')=='Discharging':
            if d.get('power_w') is None:return None
            total+=d['power_w']
    return total

def new_session(s,partial):
    return {'kind':kind(s),'observed_start':s['wall_time'],'observed_end':s['wall_time'],
        'partial_start':partial,'elapsed_s':0,'awake_s':0,'sleep_s':0,'unknown_s':0,'screen_on_s':0,'screen_unknown_s':0,
        'charging_s_by_bay':dict.fromkeys(BAYS,0),'start_percent_by_bay':{n:s['batteries'].get(n,{}).get('percent') for n in BAYS},
        'end_percent_by_bay':{n:s['batteries'].get(n,{}).get('percent') for n in BAYS},
        'energy_change_wh_by_bay':dict.fromkeys(BAYS,None),'average_power_w':None,'quality_flags':[],
        '_power_integral':0,'_power_seconds':0,'_first':s}

def flag(row,value):
    if value not in row['quality_flags']:row['quality_flags'].append(value)

def derive_sessions(samples):
    rows=[];previous=None
    for s in samples:
        dt=delta(previous,s) if previous else None
        changed=previous and kind(previous)!=kind(s)
        if previous is None or changed or dt is None:
            partial=previous is None or dt is None or kind(previous)=='unknown' or kind(s)=='unknown' or (dt and (dt[1]>180 or dt[2]>2))
            row=new_session(s,bool(partial));rows.append(row)
            if changed:flag(row,'plug-observation')
            if previous and (dt is None or dt[0]>180):flag(row,'gap')
        else:
            row=rows[-1];total,awake,sleep=dt;row['elapsed_s']+=total
            row['sleep_s']+=sleep
            if awake>180:row['unknown_s']+=awake;row['screen_unknown_s']+=awake;flag(row,'gap')
            else:
                row['awake_s']+=awake
                if previous.get('screen_on') is True and s.get('screen_on') is True:row['screen_on_s']+=awake
                elif previous.get('screen_on') is None or s.get('screen_on') is None or previous.get('screen_on')!=s.get('screen_on'):row['screen_unknown_s']+=awake
                for bay in BAYS:
                    a=previous['batteries'].get(bay,{});b=s['batteries'].get(bay,{})
                    if a.get('status')==b.get('status')=='Charging' and not bad_bay(previous,s,bay):row['charging_s_by_bay'][bay]+=awake
                pa=net_discharge(previous);pb=net_discharge(s)
                if pa is not None and pb is not None and sleep<2:
                    row['_power_integral']+=(pa+pb)/2*awake;row['_power_seconds']+=awake
            for bay in BAYS:
                if bad_bay(previous,s,bay):flag(row,'battery-jump')
            if abs((datetime.datetime.fromisoformat(s['wall_time'])-datetime.datetime.fromisoformat(previous['wall_time'])).total_seconds()-total)>5:flag(row,'clock-change')
        row['observed_end']=s['wall_time']
        for bay in BAYS:
            row['end_percent_by_bay'][bay]=s['batteries'].get(bay,{}).get('percent')
            start=row['_first']['batteries'].get(bay,{}).get('energy_uwh');end=s['batteries'].get(bay,{}).get('energy_uwh')
            row['energy_change_wh_by_bay'][bay]=(end-start)/1e6 if start is not None and end is not None and 'battery-jump' not in row['quality_flags'] else None
        previous=s
    for row in rows:
        row['average_power_w']=round(row['_power_integral']/row['_power_seconds'],2) if row['_power_seconds'] else None
        for key in ['_power_integral','_power_seconds','_first']:row.pop(key)
    return rows

def build_status(samples,now):
    if not samples:return {'schema':1,'available':False,'reason':'not-started'}
    rows=derive_sessions(samples);last=samples[-1];age=delta(last,now)
    return {'schema':1,'available':True,'recorded_at':last['wall_time'],'stale':age is None or age[0]>180,
            'current_session':rows[-1],'last_charge':next((r for r in reversed(rows[:-1]) if r['kind']=='charge'),None),
            'batteries':last['batteries'],'external_power':last['external_power']}

def build_history(samples):
    points=[];previous=None;axis=None
    for s in samples:
        dt=delta(previous,s) if previous else None
        wall=datetime.datetime.fromisoformat(s['wall_time']).timestamp()*1000
        axis=wall if axis is None else axis+dt[0]*1000 if dt else max(axis+1000,wall)
        clock_changed=previous is not None and dt is not None and abs((datetime.datetime.fromisoformat(s['wall_time'])-datetime.datetime.fromisoformat(previous['wall_time'])).total_seconds()-dt[0])>5
        if previous and (dt is None or dt[0]>180 or clock_changed):points.append({'time':s['wall_time'],'axis_time':axis,'BAT0':None,'BAT1':None,'net_discharge_w':None})
        p={'time':s['wall_time'],'axis_time':axis,'net_discharge_w':net_discharge(s)}
        for bay in BAYS:p[bay]=None if previous and bad_bay(previous,s,bay) else s['batteries'].get(bay,{}).get('percent')
        points.append(p);previous=s
    return {'schema':1,'available':bool(samples),'sessions':derive_sessions(samples),'points':points}

def rank_apps(samples,period):
    if not samples:return []
    if period=='24h':
        cutoff=datetime.datetime.fromisoformat(samples[-1]['wall_time'])-datetime.timedelta(days=1)
        samples=[s for s in samples if datetime.datetime.fromisoformat(s['wall_time'])>=cutoff]
    elif period=='session':
        index=len(samples)-1
        while index>0 and kind(samples[index])==kind(samples[index-1]) and delta(samples[index-1],samples[index]) is not None:index-=1
        samples=samples[index:]
    rows={}
    for a,b in zip(samples,samples[1:]):
        dt=delta(a,b)
        if dt is None or dt[1]>180:continue
        before={(p['pid'],p['start_ticks']):p for p in a['processes']}
        seen_names=set()
        for p in b['processes']:
            old=before.get((p['pid'],p['start_ticks']))
            if old is None or p['cpu_ticks']<=old['cpu_ticks']:continue
            r=rows.setdefault(p['name'],{'name':p['name'],'cpu_seconds':0,'observed_seconds':0,'visible_samples':0,'background_samples':0,'unknown_samples':0})
            r['cpu_seconds']+=(p['cpu_ticks']-old['cpu_ticks'])/b.get('clock_ticks',100)
            if p['name'] not in seen_names:r['observed_seconds']+=dt[1];seen_names.add(p['name'])
            k='visible_samples' if p.get('visible') is True else 'background_samples' if p.get('visible') is False else 'unknown_samples';r[k]+=1
    for r in rows.values():r['cpu_seconds']=round(r['cpu_seconds'],2)
    return sorted(rows.values(),key=lambda r:r['cpu_seconds'],reverse=True)

def update_cache(previous,s,cache):
    """Incremental status so opening the panel never scans ninety days of processes."""
    import copy
    cache=copy.deepcopy(cache) if cache else {'schema':1,'available':True,'last_charge':None}
    dt=delta(previous,s) if previous else None
    continuing=previous is not None and dt is not None and kind(previous)==kind(s) and cache.get('current_session') is not None
    if not continuing:
        old=cache.get('current_session')
        if old and old['kind']=='charge':cache['last_charge']=old
        cache['current_session']=derive_sessions([previous,s] if previous else [s])[-1]
        cache['_power_integral']=0;cache['_power_seconds']=0
    else:
        piece=derive_sessions([previous,s])[0];row=cache['current_session']
        for key in ['elapsed_s','awake_s','sleep_s','unknown_s','screen_on_s','screen_unknown_s']:row[key]+=piece[key]
        for bay in BAYS:
            row['charging_s_by_bay'][bay]+=piece['charging_s_by_bay'][bay]
            x=row['energy_change_wh_by_bay'][bay];y=piece['energy_change_wh_by_bay'][bay]
            row['energy_change_wh_by_bay'][bay]=x+y if x is not None and y is not None else None
        row['end_percent_by_bay']=piece['end_percent_by_bay'];row['observed_end']=s['wall_time']
        for f in piece['quality_flags']:flag(row,f)
        if 'battery-jump' in row['quality_flags']:row['energy_change_wh_by_bay']=dict.fromkeys(BAYS,None)
        if piece['average_power_w'] is not None:
            cache['_power_integral']+=piece['average_power_w']*dt[1];cache['_power_seconds']+=dt[1]
        row['average_power_w']=round(cache['_power_integral']/cache['_power_seconds'],2) if cache['_power_seconds'] else None
    cache.update(recorded_at=s['wall_time'],batteries=s['batteries'],external_power=s['external_power'],stale=False)
    return cache
