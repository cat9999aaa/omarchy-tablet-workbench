#!/usr/bin/env python3
"""Exercise the actual ModeSession Process lifecycle with synthetic children."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile


def main():
    source = Path(__file__).parent
    with tempfile.TemporaryDirectory(prefix='mode-transport-') as folder:
        root = Path(folder)
        for name in ('ModeSession.qml', 'ModeProtocol.js'):
            shutil.copy2(source/name, root/name)
        evidence = dict(schema_version=1, complete=True, health='observed', reason_code='observed',
                        physical_keyboard_present=True, touch_present=True, tablet_switch_capability=False,
                        excluded_virtual_count=0, unclassified_keyboard_count=0, sample_duration_ms=1)
        result = dict(schema_version=1, evidence=evidence, mode=dict(effective='desktop',health='observed',
                      reason_code='stable',pending=dict(target='desktop',since_ms=0,last_seen_ms=500)),confirm_after_ms=None)
        fixture = '''import json,os,sys,time,signal
from pathlib import Path
root=Path(__file__).parent
kind,name=sys.argv[1:]
with (root/'pids').open('a') as f:f.write(str(os.getpid())+'\\n')
def notice(event,seq):print(json.dumps(dict(schema_version=1,event=event,seq=seq)),flush=True)
if kind=='observer':
 if name=='exit-before-ready':raise SystemExit(1)
 notice('ready',0)
 if name=='ready-lost':time.sleep(.02);notice('lost',1);raise SystemExit(1)
 if name in ('changed','late'):
  deadline=time.monotonic()+3
  while not (root/('calls-'+name)).exists():
   if time.monotonic()>deadline:raise SystemExit(2)
   time.sleep(.005)
  notice('changed',1)
 time.sleep(30)
else:
 raw=json.load(sys.stdin)
 if name in ('late','changed'):signal.signal(signal.SIGTERM,signal.SIG_IGN)
 p=root/('calls-'+name)
 count=int(p.read_text())+1 if p.exists() else 1;p.write_text(str(count))
 response=RESULT
 if name in ('cancel','timeout'):time.sleep(30)
 if name in ('late','changed'):
  signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(.3)
  if count==1:response['mode']['effective']='tablet'
 if name=='paused':
  consumer=os.getppid();os.kill(consumer,signal.SIGSTOP)
  time.sleep(3);os.kill(consumer,signal.SIGCONT)
 if name=='truncated':print('{');raise SystemExit()
 if name=='oversize':print('x'*65537);raise SystemExit()
 if name=='bounded':response['mode']['health']='unknown';response['mode']['reason_code']='debouncing';response['confirm_after_ms']=1
 print(json.dumps(response),flush=True)
 if name=='nonzero':raise SystemExit(1)
'''.replace('RESULT',repr(result))
        (root/'fixture.py').write_text(fixture)
        qml = '''import QtQuick
import Quickshell
ShellRoot {
 id:root
 property var cases:["success","nonzero","truncated","oversize","ready-lost","exit-before-ready","cancel","timeout","late","changed","bounded","paused"]
 property int index:0
 property int ticks:0
 property bool closing:false
 property bool intervened:false
 property var suggestions:[]
 property int maxSamples:0
 ModeSession {id:session;onModeSuggested:mode=>{root.suggestions=root.suggestions.concat([mode])}}
 function bad(reason){console.log("MODE_FAILED "+cases[index]+" "+reason);Qt.quit()}
 function start(){
  ticks=0;closing=false;intervened=false;suggestions=[];maxSamples=0
  const script=Qt.resolvedUrl("fixture.py").toString().replace("file://","")
  session.observerCommand=["python3",script,"observer",cases[index]]
  session.sampleCommand=["python3",script,"sample",cases[index]]
  if(!session.begin(true,"auto","tablet"))bad("begin")
 }
 Component.onCompleted:start()
 Timer {interval:20;running:true;repeat:true;onTriggered:{
  root.ticks++;root.maxSamples=Math.max(root.maxSamples,session.samplesUsed)
  const name=root.cases[root.index]
  if(root.ticks>500){root.bad("deadline "+session.health+" "+session.reason+" samples="+session.samplesUsed+" dirty="+session.dirty+" request="+(session.request!==null)+" ready="+session.observerReady);return}
  if(!root.intervened && (name==="late" || name==="cancel") && session.request!==null && (name!=="late" || session.observerSeq===1)) {
   root.intervened=true
   if(name==="late")session.choose("desktop");else session.close()
   if(session.begin(true,"auto","tablet")){root.bad("overlap");return}
  }
  if(!root.closing){
   let done=false
   if(name==="success")done=session.health==="observed"
   else if(name==="late")done=root.intervened && session.isStopped
   else if(name==="cancel")done=root.intervened && session.isStopped
   else if(name==="changed")done=session.health==="observed" && session.lastEffective==="desktop"
   else if(name==="bounded")done=session.samplesUsed===4 && !session.busy
   else done=session.health==="unavailable"
   if(!done)return
   if(["success","changed","late"].indexOf(name)>=0) {
    if(root.suggestions.length!==1 || root.suggestions[0]!=="desktop"){root.bad("stale-suggestion");return}
   } else if(root.suggestions.length!==0){root.bad("unexpected-suggestion");return}
   root.closing=true;session.close()
  }
  if(session.isStopped){
   console.log("MODE_PASSED "+name+" samples="+root.maxSamples)
   root.index++;if(root.index===root.cases.length){console.log("MODE_COMPLETE");Qt.quit()}else root.start()
  }
 }}
}
'''
        (root/'shell.qml').write_text(qml)
        result = subprocess.run(['qs','-p',str(root/'shell.qml')],capture_output=True,text=True,timeout=35)
        text = result.stdout+result.stderr
        print(text[-8000:])
        assert result.returncode == 0 and 'MODE_COMPLETE' in text and 'MODE_FAILED' not in text
        for name in ('success','nonzero','truncated','oversize','ready-lost','exit-before-ready','cancel','timeout','late','changed','bounded','paused'):
            assert 'MODE_PASSED '+name+' ' in text, name
        assert (root/'calls-bounded').read_text() == '4'
        assert (root/'calls-changed').read_text() == '2'
        assert not (root/'calls-ready-lost').exists()
        assert not (root/'calls-exit-before-ready').exists()
        for pid in (root/'pids').read_text().splitlines():
            try:
                os.kill(int(pid),0)
            except ProcessLookupError:
                continue
            raise AssertionError('test-owned child remains: '+pid)
        print('12 real mode transport cases passed; all child PIDs reaped')


if __name__=='__main__':
    main()
