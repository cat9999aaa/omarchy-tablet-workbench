import sys,unittest,tempfile,json,os,sqlite3,copy,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class CollectorTests(unittest.TestCase):
 def test_two_bays_missing_fields_and_power(self):
  from collect import collect_snapshot
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);sysfs=base/'power';proc=base/'proc';sysfs.mkdir();proc.mkdir()
   for name,fields in {'BAT0':{'type':'Battery','status':'Charging','capacity':'50','voltage_now':'7500000','current_now':'1000000'},'BAT1':{'type':'Battery','status':'Not charging','capacity':'10'},'AC':{'type':'Mains','online':'1'}}.items():
    p=sysfs/name;p.mkdir()
    for k,v in fields.items():(p/k).write_text(v)
   x=collect_snapshot(sysfs,proc,{'wall_time':'2026-10-17T01:00:00+08:00','boot_id':'test','boottime_s':1,'monotonic_s':1},None)
   self.assertTrue(x['external_power']);self.assertEqual(x['batteries']['BAT0']['power_w'],7.5);self.assertIsNone(x['batteries']['BAT1']['power_w']);self.assertIsNone(x['screen_on']);self.assertFalse(x['batteries']['BAT0'].get('serial'))
 def test_stat_parentheses_and_pid_identity(self):
  from collect import parse_stat
  fields=['S']+['0']*49;fields[11]='100';fields[12]='50';fields[19]='42'
  p=parse_stat('123 (name (with) spaces) '+' '.join(fields))
  self.assertEqual((p['pid'],p['name'],p['cpu_ticks'],p['start_ticks']),(123,'name (with) spaces',150,42))
class StoreTests(unittest.TestCase):
 def test_roundtrip_and_permissions(self):
  from store import open_store,append_sample,read_samples
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'private'/'db';c=open_store(p);s=snap(0);append_sample(c,s);self.assertEqual(read_samples(c,None),[s]);c.close()
   self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(p.parent.stat().st_mode&0o777,0o700)
 def test_corruption_is_not_replaced(self):
  from store import open_store
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';p.write_bytes(b'corrupt')
   with self.assertRaises(sqlite3.DatabaseError):open_store(p)
   self.assertEqual(p.read_bytes(),b'corrupt')
 def test_retention_and_readonly(self):
  from store import open_store,append_sample,read_samples
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';c=open_store(p);old=snap(0);old['wall_time']='2025-01-01T00:00:00+08:00';append_sample(c,old);append_sample(c,snap(60));self.assertEqual(len(read_samples(c,None)),1);c.close()
class SessionTests(unittest.TestCase):
 def test_charge_wait_and_battery_rotation(self):
  from sessions import derive_sessions
  a=snap(0,ac=False);b=snap(60,ac=True);c=snap(120,ac=True)
  for x in [b,c]:x['batteries']['BAT1']['status']='Charging'
  rows=derive_sessions([a,b,c]);self.assertEqual(len(rows),2);self.assertEqual(rows[-1]['charging_s_by_bay'],{'BAT0':0,'BAT1':60});self.assertTrue(rows[0]['partial_start']);self.assertFalse(rows[-1]['partial_start'])
 def test_sleep_is_separate_from_awake(self):
  from sessions import derive_sessions
  a=snap(0);b=snap(660);b['monotonic_s']=60
  s=derive_sessions([a,b])[0];self.assertEqual((s['awake_s'],s['sleep_s'],s['unknown_s']),(60,600,0))
 def test_gap_and_clock_change(self):
  from sessions import derive_sessions
  a=snap(0);b=snap(600);b['wall_time']='2026-10-16T00:00:00+08:00'
  s=derive_sessions([a,b])[0];self.assertEqual(s['elapsed_s'],600);self.assertEqual(s['awake_s'],0);self.assertEqual(s['unknown_s'],600);self.assertIn('gap',s['quality_flags'])
 def test_reboot_and_unknown_ac_split(self):
  from sessions import derive_sessions
  a=snap(0);b=snap(60);b['boot_id']='new';c=snap(120,ac=None)
  rows=derive_sessions([a,b,c]);self.assertEqual(len(rows),3);self.assertTrue(rows[1]['partial_start']);self.assertEqual(rows[-1]['kind'],'unknown')
 def test_energy_missing_and_screen_unknown(self):
  from sessions import derive_sessions
  a=snap(0);b=snap(60);a['screen_on']=None;b['screen_on']=None
  s=derive_sessions([a,b])[0];self.assertIsNone(s['energy_change_wh_by_bay']['BAT0']);self.assertEqual(s['screen_on_s'],0);self.assertEqual(s['screen_unknown_s'],60);self.assertEqual(s['average_power_w'],5)
 def test_jump_breaks_curve(self):
  from sessions import build_history
  a=snap(0);b=snap(60);b['batteries']['BAT0']['percent']=10
  x=build_history([a,b]);self.assertIsNone(x['points'][1]['BAT0']);self.assertIn('battery-jump',x['sessions'][0]['quality_flags'])
 def test_app_multiple_instances_and_reuse(self):
  from sessions import rank_apps
  a=snap(0);b=snap(60)
  a['processes']=[process(1,0),process(2,0)];b['processes']=[process(1,6000),process(2,6000)]
  row=rank_apps([a,b],'session')[0];self.assertEqual(row['cpu_seconds'],120);self.assertEqual(row['unknown_samples'],2);self.assertEqual(row['background_samples'],0)
  b['processes'][0]['start_ticks']=99;row=rank_apps([a,b],'session')[0];self.assertEqual(row['cpu_seconds'],60)
 def test_visible_and_negative_counter(self):
  from sessions import rank_apps
  a=snap(0);b=snap(60);a['processes']=[process(1,200)];b['processes']=[process(1,100)];self.assertEqual(rank_apps([a,b],'session'),[])
 def test_status_stale(self):
  from sessions import build_status
  self.assertTrue(build_status([snap(0)],snap(181))['stale']);self.assertFalse(build_status([snap(0)],snap(60))['stale'])
