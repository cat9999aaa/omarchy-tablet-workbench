#!/usr/bin/env python3
"""Run Panel's routing/settings/lifecycle methods on real headless QsWindow slots.
Focus, device/lock responses and the bar icon are synthetic. Slot dimensions
follow the official host's implicit-size contract, not a fixed fixture size.
"""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import tempfile
from check_output_attachment import main as attachment_check

root = Path(__file__).parent
source = (root/'Panel.qml').read_text()
def block(marker):
    start=source.index(marker);end=source.index('{',start)+1;depth=1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[start:end]

# The periodic reader remains distinct; only user-triggered routes restart mode.
assert 'deviceMode.refresh' not in block(' function refresh(')
assert 'onTriggered:root.refresh()' in source

with tempfile.TemporaryDirectory(prefix='ownership-fixture-') as folder:
    temp=Path(folder)
    helper=temp/'fixture.py'
    helper.write_text('''import json,sys,time,signal,os,fcntl
from pathlib import Path
root=Path(__file__).parent
op=sys.argv[1]
if op=='observer':
 # A destroyed QML owner may SIGKILL; record kernel-confirmed exit before retry.
 events=root/'events';active=set()
 if events.exists():
  for row in events.read_text().splitlines():
   event,pid=row.split()
   if event=='start':active.add(pid)
   else:active.discard(pid)
 for pid in active:
  try:os.kill(int(pid),0)
  except ProcessLookupError:
   with events.open('a') as f:f.write('end '+pid+'\\n')
 with events.open('a') as f:f.write('start '+str(os.getpid())+'\\n')
 def stop(*a):
  time.sleep(.2)
  with (root/'events').open('a') as f:f.write('end '+str(os.getpid())+'\\n')
  raise SystemExit()
 signal.signal(signal.SIGTERM,stop)
 print('{"schema_version":1,"event":"ready","seq":0}',flush=True)
 time.sleep(30)
elif op=='prepare-open':print('{"ok":true}')
elif op=='mode-preference-read':
 d=json.load(sys.stdin);p=root/('choice-'+d['output_key']);print(json.dumps(dict(schema_version=1,choice=p.read_text() if p.exists() else 'auto',reason_code='ok')))
elif op=='mode-preference-write':
 d=json.load(sys.stdin)
 # Keep an auto-mode save pending when its output is removed.
 if d['choice']=='auto':time.sleep(1)
 if d['choice']=='desktop':print('{"schema_version":1,"saved":false}')
 else:(root/('choice-'+d['output_key'])).write_text(d['choice']);print('{"schema_version":1,"saved":true}')
elif op=='output-policy':json.load(sys.stdin);print('{"schema_version":1,"eligible":true}')
elif op=='mode-step':json.load(sys.stdin);time.sleep(30)
''')
    a=source.index(' property int routeEpoch:');b=source.index(' ContractState {',a)
    declarations=source[a:b]
    intrinsic='\n'.join(line for line in source.splitlines()
                        if line.startswith((' implicitWidth:', ' implicitHeight:')))
    declarations=declarations.replace('observerCommand:[Qt.resolvedUrl("bin/pcadmin-device-observer").toString().replace("file://","")]','observerCommand:["python3",root.helper,"observer"]')
    declarations=declarations.replace('function focusedTarget() {return targetFor(Hyprland.focusedMonitor?Hyprland.focusedMonitor.name:"")}','function focusedTarget() {return targetFor(harness.focusName)}')
    fixture='''import QtQuick
import Quickshell
import Quickshell.Io
import "OutputRoute.js" as OutputRoute
import "ModeProtocol.js" as ModeProtocol
ShellRoot {
 id:harness
 property var slots:[]
 property string focusName:"HEADLESS-1"
 property var first:null
 property var second:null
 property int phase:0
 property int ticks:0
 function check(ok,name){if(!ok){console.log("B2_FAIL:"+name);Qt.quit();return false}console.log("B2_PASS:"+name);return true}
 QtObject {id:barApi;function moduleWidgets(id){return harness.slots.filter(s=>s!==null&&s.mode!==undefined)}}
 Component {
  id:ownerFactory
  Item {
   id:root;width:implicitWidth;height:implicitHeight
   Item {id:barButton;anchors.fill:parent;implicitWidth:40;implicitHeight:32}
   property var bar:barApi
   property string moduleName:"pcadmin.control-center"
   property var activeRead:null
   property bool wantOpen:false
   property bool allowed:false
   property bool expanded:false
   property string feedback:""
   property var confirmation:null
   property string helper:Qt.resolvedUrl("fixture.py").toString().replace("file://","")
   property alias mode:deviceMode
   property alias controller:control
   readonly property bool opened:control.open
   QtObject {id:control;property bool open:false;function show(){open=true}function hide(){open=false}}
   ContractState {id:readings}
   function refresh(){}
'''+intrinsic+'\n'+declarations+'\n'+ '\n'.join(block(' function '+name+'(') for name in ['refreshFromUser','open','toggle','closeInternal','close','gesture'])+'\n'+block(' Process {\n  id: opener')+'\n'+block(' Component {\n  id:settingsRequest')+'''
  }
 }
 Variants {
  model:Quickshell.screens
  PanelWindow {
   id:barWindow;required property var modelData;screen:modelData
   anchors {top:true;left:true;right:true}
   implicitHeight:48
   Component.onCompleted:{const item=ownerFactory.createObject(contentItem);harness.slots=harness.slots.concat([item])}
  }
 }
 Timer {interval:20;running:true;repeat:true;onTriggered:{
  harness.ticks++;if(harness.ticks>850){harness.check(false,"timeout phase="+harness.phase+" first="+(harness.first?JSON.stringify({opened:harness.first.opened,want:harness.first.wantOpen,health:harness.first.mode.health,reason:harness.first.mode.reason,choice:harness.first.modeChoice,feedback:harness.first.feedback}):"gone"));return}
  const live=harness.slots.filter(s=>s!==null&&s.mode!==undefined)
  if(live.filter(s=>s.mode.observer!==null).length>1){harness.check(false,"observer-overlap");return}
  if(live.filter(s=>s.opened).length>1){harness.check(false,"window-overlap");return}
  if(harness.phase===0 && live.length===2 && live.every(s=>s.attachedScreen)) {
   harness.first=live.find(s=>s.attachedScreen.name==="HEADLESS-1");harness.second=live.find(s=>s.attachedScreen.name==="HEADLESS-2")
   if(!harness.check(harness.first!==null&&harness.second!==null,"attachment"))return
   if(!harness.check(harness.first.attachedScreen!==harness.second.attachedScreen,"two-outputs"))return
   if(!harness.check(live.every(s=>s.width===40&&s.height===32),"host-intrinsic-size"))return
   const dup=ownerFactory.createObject(harness.first.parent);harness.slots=harness.slots.concat([dup])
   if(!harness.check(harness.first.focusedTarget()===null,"ambiguous"))return
   dup.destroy();harness.phase=1
  }else if(harness.phase===1 && live.length===2){harness.second.route("open");harness.phase=2}
  else if(harness.phase===2 && harness.first.mode.observerReady) {
   if(!harness.check(harness.first.opened&&!harness.second.opened,"ipc-target"))return
   harness.second.open();harness.phase=3
  }else if(harness.phase===3 && harness.second.mode.observerReady) {
   if(!harness.check(!harness.first.opened&&harness.first.mode.isStopped,"transfer-reaped"))return
   harness.first.route("close");harness.phase=4
  }else if(harness.phase===4 && live.every(s=>s.mode.isStopped)) {
   if(!harness.check(!harness.second.opened,"close-current"))return
   harness.second.open();harness.phase=5
  }else if(harness.phase===5 && harness.second.mode.observerReady) {
   harness.first.route("gesture")
   if(!harness.check(harness.second.expanded&&harness.second.opened,"legacy-gesture"))return
   harness.second.mode.fail("observer_lost");harness.phase=51
  }else if(harness.phase===51 && harness.second.mode.isStopped) {
   const epoch=harness.second.mode.generation
   harness.second.refresh()
   if(!harness.check(harness.second.mode.generation===epoch,"periodic-no-restart"))return
   harness.first.route("gesture")
   if(!harness.check(harness.second.mode.generation>epoch,"explicit-refresh-generation"))return
   harness.phase=52
  }else if(harness.phase===52 && harness.second.mode.observerReady) {
   if(!harness.check(harness.second.opened,"explicit-refresh-recovered"))return
   harness.second.selectMode("tablet");harness.phase=7
  }else if(harness.phase===7 && harness.second.mode.isStopped && harness.second.modeSaved) {
   harness.second.close();harness.phase=8
  }else if(harness.phase===8 && harness.second.mode.isStopped && !harness.second.opened) {
   harness.second.open();harness.phase=9
  }else if(harness.phase===9 && harness.second.opened && harness.second.modeInitialized) {
   if(!harness.check(harness.second.modeChoice==="tablet"&&harness.second.mode.lastEffective==="tablet"&&harness.second.mode.isStopped,"manual-reopen"))return
   harness.second.selectMode("desktop");harness.phase=10
  }else if(harness.phase===10 && harness.second.activeSettings===null) {
   if(!harness.check(!harness.second.modeSaved&&harness.second.mode.lastEffective==="desktop","save-failure-session"))return
   harness.second.selectMode("auto");harness.phase=11
  }else if(harness.phase===11 && harness.second.mode.observerReady) {
   harness.first.open();harness.phase=6;console.log("B2_READY_REMOVE")
  }else if(harness.phase===6 && Quickshell.screens.length===1 && !harness.first.transferPending) {
   if(!harness.check(harness.second===null||!harness.second.opened,"destroy"))return
   if(!harness.check(harness.first!==null&&!harness.first.opened&&harness.first.mode.isStopped,"no-migration"))return
   harness.first.open();harness.phase=12
  }else if(harness.phase===12 && harness.first.modeInitialized) {
   if(!harness.check(harness.first.modeChoice==="auto","output-preferences-isolated"))return
   harness.phase=121
  }else if(harness.phase===121 && harness.first.mode.observerReady) {
   if(!harness.check(harness.first.opened,"retry-after-destroy"))return
   harness.first.close();harness.phase=13
  }else if(harness.phase===13 && harness.first.mode.isStopped) {
   console.log("B2_COMPLETE");Qt.quit()
  }
 }}
}
'''
    path=temp/'ownership.qml';path.write_text(fixture)
    attachment_check(path,[helper,*[root/n for n in ('ModeSession.qml','ModeProtocol.js','ContractState.qml','ContractModel.js')]],
                     ['host-intrinsic-size','ipc-target','transfer-reaped','close-current','legacy-gesture','manual-reopen','save-failure-session','retry-after-destroy','output-preferences-isolated','periodic-no-restart','explicit-refresh-recovered'],verify_children=True)
