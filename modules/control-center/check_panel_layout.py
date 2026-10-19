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
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtTest
import "Workbench" as WB
import "Workbench/Theme.js" as Theme
import "ControlModel.js" as Model
import "ControlActions.js" as Actions
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
 property real themeScale:1
 property color themeAccent:"#ffb454"
 property var themeTokens:Theme.resolve({schemaVersion:1,foreground:fg,background:bg,accent:themeAccent,urgent:orange,fontScale:themeScale})
 property var actions:[]
 property string appliedMode:"tablet"
 property string suggestedMode:"tablet"
 property string modeChoice:"auto"
 property bool modeSaved:false
 property bool modeInitialized:true
 property int buttonPressCount:0
 readonly property bool anyPointerPressed:buttonPressCount>0||brightness.pressed||volumeSlider.pressed
 onSuggestedModeChanged:Qt.callLater(applySuggestedMode)
 onAnyPointerPressedChanged:Qt.callLater(applySuggestedMode)
 onConfirmationChanged:Qt.callLater(applySuggestedMode)
 QtObject {id:deviceMode;property string health:"unknown"}
 function selectMode(choice){modeChoice=choice;suggestedMode=choice;modeSaved=false}

 QtObject {id:window;property int width:root.width;property int height:root.height;property var activeFocusItem:root.Window.window?root.Window.window.activeFocusItem:null}
 QtObject {id:actionProcess;property bool running:false;onRunningChanged:Qt.callLater(root.applySuggestedMode)}
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
prefix += block(' function ensureControlVisible(') + block(' function applySuggestedMode(') + block(' function restoreModeFocus(') + block(' function quickView(').replace('data.flight_', 'snapshot.flight_').replace('data.power_profile','snapshot.power_profile')
tests = '''
 TestCase {
  name:"ControlPanelLayout";when:windowShown
  function buttons(item,list){if(!item.visible)return;if(item.minimumTouchHeight!==undefined)list.push(item);for(let i=0;i<item.children.length;i++)buttons(item.children[i],list)}
  function bring(button){wait(30);const y=button.mapToItem(body,0,0).y;scroll.contentY=Math.max(0,Math.min(y,scroll.contentHeight-scroll.height));wait(20)}
  function test_sizes_data(){let rows=[];for(const w of [640,480,320])for(const h of [480,800])for(const mode of ["tablet","desktop"])for(const scale of [1,1.25,1.5])for(const contrast of [false,true])rows.push({tag:w+"x"+h+"-"+mode+"-"+scale+"-"+contrast,width:w,height:h,mode:mode,scale:scale,contrast:contrast});return rows}
  function init(){readings.closeSession();root.themeScale=1;root.themeAccent="#ffb454";root.confirmation=null;actionProcess.running=false;root.flight={entertainment:false,verified:false};root.expanded=false;root.suggestedMode="tablet";root.appliedMode="tablet";wait(30)}
  function test_readout_in_actual_panel_data(){let rows=[];for(const w of [320,480,864,1536])for(const scale of [1,1.25,1.5])for(const light of [false,true])rows.push({tag:w+"-"+scale+"-"+light,w:w,scale:scale,light:light});return rows}
  function test_refresh_cancels_actual_pressed_action_data(){return [{tag:"replacement",aba:false},{tag:"round-trip",aba:true}]}
  function test_refresh_cancels_actual_pressed_action(d){
   root.width=640;root.height=800;
   readings.beginOpen();const token=readings.startRequest()
   readings.accept(token,{schema_version:1,legacy:{locked:false},contracts:{version:"0.1.0",status:"ok",states:[
    {contract_version:"0.1.0",capability_id:"dashen.device.temperature",resource_id:"thermal-summary",output_id:"local",read_permission:"device.temperature.read",state:{available:true,actual:42,health:"observed",observed_at:100}},
    {contract_version:"0.1.0",capability_id:"dashen.device.touch-mode",resource_id:"touch-mode",output_id:"local",read_permission:"device.touch-mode.read",state:{available:true,actual:1,health:"observed",observed_at:100,boot_default:1}}]}})
   wait(30);const button=findChild(root,"quick-touch-normal");verify(button!==null);bring(button);const point=button.mapToItem(root,button.width/2,button.height/2);const before=root.actions.length
   mousePress(root,point.x,point.y);verify(button.pressed);const pending=readings.startRequest();wait(30);compare(button.objectName,"quick-touch-refresh")
   if(d.aba){readings.accept(pending,{schema_version:1,legacy:{locked:false},contracts:{version:"0.1.0",status:"ok",states:[{contract_version:"0.1.0",capability_id:"dashen.device.temperature",resource_id:"thermal-summary",output_id:"local",read_permission:"device.temperature.read",state:{available:true,actual:42,health:"observed"}},{contract_version:"0.1.0",capability_id:"dashen.device.touch-mode",resource_id:"touch-mode",output_id:"local",read_permission:"device.touch-mode.read",state:{available:true,actual:1,health:"observed"}}]}});wait(30)}
   mouseRelease(root,point.x,point.y);compare(root.actions.length,before,"release must not execute replacement action")
   bring(button);button.forceActiveFocus();keyClick(Qt.Key_Return);compare(root.actions.length,before+1);compare(root.actions[root.actions.length-1],d.aba?"touch-normal":"touch-refresh")
  }
  function test_readout_in_actual_panel(d){
   root.width=d.w;root.height=800;root.themeScale=d.scale;root.fg=d.light?"#182024":"#eeeeee";root.bg=d.light?"#f3f0e7":"#101518"
   readings.beginOpen();const token=readings.startRequest()
   readings.accept(token,{schema_version:1,legacy:{locked:false},contracts:{version:"0.1.0",status:"ok",states:[
    {contract_version:"0.1.0",capability_id:"dashen.device.temperature",resource_id:"thermal-summary",output_id:"local",read_permission:"device.temperature.read",state:{available:true,actual:42,health:"observed",observed_at:100}},
    {contract_version:"0.1.0",capability_id:"dashen.device.touch-mode",resource_id:"touch-mode",output_id:"local",read_permission:"device.touch-mode.read",state:{available:true,actual:1,health:"observed",observed_at:100,boot_default:1}}]}})
   readings.startRequest();wait(30)
   const temperature=findChild(root,"temperatureReadout"),touch=findChild(root,"touchReadout");verify(temperature!==null,"real Panel temperature readout missing");verify(touch!==null)
   verify(temperature.valueText.includes("上次"));verify(temperature.valueText.includes("42"));verify(touch.valueText.includes("上次"));compare(temperature.observedAt,100)
   for(const row of [temperature,touch]){const p=row.mapToItem(root,0,0);verify(p.x>=0&&p.x+row.width<=root.width);verify(row.height>=row.implicitHeight);for(let i=0;i<row.children.length;i++){const text=row.children[i];if(text.visible)verify(text.paintedWidth<=text.width+1)}}
   const refresh=findChild(root,"quick-touch-refresh");bring(refresh);const q=refresh.mapToItem(root,0,0);verify(q.y>=0&&q.y+refresh.height<=root.height);mouseClick(refresh,refresh.width/2,refresh.height/2);compare(root.actions[root.actions.length-1],"touch-refresh")
   const close=findChild(root,"workbenchClose");const c=close.mapToItem(root,0,0);verify(c.y>=0&&c.y+close.height<=root.height);verify(close.height>=48)
  }
  function test_theme_update_preserves_pressed_action_and_focus() {
   root.width=640;root.height=800
   const b=findChild(root,"quick-touch-refresh");bring(b);b.forceActiveFocus();const original=b;const oldMode=root.modeChoice;const identity=window;const before=root.actions.length
   mousePress(b,b.width/2,b.height/2);verify(b.down);root.themeAccent='#00ffff';wait(30)
   compare(findChild(root,"quick-touch-refresh"),original);verify(b.down);verify(b.activeFocus)
   mouseRelease(b,b.width/2,b.height/2);compare(root.actions.length,before+1);compare(root.actions[root.actions.length-1],'touch-refresh')
   root.confirmation={name:'flight-on',params:{}};const c=root.confirmation;root.themeScale=1.5;wait(30)
   compare(b.font.pixelSize,24);compare(root.confirmation,c);compare(root.modeChoice,oldMode);compare(window,identity)
   root.confirmation=null;bring(brightness);mousePress(brightness,brightness.width/2,brightness.height/2);verify(brightness.pressed)
   root.themeAccent='#ffb454';wait(30);verify(brightness.pressed);mouseRelease(brightness,brightness.width/2,brightness.height/2)
  }
  function test_pointer_slider_confirmation_and_action_defer() {
   root.width=640;root.height=800;const identity=window
   const touch=findChild(root,"quick-touch-refresh");bring(touch)
   mousePress(touch,touch.width/2,touch.height/2);root.suggestedMode="desktop";wait(30);compare(root.appliedMode,"tablet")
   mouseRelease(touch,touch.width/2,touch.height/2);tryCompare(root,"appliedMode","desktop")
   root.confirmation={name:"flight-on"};root.suggestedMode="tablet";wait(30);compare(root.appliedMode,"desktop")
   root.confirmation=null;tryCompare(root,"appliedMode","tablet")
   actionProcess.running=true;root.suggestedMode="desktop";wait(30);compare(root.appliedMode,"tablet")
   actionProcess.running=false;tryCompare(root,"appliedMode","desktop")
   bring(brightness);mousePress(brightness,brightness.width/2,brightness.height/2);verify(brightness.pressed,"slider not pressed enabled="+brightness.enabled+" y="+brightness.mapToItem(root,0,0).y+" viewport="+scroll.height+" cy="+scroll.contentY);root.suggestedMode="tablet";wait(30);compare(root.appliedMode,"desktop")
   mouseRelease(brightness,brightness.width/2,brightness.height/2);tryCompare(root,"appliedMode","tablet");compare(window,identity)
  }
  function test_focus_keyboard_and_save_failure() {
   root.width=640;root.height=800;const button=findChild(root,"quick-keyboard");bring(button);button.forceActiveFocus()
   keyClick(Qt.Key_Return);compare(root.actions[root.actions.length-1],"keyboard")
   root.suggestedMode="desktop";tryCompare(root,"appliedMode","desktop");wait(30)
   const moved=findChild(root,"quick-keyboard");verify(moved.activeFocus)
   keyClick(Qt.Key_Tab);wait(30);verify(!moved.activeFocus)
   const manual=findChild(root,"mode-desktop");bring(manual);mouseClick(manual,manual.width/2,manual.height/2)
   compare(root.modeChoice,"desktop");verify(findChild(root,"mode-status").text.indexOf("未保存")>=0)
  }
  function test_flight_restore_and_confirmation_reachable() {
   root.width=320;root.height=480;root.flight={entertainment:true,verified:false};wait(30)
   let all=[];buttons(body,all)
   const restore=all.find(b=>b.text.indexOf("退出飞行娱乐")===0);verify(restore!==undefined);bring(restore);mouseClick(restore,restore.width/2,restore.height/2)
   compare(root.actions[root.actions.length-1],"flight-off")
   root.confirmation={name:"flight-on",params:{}};wait(30)
   const confirm=findChild(root,"confirm-action");verify(confirm!==null);verify(confirm.height>=48)
  }
  function test_sizes(d){
   root.themeScale=d.scale;root.fg=d.contrast?"#ffffff":"#e7e9df";root.bg=d.contrast?"#000000":"#0c1014";root.confirmation=null;root.width=d.width;root.height=d.height;root.appliedMode=d.mode;root.suggestedMode=d.mode;root.expanded=false;wait(30)
   const touch=findChild(root,"quick-touch-refresh");verify(touch!==null,"touch button missing");verify(touch.visible,"touch button hidden");verify(touch.height>=48,"touch button height "+touch.height)
   bring(touch);mouseClick(touch,touch.width/2,touch.height/2);compare(root.actions[root.actions.length-1],"touch-refresh")
   root.expanded=true;wait(30)
   let all=[];buttons(body,all);verify(all.some(b=>b.text==="刷新触摸模式"))
   for(const b of all){const p=b.mapToItem(root,0,0);verify(p.x>=0 && p.x+b.width<=root.width,"horizontal overflow: "+b.text);verify(b.height>=48,"target height");verify(b.contentItem.paintedWidth<=b.contentItem.width+1,"text width")}
   compare(root.width,d.width);compare(root.height,d.height)
  }
 }
}
'''
if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='control-layout-') as tmp:
        p=Path(tmp);shutil.copytree(root/'Workbench',p/'Workbench')
        for name in ('ControlActions.js','ControlModel.js','ContractModel.js','ContractState.qml'):
            shutil.copy2(root/name,p/name)
        (p/'tst_layout.qml').write_text(prefix+layout+button+tests)
        runner=shutil.which('qmltestrunner') or next((v for v in ('/usr/lib/qt6/bin/qmltestrunner','/usr/lib/qt6/qmltestrunner') if Path(v).is_file()),'qmltestrunner')
        subprocess.run([runner,'-platform','offscreen','-input',str(p/'tst_layout.qml')],check=True)
