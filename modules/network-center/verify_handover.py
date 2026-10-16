import subprocess,time,json,threading,os,argparse
parser=argparse.ArgumentParser(description="仅验证链路和代理核心，不代表浏览器/GPT已接管。会临时关闭Wi-Fi。")
parser.add_argument("--run",action="store_true");options=parser.parse_args()
if not options.run:
 print("使用 --run 明确开始五轮切换和十分钟4G拨测；请保留恢复网络的备用方式。");raise SystemExit(0)
from pathlib import Path
ROOT=Path.home()/'.local/state/pcadmin-network';ROOT.mkdir(parents=True,exist_ok=True);out=ROOT/'handover-test.json';rows=[]
def call(a,timeout=15):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.strip()[:100] or 'command failed')
 return p.stdout.strip()
def iface():
 try:return json.loads(call(['ip','-j','route','get','1.1.1.1']))[0]['dev']
 except Exception:return ''
def pid():return call(['systemctl','--user','show','app-v2rayN@autostart.service','-p','MainPID','--value'])
def proxy():
 p=subprocess.run(['curl','--proxy','http://127.0.0.1:10808','-sS','-o','/dev/null','-w','%{http_code}','--max-time','8','https://www.google.com'],capture_output=True,text=True,timeout=10)
 return p.returncode==0 and p.stdout in ('200','301','302')
def save(row):
 rows.append(row);out.write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
original=call(['nmcli','-g','GENERAL.CONNECTION','dev','show','wlp3s0']);original_pid=pid()
# Independent emergency restore survives this diagnostic process exiting.
restore='import subprocess,time;time.sleep(850);subprocess.run(["nmcli","radio","wifi","on"]);subprocess.run(["nmcli","--wait","20","con","up",'+repr(original)+'])'
watchdog=subprocess.Popen(['/usr/bin/python','-c',restore],start_new_session=True)
def wifi_restore():
 subprocess.run(['nmcli','radio','wifi','on'],capture_output=True,timeout=10)
 subprocess.run(['nmcli','--wait','20','con','up',original],capture_output=True,timeout=25)
def wait_link(expected,deadline=28):
 start=time.monotonic()
 while time.monotonic()-start<deadline:
  if iface()==expected and proxy():return round(time.monotonic()-start,2)
  time.sleep(1)
 raise RuntimeError('route/proxy recovery timed out: '+expected)
try:
 if not proxy():raise RuntimeError('baseline proxy failed')
 for n in range(1,6):
  call(['nmcli','radio','wifi','off']);seconds=wait_link('wwp0s20f0u2c2');save({'cycle':n,'phase':'cellular','seconds':seconds,'same_gui_pid':pid()==original_pid,'proxy':True})
  wifi_restore();seconds=wait_link('wlp3s0');save({'cycle':n,'phase':'wifi','seconds_after_reconnect':seconds,'same_gui_pid':pid()==original_pid,'proxy':True})
  time.sleep(3)
 call(['nmcli','radio','wifi','off']);wait_link('wwp0s20f0u2c2')
 for n in range(21):
  if iface()!='wwp0s20f0u2c2':raise RuntimeError('测试期间出口已变化；停止蜂窝持续测试')
  passed=proxy();save({'phase':'cellular_steady','sample':n,'interface':iface(),'proxy':passed,'same_gui_pid':pid()==original_pid})
  if not passed:raise RuntimeError('蜂窝代理拨测失败')
  if n<20:time.sleep(30)
 save({'result':'PASS' if all(r.get('proxy',True) and r.get('same_gui_pid',True) for r in rows) else 'FAIL'})
except Exception as e:save({'result':'FAIL','reason':str(e)})
finally:
 wifi_restore();watchdog.terminate();save({'phase':'restored','interface':iface(),'proxy':proxy(),'same_gui_pid':pid()==original_pid})
