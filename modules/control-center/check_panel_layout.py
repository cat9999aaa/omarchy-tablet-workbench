"""Render the actual Panel content with synthetic state, no shell or devices."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parent
source = (root / 'Panel.qml').read_text()
def block(start):
    a = source.index(start); b = source.index('{', a) + 1; depth = 1
    while depth:
        if source[b] == '{': depth += 1
        if source[b] == '}': depth -= 1
        b += 1
    return source[a:b]
layout = block('   ColumnLayout {').replace('Style.font.family', '"sans-serif"').replace('root.data', 'root.snapshot')
button = block(' component CButton:').replace('Style.font.family', '"sans-serif"')
prefix = '''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtTest
import "Workbench" as WB
import "ControlModel.js" as Model
Item {
 id:root;width:640;height:604
 property var snapshot:({brightness:50,power_profile:"balanced",flight_active:false})
 property var flight:({entertainment:false,verified:false})
 property bool expanded:false
 property string page:"设备"
 property string feedback:"状态暂不可用，等待下一次读取。".repeat(20)
 property var confirmation:null
 property bool audioAvailable:false
 property int volume:0
 property bool muted:false
 property var source:null
 property color fg:"#eeeeee"
 property color bg:"#222222"
 property color purple:"#cc88ff"
 property color green:"#cc88ff"
 property color orange:"#ffaa66"
 property var actions:[]
 QtObject {id:window;property int width:root.width;property int height:root.height}
 QtObject {id:actionProcess;property bool running:false}
 ContractState {id:readings}
 function close(){}
 function act(name,params){actions=actions.concat([name])}
 function summary(){return "测试状态"}
 function batteryText(){return "电池状态未知"}
 function labelNetwork(){return "未知"}
 function nightlightLabel(){return "状态待确认"}
 function touchLabel(){return readings.touchText}
 function b(key){return {known:false,value:null,label:"未知"}}
'''
tests = '''
 TestCase {
  name:"ControlPanelLayout";when:windowShown
  function buttons(item,list){if(!item.visible)return;if(item.minimumTouchHeight!==undefined)list.push(item);for(const c of item.children)buttons(c,list)}
  function test_sizes_data(){return [640,480,320].map(w=>({tag:String(w),width:w}))}
  function test_sizes(d){
   root.width=d.width;root.height=604;root.expanded=false;wait(30)
   const touch=findChild(root,"quick-touch-refresh");verify(touch!==null,"touch button missing");verify(touch.visible,"touch button hidden");verify(touch.height>=48,"touch button height "+touch.height)
   mouseClick(touch,touch.width/2,touch.height/2);compare(root.actions[root.actions.length-1],"touch-refresh")
   root.expanded=true;wait(30)
   let all=[];buttons(body,all);verify(all.some(b=>b.text==="刷新触摸模式"))
   for(const b of all){const p=b.mapToItem(root,0,0);verify(p.x>=0 && p.x+b.width<=root.width,"horizontal overflow: "+b.text);verify(b.height>=48,"target height");verify(b.contentItem.paintedWidth<=b.contentItem.width+1,"text width")}
   compare(root.width,d.width);compare(root.height,604)
  }
 }
}
'''
with tempfile.TemporaryDirectory(prefix='control-layout-') as tmp:
    p=Path(tmp);shutil.copytree(root/'Workbench',p/'Workbench')
    for name in ('ControlModel.js','ContractModel.js','ContractState.qml'):
        shutil.copy2(root/name,p/name)
    (p/'tst_layout.qml').write_text(prefix+layout+button+tests)
    runner=shutil.which('qmltestrunner') or next((v for v in ('/usr/lib/qt6/bin/qmltestrunner','/usr/lib/qt6/qmltestrunner') if Path(v).is_file()),'qmltestrunner')
    subprocess.run([runner,'-platform','offscreen','-input',str(p/'tst_layout.qml')],check=True)
