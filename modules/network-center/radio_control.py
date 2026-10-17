#!/usr/bin/python3
"""Root-owned narrow radio operations and sanitized ZeroTier status export."""
import json,os,subprocess,sys,tempfile,time,re,fcntl
from pathlib import Path

def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=20,env={**os.environ,"LC_ALL":"C"})
 if p.returncode:raise RuntimeError(p.stderr.strip()[-160:] or '系统操作失败')
 return p.stdout.strip()

def zero_summary(networks):
 names={'OK':'已连接／已授权','ACCESS_DENIED':'未授权','REQUESTING_CONFIGURATION':'等待网络配置','NOT_FOUND':'网络不存在','PORT_ERROR':'虚拟接口错误','CLIENT_TOO_OLD':'客户端需要更新'}
 return [{'name':x.get('name') or '未命名网络','state':names.get(x.get('status'), '状态未知'),'status':x.get('status','UNKNOWN'),'addresses':x.get('assignedAddresses',[])} for x in networks]

def peer_summary(peers):
 leaves=[p for p in peers if p.get('role')=='LEAF']
 active=[p for p in leaves if any(x.get('active') is True for x in p.get('paths',[]))]
 timings=[p['latency'] for p in active if isinstance(p.get('latency'),(int,float)) and p['latency']>=0]
 return {'active_devices':len(active),'best_latency_ms':min(timings) if timings else None,'unconfirmed_devices':len(leaves)-len(active)}

def enabled(value):
 if value not in ('enabled','disabled'):raise ValueError('无线状态未知')
 return value=='enabled'

def rf_devices(runner):
 devices=json.loads(runner(['rfkill','--json']))['rfkilldevices']
 for x in devices:
  if x.get('soft') not in ('blocked','unblocked') or x.get('hard') not in ('blocked','unblocked'):raise ValueError('无线开关状态未知')
 return devices

def radio_state(runner=run):
 values=runner(['nmcli','-t','-f','WIFI,WWAN','radio']).split(':')
 if len(values)!=2:raise ValueError('网络无线状态未知')
 bt=[x for x in rf_devices(runner) if x.get('type')=='bluetooth']
 return {'wifi':enabled(values[0]),'wwan':enabled(values[1]),'bluetooth':any(x['soft']=='unblocked' and x['hard']=='unblocked' for x in bt)}

def modem_states(runner):
 paths=json.loads(runner(['mmcli','-L','-J']))['modem-list']
 result=[]
 for path in paths:
  if not re.fullmatch(r'/org/freedesktop/ModemManager1/Modem/[0-9]+',path):raise ValueError('蜂窝模块路径无效')
  g=json.loads(runner(['mmcli','-m',path,'-J']))['modem']['generic']
  if g.get('power-state') not in ('on','low','off'):raise ValueError('蜂窝射频状态未知')
  result.append({'path':path,'power':g['power-state'],'state':g.get('state','unknown')})
 return result

def flight_status(snapshot,runner=run):
 try:
  radios=radio_state(runner);net=enabled(runner(['nmcli','networking']))
  rf=rf_devices(runner);modems=modem_states(runner)
  expected_rf={(x['type'],x['device']) for x in snapshot.get('rfkill',[])} if snapshot else set()
  blocked=expected_rf.issubset({(x['type'],x['device']) for x in rf}) and all(x['soft']=='blocked' or x['hard']=='blocked' for x in rf)
  # A vanished modem is not evidence of a powered-down radio.
  expected={m['path'] for m in snapshot.get('modems',[])} if snapshot else set()
  seen={m['path'] for m in modems}
  cell_off=expected.issubset(seen) and all(m['power'] in ('low','off') and m['state']=='disabled' for m in modems)
  verified=not net and not any(radios.values()) and blocked and cell_off
  return {'flight_saved':snapshot is not None,'flight_active':snapshot is not None and verified,'flight_error':'' if verified or snapshot is None else '无线关闭尚未全部确认，请重试关闭；不要按已成功处理','radios':radios,'flight_checks':{'networking_off':not net,'rfkill_blocked':blocked,'cellular_radio_off':cell_off},'flight_observed_at':time.time()}
 except Exception:
  return {'flight_saved':snapshot is not None,'flight_active':None,'flight_error':'无法读取完整无线状态，尚未确认关闭','flight_checks':{},'flight_observed_at':time.time()}

def atomic_json(path,data,mode):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.status-')
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False)
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

