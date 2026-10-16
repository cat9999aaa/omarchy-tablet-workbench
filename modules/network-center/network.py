#!/usr/bin/python3
"""Local touch-network adapter. Never reads proxy credentials or ZeroTier tokens."""
import json,subprocess,sys,os,socket,time,fcntl,signal,tempfile
from pathlib import Path
from policy import read_policy,update_policy
PROFILE=os.environ.get('PCADMIN_CELL_PROFILE','平板蜂窝网络')
CELL='wwp0s20f0u2c2'
def call(args,timeout=8):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.strip()[-180:] or '操作未成功')
 return p.stdout.strip()
def optional(args,default='',timeout=8):
 try:return call(args,timeout)
 except (OSError,subprocess.SubprocessError,RuntimeError):return default
def classify(interface,types,cell):
 if interface==cell or types.get(interface)=='gsm':return '4g'
 if types.get(interface)=='tun' or interface.startswith(('zt','tun','tailscale','singbox')):return 'virtual'
 return 'wifi' if types.get(interface)=='wifi' else 'ethernet'
def traffic_totals(data,interface):
 item=next((x for x in data.get('interfaces',[]) if x.get('name')==interface),{})
 traffic=item.get('traffic',{})
 def total(k):
  rows=traffic.get(k,[])
  if not rows:return None
  latest=max(rows,key=lambda r:tuple(r.get('date',{}).get(k,0) for k in ('year','month','day')))
  return latest.get('rx',0)+latest.get('tx',0)
 return {'day':total('day'),'month':total('month')}
def action_command(op):
 commands={'cell-on':['nmcli','--wait','25','con','up',PROFILE], 'cell-off':['nmcli','--wait','15','con','down',PROFILE], 'cell-radio-off':['nmcli','radio','wwan','off'], 'cell-radio-on':['nmcli','radio','wwan','on'], 'zero-on':['pkexec','/usr/bin/systemctl','start','zerotier-one.service'], 'gps-on':['pkexec','/usr/bin/systemctl','start','pcadmin-gps.service'], 'gps-off':['pkexec','/usr/bin/systemctl','stop','pcadmin-gps.service'], 'wifi-on':['nmcli','radio','wifi','on'], 'wifi-off':['nmcli','radio','wifi','off'], 'flight-on':['pkexec','/usr/local/libexec/pcadmin-radio-control','flight-on'], 'flight-off':['pkexec','/usr/local/libexec/pcadmin-radio-control','flight-off'], 'zero-refresh':['pkexec','/usr/local/libexec/pcadmin-radio-control','refresh'], 'gps-details':['/usr/bin/xgps','127.0.0.1:2947'], 'proxy-open':['/opt/v2rayn-bin/v2rayN']}
 if op not in commands:raise ValueError('不支持的操作')
 return commands[op]
def consume_gps(d,out):
 if d.get('class')=='TPV':out['mode']=d.get('mode',1)
 if d.get('class')=='SKY':
  sats=d.get('satellites',[])
  if sats:out.update(satellites=len(sats),used=sum(bool(x.get('used')) for x in sats))
  elif isinstance(d.get('nSat'),int):out.update(satellites=d['nSat'],used=d.get('uSat'))
def gps_status():
 if optional(['systemctl','is-active','pcadmin-gps.service'])!='active':return {'state':'关闭'}
 out={'state':'等待卫星定位','satellites':None,'used':None,'mode':1}
 try:
  with socket.create_connection(('127.0.0.1',2947),timeout=.5) as sock:
   sock.settimeout(.25);sock.sendall(b'?WATCH={"enable":true,"json":true};\n');buf=b'';end=time.monotonic()+1.4
   while time.monotonic()<end:
    try:chunk=sock.recv(16384)
    except TimeoutError:continue
    if not chunk:break
    buf+=chunk
    while b'\n' in buf:
     line,buf=buf.split(b'\n',1)
     try:consume_gps(json.loads(line),out)
     except ValueError:pass
    if out['mode']>=2 and out['satellites'] is not None:break
   if out['mode']>=2:out['state']='已定位'
 except (OSError,ValueError):out['state']='服务已开，等待数据'
 return out
