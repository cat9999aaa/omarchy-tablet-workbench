"""Exercise actual navigation layout without a compositor or user windows."""
from pathlib import Path
import tempfile,subprocess,shutil
root=Path(__file__).resolve().parent
source=(root/'Navigation.qml').read_text();a=source.index('   ColumnLayout {');b=source.index('{',a)+1;depth=1
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
Item {
 id:root;width:640;height:604
 property string page:"开始"
 property string feedback:""
 property var actions:[]
 property color fg:"#eeeeee"
 property color bg:"#202020"
 property var snapshot:({current:1,workspaces:[{id:1,count:4},{id:2,count:0}],windowLabel:"测试窗口",bindings:{P1:"keyboard",P2:"voice",P3:"authorize",rotation:"navigation"},labels:{keyboard:"输入法",voice:"语音",authorize:"授权",navigation:"开始",desktops:"桌面",windows:"窗口",disabled:"不执行操作"}})
 QtObject{id:command;property bool running:false}
 function close(){}
 function act(name,value){actions=actions.concat([{action:name,value:value}])}
'''
tests='''
 TestCase {
  name:"NavigationGeometry";when:windowShown
  function test_pages_data(){var rows=[];for(var page of ["开始","桌面","窗口","按键"])for(var size of [[640,604],[480,540]])rows.push({tag:page+size[0],page:page,w:size[0],h:size[1]});return rows}
  function buttons(item,list) {
   if(!item.visible)return
   if(item.minimumTouchHeight!==undefined)list.push(item)
   for(var i=0;i<item.children.length;i++)buttons(item.children[i],list)
  }
  function test_pages(d){
   root.width=d.w;root.height=d.h;root.page=d.page;root.actions=[];root.snapshot={current:1,workspaces:Array.from({length:10},(_,i)=>({id:i+1,count:i})),windowLabel:"用于测试超长标题的窗口".repeat(20),bindings:{P1:"keyboard",P2:"voice",P3:"authorize",rotation:"navigation"},labels:{keyboard:"输入法",voice:"语音",authorize:"授权",navigation:"开始",desktops:"桌面",windows:"窗口",disabled:"不执行操作"}};wait(50)
   if(d.page==="窗口") {
    var found=[];buttons(body,found)
    var quick=found.filter(b=>b.objectName.indexOf("quickDesktop")===0);compare(quick.length,9)
    for(var q of quick){var qp=q.mapToItem(root,0,0);verify(qp.y>=0 && qp.y+q.height<=root.height,"quick desktop requires scrolling");var prior=root.actions.length;mouseClick(q,q.width/2,q.height/2);compare(root.actions.length,prior+1);compare(root.actions[prior].action,"switch");compare(root.actions[prior].value.workspace,Number(q.text))}
   }
   var list=[];buttons(body,list);verify(list.length>0,"page needs actual buttons")
   var scroll=body.parent.parent;verify(scroll.contentHeight>=body.implicitHeight,"content must be scrollable")
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
with tempfile.TemporaryDirectory(prefix='navigation-layout-') as tmp:
 p=Path(tmp);shutil.copytree(root/'Workbench',p/'Workbench');(p/'tst_layout.qml').write_text(prefix+layout+tests)
 runner=shutil.which('qmltestrunner') or next((name for name in ('/usr/lib/qt6/bin/qmltestrunner','/usr/lib/qt6/qmltestrunner') if Path(name).is_file()),'qmltestrunner')
 subprocess.run([runner,'-platform','offscreen','-input',str(p/'tst_layout.qml')],check=True)
