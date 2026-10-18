#!/usr/bin/python3
"""Tablet navigation and key actions. Fixed actions only, no shell evaluation."""
import json,os,re,signal,subprocess,sys,tempfile
from pathlib import Path
from navigation_read import ReadBudget,ReadError,read_json,check_lock,focused_output,window_identity,workspace,workspace_counts
DEFAULTS={'P1':'keyboard','P2':'voice','P3':'authorize','rotation':'windows'}
LABELS={'keyboard':'输入法开关','voice':'语音开始 / 停止','authorize':'系统窗口授权','navigation':'开始菜单','desktops':'选择桌面','windows':'当前窗口操作','control-center':'随身控制台','disabled':'不执行操作'}
CONFIG=Path.home()/'.config/omarchy-tablet-workbench/buttons.json'
COMMANDS={'keyboard':['omarchy-shell','omtInput','toggle'],'voice':['omarchy-shell','omtInput','voice'],'authorize':['omarchy-shell','pcadminAuth','authorize'],'navigation':['omarchy-shell','pcadmin.navigation','toggle','开始'],'desktops':['omarchy-shell','pcadmin.navigation','toggle','桌面'],'windows':['omarchy-shell','pcadmin.navigation','toggle','窗口'],'control-center':['omarchy-shell','pcadmin.controlCenter','toggle']}

def output(argv):
 try:return subprocess.check_output(argv,text=True,stderr=subprocess.DEVNULL,timeout=4).strip()
 except (OSError,subprocess.SubprocessError):return ''
def run(argv):
 try:
  p=subprocess.run(argv,capture_output=True,text=True,timeout=5)
  return p.returncode==0 and (argv[:2]!=['hyprctl','eval'] or p.stdout.strip()=='ok')
 except (OSError,subprocess.SubprocessError):return False
def unlocked():return output(['omarchy-shell','lock','isLocked'])=='false'
def validate_bindings(value):
 if not isinstance(value,dict) or set(value)!=set(DEFAULTS):raise ValueError('按键配置不完整')
 for key,action in value.items():
  if not isinstance(action,str) or action not in LABELS or (key=='P3' and action not in ('authorize','disabled')) or (key!='P3' and action=='authorize'):raise ValueError('不支持的按键动作')
 return dict(value)
def load_bindings(path=CONFIG):
 try:return validate_bindings(json.loads(path.read_text()))
 except (OSError,ValueError):return dict(DEFAULTS)
