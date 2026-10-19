import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "Workbench" as WB
import "Workbench/Layout.js" as LayoutModel
import "TaskSession.js" as Session
Item {
 id:root
 property var session:Session.initial()
 readonly property bool opened:session.phase==="open"
 readonly property bool busy:session.pending!==null||activeAction!==null
 readonly property string helper:Quickshell.env("PCADMIN_TASK_HELPER")||Quickshell.env("HOME")+"/Projects/pcadmin/tools/window-controls/tasks.py"
 property var activeRead:null
 property var activeGuard:null
 property var activeAction:null
 signal opening()
 signal closed()
 WB.ThemeContext{id:themeContext}
 readonly property var themeTokens:themeContext.tokens
 readonly property var targetScreen:{var matches=Quickshell.screens.filter(s=>s.name===session.output);return matches.length===1?matches[0]:null}
 readonly property alias boundScreen:window.screen
 onTargetScreenChanged:Qt.callLater(function(){if(root.session.phase!=="closed"&&!root.targetScreen)root.dispatch({type:"OUTPUT_LOST"})})
 function dispatch(event){
  const oldPhase=session.phase
  const result=Session.reduce(session,event);session=result.state
  for(const effect of result.effects){
   if(effect.type==="cancel-read"&&activeRead){const reader=activeRead;activeRead=null;reader.running=false}
   if(effect.type==="read-snapshot"||effect.type==="read-detail"){
    const command=effect.type==="read-snapshot"?"snapshot":"detail"
    const value=command==="snapshot"?{generation:effect.generation}:{generation:effect.generation,agent_id:effect.agent_id,remaining_ms:effect.remaining_ms,output:effect.output}
    activeRead=processFactory.createObject(root,{operation:command,requestGeneration:effect.generation,requestId:effect.requestId,request:JSON.stringify(value)})
    activeRead.running=true
   }
  }
  if(session.phase==="closed"){
   if(activeGuard){const guard=activeGuard;activeGuard=null;guard.running=false}
   if(oldPhase!=="closed")closed()
  }
  if(session.phase!=="closed"&&!targetScreen)dispatch({type:"OUTPUT_LOST"})
 }
 function open(outputName){opening();dispatch({type:"OPEN",output:outputName})}
 function close(){dispatch({type:"CLOSE"})}
 function refresh(){if(!busy)dispatch({type:"REFRESH"})}
 function detail(id){if(!busy)dispatch({type:"DETAIL",agent_id:id})}
 function handoff(action){
  if(!opened||busy||["open-paseo","notification-history"].indexOf(action)<0)return
  activeAction=processFactory.createObject(root,{operation:"action",requestGeneration:session.generation,requestId:0,request:JSON.stringify({action:action,output:session.output})});activeAction.running=true
 }
 function sourceText(code){return ({'invalid-project':'未选择有效项目','timeout':'读取超时，请刷新','read-failed':'暂时无法读取','invalid-data':'来源数据不兼容','scope-changed':'会话归属已变化'})[code]||'暂时无法读取'}
 function publicState(){return JSON.stringify({version:"0.1.5",phase:session.phase,opened:opened,count:session.rows.length,needsPermission:session.rows.filter(r=>r.kind==="needs_permission").length,readers:(activeRead?1:0)+(activeGuard?1:0)})}
 IpcHandler{target:"pcadmin.tasks"
  function ready():bool{return true}
  function open(output:string):void{root.open(output)}
  function close():void{root.close()}
  function state():string{return root.publicState()}
 }
 Component{
  id:processFactory
  Process{
   id:proc
   required property string operation
   required property int requestGeneration
   required property int requestId
   required property string request
   property bool received:false
   command:["python",root.helper,operation];stdinEnabled:true
   onStarted:{write(request);stdinEnabled=false}
   function deliver(value){
    if(operation==="guard"){
     if(root.session.generation!==requestGeneration)return
     if(!value||value.ok!==true||value.output!==root.session.output||!Number.isFinite(value.sampled_boottime_ms))root.dispatch({type:"LOCKED"})
     else root.dispatch({type:"TICK",now:value.sampled_boottime_ms})
    }else if(operation==="action"){
     if(root.session.generation!==requestGeneration)return
     if(value&&value.ok===true)root.close()
     else root.session=Object.assign({},root.session,{feedback:"无法打开原应用，请重试"})
    }else root.dispatch({type:"RESULT",generation:requestGeneration,requestId:requestId,value:value})
   }
   stdout:StdioCollector{onStreamFinished:{proc.received=true;var value;try{value=JSON.parse(text)}catch(e){value=null}proc.deliver(value)}}
   onExited:{if(!received)deliver(null);if(root.activeRead===proc)root.activeRead=null;if(root.activeGuard===proc)root.activeGuard=null;if(root.activeAction===proc)root.activeAction=null;destroy()}
   property Timer watchdog:Timer{interval:proc.operation==="guard"?1400:5500;running:proc.running;onTriggered:{proc.deliver(null);proc.running=false}}
  }
 }
 Timer{interval:500;repeat:true;running:root.opened;onTriggered:{if(!root.activeGuard){root.activeGuard=processFactory.createObject(root,{operation:"guard",requestGeneration:root.session.generation,requestId:0,request:JSON.stringify({output:root.session.output})});root.activeGuard.running=true}}}
 PanelWindow{
  id:window;visible:root.opened&&root.targetScreen!==null;screen:root.targetScreen
  anchors{top:true;bottom:true;left:true;right:true}
  exclusionMode:ExclusionMode.Ignore;color:"transparent"
  WlrLayershell.namespace:"pcadmin-tasks";WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
  MouseArea{anchors.fill:parent;onPressed:root.close()}
  Rectangle{
   anchors.centerIn:parent;width:LayoutModel.panelSize(window.width,window.height).width;height:LayoutModel.panelSize(window.width,window.height).height
   color:root.themeTokens.colors.background;radius:root.themeTokens.metrics.radius;border.width:root.themeTokens.states.focusBorderWidth;border.color:root.themeTokens.colors.accent
   MouseArea{anchors.fill:parent}
   WB.PanelBody{
    anchors.fill:parent;anchors.margins:root.themeTokens.metrics.paddingX
    themeTokens:root.themeTokens;title:"任务与通知";subtitle:"只读状态 · 操作回原应用";onCloseRequested:root.close()
    ColumnLayout{
     id:body;width:parent.width;spacing:root.themeTokens.metrics.gap
     WB.ActionGrid{Layout.fillWidth:true;themeTokens:root.themeTokens;busy:root.busy;columns:2;items:[{id:"refresh",label:"刷新状态",action:"refresh"},{id:"paseo",label:"打开 Paseo",action:"open-paseo"},{id:"notifications",label:"系统通知历史",action:"notification-history"}];onTriggered:function(action,payload){if(action==="refresh")root.refresh();else root.handoff(action)}}
     WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;wrapMode:Text.Wrap;text:"免打扰："+(root.session.dnd===null?"未知":root.session.dnd?"已开启":"未开启")+" · "+(root.session.stale?"上次读取":"本次读取")+"\n采样："+new Date(root.session.observedAt).toLocaleString(Qt.locale("zh_CN"))}
     WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;visible:!!root.session.sourceReason;wrapMode:Text.Wrap;text:root.sourceText(root.session.sourceReason);tone:"urgent"}
     WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;visible:!!root.session.feedback;wrapMode:Text.Wrap;text:root.session.feedback;tone:"urgent"}
     WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;visible:!root.session.sourceReason&&root.session.rows.length===0;wrapMode:Text.Wrap;text:"本项目暂无会话"}
     WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;visible:root.session.truncated;wrapMode:Text.Wrap;text:"仅显示前20个会话，请到 Paseo 查看全部"}
     Repeater{model:root.session.rows
      ColumnLayout{
       required property var modelData
       Layout.fillWidth:true;spacing:root.themeTokens.metrics.gapSmall
       WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;role:"title";wrapMode:Text.Wrap;text:"会话 "+parent.modelData.ordinal+" · "+Session.label(parent.modelData.kind)}
       WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;wrapMode:Text.Wrap;text:"等待授权："+(parent.modelData.pending_permission_count===null?"未知":parent.modelData.pending_permission_count)+" · "+(parent.modelData.stale?"上次读取":"本次读取")}
       WB.StyledText{Layout.fillWidth:true;themeTokens:root.themeTokens;role:"subtitle";wrapMode:Text.Wrap;text:"采样："+new Date(parent.modelData.observed_at).toLocaleString(Qt.locale("zh_CN"))+ (parent.modelData.source_updated_at?"\n来源更新："+new Date(parent.modelData.source_updated_at).toLocaleString(Qt.locale("zh_CN")):"")}
       WB.TouchButton{Layout.fillWidth:true;themeTokens:root.themeTokens;objectName:"task-detail-"+parent.modelData.ordinal;text:root.session.detailsRead.indexOf(parent.modelData.agent_id)<0?"待展开读取":parent.modelData.detailReason||"本轮已读取";enabled:!root.busy&&root.session.detailsRead.indexOf(parent.modelData.agent_id)<0;onClicked:root.detail(parent.modelData.agent_id)}
      }
     }
    }
   }
  }
 }
}