class CliTests(unittest.TestCase):
 def test_not_started_and_readonly(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'battery.py'),'status','--db',str(p)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['reason'],'not-started');self.assertFalse(p.exists())
 def test_corruption_reason(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';p.write_bytes(b'corrupt');r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'battery.py'),'status','--db',str(p)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['reason'],'database-error');self.assertEqual(p.read_bytes(),b'corrupt')
def process(pid,ticks):return {'pid':pid,'name':'mame','start_ticks':1,'cpu_ticks':ticks,'visible':None}
def snap(t,ac=False):
 import datetime
 return {'schema':1,'wall_time':(datetime.datetime(2026,10,17,tzinfo=datetime.timezone(datetime.timedelta(hours=8)))+datetime.timedelta(seconds=t)).isoformat(),'boot_id':'test','boottime_s':t,'monotonic_s':t,'external_power':ac,'screen_on':True,'clock_ticks':100,'batteries':{n:{'present':True,'status':'Not charging' if ac else 'Discharging','percent':50,'energy_uwh':None,'full_energy_uwh':None,'charge_uah':100,'full_charge_uah':200,'power_w':5 if n=='BAT0' else 0} for n in ['BAT0','BAT1']},'processes':[]}

class CacheTests(unittest.TestCase):
 def test_incremental_matches_observed_session(self):
  from sessions import update_cache,derive_sessions
  samples=[snap(0),snap(60),snap(120)];cache=None;prev=None
  for s in samples:cache=update_cache(prev,s,cache);prev=s
  for key in ['elapsed_s','awake_s','sleep_s','start_percent_by_bay','end_percent_by_bay','average_power_w']:
   self.assertEqual(cache['current_session'][key],derive_sessions(samples)[0][key])
 def test_cache_retains_last_charge_on_unplug(self):
  from sessions import update_cache
  a=snap(0,True);b=snap(60,True);c=snap(120,False)
  cache=update_cache(None,a,None);cache=update_cache(a,b,cache);cache=update_cache(b,c,cache)
  self.assertEqual(cache['last_charge']['elapsed_s'],60);self.assertEqual(cache['current_session']['kind'],'discharge')

class ReviewRegressions(unittest.TestCase):
 def test_unknown_power_is_unknown_not_zero(self):
  from sessions import derive_sessions
  a=snap(0);b=snap(60)
  for x in [a,b]:
   x['batteries']['BAT0']['status']=None;x['batteries']['BAT0']['power_w']=None
  self.assertIsNone(derive_sessions([a,b])[0]['average_power_w'])
 def test_clock_rollback_apps_keeps_current_session(self):
  from store import open_store,append_sample
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';a=snap(0);b=snap(60);a['processes']=[process(1,0)];b['processes']=[process(1,12000)];b['wall_time']='2026-10-16T23:00:00+08:00'
   c=open_store(p);append_sample(c,a);append_sample(c,b);c.close()
   r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'battery.py'),'apps','--db',str(p)],capture_output=True,text=True)
   rows=json.loads(r.stdout)['apps'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['cpu_seconds'],120)
 def test_clock_change_curve_has_gap_and_monotonic_axis(self):
  from sessions import build_history
  a=snap(0);b=snap(60);c=snap(120);b['wall_time']='2026-10-16T23:00:00+08:00'
  rows=build_history([a,b,c])['points'];self.assertTrue(any(r['BAT0'] is None for r in rows));self.assertEqual(sorted(r['axis_time'] for r in rows),[r['axis_time'] for r in rows])
 def test_concurrent_app_observed_time_not_multiplied(self):
  from sessions import rank_apps
  a=snap(0);b=snap(60);a['processes']=[process(1,0),process(2,0)];b['processes']=[process(1,6000),process(2,6000)]
  self.assertEqual(rank_apps([a,b],'session')[0]['observed_seconds'],60)