def health_check():
 route=route_status();iface=route['interface'];out={'observed_at':time.time(),'interface':iface,'internet':'unavailable','proxy':'off'}
 if iface:
  answer=optional(['curl','--noproxy','*','--interface',iface,'-4','-sS','--max-time','4','http://ping.archlinux.org/nm-check.txt'],timeout=6)
  out['internet']='ok' if answer=='NetworkManager is online' else 'failed'
 if read_policy()['proxy_enabled']:
  code=optional(['curl','--proxy','http://127.0.0.1:10808','-sS','-o','/dev/null','-w','%{http_code}','--max-time','5','https://www.google.com'],timeout=7)
  out['proxy']='ok' if code in ('200','301','302') else 'failed'
 if optional(['systemctl','is-active','pcadmin-v2ray-tun.service'])=='active':
  code=optional(['curl','--noproxy','*','-sS','-o','/dev/null','-w','%{http_code}','--max-time','5','https://www.google.com/generate_204'],timeout=7)
  out['tun']='ok' if code=='204' else 'failed'
 p=Path.home()/'.local/state/pcadmin-network/health.json';p.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(dir=p.parent,prefix='.health-')
 with os.fdopen(fd,'w') as f:json.dump(out,f)
 os.replace(name,p)
 return out

def route_status():
 routes=json.loads(optional(['ip','-j','route','get','1.1.1.1'],'[]'))
 iface=routes[0].get('dev','') if routes else ''
 if iface.startswith(('singbox','tun','zt','tailscale')):
  physical=json.loads(optional(['ip','-j','route','show','table','main','default'],'[]'))
  physical=[r for r in physical if not r.get('dev','').startswith(('singbox','tun','zt','tailscale'))]
  iface=min(physical,key=lambda r:r.get('metric',0)).get('dev','') if physical else ''
 kind='wifi' if (Path('/sys/class/net')/iface/'wireless').exists() else classify(iface,{},CELL) if iface else 'none'
 return {'primary':kind,'interface':iface}

def status():
 devices=[]
 for line in optional(['nmcli','-t','-f','DEVICE,TYPE,STATE','dev']).splitlines():
  p=line.split(':',2)
  if len(p)==3:devices.append(p)
 types={x[0]:x[1] for x in devices}
 cell=next((x for x in devices if x[1]=='gsm'),None)
 iface=route_status()['interface']
 radios=optional(['nmcli','-t','-f','WWAN','radio']).strip()
 signal=None
 try:
  m=json.loads(call(['mmcli','-m','0','-J'])).get('modem',{}).get('generic',{}).get('signal-quality',{})
  signal=m.get('value') if isinstance(m,dict) else m
 except (ValueError,RuntimeError,subprocess.SubprocessError):pass
 traffic=traffic_totals(json.loads(optional(['vnstat','-i',CELL,'--json'],'{}')),CELL)
 net=json.loads(optional(['ip','-j','address'],'[]'))
 zero=[a.get('local') for x in net if x.get('ifname','').startswith('zt') for a in x.get('addr_info',[]) if a.get('family')=='inet']
 proxy_mode=optional(['gsettings','get','org.gnome.system.proxy','mode']).strip("'")
 proxy_port=False
 try:
  with socket.create_connection(('127.0.0.1',10808),timeout=.2):proxy_port=True
 except OSError:pass
 cache={}
 try:cache=json.loads(Path('/run/pcadmin-network/status.json').read_text())
 except (OSError,ValueError):pass
 if cache and time.time()-Path('/run/pcadmin-network/status.json').stat().st_mtime>45:
  cache.update(zero_online=False,zero_networks=[],zero_error='授权状态已过期，请重新核对')
 linkage={}
 try:linkage=json.loads((Path.home()/'.local/state/pcadmin-network/cell-proxy.json').read_text())
 except (OSError,ValueError):pass
 wifi=next((x for x in devices if x[1]=='wifi'),None)
 wired=[{'interface':x[0],'state':x[2]} for x in devices if x[1]=='ethernet']
 local=[{'interface':x.get('ifname'),'addresses':[a.get('local')+'/'+str(a.get('prefixlen')) for a in x.get('addr_info',[]) if a.get('family')=='inet']} for x in net if types.get(x.get('ifname')) in ('wifi','ethernet')]
 health={}
 try:
  health=json.loads((Path.home()/'.local/state/pcadmin-network/health.json').read_text())
  if health.get('interface')!=iface or time.time()-health.get('observed_at',0)>65:health={}
 except (OSError,ValueError):pass
 return {**cache,'health':health,'policy':read_policy(),'cell_proxy':linkage,'local_addresses':local,'wifi_enabled':optional(['nmcli','-t','-f','WIFI','radio'])=='enabled','wifi_state':wifi[2] if wifi else '未发现设备','wifi_connection':optional(['nmcli','-g','GENERAL.CONNECTION','dev','show',wifi[0]]) if wifi else '','wired':wired,'primary':classify(iface,types,CELL) if iface else 'none','interface':iface,'cell':cell[2] if cell else '未发现设备','cell_connected':bool(cell and cell[2]=='connected'),'wwan':radios=='enabled','signal':signal,'traffic':traffic,'zero_enabled':optional(['systemctl','is-active','zerotier-one.service'])=='active','zero_ips':zero,'proxy_available':proxy_port,'proxy_tun':optional(['systemctl','is-active','pcadmin-v2ray-tun.service'])=='active','proxy_system':proxy_mode=='manual','gps':gps_status()}
