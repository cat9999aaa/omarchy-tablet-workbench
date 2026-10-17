"""Exercise actual navigation layout without a compositor or user windows."""
from pathlib import Path
import tempfile,subprocess,shutil
root=Path(__file__).resolve().parent
source=(root/'Navigation.qml').read_text();a=source.index('   ColumnLayout {');b=source.index('{',a)+1;depth=1
while depth:
 if source[b]=='{':depth+=1
 if source[b]=='}':depth-=1
 b+=1
layout=source[a:b].replace('Style.font.family','"sans-serif"').replace('Color.accent','"#bb88ff"').replace('Color.urgent','"#ee8866"')
prefix='''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtTest
import "Workbench" as WB
Item {
 id:root;width:640;height:604
 property string page:"开始"
 property string feedback:""
 property color fg:"#eeeeee"
 property color bg:"#202020"
 property var data:({current:1,workspaces:[{id:1,count:4},{id:2,count:0}],windowLabel:"测试窗口",bindings:{P1:"keyboard",P2:"voice",P3:"authorize",rotation:"navigation"},labels:{keyboard:"输入法",voice:"语音",authorize:"授权",navigation:"开始",desktops:"桌面",windows:"窗口",disabled:"不执行操作"}})
 QtObject{id:command;property bool running:false}
 function close(){}
 function act(name,value){}
'''
tests='''
 TestCase {
  name:"NavigationGeometry";when:windowShown
  function test_pages_data(){var rows=[];for(var page of ["开始","桌面","窗口","按键"])for(var size of [[640,604],[480,540]])rows.push({tag:page+size[0],page:page,w:size[0],h:size[1]});return rows}
  function test_pages(d){root.width=d.w;root.height=d.h;root.page=d.page;wait(50);compare(root.width,d.w);compare(root.height,d.h);verify(body.implicitHeight>0)}
 }
}
'''
with tempfile.TemporaryDirectory(prefix='navigation-layout-') as tmp:
 p=Path(tmp);shutil.copytree(root/'Workbench',p/'Workbench');(p/'tst_layout.qml').write_text(prefix+layout+tests)
 runner=shutil.which('qmltestrunner') or next((name for name in ('/usr/lib/qt6/bin/qmltestrunner','/usr/lib/qt6/qmltestrunner') if Path(name).is_file()),'qmltestrunner')
 subprocess.run([runner,'-platform','offscreen','-input',str(p/'tst_layout.qml')],check=True)
