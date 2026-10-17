#!/usr/bin/python3
"""Tablet navigation and key actions. Fixed actions only, no shell evaluation."""
import json,os,re,subprocess,sys,tempfile
from pathlib import Path
DEFAULTS={'P1':'keyboard','P2':'voice','P3':'authorize','rotation':'navigation'}
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
def window_script(action,target,workspace=None):
 if not isinstance(target,dict):raise ValueError('窗口无效')
 address=target.get('address','');pid=target.get('pid')
 if not isinstance(address,str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,16}',address) or int(address,16)==0 or type(pid)!=int or pid<=0:raise ValueError('窗口无效')
 expressions={'maximize':'hl.dsp.window.fullscreen({mode="maximized"})','float':'hl.dsp.window.float({action="toggle"})','hide':'hl.dsp.window.move({workspace="special:tablet",follow=false})','center':'hl.dsp.window.center()','close':'hl.dsp.window.close()'}
 if action=='move':expression='hl.dsp.window.move({workspace="'+str(workspace_id(workspace))+'"})'
 elif action in expressions:expression=expressions[action]
 else:raise ValueError('未知窗口操作')
 return f'local w=hl.get_active_window(); assert(w and w.address=="{address}" and w.pid=={pid} and w.active,"window changed"); hl.dispatch({expression})'
def snapshot():
 if not unlocked():return {'ok':False,'reason':'锁屏或状态未知'}
 try:
  active=json.loads(output(['hyprctl','activewindow','-j']));work=json.loads(output(['hyprctl','activeworkspace','-j']));clients=json.loads(output(['hyprctl','clients','-j']))
 except (ValueError,TypeError):return {'ok':False,'reason':'无法读取桌面'}
 counts={i:0 for i in range(1,11)}
 for client in clients:
  ws=client.get('workspace',{}).get('id');
  if ws in counts:counts[ws]+=1
 return {'ok':True,'target':{'address':active.get('address',''),'pid':active.get('pid',0)},'windowLabel':active.get('class','') or '当前没有应用窗口','current':work.get('id'),'workspaces':[{'id':i,'count':counts[i]} for i in counts],'bindings':load_bindings(),'labels':LABELS}
def action(request):
 if not unlocked():return {'ok':False,'reason':'锁屏或状态未知，操作已取消'}
 name=request.get('action')
 if name=='bindings':save_bindings(CONFIG,request.get('bindings'));return {'ok':True,'bindings':load_bindings()}
 if name=='defaults':save_bindings(CONFIG,DEFAULTS);return {'ok':True,'bindings':load_bindings()}
 if name=='switch':ok=run(['hyprctl','dispatch','hl.dsp.focus({workspace="'+str(workspace_id(request.get('workspace')))+'"})'])
 elif name=='restore':ok=run(['hyprctl','dispatch','hl.dsp.workspace.toggle_special("tablet")'])
 elif name in ('maximize','float','hide','center','close','move'):ok=run(['hyprctl','eval',window_script(name,request.get('target'),request.get('workspace'))])
 elif name in ('keyboard','voice','control-center'):ok=run(COMMANDS[name])
 elif name=='browser':ok=run(['omarchy','launch','browser'])
 elif name=='files':ok=run(['omarchy','launch','nautilus'])
 elif name=='launcher':ok=run(['omarchy','menu','summon','apps'])
 else:raise ValueError('未知操作')
 return {'ok':ok,'reason':'' if ok else '操作未完成；窗口可能已改变，请重新打开菜单'}
def main():
 try:
  args=sys.argv[1:]
  if args==['snapshot']:result=snapshot()
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