def auto_metric(kind):
 return {'802-3-ethernet':100,'802-11-wireless':600,'gsm':700}.get(kind)

def auto_mode():
 rows=[line.split(':',1) for line in call(['nmcli','-t','-f','UUID,TYPE','con','show']).splitlines()]
 changed=[]
 try:
  for uuid,kind in rows:
   metric=auto_metric(kind)
   if metric is None:continue
   old=call(['nmcli','-g','ipv4.route-metric,ipv6.route-metric','con','show',uuid]).splitlines()
   if old!=[str(metric),str(metric)]:
    call(['nmcli','con','mod',uuid,'ipv4.route-metric',str(metric),'ipv6.route-metric',str(metric)]);changed.append((uuid,old))
  old_auto=call(['nmcli','-g','connection.autoconnect','con','show',PROFILE])
  call(['nmcli','con','mod',PROFILE,'connection.autoconnect','yes','connection.metered','yes'])
  active=[line.split(':',2) for line in call(['nmcli','-t','-f','DEVICE,TYPE,STATE','dev']).splitlines()]
  for dev,kind,state in active:
   if state=='connected' and kind in ('wifi','ethernet'):call(['nmcli','device','reapply',dev])
  cell_uuid=next((uuid for uuid,kind in rows if kind=='gsm'),None)
  if cell_uuid and any(uuid==cell_uuid for uuid,old in changed) and cell_connected():call(action_command('cell-on'),35)
  update_policy(mode='auto')
 except Exception:
  for uuid,old in reversed(changed):optional(['nmcli','con','mod',uuid,'ipv4.route-metric',old[0],'ipv6.route-metric',old[1]])
  if 'old_auto' in locals():optional(['nmcli','con','mod',PROFILE,'connection.autoconnect',old_auto])
  for dev,kind,state in locals().get('active',[]):
   if state=='connected' and kind in ('wifi','ethernet'):optional(['nmcli','device','reapply',dev])
  raise

def preference(op):
 # Explicit user selection only; no balancing or periodic route changes.
 target_type={'prefer-wifi':'wifi','prefer-cell':'gsm','prefer-wired':'ethernet'}[op]
 rows=[x.split(':',2) for x in call(['nmcli','-t','-f','DEVICE,TYPE,STATE','dev']).splitlines()]
 target=next((x for x in rows if len(x)==3 and x[1]==target_type and x[2]=='connected'),None)
 if target is None:
  if target_type!='gsm':raise RuntimeError('请先连接此网络，再选择用它上网')
  call(['nmcli','radio','wwan','on']);call(action_command('cell-on'),35)
  target=['cdc-wdm0','gsm','connected']
 changes=[]
 try:
  for row in rows:
   if len(row)!=3 or row[1] not in ('wifi','gsm','ethernet'):continue
   dev,kind,connected=row
   profile=PROFILE if kind=='gsm' else optional(['nmcli','-g','GENERAL.CONNECTION','dev','show',dev])
   if not profile or profile=='--':continue
   old=call(['nmcli','-g','ipv4.route-metric,ipv6.route-metric','con','show',profile]).splitlines()
   value='50' if dev==target[0] else '30000'
   if old==[value,value]:continue
   call(['nmcli','con','mod',profile,'ipv4.route-metric',value,'ipv6.route-metric',value]);changes.append((dev,profile,old,kind))
   if connected=='connected' or dev==target[0]:
    if kind=='gsm':call(action_command('cell-on'),35)
    else:call(['nmcli','device','reapply',dev],20)
 except Exception:
  for dev,profile,old,kind in reversed(changes):
   optional(['nmcli','con','mod',profile,'ipv4.route-metric',old[0],'ipv6.route-metric',old[1]])
   if kind=='gsm':optional(action_command('cell-on'),timeout=35)
   else:optional(['nmcli','device','reapply',dev])
  raise

def wired_command(op):
 rows=[x.split(':',1) for x in call(['nmcli','-t','-f','DEVICE,TYPE','dev']).splitlines()]
 dev=next((x[0] for x in rows if len(x)==2 and x[1]=='ethernet'),None)
 if not dev:raise RuntimeError('未接入有线网卡')
 return ['nmcli','--wait','25','device','connect' if op=='wired-on' else 'disconnect',dev]

def cell_connected():
 return any(line.split(':',2)[1:]==['gsm','connected'] for line in optional(['nmcli','-t','-f','DEVICE,TYPE,STATE','dev']).splitlines())

