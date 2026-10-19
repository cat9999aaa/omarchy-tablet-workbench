import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import "Workbench" as WB
import "Workbench/Layout.js" as LayoutModel
import "NavigationSession.js" as Session
Item {
 id:root
 property var session:Session.initial()
 readonly property bool opened:session.phase==="open"||session.phase==="acting"||session.phase==="error"
 readonly property string page:session.page
 readonly property var snapshot:session.data||({})
 readonly property string feedback:session.feedback
 readonly property bool busy:session.phase==="acting"
 readonly property string helper:Quickshell.env("PCADMIN_NAVIGATION_HELPER") || Quickshell.env("HOME")+"/Projects/pcadmin/tools/window-controls/navigation.py"
 TaskCenter {id:tasks;onOpening:root.close()}
 WB.ThemeContext {id:themeContext}
 readonly property var themeTokens:themeContext.tokens
 readonly property color fg:themeTokens.colors.foreground
 readonly property color bg:themeTokens.colors.background
 readonly property alias boundScreen:window.screen
 readonly property var targetScreen:{
  var matches=Quickshell.screens.filter(s=>s.name===root.session.output)
  return matches.length===1?matches[0]:null
 }
 onTargetScreenChanged:Qt.callLater(function(){if(root.opened&&!root.targetScreen)root.dispatch({type:"OUTPUT_LOST"})})
 property var activeRead:null
 property int actionSerial:0
 function dispatch(event) {
  var result=Session.reduce(session,event);session=result.state
  for(var effect of result.effects) {
   if(effect.type==="cancel-read"&&activeRead){activeRead.running=false;activeRead=null}
   if(effect.type==="read") {
    var reader=readFactory.createObject(root,{requestGeneration:effect.generation})
    activeRead=reader;reader.running=true
   }
  }
  if(opened&&!targetScreen)dispatch({type:"OUTPUT_LOST"})
 }
 function openPage(value){tasks.close();dispatch({type:"OPEN",page:value})}
 function close(){dispatch({type:"CLOSE"})}
 function selectPage(value){if(session.phase==="open"&&["开始","桌面","窗口","按键"].indexOf(value)>=0)session=Object.assign({},session,{page:value,feedback:""})}
 function act(action,extra) {
  if(session.phase!=="open")return
  var id=String(++actionSerial),generation=session.generation
  var value=Object.assign({action:action,target:snapshot.target,context:{output:session.output}},extra||{})
  dispatch({type:"ACT_STARTED",generation:generation,id:id})
  var process=actionFactory.createObject(root,{requestGeneration:generation,requestId:id,request:JSON.stringify(value)})
  process.running=true
 }
 function publicState(){return JSON.stringify({version:"0.1.5",opened:opened,page:page,width:card.width,height:card.height,phase:session.phase,generation:session.generation,reason_code:session.phase==="closed"?session.feedback:""})}
 IpcHandler {
  target:"pcadmin.navigation"
  function ready():bool{return true}
  function toggle(page:string):void {if(root.session.phase!=="closed")root.close();else root.openPage(page)}
  function open(page:string):void {root.openPage(page)}
  function close():void {root.close()}
  function state():string{return root.publicState()}
 }
 Component {
  id:readFactory
  Process {
   id:reader
   required property int requestGeneration
   property bool received:false
   command:["python",root.helper,"snapshot"]
   stdout:StdioCollector {onStreamFinished:{
    reader.received=true
    try {var value=JSON.parse(text);root.dispatch(value.ok?{type:"READ_OK",generation:reader.requestGeneration,data:value}:{type:"READ_ERROR",generation:reader.requestGeneration,code:value.reason_code||"read-failed",output:value.output})}
    catch(error){root.dispatch({type:"READ_ERROR",generation:reader.requestGeneration,code:"invalid-data"})}
   }}
   onExited:{if(!received)root.dispatch({type:"READ_ERROR",generation:requestGeneration,code:"read-failed"});if(root.activeRead===reader)root.activeRead=null;destroy()}
  }
 }
 Component {
  id:lockFactory
  Process {
   id:lockProcess
   required property int requestGeneration
   property bool unlocked:false
   command:["omarchy-shell","lock","isLocked"]
   stdout:StdioCollector {onStreamFinished:lockProcess.unlocked=text.trim()==="false"}
   onExited:function(code){if(root.session.generation===requestGeneration&&(code!==0||!unlocked))root.dispatch({type:"LOCKED"});destroy()}
   property Timer watchdog:Timer {interval:1000;running:lockProcess.running;onTriggered:{if(root.session.generation===lockProcess.requestGeneration)root.dispatch({type:"LOCKED"});lockProcess.running=false}}
  }
 }
 Timer {interval:500;repeat:true;running:root.opened;onTriggered:{var check=lockFactory.createObject(root,{requestGeneration:root.session.generation});check.running=true}}
 Component {
  id:actionFactory
  Process {
   id:actionProcess
   required property int requestGeneration
   required property string requestId
   required property string request
   property bool received:false
   command:["python",root.helper,"action"];stdinEnabled:true
   onStarted:{write(request);stdinEnabled=false}
   stdout:StdioCollector {onStreamFinished:{
    actionProcess.received=true
    var value;try{value=JSON.parse(text)}catch(error){value={ok:false,reason:"操作未完成"}}
    const target=value&&value.ok===true&&value.open_tasks===root.session.output&&root.session.generation===actionProcess.requestGeneration&&root.session.actionId===actionProcess.requestId?value.open_tasks:null
    root.dispatch({type:"ACT_RESULT",generation:actionProcess.requestGeneration,id:actionProcess.requestId,result:value})
    if(target)tasks.open(target)
   }}
   onExited:{if(!received)root.dispatch({type:"ACT_RESULT",generation:requestGeneration,id:requestId,result:{ok:false,reason:"操作未完成"}});destroy()}
  }
 }
 PanelWindow {
  id:window;visible:root.opened&&root.targetScreen!==null;screen:root.targetScreen
  anchors{top:true;bottom:true;left:true;right:true}
  exclusionMode:ExclusionMode.Ignore;color:"transparent"
  WlrLayershell.namespace:"pcadmin-navigation"
  WlrLayershell.layer:WlrLayer.Overlay
  WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
  MouseArea{anchors.fill:parent;onPressed:root.close()}
  Rectangle {
   id:card;anchors.centerIn:parent
   width:LayoutModel.panelSize(window.width,window.height).width
   height:LayoutModel.panelSize(window.width,window.height).height
   color:root.bg;radius:root.themeTokens.metrics.radius;border.width:root.themeTokens.states.focusBorderWidth;border.color:root.themeTokens.colors.accent
   MouseArea{anchors.fill:parent}
   WB.PanelBody {
    anchors.fill:parent;anchors.margins:root.themeTokens.metrics.paddingX
    themeTokens:root.themeTokens;title:"平板导航";subtitle:"应用 · 全局桌面 · 打开时窗口"
    onCloseRequested:root.close()
    ColumnLayout {
      id:body;width:parent.width;spacing:root.themeTokens.metrics.gap
      TextMetrics {id:desktopNumberMetrics;text:"10";font.family:root.themeTokens.font.family;font.pixelSize:root.themeTokens.font.body}
      function numberColumns(available,gap,limit) {
       const minimum=Math.max(48,Math.ceil(desktopNumberMetrics.advanceWidth)+2*root.themeTokens.metrics.paddingX)
       return Math.max(1,Math.min(limit,Math.floor((available+gap)/(minimum+gap))))
      }
    RowLayout {
     visible:root.session.phase!=="error"
     Layout.fillWidth:true;spacing:root.themeTokens.metrics.gapSmall
     Repeater{model:["开始","桌面","窗口","按键"]
      WB.TouchButton{themeTokens:root.themeTokens;required property string modelData;objectName:"navigation-tab-"+modelData;Layout.fillWidth:true;text:modelData;foreground:root.fg;accent:root.themeTokens.colors.accent;selected:root.page===modelData;onClicked:root.selectPage(modelData)}
     }
    }
    WB.StyledText{themeTokens:root.themeTokens;visible:!!root.feedback;Layout.fillWidth:true;text:root.feedback;color:root.themeTokens.colors.urgent;wrapMode:Text.Wrap;role:"body"}
      WB.TouchButton{themeTokens:root.themeTokens;objectName:"navigation-retry";visible:root.session.phase==="error";Layout.fillWidth:true;text:"重新读取";foreground:root.fg;accent:root.themeTokens.colors.accent;onClicked:root.openPage(root.page)}
      ColumnLayout {
       visible:root.session.phase!=="error"&&root.page==="开始";Layout.fillWidth:true;spacing:root.themeTokens.metrics.gap
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"开始使用";color:root.fg;role:"title"}
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"设备状态和网络设置仍在三指下滑的随身控制台。";color:root.fg;wrapMode:Text.Wrap;role:"body"}
       WB.ActionGrid {
        Layout.fillWidth:true;themeTokens:root.themeTokens;busy:root.busy;columns:2
        items:[{id:"launcher",label:"全部应用",action:"launcher"},{id:"files",label:"文件",action:"files"},{id:"browser",label:"浏览器",action:"browser"},{id:"keyboard",label:"触屏输入法",action:"keyboard"},{id:"voice",label:"语音输入",action:"voice"},{id:"control-center",label:"随身控制台",action:"control-center"},{id:"task-center",label:"任务与通知",action:"task-center"}]
        onTriggered:function(action,payload){root.act(action,payload)}
       }
      }
      ColumnLayout {
       visible:root.session.phase!=="error"&&root.page==="桌面";Layout.fillWidth:true;spacing:root.themeTokens.metrics.gap
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"全局桌面 · 打开时所在桌面带 ✓";color:root.fg;role:"body"}
       GridLayout{Layout.fillWidth:true;columns:2;rowSpacing:10;columnSpacing:10
        Repeater{model:root.snapshot.workspaces||[]
         WB.TouchButton{themeTokens:root.themeTokens;required property var modelData;Layout.fillWidth:true;Layout.minimumHeight:66;text:(root.snapshot.current===modelData.id?"✓ ":"")+"桌面 "+modelData.id+" · "+modelData.count+" 个窗口";foreground:root.fg;accent:root.themeTokens.colors.accent;enabled:!root.busy;onClicked:root.act("switch",{workspace:modelData.id})}
        }
       }

       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"移动打开时的窗口到桌面";color:root.fg;role:"body"}
       GridLayout{Layout.fillWidth:true;columns:body.numberColumns(width,columnSpacing,5);rowSpacing:8;columnSpacing:8
        Repeater{model:10
         WB.TouchButton{themeTokens:root.themeTokens;required property int index;Layout.fillWidth:true;text:String(index+1);foreground:root.fg;accent:root.themeTokens.colors.accent;enabled:!root.busy&&!!root.snapshot.target;onClicked:root.act("move",{workspace:index+1})}
        }
       }
      }
      ColumnLayout {
       visible:root.session.phase!=="error"&&root.page==="窗口";Layout.fillWidth:true;spacing:root.themeTokens.metrics.gap
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:root.snapshot.windowLabel||"当前窗口";elide:Text.ElideRight;maximumLineCount:1;color:root.fg;role:"title"}
       WB.ActionGrid {
        Layout.fillWidth:true;themeTokens:root.themeTokens;busy:root.busy;columns:3
        items:[{id:"maximize",label:"放大 / 还原",action:"maximize",enabled:!!root.snapshot.target},{id:"float",label:"浮动 / 平铺",action:"float",enabled:!!root.snapshot.target},{id:"hide",label:"暂存窗口",action:"hide",enabled:!!root.snapshot.target},{id:"restore",label:"找回暂存",action:"restore"},{id:"center",label:"浮动窗口居中",action:"center",enabled:!!root.snapshot.target},{id:"close",label:"关闭打开时窗口",action:"close",tone:"urgent",enabled:!!root.snapshot.target}]
        onTriggered:function(action,payload){root.act(action,payload)}
       }
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"切换桌面";color:root.fg;role:"body"}
       GridLayout{Layout.fillWidth:true;columns:body.numberColumns(width,columnSpacing,width>=550?9:5);rowSpacing:8;columnSpacing:6
        Repeater{model:9
         WB.TouchButton{themeTokens:root.themeTokens;required property int index;objectName:"quickDesktop"+(index+1);Layout.fillWidth:true;Layout.minimumHeight:52;text:String(index+1);selected:root.snapshot.current===index+1;foreground:root.fg;accent:root.themeTokens.colors.accent;enabled:!root.busy;onClicked:root.act("switch",{workspace:index+1})}
        }
       }
      }
      ColumnLayout {
       visible:root.session.phase!=="error"&&root.page==="按键";Layout.fillWidth:true;spacing:root.themeTokens.metrics.gap
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"自定义短按 · 长按暂保留原行为";color:root.fg;role:"body"}
       Repeater{model:["P1","P2","P3","rotation"]
        RowLayout{
         required property string modelData;Layout.fillWidth:true
         WB.StyledText{themeTokens:root.themeTokens;text:parent.modelData==="rotation"?"旋转键":parent.modelData;Layout.preferredWidth:Math.max(72,implicitWidth);color:root.fg;role:"title"}
         ComboBox{
          id:choice;Layout.fillWidth:true;Layout.minimumHeight:52
          property string button:parent.modelData
          property var actions:button==="P3"?["authorize","disabled"]:["keyboard","voice","navigation","desktops","windows","control-center","disabled"]
          model:actions.map(a=>(root.snapshot.labels||{})[a]||a)
          currentIndex:actions.indexOf((root.snapshot.bindings||{})[button])
          enabled:!root.busy
          onActivated:{var b=Object.assign({},root.snapshot.bindings);b[button]=actions[currentIndex];root.act("bindings",{bindings:b})}
         }
        }
       }
       WB.StyledText{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"P3 只用于已有系统授权；电源与音量键保持系统原有行为。";color:root.fg;role:"body";wrapMode:Text.Wrap}
       WB.TouchButton{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"恢复这台平板的默认按键";foreground:root.fg;accent:root.themeTokens.colors.accent;enabled:!root.busy;onClicked:root.act("defaults")}
      }
    }
   }
  }
 }
}