def save_bindings(path,value):
 value=validate_bindings(value);path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix='.buttons-',delete=False) as f:
  temp=Path(f.name);json.dump(value,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
 try:temp.chmod(0o600);temp.replace(path)
 finally:temp.unlink(missing_ok=True)
def key_action(key):
 if key not in DEFAULTS or not unlocked():return False
 action=load_bindings()[key]
 return action=='disabled' or run(COMMANDS[action])
def workspace_id(value):
 if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=10:raise ValueError('无效桌面编号')
 return value
def output_literal(value):
 if not isinstance(value,str) or not value.strip() or len(value)>256 or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('无效屏幕上下文')
 # Lua quoted strings share these two escapes with JSON; reject controls above.
 return json.dumps(value,ensure_ascii=False)
def output_guard(output):
 return 'assert(type(hl.get_active_monitor)=="function","capability-unavailable"); local m=hl.get_active_monitor(); assert(m and m.name=='+output_literal(output)+',"context-changed"); '
def execute_script(script):
 try:
  result=subprocess.run(['hyprctl','eval',script],capture_output=True,text=True,timeout=5)
  if result.returncode==0 and result.stdout.strip()=='ok':return {'ok':True,'reason_code':'','reason':''}
  code=next((code for code in ('capability-unavailable','context-changed','window-changed') if code in result.stdout),'action-failed')
 except (OSError,subprocess.SubprocessError):code='action-unavailable'
 reasons={'capability-unavailable':'桌面接口不支持此操作','context-changed':'操作屏幕已变化，请重新打开','window-changed':'窗口已变化，请重新打开'}
 return {'ok':False,'reason_code':code,'reason':reasons.get(code,'操作未完成，请重新打开菜单')}
def window_script(action,target,workspace=None,output=None):
 if not isinstance(target,dict):raise ValueError('窗口无效')
 address=target.get('address','');pid=target.get('pid')
 if not isinstance(address,str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,16}',address) or int(address,16)==0 or type(pid)!=int or pid<=0:raise ValueError('窗口无效')
 expressions={'maximize':'hl.dsp.window.fullscreen({mode="maximized"})','float':'hl.dsp.window.float({action="toggle"})','hide':'hl.dsp.window.move({workspace="special:tablet",follow=false})','center':'hl.dsp.window.center()','close':'hl.dsp.window.close()'}
 if action=='move':expression='hl.dsp.window.move({workspace="'+str(workspace_id(workspace))+'"})'
 elif action in expressions:expression=expressions[action]
 else:raise ValueError('未知窗口操作')
 return output_guard(output)+f'local w=hl.get_active_window(); assert(w and w.address=="{address}" and w.pid=={pid} and w.active,"window-changed"); hl.dispatch({expression})'
def snapshot():
 budget=ReadBudget()
 try:
  check_lock(read_json(['omarchy-shell','lock','isLocked'],budget))
  output_name=focused_output(read_json(['hyprctl','monitors','-j'],budget))
  active=read_json(['hyprctl','activewindow','-j'],budget);target=window_identity(active)
  current=workspace(read_json(['hyprctl','activeworkspace','-j'],budget))
  counts=workspace_counts(read_json(['hyprctl','clients','-j'],budget))
  after=window_identity(read_json(['hyprctl','activewindow','-j'],budget))
  output_after=focused_output(read_json(['hyprctl','monitors','-j'],budget))
  check_lock(read_json(['omarchy-shell','lock','isLocked'],budget))
  budget.timeout()
  if target!=after or output_name!=output_after:raise ReadError('context-changed')
  return {'ok':True,'reason_code':'','output':output_name,'target':target,'windowLabel':active.get('class','') or '当前没有应用窗口','current':current,'workspaces':[{'id':i,'count':counts[i]} for i in counts],'bindings':load_bindings(),'labels':LABELS}
 except ReadError as error:
  reasons={'locked':'设备已锁屏','lock-unknown':'锁屏状态未知','output-unavailable':'无法确定操作屏幕','context-changed':'操作目标已变化，请重新打开','timeout':'读取超时，请重试','invalid-data':'桌面数据无效','read-failed':'无法读取桌面'}
  return {'ok':False,'reason_code':error.code,'reason':reasons.get(error.code,'无法读取桌面')}
def action(request):
 context=request.get('context')
 try:
  expected=context.get('output') if isinstance(context,dict) else None
  guard=output_guard(expected)
 except ValueError:return {'ok':False,'reason_code':'context-changed','reason':'缺少有效屏幕上下文，请重新打开菜单'}
 if not unlocked():return {'ok':False,'reason_code':'locked-or-unknown','reason':'锁屏或状态未知，操作已取消'}
 name=request.get('action')
 if name=='switch':return execute_script(guard+'hl.dispatch(hl.dsp.focus({workspace="'+str(workspace_id(request.get('workspace')))+'"}))')
 if name=='restore':return execute_script(guard+'hl.dispatch(hl.dsp.workspace.toggle_special("tablet"))')
 if name in ('maximize','float','hide','center','close','move'):
  return execute_script(window_script(name,request.get('target'),request.get('workspace'),expected))
 # App/config handoff crosses processes: recheck, but never claim atomic dispatch.
 try:
  budget=ReadBudget()
  if focused_output(read_json(['hyprctl','monitors','-j'],budget))!=expected:raise ReadError('context-changed')
  actual=window_identity(read_json(['hyprctl','activewindow','-j'],budget))
  if actual!=request.get('target'):raise ReadError('context-changed')
  check_lock(read_json(['omarchy-shell','lock','isLocked'],budget))
 except ReadError as error:return {'ok':False,'reason_code':error.code,'reason':'操作上下文已变化或不可用，请重新打开菜单'}
 if name=='bindings':save_bindings(CONFIG,request.get('bindings'));return {'ok':True,'bindings':load_bindings()}
 if name=='defaults':save_bindings(CONFIG,DEFAULTS);return {'ok':True,'bindings':load_bindings()}
 if name in ('keyboard','voice','control-center'):ok=run(COMMANDS[name])
 elif name=='browser':ok=run(['omarchy','launch','browser'])
 elif name=='files':ok=run(['omarchy','launch','nautilus'])
 elif name=='launcher':ok=run(['omarchy','menu','summon','apps'])
 else:raise ValueError('未知操作')
 return {'ok':ok,'reason_code':'' if ok else 'handoff-failed','reason':'' if ok else '操作未完成，请重试'}
def main():
 try:
  args=sys.argv[1:]
  if args==['snapshot']:
   def cancelled(signum,frame):raise SystemExit(128+signum)
   previous=signal.signal(signal.SIGTERM,cancelled)
   try:result=snapshot()
   finally:signal.signal(signal.SIGTERM,previous)
  elif len(args)==2 and args[0]=='key':result={'ok':key_action(args[1])}
  elif args==['action']:
   raw=sys.stdin.read(8193)
   if len(raw)>8192:raise ValueError('请求过长')
   request=json.loads(raw)
   if not isinstance(request,dict):raise ValueError('无效请求')
   result=action(request)
  else:raise ValueError('未知入口')
 except (OSError,ValueError,TypeError) as error:result={'ok':False,'reason':str(error)}
 print(json.dumps(result,ensure_ascii=False));return 0 if result.get('ok') else 1
if __name__=='__main__':raise SystemExit(main())
