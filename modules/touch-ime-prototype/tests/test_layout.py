"""Render the actual panel layout in Qt's offscreen test window."""
from pathlib import Path
import tempfile, subprocess, shutil, os, json
root=Path(__file__).resolve().parents[1]
source=(root/'qml/TouchIme.qml').read_text()
a=source.index('        ColumnLayout {'); opening=source.index('{',a);depth=1;b=opening+1
while depth:
    if source[b]=='{':depth+=1
    if source[b]=='}':depth-=1
    b+=1
layout=source[a:b]
prefix='''import QtQuick
import QtQuick.Layouts
import QtTest
Item {
 id: root; width:440; height:829
 property var state: ({})
 property bool uppercase:false
 property bool settingsOpen:false
 property int keyHeight:56
 property bool inputActive:true
 property color bg:"#202020"
 property color fg:"#eeeeee"
 property color buttonBg:"#303030"
 property color accent:"#4466aa"
 function send(action) {}
 function key(name) {}
 function mode(name) {}
'''
tests='''
 TestCase {
  name:"PanelLayout"; when:windowShown
  function test_modes_data() { return [{tag:"t9"},{tag:"pinyin"},{tag:"abc"},{tag:"number"},{tag:"symbols"},{tag:"handwriting"}] }
  function test_settings_fit() {
   root.settingsOpen=true;root.state={visible:true,focused:true,mode:"abc",voicePhase:"idle",candidates:[]};wait(50)
   verify(inputLayout.implicitHeight<=inputLayout.height)
   root.settingsOpen=false
  }
  function test_reach() {
   root.state={visible:true,focused:true,mode:"t9",voicePhase:"idle",preedit:"64426",candidates:["你好","拟稿","米高","你好啊","你好呀","你好么"],page:0,lastPage:false};wait(50)
   var c=findChild(inputLayout,"candidateArea"), k=findChild(inputLayout,"t9Keys")
   verify(c!==null && k!==null,"candidate and keys need measurable reachable groups")
   var cp=c.mapToItem(inputLayout,0,c.height), kp=k.mapToItem(inputLayout,0,0)
   verify(kp.y-cp.y>=0 && kp.y-cp.y<=12,"candidates must touch keyboard area")
   verify(findChild(inputLayout,"editToolbar")!==null,"copy/paste toolbar required")
  }
  function test_new_controls() {
   root.state={visible:true,focused:true,mode:"abc",voicePhase:"idle",candidates:[]}
   wait(50)
   var digits=findChild(inputLayout,"digitRow")
   verify(digits!==null,"ABC needs number row")
   verify(digits.visible)
   root.state={visible:true,focused:true,mode:"t9",voicePhase:"idle",candidates:[]}
   wait(50)
   var back=findChild(inputLayout,"t9Backspace")
   verify(back!==null,"T9 needs right-side large backspace")
   verify(back.height>=110)
  }
  function test_modes(data) {
   root.state={visible:true,focused:true,generation:1,mode:data.tag,sensitive:false,error:"",editingVoice:false,voicePhase:"idle",voiceText:"这是长语音预览测试。".repeat(100),preedit:(data.tag==="t9"||data.tag==="pinyin")?"64 426":"",candidates:(data.tag==="t9"||data.tag==="pinyin")?["你好","拟稿","米高"]:[],page:0,lastPage:false}
   wait(50)
   verify(inputLayout.implicitHeight<=inputLayout.height,"layout overflow: "+data.tag+" "+inputLayout.implicitHeight+" > "+inputLayout.height)
  }
 }
}
'''
shot=os.environ.get('OMT_LAYOUT_SCREENSHOT')
if shot:
    tests=tests.replace('  function test_settings_fit() {', '  function test_screenshot() {\n   root.settingsOpen=false;root.state={visible:true,focused:true,mode:"t9",voicePhase:"idle",preedit:"64426",candidates:["你好","拟稿","米高","你好啊","你好呀","你好么"],page:0,lastPage:false};wait(100)\n   var saved=false;root.grabToImage(function(result){saved=result.saveToFile('+json.dumps(shot)+');});tryVerify(function(){return saved},2000)\n  }\n  function test_settings_fit() {')
with tempfile.TemporaryDirectory(prefix='omt-layout-') as tmp:
    tmp=Path(tmp)
    for f in (root/'qml').glob('*.qml'): shutil.copy2(f,tmp/f.name)
    (tmp/'tst_layout.qml').write_text(prefix+layout+tests)
    subprocess.run(['/usr/lib/qt6/bin/qmltestrunner','-platform','offscreen','-input',str(tmp/'tst_layout.qml')],check=True)