def set_system_proxy(enabled):
 if enabled:
  for protocol in ('http','https','socks'):
   call(['gsettings','set','org.gnome.system.proxy.'+protocol,'host','127.0.0.1'])
   call(['gsettings','set','org.gnome.system.proxy.'+protocol,'port','10808'])
 call(['gsettings','set','org.gnome.system.proxy','mode','manual' if enabled else 'none'])

def close_extra_clients(keep):
 for item in optional(['pgrep','-u',str(os.getuid()),'-x','v2rayN']).splitlines():
  pid=int(item)
  if pid==keep:continue
  try:
   if Path('/proc/'+item+'/exe').resolve()==Path('/opt/v2rayn-bin/v2rayN'):os.kill(pid,signal.SIGTERM)
  except (OSError,ProcessLookupError):pass

def start_proxy_client():
 call(['systemctl','--user','start','app-v2rayN@autostart.service'],20)
 pid=int(call(['systemctl','--user','show','app-v2rayN@autostart.service','-p','MainPID','--value']))
 if not pid:raise RuntimeError('V2Ray 客户端未启动')
 close_extra_clients(pid)

def tun_control(op):
 if op not in ('start','stop'):raise ValueError('不支持的 TUN 操作')
 active=optional(['systemctl','is-active','pcadmin-v2ray-tun.service'])=='active'
 if (op=='start' and active) or (op=='stop' and not active):return
 call(['pkexec','/usr/bin/systemctl',op,'pcadmin-v2ray-tun.service'],90)

def ensure_proxy():
 directory=Path.home()/'.local/state/pcadmin-network';directory.mkdir(parents=True,exist_ok=True)
 with (directory/'cell-proxy.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  try:
   if not read_policy()["proxy_enabled"]:return
   def available():
    try:
     with socket.create_connection(('127.0.0.1',10808),timeout=.25):return True
    except OSError:return False
   start_proxy_client()
   if not available():
    end=time.monotonic()+15
    while not available():
     if time.monotonic()>=end:raise RuntimeError('本地代理端口尚未就绪')
     time.sleep(.25)
   set_system_proxy(True)
   tun_control('start')
   (directory/'cell-proxy.json').write_text(json.dumps({'state':'ready','message':'V2Ray 单实例与 TUN 应用接管已开启'},ensure_ascii=False))
  except Exception as e:
   (directory/'cell-proxy.json').write_text(json.dumps({'state':'failed','message':'4G 联动失败，请检查 V2Ray 节点或启动状态'},ensure_ascii=False))
   raise RuntimeError('4G 已连接，但 V2Ray 联动失败：'+str(e)[:120]) from e

def action(op):
 if op=='auto-mode':auto_mode();return
 if op in ('prefer-cell','prefer-wifi','prefer-wired'):
  preference(op)
  update_policy(mode='manual')
  if op=='prefer-cell':ensure_proxy()
  return
 if op=='cell-proxy-on':
  if cell_connected():ensure_proxy()
  return
 if op=='proxy-auto-on':ensure_proxy();return
 if op=='proxy-user-exit':
  if optional(['systemctl','--user','is-active','app-v2rayN@autostart.service'])!='active':
   update_policy(proxy_enabled=False);tun_control('stop');set_system_proxy(False)
  return
 if op=='proxy-on':update_policy(proxy_enabled=True);ensure_proxy();return
 if op=='proxy-off':
  update_policy(proxy_enabled=False)
  tun_control('stop')
  set_system_proxy(False)
  call(['systemctl','--user','stop','app-v2rayN@autostart.service'],25)
  close_extra_clients(0)
  return
 if op=='proxy-open':update_policy(proxy_enabled=True);ensure_proxy();return
 args=wired_command(op) if op in ('wired-on','wired-off') else action_command(op)
 if op=='cell-on':
  call(['nmcli','radio','wwan','on'])
  if status()['cell_connected']:ensure_proxy();return
 if op in ('proxy-open','gps-details'):subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True);return
 call(args,90 if args[0]=='pkexec' else 35)
 if op=='cell-on':ensure_proxy()
if __name__=='__main__':
 try:
  op=sys.argv[1] if len(sys.argv)==2 else 'status'
  if op=='status':print(json.dumps(status(),ensure_ascii=False))
  elif op=='route':print(json.dumps(route_status()))
  elif op=='health':print(json.dumps(health_check()))
  else:action(op);print(json.dumps({'ok':True,'message':'操作完成，请查看状态'},ensure_ascii=False))
 except Exception as e:print(json.dumps({'ok':False,'message':str(e)[:200]},ensure_ascii=False));sys.exit(1)
