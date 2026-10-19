"""Exercise actual navigation layout without a compositor or user windows."""
from pathlib import Path
import tempfile,subprocess,shutil
root=Path(__file__).resolve().parent
source=(root/'Navigation.qml').read_text();a=source.index('   WB.PanelBody {');b=source.index('{',a)+1;depth=1
while depth:
 if source[b]=='{':depth+=1
 if source[b]=='}':depth-=1
 b+=1
layout=source[a:b].replace('Style.font.family','"sans-serif"').replace('Color.accent','"#bb88ff"').replace('Color.urgent','"#ee8866"').replace('root.data','root.snapshot')
prefix='''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtTest
import "Workbench" as WB
import "Workbench/Theme.js" as Theme
Item {
 id:root;width:640;height:604
 property var session:({phase:"open"})
 property int retries:0
 function openPage(value){retries++;page=value}
 property string page:"开始"
 property string feedback:""
 property bool busy:false
 property real themeScale:1
 property color themeAccent:"#ffb454"
 property var themeTokens:Theme.resolve({schemaVersion:1,foreground:fg,background:bg,accent:themeAccent,fontScale:themeScale})
 property var actions:[]
 property color fg:"#eeeeee"
 property color bg:"#202020"
 property var snapshot:({target:{address:"0x1",pid:1},current:1,workspaces:[{id:1,count:4},{id:2,count:0}],windowLabel:"测试窗口",bindings:{P1:"keyboard",P2:"voice",P3:"authorize",rotation:"navigation"},labels:{keyboard:"输入法",voice:"语音",authorize:"授权",navigation:"开始",desktops:"桌面",windows:"窗口",disabled:"不执行操作"}})
 QtObject{id:command;property bool running:false}
 function close(){}
 function selectPage(value){page=value;feedback=""}
 function act(name,value){actions=actions.concat([{action:name,value:value}])}
'''
tests='''
 TestCase {
  name:"NavigationGeometry";when:windowShown
  function test_error_has_only_retry_and_close() {
   root.width=320;root.height=480;root.session={phase:'error'};root.feedback='读取超时，请重试';wait(30)
   const retry=findChild(root,'navigation-retry');verify(retry.visible);verify(retry.width>=48);verify(retry.height>=48)
   for(const id of ['browser','close','maximize'])verify(!findChild(root,'action-'+id).visible)
   verify(!findChild(root,'navigation-tab-开始').visible)
   const before=root.retries;mouseClick(retry,retry.width/2,retry.height/2);compare(root.retries,before+1)
   root.session={phase:'open'};root.feedback=''
  }
  function test_no_window_disables_only_target_actions() {
   root.width=640;root.height=800;root.page='窗口';root.snapshot=Object.assign({},root.snapshot,{target:null});wait(30)
   for(const id of ['maximize','float','hide','center','close'])verify(!findChild(root,'action-'+id).enabled)
   verify(findChild(root,'action-restore').enabled);verify(findChild(root,'quickDesktop1').enabled)
   root.snapshot=Object.assign({},root.snapshot,{target:{address:'0x1',pid:1}})
  }
  function test_action_group_theme_keeps_pressed_target() {
   root.width=640;root.height=800;root.page='开始';root.themeScale=1;wait(30)
   const button=findChild(root,'action-browser');const before=root.actions.length
   button.forceActiveFocus();mousePress(button,button.width/2,button.height/2)
   root.themeAccent='#12abef';wait(20);compare(findChild(root,'action-browser'),button);verify(button.down);verify(button.activeFocus)
   mouseRelease(button,button.width/2,button.height/2);compare(root.actions.length,before+1);compare(root.actions[before].action,'browser')
  }
  function test_tabs_remain_reachable_on_small_landscape() {
   root.width=320;root.height=240;root.themeScale=1.5;root.feedback='合成错误，请检查设备';wait(30)
   for(const page of ['开始','桌面','窗口','按键']) {
    const scroll=findChild(root,"workbenchScroll");scroll.contentY=0;wait(10)
    const tab=findChild(root,'navigation-tab-'+page);verify(tab!==null);verify(tab.height>=48)
    const point=tab.mapToItem(scroll,tab.width/2,tab.height/2);verify(point.y>=0&&point.y<scroll.height)
    mouseClick(tab,tab.width/2,tab.height/2);compare(root.page,page)
   }
   root.themeScale=1;root.feedback=''
  }
  function test_theme_update_preserves_navigation_action() {
   root.width=640;root.height=800;root.page='窗口';root.themeScale=1;wait(50)
   const b=findChild(root,'quickDesktop1');verify(b!==null);const snapshot=root.snapshot;const before=root.actions.length
   b.forceActiveFocus();mousePress(b,b.width/2,b.height/2);verify(b.down)
   root.themeAccent='#00ffff';wait(20);compare(findChild(root,'quickDesktop1'),b);verify(b.down);verify(b.activeFocus)
   mouseRelease(b,b.width/2,b.height/2);compare(root.actions.length,before+1);compare(root.actions[before].action,'switch');compare(root.actions[before].value.workspace,1)
   root.themeScale=1.5;wait(20);compare(b.font.pixelSize,24);compare(root.snapshot,snapshot);compare(root.page,'窗口');root.themeScale=1
  }
  function test_pages_data(){var rows=[];for(var page of ["开始","桌面","窗口","按键"])for(var size of [[640,604],[480,540],[320,480],[320,800],[640,480],[480,800]])for(var scale of [1,1.25,1.5])for(var contrast of [false,true])rows.push({tag:page+size[0]+"x"+size[1]+"-"+scale+"-"+contrast,page:page,w:size[0],h:size[1],scale:scale,contrast:contrast});return rows}
  function buttons(item,list) {
   if(!item.visible)return
   if(item.minimumTouchHeight!==undefined&&item.objectName.indexOf("navigation-tab-")!==0)list.push(item)
   for(var i=0;i<item.children.length;i++)buttons(item.children[i],list)
  }
  function test_pages(d){
   root.themeScale=d.scale;root.fg=d.contrast?"#ffffff":"#e7e9df";root.bg=d.contrast?"#000000":"#0c1014";root.width=d.w;root.height=d.h;root.page=d.page;root.actions=[];root.snapshot={target:{address:"0x1",pid:1},current:1,workspaces:Array.from({length:10},(_,i)=>({id:i+1,count:i})),windowLabel:"用于测试超长标题的窗口".repeat(20),bindings:{P1:"keyboard",P2:"voice",P3:"authorize",rotation:"navigation"},labels:{keyboard:"输入法",voice:"语音",authorize:"授权",navigation:"开始",desktops:"桌面",windows:"窗口",disabled:"不执行操作"}};wait(50)
   if(d.page==="窗口") {
    var found=[];buttons(body,found)
    var quick=found.filter(b=>b.objectName.indexOf("quickDesktop")===0);compare(quick.length,9)
    for(var q of quick){var qp=q.mapToItem(root,0,0);if(d.scale===1&&d.w>=480&&d.h>=540)verify(qp.y>=0 && qp.y+q.height<=root.height,"quick desktop requires scrolling: "+qp.y+"+"+q.height+">"+root.height);var sc=findChild(root,"workbenchScroll");var pos=q.mapToItem(body,0,0);sc.contentY=Math.max(0,Math.min(pos.y,sc.contentHeight-sc.height));wait(10);var prior=root.actions.length;mouseClick(q,q.width/2,q.height/2);compare(root.actions.length,prior+1);compare(root.actions[prior].action,"switch");compare(root.actions[prior].value.workspace,Number(q.text))}
   }
   var list=[];buttons(body,list);verify(list.length>0,"page needs actual buttons")
   var scroll=findChild(root,"workbenchScroll");verify(scroll.contentHeight>=body.implicitHeight,"content must be scrollable")
   for(var b of list) {
    verify(b.width>=48 && b.height>=48,"touch target too small: "+b.text+" "+b.width+"x"+b.height)
    var xy=b.mapToItem(root,0,0);verify(xy.x>=0 && xy.x+b.width<=root.width,"horizontal overflow: "+b.text)
    verify(b.contentItem.paintedHeight<=b.contentItem.height+1,"label vertical clipping: "+b.text)
    verify(b.contentItem.paintedWidth<=b.contentItem.width+1,"label horizontal clipping: "+b.text)
    var pos=b.mapToItem(body,0,0);scroll.contentY=Math.max(0,Math.min(pos.y,scroll.contentHeight-scroll.height));wait(10)
    var local=b.mapToItem(scroll,b.width/2,b.height/2)
    verify(local.y>=0 && local.y<scroll.height,"button cannot be scrolled into view: "+b.text)
    var count=root.actions.length;mouseClick(b,b.width/2,b.height/2);compare(root.actions.length,count+1,"button action: "+b.text)
   }
   scroll.contentY=0
  }
 }
}
'''
if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='navigation-layout-') as tmp:
     p=Path(tmp);shutil.copytree(root/'Workbench',p/'Workbench');(p/'tst_layout.qml').write_text(prefix+layout+tests)
     runner=shutil.which('qmltestrunner') or next((name for name in ('/usr/lib/qt6/bin/qmltestrunner','/usr/lib/qt6/qmltestrunner') if Path(name).is_file()),'qmltestrunner')
     subprocess.run([runner,'-platform','offscreen','-input',str(p/'tst_layout.qml')],check=True)
