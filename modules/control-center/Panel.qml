import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Wayland
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import qs.Ui as Ui
import qs.Commons
import "OutputRoute.js" as OutputRoute
import "ModeProtocol.js" as ModeProtocol
import "ControlActions.js" as Actions
import "ControlModel.js" as Model
import "ContractModel.js" as ContractModel
import "Workbench" as WB
import "Workbench/Layout.js" as LayoutModel
import "Workbench/State.js" as SharedState

Ui.Panel {
 id: root
 moduleName: "pcadmin.control-center"
 manageIpc: false
 property var data: ({})
 readonly property var flight: Model.flightView(data,Date.now()/1000)
 property bool expanded: false
 property string page: "连接"
 property string feedback: ""
 property var confirmation: null
 property bool allowed: false
 property bool wantOpen: false
 property var activeRead: null
 property int routeEpoch: 0
 property bool transferPending: false
 property var transferCallbacks: []
 property bool destroying: false
 property var hostScreen: null
 readonly property var attachedScreen: {
  const w=root.QsWindow.window
  return w && Quickshell.screens.indexOf(w.screen)>=0 ? w.screen : null
 }
 property var activeSettings: null
 property string modeChoice: "auto"
 property bool modeEligible: false
 property bool modeInitialized: false
 property bool modeSaved: true
 property string savePending: ""
 property string suggestedMode: "tablet"
 property string appliedMode: "tablet"
 onAttachedScreenChanged: if((opened||wantOpen||transferPending) && attachedScreen!==hostScreen)close()
 onActiveReadChanged: releaseTransfer()
 onActiveSettingsChanged: releaseTransfer()
 ModeSession {
  id:deviceMode
  observerCommand:[Qt.resolvedUrl("bin/pcadmin-device-observer").toString().replace("file://","")]
  sampleCommand:["python",root.helper,"mode-step"]
  onModeSuggested:mode=>root.suggestedMode=mode
  onHealthChanged:if(health!=="observed"&&root.modeChoice==="auto")root.suggestedMode=root.appliedMode
  onStopped:Qt.callLater(root.releaseTransfer)
 }
 function peers() {return bar && typeof bar.moduleWidgets==="function" ? bar.moduleWidgets(moduleName).filter(p=>p && p.destroying===false && typeof p.requestOpen==="function") : []}
 function targetFor(name) {
  const list=peers(), candidates=list.map((p,i)=>({id:String(i),screenName:p.attachedScreen?p.attachedScreen.name:"",attached:p.attachedScreen!==null,visibleSlot:p.width>0&&p.height>0}))
  const id=OutputRoute.pickTarget(candidates,name)
  return id===null?null:list[Number(id)]
 }
 function focusedTarget() {return targetFor(Hyprland.focusedMonitor?Hyprland.focusedMonitor.name:"")}
 function currentPanel() {const items=peers().filter(p=>p.opened);return items.length===1?items[0]:null}
 function route(method) {
  const current=currentPanel()
  if(method==="close" || (method==="toggle" && current)) {peers().filter(p=>p.opened||p.wantOpen||p.transferPending).forEach(p=>p.close());return}
  if((method==="gesture"||method==="expand") && current){current.expanded=true;current.refresh();return}
  const target=focusedTarget()
  if(target){if(method==="expand")target.expanded=true;target.open()}
 }
 function releaseTransfer() {
  if(!deviceMode.isStopped || activeRead || activeSettings || opener.running)return
  const callbacks=transferCallbacks;transferCallbacks=[];callbacks.forEach(f=>f())
 }
 function closeForTransfer(callback) {transferCallbacks=transferCallbacks.concat([callback]);closeInternal();releaseTransfer()}
 function requestOpen() {
  if(destroying || !attachedScreen || targetFor(attachedScreen.name)!==root || opener.running)return
  hostScreen=attachedScreen;modeInitialized=false;wantOpen=true;opener.running=true
 }
 function startSettings(op, choice) {
  if(!opened || !hostScreen || activeSettings)return
  if(op==="mode-preference-write")modeSaved=false
  const value={output_key:hostScreen.name};if(op==="mode-preference-write")value.choice=choice
  activeSettings=settingsRequest.createObject(root,{operation:op,epoch:routeEpoch,payload:JSON.stringify(value)})
  if(activeSettings)activeSettings.running=true
  else {modeSaved=false;finishModeSetup(false)}
 }
 function finishModeSetup(eligible) {
  if(!opened)return
  modeEligible=eligible;modeInitialized=true
  deviceMode.begin(eligible,modeChoice,appliedMode)
 }
 function settingsResult(op, text, code, epoch) {
  if(epoch!==routeEpoch || !opened)return
  let value=null
  try {if(code===0 && ModeProtocol.size(text)<=65536)value=JSON.parse(text)}catch(e){}
  if(op==="mode-preference-read") {
   modeChoice=value&&value.schema_version===1&&["auto","tablet","desktop"].indexOf(value.choice)>=0?value.choice:"auto"
   modeSaved=!!(value&&value.reason_code==="ok")
   startSettings("output-policy","")
  } else if(op==="output-policy")finishModeSetup(!!(value&&value.schema_version===1&&value.eligible===true))
  else {modeSaved=!!(value&&value.saved===true);if(savePending){const next=savePending;savePending="";startSettings("mode-preference-write",next)}}
 }
 function selectMode(choice) {
  if(!modeInitialized || ["auto","tablet","desktop"].indexOf(choice)<0)return
  modeChoice=choice;modeSaved=false;deviceMode.choose(choice)
  if(activeSettings)savePending=choice;else startSettings("mode-preference-write",choice)
 }
 Component.onDestruction:{destroying=true;routeEpoch++;deviceMode.close();if(activeSettings)activeSettings.signal(9);if(activeRead)activeRead.signal(9);if(opener.running)opener.signal(9)}
 ContractState { id: readings }
 property int buttonPressCount:0
 readonly property bool anyPointerPressed:buttonPressCount>0||brightness.pressed||volumeSlider.pressed
 onSuggestedModeChanged:Qt.callLater(applySuggestedMode)
 onAnyPointerPressedChanged:Qt.callLater(applySuggestedMode)
 onConfirmationChanged:Qt.callLater(applySuggestedMode)
 function quickView() {return {network:labelNetwork(),tun:b("tun"),proxy:b("proxy_core"),zero:b("zero"),touch:touchLabel(),touchValue:readings.touchValue,night:nightlightLabel(),flightActive:data.flight_active,flightSaved:data.flight_saved,power:data.power_profile}}
 function applySuggestedMode() {
  const next=Model.selectLayout(suggestedMode,appliedMode,{confirmation:confirmation!==null,action:actionProcess.running,pointer:anyPointerPressed})
  if(next===appliedMode)return
  const previous=body.Window.window?body.Window.window.activeFocusItem:null
  const key=previous&&previous.stableActionId?previous.stableActionId:""
  appliedMode=next
  Qt.callLater(function(){root.restoreModeFocus(key,previous)})
 }
 function ensureControlVisible(control) {
  Qt.callLater(function(){
   if(!control||typeof control.mapToItem!=="function"||!control.visible)return
   let ancestor=control;while(ancestor&&ancestor!==body)ancestor=ancestor.parent
   if(ancestor!==body)return
   const y=control.mapToItem(body,0,0).y
   if(y<scroll.contentY)scroll.contentY=y
   else if(y+control.height>scroll.contentY+scroll.height)scroll.contentY=y+control.height-scroll.height
   scroll.contentY=Math.max(0,Math.min(scroll.contentY,scroll.contentHeight-scroll.height))
  })
 }
 function restoreModeFocus(key,previous) {
  function find(item) {
   if(!item||!item.visible)return null
   if(key && item.stableActionId===key && item.enabled)return item
   for(let i=0;i<item.children.length;i++){const result=find(item.children[i]);if(result)return result}
   return null
  }
  const target=find(body)
  if(target){target.forceActiveFocus();ensureControlVisible(target)}
  else if(previous&&typeof previous.forceActiveFocus==="function"&&previous.visible&&previous.enabled)previous.forceActiveFocus()
  else if(previous)modeAuto.forceActiveFocus()
 }
 onOpenedChanged: {
  if(opened){readings.beginOpen();refresh()}
  else {readings.closeSession();if(activeRead)activeRead.cancelRead();deviceMode.close();if(activeSettings)activeSettings.cancel();allowed=false}
 }
 readonly property string helper: Quickshell.env("PCADMIN_CONTROL_HELPER") || Quickshell.env("HOME")+"/Projects/pcadmin/tools/control-center/control_center.py"
 readonly property color bg: Color.popups.background
 readonly property color fg: Color.foreground
 readonly property color purple: Color.accent
 readonly property color green: Color.accent
 readonly property color orange: Color.urgent
 readonly property var sink: Pipewire.defaultAudioSink
 readonly property var source: Pipewire.defaultAudioSource
 property string resolvedSink: ""
 readonly property var volumeSink: {
  const nodes=Pipewire.nodes ? Pipewire.nodes.values : []
  for(let i=0;i<nodes.length;i++)if(nodes[i] && nodes[i].name===resolvedSink)return nodes[i]
  return sink
 }
 readonly property bool audioAvailable: !!(volumeSink && volumeSink.audio)
 readonly property int volume: audioAvailable ? Math.round(volumeSink.audio.volume*100) : 0
 readonly property bool muted: audioAvailable && volumeSink.audio.muted
 readonly property var batteries: {
  const nodes=UPower.devices ? UPower.devices.values : [], result=[]
  for(let i=0;i<nodes.length;i++)if(nodes[i].isPresent && nodes[i].type===UPowerDeviceType.Battery)result.push(nodes[i])
  return result
 }
 PwObjectTracker { objects: [root.sink,root.source,root.volumeSink].filter(x=>!!x) }
 function f(key) { const f=SharedState.fieldState(data[key],Date.now()/1000);return f.known?String(f.value):f.label }
 function b(key) { return SharedState.fieldState(data[key],Date.now()/1000) }
 function labelNetwork() {return ({"4g":"中国电信 4G",wifi:"Wi-Fi",ethernet:"有线网络",none:"未连接"})[f("physical_uplink")] || f("physical_uplink")}
 function nightlightLabel() {const n=b("nightlight");return n.known?(n.value?"已开启 · 暖色":"已关闭 · 原色"):"状态待确认 · 点按切换"}
 function batteryText() {
  return batteries.map((x,i)=>"电池"+(i+1)+" "+Math.round(x.percentage*100)+"%"+(x.state===UPowerDeviceState.Charging?" ↑":"")).join("  ·  ") || "电池状态未知"
 }
 function refresh() {
  if(opened && !activeRead) {
   const token=readings.startRequest()
   if(token!==null) {
    activeRead=readRequest.createObject(root,{requestToken:token})
    if(activeRead)activeRead.running=true
    else readings.fail(token,"start_failed")
   }
  }
  if(opened&&!sinkPoll.running)sinkPoll.running=true
 }
 function open() {
  if(!attachedScreen || targetFor(attachedScreen.name)!==root)return
  if(opened){refresh();return}
  const list=peers()
  OutputRoute.handoff(list,root,()=>!root.destroying && root.attachedScreen!==null && root.targetFor(root.attachedScreen.name)===root)
 }
 function toggle() {if(opened)close();else open()}
 function closeInternal() {
  wantOpen=false;readings.closeSession();if(activeRead)activeRead.cancelRead()
  deviceMode.close();if(activeSettings)activeSettings.cancel();savePending=""
  if(opener.running)opener.signal(15)
  controller.hide();confirmation=null;allowed=false
 }
 function close() {routeEpoch++;transferPending=false;closeInternal()}
 function gesture() {if(!opened)open();else {expanded=true;refresh()}}
 function act(name,params,confirmed) {
  if(actionProcess.running || !allowed)return
  if(!confirmed && (name==="proxy-off" || name==="flight-on" || name==="touch-normal")) {
   confirmation={name:name,params:params||{}};return
  }
  feedback="正在处理…"
  actionProcess.request=JSON.stringify({action:name,params:params||{},confirmed:confirmed===true})
  actionProcess.running=true
  if(["network","power","audio","monitor","bluetooth","keyboard","windows","player","music","reader","games","screen-off","lock"].indexOf(name)>=0)close()
 }
 function touchLabel() {return readings.touchText}
 function summary() {
  if(flight.entertainment)return "飞行娱乐 · "+flight.label+"\n"+(flight.verified?"Wi-Fi / 4G / 蓝牙已关 · 联网已停":"请检查关闭结果，或重试关闭无线")
  return labelNetwork()+"  ·  "+(f("internet")==="ok"?"可上网":f("internet")==="failed"?"联网检测异常":f("internet"))+"\n"+
    "代理核心 "+b("proxy_core").label+"  ·  TUN "+b("tun").label
 }
 function serializedState() {return JSON.stringify({uiRevision:5,version:"0.2.0",nightlight:data.nightlight,flight:flight,opened:opened,expanded:expanded,width:card.width,height:card.height,columns:tiles.columns,locked:!allowed,network:labelNetwork(),touch:touchLabel(),batteryCount:batteries.length,modeChoice:modeChoice,effectiveMode:appliedMode,modeHealth:deviceMode.health})}
 IpcHandler {
  target: "pcadmin.controlCenter"
  function ready(): bool {return root.focusedTarget()!==null && !root.peers().some(p=>p.transferPending)}
  function open(): void {root.route("open")}
  function close(): void {root.route("close")}
  function toggle(): void {root.route("toggle")}
  function gesture(): void {root.route("gesture")}
  function expand(): void {root.route("expand")}
  function state(): string {const target=root.currentPanel()||root.focusedTarget();return target?target.serializedState():JSON.stringify({uiRevision:5,version:"0.2.0",opened:false,locked:true,available:false})}

 }
 Ui.BarIconButton { id:barButton;anchors.fill:parent;bar:root.bar;text:"󰒓";onPressed:root.toggle() }
 Process {
  id: opener;onExited:function(code){if(code!==0&&root.wantOpen)root.close();root.releaseTransfer()}
  command:["python",root.helper,"prepare-open"]
  stdout: StdioCollector { onStreamFinished: {
   try {const d=JSON.parse(text);if(d.ok===true&&root.wantOpen&&root.attachedScreen===root.hostScreen){root.allowed=true;root.controller.show();root.startSettings("mode-preference-read","")}else root.feedback="锁屏或键盘未收起，暂未打开"}catch(e){root.feedback="无法确认打开条件"}
  } }
 }
 Component {
  id:settingsRequest
  Process {
   id:request
   required property string operation
   required property int epoch
   required property string payload
   property bool cancelled:false
   property bool timedOut:false
   property bool disposed:false
   property bool started:false
   property bool streamDone:false
   property bool exitSeen:false
   property int code:-1
   command:["python",root.helper,operation]
   stdinEnabled:true
   function cancel(){cancelled=true;deadline.stop();if(running)signal(15);reap.start()}
   function complete(text,resultCode) {
    if(disposed)return
    disposed=true;deadline.stop();reap.stop()
    const op=operation,token=epoch,deliver=!cancelled||timedOut
    if(root.activeSettings===request)root.activeSettings=null
    if(deliver)root.settingsResult(op,text,resultCode,token)
    destroy();root.releaseTransfer()
   }
   function finish(){if(streamDone&&exitSeen)complete(output.text,code)}
   onStarted:{started=true;write(payload);stdinEnabled=false}
   stdout:StdioCollector {
    id:output;waitForEnd:false
    onDataChanged:if(ModeProtocol.size(text)>65536){request.timedOut=true;request.cancel()}
    onStreamFinished:{request.streamDone=true;request.finish()}
   }
   onExited:function(exitCode,exitStatus){code=exitStatus===0?exitCode:-1;exitSeen=true;finish()}
   onRunningChanged:if(!running&&!started)Qt.callLater(function(){if(!disposed&&!running&&!started)complete("",-1)})
   property Timer deadline:Timer {interval:6000;running:true;onTriggered:{request.timedOut=true;request.cancel()}}
   property Timer reap:Timer {interval:500;onTriggered:{if(request.running){request.signal(9);restart()}else request.complete("",-1)}}
  }
 }
 Component {
  id: readRequest
  Process {
   id: request
   required property string requestToken
   property bool streamDone: false
   property bool exitSeen: false
   property int code: -1
   property bool cancelled: false
   property bool disposed: false
   command:["python",root.helper,"status-readonly"]
   function dispose() {
    if(disposed)return
    disposed=true;deadline.stop();cancelDeadline.stop()
    if(root.activeRead===request)root.activeRead=null
    request.destroy()
   }
   function cancelRead() {
    if(disposed||cancelled)return
    cancelled=true;readings.fail(requestToken,"cancelled");deadline.stop()
    if(running)signal(15)
    cancelDeadline.start()
   }
   function finishIfDone() {
    if(disposed || !exitSeen || !streamDone)return
    if(!cancelled && readings.current(requestToken)) {
     if(readings.finish(requestToken,output.text,code,true))root.data=readings.legacy
     else root.feedback="状态暂不可用"
     if(!readings.sessionOpen)root.close()
    }
    dispose()
   }
   stdout: StdioCollector {
    id:output;waitForEnd:false
    onDataChanged:if(ContractModel.utf8Size(text)>65536)request.cancelRead()
    onStreamFinished:{request.streamDone=true;request.finishIfDone()}
   }
   onExited:function(exitCode,exitStatus){code=exitStatus===0?exitCode:-1;exitSeen=true;finishIfDone()}
   property Timer deadline: Timer {
    interval:20000;running:true
    onTriggered:{readings.fail(request.requestToken,"read_timeout");request.cancelRead()}
   }
   property Timer cancelDeadline: Timer {
    interval:2000
    onTriggered:{if(request.running){request.signal(9);restart()}else request.dispose()}
   }
  }
 }
 Process { id:sinkPoll;command:["omarchy","audio","output","sink"];stdout:StdioCollector {onStreamFinished:root.resolvedSink=text.trim()} }
 Process {
  id: lockPoll;command:["python",root.helper,"lock-state"]
  stdout: StdioCollector {onStreamFinished:{try{if(JSON.parse(text).locked!==false)root.close()}catch(e){root.close()}}}
  onExited: function(code) {if(code!==0)root.close()}
 }
 Timer {interval:500;repeat:true;running:root.opened;onTriggered:if(!lockPoll.running)lockPoll.running=true}
 Timer {interval:5000;repeat:true;running:root.opened;onTriggered:root.refresh()}
 Process {
  id:actionProcess;property string request:"";command:["python",root.helper,"action"];stdinEnabled:true
  onStarted: {write(request);stdinEnabled=false}
  onRunningChanged: {if(!running)stdinEnabled=true;Qt.callLater(root.applySuggestedMode)}
  stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);root.feedback=d.ok?"请求已提交，状态以实际读回为准":d.reason || ({locked:"锁屏中，操作已拒绝",busy:"同类操作正在执行",cancelled:"认证已取消或已锁屏",confirmation:"请确认操作"}[d.stage] || "操作未完成")}catch(e){root.feedback="操作未完成"}}}
  onExited:root.refresh()
 }
 PanelWindow {
  id: window
  visible:root.opened
  screen:root.hostScreen
  anchors {top:true;bottom:true;left:true;right:true}
  color:"transparent"
  exclusionMode:ExclusionMode.Ignore
  WlrLayershell.namespace:"pcadmin-control-center"
  WlrLayershell.layer:WlrLayer.Overlay
  WlrLayershell.keyboardFocus:root.opened?WlrKeyboardFocus.Exclusive:WlrKeyboardFocus.None
  MouseArea {anchors.fill:parent;onPressed:root.close()}
  Rectangle {
   id:card;anchors.top:parent.top;anchors.topMargin:12;anchors.horizontalCenter:parent.horizontalCenter
   width:LayoutModel.panelSize(window.width,window.height).width
   height:LayoutModel.panelSize(window.width,window.height).height
   color:root.bg;radius:14;border.color:root.purple;border.width:2
   opacity:root.opened?1:0
   Behavior on opacity {NumberAnimation {duration:120}}
   MouseArea {anchors.fill:parent}
   ColumnLayout {
    anchors.fill:parent;anchors.margins:16;spacing:10
    WB.PanelHeader {
     Layout.fillWidth:true;Layout.preferredHeight:implicitHeight
     title:root.flight.entertainment?"飞行娱乐":"启明 · 随身控制台"
     foreground:root.fg;accent:root.purple;fontFamily:Style.font.family
     onCloseRequested:root.close()
    }
    Text {Layout.fillWidth:true;text:root.summary();color:root.green;font.pixelSize:15;wrapMode:Text.Wrap}
    Text {Layout.fillWidth:true;text:root.batteryText()+"  ·  温度 "+readings.temperatureText;color:root.fg;font.pixelSize:14;wrapMode:Text.Wrap}
    Text {Layout.fillWidth:true;text:"最近一次采样结果 · 触摸开机默认："+readings.bootDefaultLabel;color:root.fg;opacity:.65;font.pixelSize:12;wrapMode:Text.Wrap}
    Flickable {
     id:scroll
     Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:width;contentHeight:body.implicitHeight;boundsBehavior:Flickable.StopAtBounds
     ColumnLayout {
      id:body;width:parent.width;spacing:10
      Text {objectName:"mode-status";Layout.fillWidth:true;text:Model.modeLabel(root.modeChoice,deviceMode.health,root.appliedMode,root.modeSaved);color:root.fg;font.pixelSize:14;wrapMode:Text.Wrap}
      RowLayout {
       Layout.fillWidth:true;spacing:8
       CButton {id:modeAuto;objectName:"mode-auto";Layout.fillWidth:true;Layout.minimumWidth:0;text:"自动";selected:root.modeChoice==="auto";enabled:root.modeInitialized;onClicked:root.selectMode("auto")}
       CButton {objectName:"mode-tablet";Layout.fillWidth:true;Layout.minimumWidth:0;text:"平板";selected:root.modeChoice==="tablet";enabled:root.modeInitialized;onClicked:root.selectMode("tablet")}
       CButton {objectName:"mode-desktop";Layout.fillWidth:true;Layout.minimumWidth:0;text:"桌面";selected:root.modeChoice==="desktop";enabled:root.modeInitialized;onClicked:root.selectMode("desktop")}
      }
      CButton {visible:!root.flight.entertainment;Layout.fillWidth:true;text:root.expanded?"返回快捷控制":"查看全部功能";onClicked:root.expanded=!root.expanded}
      ColumnLayout {
       visible:root.flight.entertainment;Layout.fillWidth:true;spacing:12
       Text {Layout.fillWidth:true;text:"离线时间，随你安排";font.pixelSize:22;font.bold:true;color:root.fg}
       Text {Layout.fillWidth:true;text:"使用已下载的内容和本地存档。此模式会关闭蓝牙，请准备触屏、USB 手柄或有线耳机。";font.pixelSize:15;color:root.fg;wrapMode:Text.Wrap}
       GridLayout {
        columns:2;Layout.fillWidth:true;columnSpacing:10;rowSpacing:10
        Repeater {model:[{label:"游戏\n离线街机与存档",op:"games"},{label:"视频\n打开本地影片",op:"player"},{label:"音乐\n本地音乐库",op:"music"},{label:"阅读\n继续读书",op:"reader"}]
         CButton {required property var modelData;Layout.fillWidth:true;Layout.minimumHeight:90;text:modelData.label;enabled:!actionProcess.running;onClicked:root.act(modelData.op,{})}
        }
       }
       RowLayout {
        Layout.fillWidth:true
        CButton {Layout.fillWidth:true;text:"电池与续航";onClicked:root.act("power",{})}
        CButton {Layout.fillWidth:true;text:"输入法";onClicked:root.act("keyboard",{})}
        CButton {Layout.fillWidth:true;text:"锁屏";onClicked:root.act("lock",{})}
       }
       CButton {Layout.fillWidth:true;text:"夜间模式 · "+root.nightlightLabel();enabled:!actionProcess.running;onClicked:root.act("nightlight",{})}
       CButton {Layout.fillWidth:true;visible:!root.flight.verified;text:"重试关闭无线";enabled:!actionProcess.running;onClicked:root.act("flight-on",{})}
       CButton {Layout.fillWidth:true;text:"退出飞行娱乐 · 恢复原网络开关";enabled:!actionProcess.running;onClicked:root.act("flight-off",{})}
      }
      GridLayout {
       id:tiles;Layout.fillWidth:true;columns:root.appliedMode==="desktop"?1:Model.layout(window.width,window.height).columns;columnSpacing:8;rowSpacing:8;visible:!root.expanded&&!root.flight.entertainment
       Repeater {
        model:Actions.ids(root.appliedMode)
        ColumnLayout {
         required property string modelData
         required property int index
         readonly property var entry:Actions.quick(root.quickView())[modelData]
         Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
         Text {Layout.fillWidth:true;visible:root.appliedMode==="desktop"&&(index===0||Actions.quick(root.quickView())[Actions.ids(root.appliedMode)[index-1]].group!==entry.group);text:entry.group;color:root.purple;font.pixelSize:14;wrapMode:Text.Wrap}
         CButton {
          Layout.fillWidth:true;Layout.minimumWidth:0;Layout.minimumHeight:root.appliedMode==="desktop"?48:68
          stableActionId:parent.modelData
          objectName:"quick-"+entry.action
          selected:entry.action==="nightlight"&&root.b("nightlight").value===true
          text:entry.label+(root.appliedMode==="desktop"?" · ":"\n")+entry.sub
          enabled:!actionProcess.running&&entry.available!==false
          onClicked:{if(entry.action==="zero"){root.expanded=true;root.page="连接"}else if(entry.action==="power-mode"){root.expanded=true;root.page="设备"}else root.act(entry.action,entry.params)}
         }
        }
       }
      }
      GridLayout {
       visible:root.expanded&&!root.flight.entertainment;Layout.fillWidth:true;columns:window.width<620?2:4;columnSpacing:8;rowSpacing:8
       Repeater {model:["连接","设备","工作","旅途"];CButton {required property string modelData;Layout.fillWidth:true;text:modelData;onClicked:root.page=modelData}}
      }
      ColumnLayout {
       Layout.fillWidth:true;visible:root.expanded&&!root.flight.entertainment;spacing:8
       Text {Layout.fillWidth:true;color:root.purple;font.pixelSize:18;text:root.page;wrapMode:Text.Wrap}
       Text {Layout.fillWidth:true;color:root.fg;font.pixelSize:14;wrapMode:Text.Wrap;text:root.page==="连接"?"网络详情保留 Wi-Fi、4G、有线、代理、ZeroTier 和 GPS。打开详情不会切网。":root.page==="设备"?"触摸模式仅影响本次。重启或触屏重连后默认恢复手套／原装笔模式。":root.page==="工作"?"输入法、声音与窗口操作沿用已有入口。AI 对话与任务编排尚未接入。":"已有离线播放器、阅读器和游戏。飞行模式会关闭 Wi-Fi、4G 和蓝牙，后台任务继续但网络会断开。"}
       GridLayout {
        Layout.fillWidth:true;columns:root.appliedMode==="desktop"?1:2;columnSpacing:8;rowSpacing:8
        Repeater {
         model:Actions.group(root.page)
         CButton {required property var modelData;Layout.fillWidth:true;stableActionId:"group-"+modelData.id;text:modelData.label+(modelData.op==="nightlight"?" · "+root.nightlightLabel():"");enabled:!actionProcess.running&&modelData.op!=="unavailable";onClicked:root.act(modelData.op,modelData.params)}
        }
       }
      }
      Text {Layout.fillWidth:true;color:root.fg;text:"亮度 "+(root.data.brightness===null||root.data.brightness===undefined?"不可用":Math.round(brightness.value)+"%");font.pixelSize:15}
      Slider {id:brightness;onActiveFocusChanged:if(activeFocus)root.ensureControlVisible(brightness);Layout.fillWidth:true;Layout.minimumHeight:48;from:0;to:100;stepSize:1;value:root.data.brightness||0;enabled:root.data.brightness!==null&&root.data.brightness!==undefined&&!actionProcess.running;onPressedChanged:if(!pressed&&enabled)root.act("brightness",{percent:Math.round(value)})}
      RowLayout {
       Layout.fillWidth:true
       Text {Layout.fillWidth:true;color:root.fg;text:"音量 "+(root.audioAvailable?Math.round(volumeSlider.value)+"%":"无输出设备");font.pixelSize:15}
       CButton {text:root.muted?"取消静音":"静音";enabled:root.audioAvailable&&!actionProcess.running;onClicked:root.act("mute",{})}
      }
      Slider {id:volumeSlider;onActiveFocusChanged:if(activeFocus)root.ensureControlVisible(volumeSlider);Layout.fillWidth:true;Layout.minimumHeight:48;from:0;to:100;stepSize:1;value:root.volume;enabled:root.audioAvailable&&!actionProcess.running;onPressedChanged:if(!pressed&&enabled)root.act("volume",{percent:Math.round(value)})}
      Text {Layout.fillWidth:true;color:root.fg;opacity:.65;font.pixelSize:13;wrapMode:Text.Wrap;text:"麦克风："+(root.source&&root.source.audio?(root.source.audio.muted?"已静音":"可用 · 静音关闭"):"未知")+"  ·  "+(root.data.observed_at?new Date(root.data.observed_at*1000).toLocaleTimeString():"读取中")}
      Text {Layout.fillWidth:true;color:root.orange;font.pixelSize:14;wrapMode:Text.Wrap;visible:root.feedback!=="";text:root.feedback}
     }
    }
    ColumnLayout {
     visible:root.confirmation!==null;Layout.fillWidth:true
     Text {Layout.fillWidth:true;color:root.orange;font.pixelSize:15;wrapMode:Text.Wrap;text:root.confirmation&&root.confirmation.name==="touch-normal"?"切换普通模式后，原装无源笔可能不能使用；重启仍恢复手套模式。":root.confirmation&&root.confirmation.name==="proxy-off"?"关闭代理可能中断 ChatGPT 等应用的联网。":"进入离线娱乐：关闭 Wi-Fi、4G 射频和蓝牙，停止网络连接。蓝牙手柄和耳机也会断开；现有工作保留。退出后恢复原开关。"}
     RowLayout {Layout.fillWidth:true;CButton {Layout.fillWidth:true;text:"取消";onClicked:root.confirmation=null}CButton {Layout.fillWidth:true;objectName:"confirm-action";text:"确认执行";onClicked:{const c=root.confirmation;root.confirmation=null;if(c)root.act(c.name,c.params,true)}}}
    }
   }
   focus:true
   Keys.onEscapePressed:root.close()
  }
 }
 component CButton: WB.TouchButton {
  id:controlButton
  Keys.onReturnPressed:event=>{if(enabled&&!event.isAutoRepeat){clicked();event.accepted=true}}
  Keys.onEnterPressed:event=>{if(enabled&&!event.isAutoRepeat){clicked();event.accepted=true}}
  onActiveFocusChanged:if(activeFocus)root.ensureControlVisible(controlButton)
  property string stableActionId:""
  property bool trackedPress:false
  onPressedChanged:{if(pressed!==trackedPress){root.buttonPressCount+=pressed?1:-1;trackedPress=pressed}if(!pressed)Qt.callLater(root.applySuggestedMode)}
  Component.onDestruction:if(trackedPress)root.buttonPressCount--
  foreground:root.fg;accent:root.purple;font.family:Style.font.family;font.pixelSize:15
 }
}