def restore(snapshot,runner,guard):
 # Restore modem power before allowing NetworkManager to reconnect it.
 current={m['path'] for m in modem_states(runner)}
 for modem in snapshot.get('modems',[]):
  if modem['path'] not in current:raise RuntimeError('蜂窝模块已重新枚举，保留恢复记录，请重新检查')
  guard();runner(['mmcli','-m',modem['path'],'--set-power-state-'+modem['power']])
 for device in snapshot.get('rfkill',[]):
  present=next((x for x in rf_devices(runner) if x.get('type')==device['type'] and x.get('device')==device['device']),None)
  if present is None:raise RuntimeError('无线设备已变化，保留恢复记录')
  guard();runner(['rfkill','block' if device['soft']=='blocked' else 'unblock',str(present['id'])])
 for kind in ('wifi','wwan'):
  guard();runner(['nmcli','radio',kind,'on' if snapshot[kind] else 'off'])
 if 'rfkill' not in snapshot:
  guard();runner(['rfkill','unblock' if snapshot['bluetooth'] else 'block','bluetooth'])
 guard();runner(['nmcli','networking','on' if snapshot.get('networking',True) else 'off'])
 actual_modems={m['path']:m for m in modem_states(runner)}
 if any(actual_modems.get(m['path'],{}).get('power')!=m['power'] for m in snapshot.get('modems',[])):raise RuntimeError('蜂窝电源恢复尚未确认，保留恢复记录')
 actual_rf={(x['type'],x['device']):x['soft'] for x in rf_devices(runner)}
 if any(actual_rf.get((x['type'],x['device']))!=x['soft'] for x in snapshot.get('rfkill',[])):raise RuntimeError('无线开关恢复尚未确认，保留恢复记录')
 actual=radio_state(runner)
 if any(actual[k]!=snapshot[k] for k in ('wifi','wwan','bluetooth')) or enabled(runner(['nmcli','networking']))!=snapshot.get('networking',True):raise RuntimeError('无线恢复尚未确认，保留记录以便重试')

def flight(enabled_mode,path,runner=run,guard=None):
 if runner is run:
  with open('/run/lock/pcadmin-flight.lock','w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   try:return change_flight(enabled_mode,path,runner,guard)
   finally:export_status()
 return change_flight(enabled_mode,path,runner,guard)

def change_flight(enabled_mode,path,runner,guard):
 guard=guard or (lambda:None)
 guard()
 if enabled_mode:
  if path.exists():snapshot=json.loads(path.read_text())
  else:
   snapshot={**radio_state(runner),'networking':enabled(runner(['nmcli','networking'])),'modems':modem_states(runner),'rfkill':[{'type':d['type'],'device':d['device'],'soft':d['soft']} for d in rf_devices(runner)]}
   guard();atomic_json(path,snapshot,0o600)
  # Failure keeps the snapshot and already blocked radios; never silently reconnect.
  commands=[['nmcli','radio','all','off'],['rfkill','block','all'],['nmcli','networking','off']]
  for command in commands:
   guard()
   try:runner(command)
   except Exception:pass # Final readback determines whether the requested state was achieved.
  for modem in modem_states(runner):
   for option in ('--disable','--set-power-state-low'):
    guard()
    try:runner(['mmcli','-m',modem['path'],option])
    except Exception:pass # Some firmware enters low power as part of disable already.
  state=flight_status(snapshot,runner)
  if state['flight_active'] is not True:raise RuntimeError(state['flight_error'] or '无线关闭未确认')
 else:
  if not path.exists():raise RuntimeError('没有保存的无线状态，请分别开启所需网络')
  restore(json.loads(path.read_text()),runner,guard);path.unlink()

def export_status():
 networks=[];error='';node_online=False;peers={};peer_error=''
 try:
  node_online=json.loads(run(['/usr/bin/zerotier-cli','-j','info'])).get('online',False)
  networks=zero_summary(json.loads(run(['/usr/bin/zerotier-cli','-j','listnetworks'])))
 except Exception:error='ZeroTier 服务未连接或状态读取失败'
 try:peers=peer_summary(json.loads(run(['/usr/bin/zerotier-cli','-j','listpeers'])))
 except Exception:peer_error='设备连接状态读取失败'
 snapshot=Path('/var/lib/pcadmin-network/flight.json')
 saved=json.loads(snapshot.read_text()) if snapshot.exists() else None
 state=flight_status(saved)
 atomic_json(Path('/run/pcadmin-network/status.json'),{'zero_online':node_online,'zero_networks':networks,'zero_error':error,'zero_peers':peers,'zero_peer_error':peer_error,**state},0o644)

if __name__=='__main__':
 try:
  if os.geteuid()!=0:raise RuntimeError('需要系统认证')
  op=sys.argv[1] if len(sys.argv)==2 else ''
  if op in ('flight-on','flight-off'):flight(op=='flight-on',Path('/var/lib/pcadmin-network/flight.json'))
  elif op!='refresh':raise ValueError('不支持的操作')
  export_status()
  print(json.dumps({'ok':True,'message':'操作完成'},ensure_ascii=False))
 except Exception as e:print(json.dumps({'ok':False,'message':str(e)[:200]},ensure_ascii=False));sys.exit(1)
