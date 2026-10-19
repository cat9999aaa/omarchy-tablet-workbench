"""Actual task panel in isolated dual-output Quickshell. Synthetic source only."""
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/themes'))
from render_support import compositor
HELPER='''import json,os,sys,time
from pathlib import Path
r=Path(__file__).parent;request=json.load(sys.stdin);cmd=sys.argv[1]
with (r/'calls').open('a') as f:f.write(cmd+'\\n')
(r/'pid').write_text(str(os.getpid()))
if cmd=='action':\n (r/'action-pid').write_text(str(os.getpid()));time.sleep(3);(r/'action-completed').touch()\nif cmd=='snapshot' and (r/'slow').exists():time.sleep(3)
v={'schema':1,'ok':True,'output':'HEADLESS-2','observed_at':'2026-01-01T00:00:00Z','sampled_boottime_ms':int(time.monotonic()*1000),'elapsed_ms':10}
if (r/'locked').exists():v.update(ok=False,reason_code='locked')
elif cmd=='snapshot':v.update(scope='a'*64,rows=[{'agent_id':'00000000-0000-4000-8000-000000000001','status':'idle'}],dnd=False)
elif cmd=='detail':v.update(agent_id=request['agent_id'],detail={'status':'idle','pending_permission_count':2,'source_updated_at':None})
print(json.dumps(v))
'''
def wait(fn,label):
 end=time.monotonic()+6
 while time.monotonic()<end:
  if fn():return
  time.sleep(.05)
 raise AssertionError(label)
def main():
 if os.environ.get('C1_ISOLATED_TEST')!='1':raise RuntimeError('isolated namespace required')
 source=Path(__file__).parent
 assert (source/'TaskCenter.qml').is_file(),'task panel missing'
 with tempfile.TemporaryDirectory(prefix='task-panel-') as tmp:
  root=Path(tmp)
  for n in ['TaskCenter.qml','TaskSession.js']:shutil.copy2(source/n,root/n)
  capture=Path('/evidence/c3-task-panel.png')
  qml=root/'TaskCenter.qml';qml.write_text(qml.read_text().replace('id:root','id:root\n function capture():void{capturePanel.grabToImage(function(r){r.saveToFile("/evidence/c3-task-panel.png")})}',1).replace('  Rectangle{','  Rectangle{id:capturePanel',1))
  shutil.copytree(source/'Workbench',root/'Workbench');shutil.copytree('/official/Commons',root/'Commons')
  (root/'Commons/qmldir').write_text('module qs.Commons\n'+''.join('singleton '+n+' 1.0 '+n+'.qml\n' for n in ['Color','Style','Util','Border']))
  (root/'Main.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot { TaskCenter {id:panel} IpcHandler {target:"testTasks"
function detail():void{panel.detail("00000000-0000-4000-8000-000000000001")}
function action():void{panel.handoff("open-paseo")}
function capture():void{panel.capture()}
function surface():string{return panel.boundScreen?panel.boundScreen.name:""}
}}''')
  helper=root/'helper.py';helper.write_text(HELPER)
  with compositor(root) as env:
   env['SWAYSOCK']=str(next((root/'runtime').glob('sway-ipc.*.sock')))
   def sway(*args):subprocess.run(['swaymsg',*args],env=env,check=True,stdout=subprocess.PIPE,timeout=3)
   sway('create_output');env['PCADMIN_TASK_HELPER']=str(helper)
   with (root/'shell.log').open('w+') as log:
    p=subprocess.Popen(['qs','-p',str(root/'Main.qml')],env=env,stdout=log,stderr=subprocess.STDOUT)
    def call(method,*args,target='pcadmin.tasks'):
     r=subprocess.run(['qs','ipc','--pid',str(p.pid),'call',target,method,*args],env=env,capture_output=True,text=True,timeout=3);return r.stdout.strip() if r.returncode==0 else ''
    def state():return json.loads(call('state') or '{}')
    try:
     wait(lambda:call('ready')=='true','ready');call('open','HEADLESS-2');wait(lambda:state().get('opened'),'open')
     assert call('surface',target='testTasks')=='HEADLESS-2';assert state()['count']==1
     time.sleep(1.2);assert (root/'calls').read_text().splitlines().count('snapshot')==1
     call('detail',target='testTasks');wait(lambda:state().get('needsPermission')==1,'details')
     call('capture',target='testTasks');wait(lambda:capture.exists(),'synthetic capture')
     call('action',target='testTasks');wait(lambda:(root/'action-pid').exists(),'action running');action_pid=int((root/'action-pid').read_text())
     call('close');wait(lambda:not Path('/proc',str(action_pid)).exists(),'action cancelled');assert not (root/'action-completed').exists()
     wait(lambda:state().get('readers')==0,'closed readers');before=(root/'calls').read_text();time.sleep(.8);assert (root/'calls').read_text()==before
     (root/'slow').touch();call('open','HEADLESS-2');time.sleep(.3);call('close');time.sleep(.4);assert not state()['opened'];(root/'slow').unlink()
     call('open','HEADLESS-2');wait(lambda:state().get('opened'),'reopen');(root/'locked').touch();wait(lambda:not state().get('opened'),'lock');(root/'locked').unlink()
     call('open','HEADLESS-2');wait(lambda:state().get('opened'),'before output removal');sway('output','HEADLESS-2','disable');wait(lambda:not state().get('opened'),'output removal')
     print('C3 runtime: output, no source polling, detail, close, cancel, lock, output removal passed')
    finally:
     p.terminate()
     try:p.wait(timeout=3)
     except subprocess.TimeoutExpired:p.kill();p.wait()
     log.seek(0);text=log.read();print(text)
    assert not any(x in text for x in ['TypeError:','ReferenceError:','Unable to assign','Binding loop','Failed to load']),text
if __name__=='__main__':main()
