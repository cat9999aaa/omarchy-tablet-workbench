"""Actual Navigation.qml + IPC under isolated dual-output sway.

Device commands are synthetic; screen/window lifecycle is real Quickshell.
This does not claim Hyprland action or physical touchscreen acceptance.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/themes'))
from render_support import compositor

FIXTURE = '''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 Navigation {id:nav}
 IpcHandler {
  target:"testNavigation"
  function surface():string{return JSON.stringify({screen:nav.boundScreen?nav.boundScreen.name:null,width:nav.boundScreen?nav.boundScreen.width:0})}
  function action():void{nav.act("browser")}
 }
}
'''
HELPER = '''import json,os,time,sys
from pathlib import Path
root=Path(__file__).parent
if sys.argv[1]=='action':
 sys.stdin.read();time.sleep(1.3);print('{"ok":true}');sys.exit()
(root/'reader-pid').write_text(str(os.getpid()))
mode=(root/'mode').read_text()
time.sleep(.4 if mode!='slow' else 2)
value={'ok':True,'output':'HEADLESS-2','target':None,'workspaces':[],'bindings':{},'labels':{}}
if mode=='changed':value={'ok':False,'reason_code':'context-changed'}
if mode=='missing':value['output']='HEADLESS-missing'
print(json.dumps(value))
'''

def wait_for(fn,label,timeout=5):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if fn():return
  time.sleep(.05)
 raise AssertionError(label)

def main():
 if os.environ.get('C1_ISOLATED_TEST')!='1':raise RuntimeError('isolated namespace required')
 source=Path(__file__).resolve().parent
 with tempfile.TemporaryDirectory(prefix='navigation-session-') as temp:
  root=Path(temp)
  for name in ['Navigation.qml','NavigationSession.js']:shutil.copy2(source/name,root/name)
  shutil.copytree(source/'Workbench',root/'Workbench')
  shutil.copytree('/official/Commons',root/'Commons')
  (root/'Commons/qmldir').write_text('module qs.Commons\n'+''.join('singleton '+n+' 1.0 '+n+'.qml\n' for n in ['Color','Style','Util','Border']))
  (root/'Test.qml').write_text(FIXTURE)
  helper=root/'helper.py';helper.write_text(HELPER)
  mode=root/'mode';mode.write_text('normal')
  binpath=root/'bin';binpath.mkdir()
  lock=binpath/'omarchy-shell';lock.write_text('#!/usr/bin/python3\nfrom pathlib import Path\np=Path(__file__).parent.parent/"locked"\nprint("true" if p.exists() else "false")\n');lock.chmod(0o755)
  with compositor(root) as env:
   env['SWAYSOCK']=str(next((root/'runtime').glob('sway-ipc.*.sock')))
   def sway(*args):subprocess.run(['swaymsg',*args],env=env,check=True,stdout=subprocess.PIPE,timeout=3)
   sway('create_output');sway('output','HEADLESS-2','resolution','1280x960')
   env.update(PCADMIN_NAVIGATION_HELPER=str(helper),PATH=str(binpath)+':'+env['PATH'])
   with (root/'shell.log').open('w+') as log:
    shell=subprocess.Popen(['qs','-p',str(root/'Test.qml')],env=env,stdout=log,stderr=subprocess.STDOUT)
    def call(method,*args,target='pcadmin.navigation'):
     p=subprocess.run(['qs','ipc','--pid',str(shell.pid),'call',target,method,*args],env=env,capture_output=True,text=True,timeout=3)
     return p.stdout.strip() if p.returncode==0 else None
    def state():return json.loads(call('state') or '{}')
    def opened():return state().get('opened') is True
    try:
     wait_for(lambda:call('ready')=='true','old IPC ready')
     call('open','窗口');wait_for(opened,'open')
     assert json.loads(call('surface',target='testNavigation'))['screen']=='HEADLESS-2'
     public=state();assert set(['version','opened','page','width','height','phase','generation','reason_code'])<=public.keys()
     assert not any(k in public for k in ['output','target','address','pid'])
     print('C2_PASS:second-output-and-old-ipc')
     call('close');mode.write_text('slow');(root/'reader-pid').unlink();call('open','桌面')
     wait_for(lambda:(root/'reader-pid').exists(),'reader started')
     pid=int((root/'reader-pid').read_text());call('close')
     wait_for(lambda:not Path('/proc',str(pid)).exists(),'read process not reaped')
     time.sleep(2.1);assert not opened();print('C2_PASS:cancel-reap-no-reopen')
     mode.write_text('normal');call('open','开始');call('open','按键');wait_for(opened,'new session open');assert state()['page']=='按键'
     call('action',target='testNavigation');call('open','桌面');wait_for(opened,'new session during action');time.sleep(1.4)
     assert opened() and state()['page']=='桌面';print('C2_PASS:late-action-does-not-close-new-session')
     before=json.loads(call('surface',target='testNavigation'))['width'];generation=state()['generation']
     sway('output','HEADLESS-2','scale','2')
     wait_for(lambda:json.loads(call('surface',target='testNavigation'))['width']<before,'same output scale')
     assert opened() and state()['generation']==generation;print('C2_PASS:scale-retains-session')
     sway('output','HEADLESS-2','disable');wait_for(lambda:not opened(),'output removal closes');print('C2_PASS:output-loss-no-migration')
     sway('output','HEADLESS-2','enable');time.sleep(.2)
     mode.write_text('missing');call('open','窗口');time.sleep(.7);assert not opened();print('C2_PASS:unmatched-output-closes')
     mode.write_text('changed');call('open','窗口');wait_for(lambda:state().get('reason_code')=='context-changed','changed focus cancels preparation');assert not opened()
     print('C2_PASS:preparation-context-change')
     mode.write_text('normal');call('toggle','开始');wait_for(opened,'old toggle open');call('toggle','开始');assert not opened()
     call('open','窗口');wait_for(opened,'before lock');(root/'locked').touch();wait_for(lambda:not opened(),'lock closes');print('C2_PASS:lock-closes')
    finally:
     shell.terminate()
     try:shell.wait(timeout=3)
     except subprocess.TimeoutExpired:shell.kill();shell.wait()
     log.seek(0);text=log.read();print(text)
    if any(s in text for s in ['ReferenceError:','TypeError:','Unable to assign','Binding loop','Failed to load']):raise RuntimeError('navigation runtime warnings')
 print('navigation runtime gate passed')
if __name__=='__main__':main()
