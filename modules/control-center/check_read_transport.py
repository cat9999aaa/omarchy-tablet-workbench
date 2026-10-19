"""Optional Quickshell integration check with synthetic subprocesses only.
Run on a disposable host providing qs; ordinary Qt CI uses ContractState tests.
"""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

root=Path(__file__).resolve().parent
source=(root/'Panel.qml').read_text();a=source.index(' Component {\n  id: readRequest');b=source.index('{',a)+1;depth=1
while depth:
    if source[b]=='{':depth+=1
    if source[b]=='}':depth-=1
    b+=1
component=source[a:b]
def envelope(kind):
    t=kind=='temperature'
    return dict(contract_version='0.1.0',capability_id='dashen.device.'+('temperature' if t else 'touch-mode'),resource_id='thermal-summary' if t else 'touch-mode',output_id='local',read_permission='device.temperature.read' if t else 'device.touch-mode.read',state=dict(available=True,actual=0,health='observed',boot_default=1))
response=dict(schema_version=1,legacy=dict(locked=False),contracts=dict(version='0.1.0',status='ok',states=[envelope('temperature'),envelope('touch')]))
with tempfile.TemporaryDirectory(prefix='contract-transport-') as tmp:
    p=Path(tmp)
    for name in ('ContractModel.js','ContractState.qml'):shutil.copy2(root/name,p/name)
    payload=repr(json.dumps(response))
    scripts={'success':f'print({payload})', 'nonzero':f'print({payload});raise SystemExit(1)', 'huge':'print("中"*24000)', 'truncated':'print("{")', 'locked':f'print({repr(json.dumps({**response,"legacy":{"locked":True}}))})', 'cancel':'import time;time.sleep(30)', 'timeout':'import time;time.sleep(30)', 'partial_timeout':f'import time,signal,sys;signal.signal(signal.SIGTERM,lambda *args:(print({payload},flush=True),sys.exit(0)));print("{{",flush=True);time.sleep(30)', 'complete_text_timeout':f'import time;print({payload},flush=True);time.sleep(30)'}
    for name,body in scripts.items():(p/(name+'.py')).write_text(body)
    qml='''import QtQuick
import Quickshell
import Quickshell.Io
import "ContractModel.js" as ContractModel
ShellRoot {
 id:root
 property var activeRead:null
 property string helper:""
 property string feedback:""
 property var data:({})
 property int index:0
 property var cases:["success","nonzero","huge","truncated","locked","cancel","timeout","partial_timeout","complete_text_timeout"]
 ContractState {id:readings}
 function close(){readings.closeSession();if(activeRead)activeRead.cancelRead()}
 function start(){
  readings.beginOpen();helper=Qt.resolvedUrl(cases[index]+".py").toString().replace("file://","")
  readings.accept(readings.startRequest(),GOOD_RESPONSE)
  activeRead=readRequest.createObject(root,{requestToken:readings.startRequest()});activeRead.running=true
  if(cases[index]==="cancel")cancelLater.start()
 }
 Component.onCompleted:start()
 Timer {id:cancelLater;interval:30;onTriggered:root.close()}
 Timer {interval:20;running:true;repeat:true;onTriggered:{
  if(root.activeRead!==null)return
  const name=root.cases[root.index]
  const keepHistory=name==="timeout" || name==="nonzero"
  if(name==="success" ? !readings.ready || readings.temperatureText!=="0 °C" : readings.ready || (keepHistory ? !readings.temperatureDisplay.historical : readings.temperatureText.indexOf("°C")>=0)){console.log("TRANSPORT_FAILED "+name);Qt.quit();return}
  console.log("TRANSPORT_PASSED "+name)
  root.index++;if(root.index===root.cases.length){Qt.quit();return}root.start()
 }}
'''+component+'\n}\n'
    (p/'shell.qml').write_text(qml.replace('GOOD_RESPONSE',json.dumps(response)))
    result=subprocess.run(['qs','-p',str(p/'shell.qml')],capture_output=True,text=True,timeout=85)
    output=result.stdout+result.stderr
    print(output[-5000:])
    assert result.returncode==0,result.returncode
    assert 'TRANSPORT_FAILED' not in output
    for name in scripts:assert 'TRANSPORT_PASSED '+name in output,name
