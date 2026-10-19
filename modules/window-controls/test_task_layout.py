"""Exercise extracted actual task content with anonymous synthetic data."""
from pathlib import Path
import shutil,subprocess,tempfile
root=Path(__file__).parent
source=(root/'TaskCenter.qml').read_text();a=source.index('   WB.PanelBody{');b=source.index('{',a)+1;depth=1
while depth:
 if source[b]=='{':depth+=1
 if source[b]=='}':depth-=1
 b+=1
layout=source[a:b]
prefix='''import QtQuick
import QtQuick.Layouts
import QtTest
import "Workbench" as WB
import "Workbench/Theme.js" as Theme
import "TaskSession.js" as Session
Item {
 id:root;width:640;height:604
 property real scaleValue:1
 property bool dark:true
 property var themeTokens:Theme.resolve({schemaVersion:1,foreground:dark?"#eeeeee":"#111111",background:dark?"#111111":"#eeeeee",accent:"#ee8844",fontScale:scaleValue})
 property bool busy:false
 property var session:({rows:[],detailsRead:[],dnd:null,truncated:false,sourceReason:"",feedback:""})
 property int clicks:0
 function close(){clicks++}
 function refresh(){clicks++}
 function handoff(a){clicks++}
 function detail(a){clicks++}
 function sourceText(a){return "暂时无法读取"}
'''
tests='''
 TestCase{name:"TaskLayout";when:windowShown
 function test_content_data(){var rows=[];for(var size of [[320,480],[640,480],[480,800],[640,604]])for(var scale of [1,1.25,1.5])for(var dark of [true,false])rows.push({tag:size+"-"+scale+"-"+dark,w:size[0],h:size[1],scale:scale,dark:dark});return rows}
 function scan(item,buttons,texts){if(!item.visible)return;if(item.minimumTouchHeight!==undefined)buttons.push(item);if(item.text!==undefined)texts.push(item.text);for(var i=0;i<item.children.length;i++)scan(item.children[i],buttons,texts)}
 function test_content(d){
  root.width=d.w;root.height=d.h;root.scaleValue=d.scale;root.dark=d.dark
  const rows=['idle','closed','needs_permission','error','unknown','initializing','running'].map((kind,i)=>({agent_id:'PRIVATE-'+i,ordinal:i+1,kind:kind,pending_permission_count:i===2?2:null,observed_at:'2026-01-01T00:00:00Z',sampled_boottime_ms:0,source_updated_at:null,stale:i>1,detailReason:''}))
  root.session={observedAt:'2026-01-01T00:00:00Z',stale:false,rows:rows,detailsRead:[],dnd:null,truncated:true,sourceReason:'read-failed',feedback:'读取失败，请重试'};wait(40)
  var buttons=[],texts=[];scan(body,buttons,texts);verify(buttons.length>=10);verify(!texts.join(' ').includes('PRIVATE'));verify(!texts.join(' ').includes('完成'));verify(texts.join(' ').includes('等待授权：未知'))
  const scroll=findChild(root,'workbenchScroll')
  for(var button of buttons){verify(button.width>=48&&button.height>=48);verify(button.contentItem.paintedWidth<=button.contentItem.width+1,'text clipped '+button.text);const xy=button.mapToItem(body,0,0);scroll.contentY=Math.max(0,Math.min(xy.y,scroll.contentHeight-scroll.height));wait(10);const before=root.clicks;mouseClick(button,button.width/2,button.height/2);compare(root.clicks,before+1)}
  root.session={observedAt:'2026-01-01T00:00:00Z',stale:false,rows:[],detailsRead:[],dnd:false,truncated:false,sourceReason:'',feedback:''};wait(20);texts=[];scan(body,[],texts);verify(texts.join(' ').includes('本项目暂无会话'));scroll.contentY=0
 }
 }
}
'''
if __name__=='__main__':
 with tempfile.TemporaryDirectory(prefix='task-layout-') as tmp:
  p=Path(tmp);shutil.copytree(root/'Workbench',p/'Workbench');shutil.copy2(root/'TaskSession.js',p/'TaskSession.js');(p/'tst_task.qml').write_text(prefix+layout+tests)
  runner=shutil.which('qmltestrunner') or next((n for n in ['/usr/lib/qt6/bin/qmltestrunner','/usr/lib/qt6/qmltestrunner'] if Path(n).exists()),'qmltestrunner')
  r=subprocess.run([runner,'-platform','offscreen','-input',str(p/'tst_task.qml')],capture_output=True,text=True);print(r.stdout+r.stderr)
  if r.returncode or any(x in r.stdout+r.stderr for x in ['TypeError:','ReferenceError:','Binding loop','Unable to assign']):raise SystemExit(1)
