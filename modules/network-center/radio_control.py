#!/usr/bin/python3
"""Root-owned narrow radio operations and sanitized ZeroTier status export."""
import json,os,subprocess,sys,tempfile
from pathlib import Path

def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=20)
 if p.returncode:raise RuntimeError(p.stderr.strip()[-160:] or '系统操作失败')
 return p.stdout.strip()

def zero_summary(networks):
 names={'OK':'已连接／已授权','ACCESS_DENIED':'未授权','REQUESTING_CONFIGURATION':'等待网络配置','NOT_FOUND':'网络不存在','PORT_ERROR':'虚拟接口错误','CLIENT_TOO_OLD':'客户端需要更新'}
 return [{'name':x.get('name') or '未命名网络','state':names.get(x.get('status'), '状态未知'),'status':x.get('status','UNKNOWN'),'addresses':x.get('assignedAddresses',[])} for x in networks]

def radio_state(runner=run):
 values=runner(['nmcli','-t','-f','WIFI,WWAN','radio']).split(':')
 bt=[x for x in json.loads(runner(['rfkill','--json'])).get('rfkilldevices',[]) if x.get('type')=='bluetooth']
 return {'wifi':values[0]=='enabled','wwan':values[-1]=='enabled','bluetooth':any(x.get('soft')=='unblocked' for x in bt)}

def atomic_json(path,data,mode):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.status-')
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False)
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

def restore(snapshot,runner):
 for kind in ('wifi','wwan'):runner(['nmcli','radio',kind,'on' if snapshot[kind] else 'off'])
 runner(['rfkill','unblock' if snapshot['bluetooth'] else 'block','bluetooth'])

def flight(enabled,path,runner=run):
 if enabled:
  if not path.exists():atomic_json(path,radio_state(runner),0o600)
  snapshot=json.loads(path.read_text())
  try:
   runner(['nmcli','radio','all','off']);runner(['rfkill','block','bluetooth'])
  except Exception:
   restore(snapshot,runner)
   path.unlink(missing_ok=True)
   raise
 else:
  if not path.exists():raise RuntimeError('没有保存的无线状态，请分别开启所需网络')
  restore(json.loads(path.read_text()),runner);path.unlink()

def export_status():
 networks=[];error='';node_online=False
 try:
  node_online=json.loads(run(['/usr/bin/zerotier-cli','-j','info'])).get('online',False)
  networks=zero_summary(json.loads(run(['/usr/bin/zerotier-cli','-j','listnetworks'])))
 except Exception:error='ZeroTier 服务未连接或状态读取失败'
 snapshot=Path('/var/lib/pcadmin-network/flight.json')
 radios=radio_state()
 atomic_json(Path('/run/pcadmin-network/status.json'),{'zero_online':node_online,'zero_networks':networks,'zero_error':error,'flight_saved':snapshot.exists(),'flight_active':snapshot.exists() and not any(radios.values()),'radios':radios},0o644)

if __name__=='__main__':
 try:
  if os.geteuid()!=0:raise RuntimeError('需要系统认证')
  op=sys.argv[1] if len(sys.argv)==2 else ''
  if op in ('flight-on','flight-off'):flight(op=='flight-on',Path('/var/lib/pcadmin-network/flight.json'))
  elif op!='refresh':raise ValueError('不支持的操作')
  export_status()
  print(json.dumps({'ok':True,'message':'操作完成'},ensure_ascii=False))
 except Exception as e:print(json.dumps({'ok':False,'message':str(e)[:200]},ensure_ascii=False));sys.exit(1)