class ActivityStorageTests(unittest.TestCase):
 def test_activity_retained_without_full_process_history(self):
  from store import open_store,append_sample,read_samples,read_activity
  with tempfile.TemporaryDirectory() as d:
   c=open_store(Path(d)/'db');a=snap(0);b=snap(60);a['processes']=[process(1,0)];b['processes']=[process(1,6000)]
   append_sample(c,a);append_sample(c,b)
   self.assertEqual(read_samples(c,None)[0]['processes'],[])
   self.assertEqual(read_activity(c,1,None)[0]['cpu_seconds'],60);c.close()
 def test_locked_database_returns_json_error(self):
  from store import open_store
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';c=open_store(p);c.execute('BEGIN EXCLUSIVE')
   r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'battery.py'),'status','--db',str(p)],capture_output=True,text=True,timeout=6)
   self.assertEqual(json.loads(r.stdout)['reason'],'database-locked');c.rollback();c.close()

class SecondReviewRegressions(unittest.TestCase):
 def test_new_session_does_not_inherit_preceding_cpu(self):
  from store import open_store,append_sample,read_activity,read_cache
  with tempfile.TemporaryDirectory() as d:
   c=open_store(Path(d)/'db');a=snap(0,True);b=snap(60,False);a['processes']=[process(1,0)];b['processes']=[process(1,6000)];append_sample(c,a);append_sample(c,b)
   self.assertEqual(read_activity(c,read_cache(c)['_session_start_id'],None),[]);c.close()
 def test_migration_rebuilds_current_session_start(self):
  from store import open_store,read_activity,read_cache
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'db';c=sqlite3.connect(p);c.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY,wall_time TEXT,boot_id TEXT,boottime_s REAL,monotonic_s REAL,payload_json TEXT)');c.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)');c.execute('PRAGMA user_version=1')
   for i,ac in enumerate([True,True,False,False]):
    s=snap(i*60,ac);s['processes']=[process(1,i*6000)];c.execute('INSERT INTO sample VALUES(?,?,?,?,?,?)',(i+1,s['wall_time'],s['boot_id'],s['boottime_s'],s['monotonic_s'],json.dumps(s)))
   c.commit();c.close();c=open_store(p);cache=read_cache(c);self.assertEqual(cache['_session_start_id'],3);self.assertEqual(read_activity(c,cache['_session_start_id'],None)[0]['cpu_seconds'],60);c.close()
 def test_awake_gap_marks_unknown_display_time(self):
  from sessions import derive_sessions
  r=derive_sessions([snap(0),snap(600)])[0];self.assertEqual(r['screen_unknown_s'],600)

if __name__=='__main__':unittest.main()
