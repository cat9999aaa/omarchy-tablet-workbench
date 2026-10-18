import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import qs.Ui as Ui
import qs.Commons
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
 ContractState { id: readings }
 onOpenedChanged: {
  if(opened){readings.beginOpen();refresh()}
  else {readings.closeSession();if(activeRead)activeRead.cancelRead();allowed=false}
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
 function open() { if(!opener.running&&!opened){wantOpen=true;opener.running=true} }
 function toggle() { if(opened)close();else open() }
 function close() { wantOpen=false;readings.closeSession();if(activeRead)activeRead.cancelRead();controller.hide();confirmation=null;allowed=false }
 function gesture() { if(!opened)open();else {expanded=true;refresh()} }
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
 IpcHandler {
  target: "pcadmin.controlCenter"
  function ready(): bool {return true}
  function open(): void {root.open()}
  function close(): void {root.close()}
  function toggle(): void {root.toggle()}
  function gesture(): void {root.gesture()}
  function expand(): void {root.expanded=true;root.open()}
  function state(): string {return JSON.stringify({uiRevision:3,version:"0.1.8",nightlight:root.data.nightlight,flight:root.flight,opened:root.opened,expanded:root.expanded,width:card.width,height:card.height,columns:tiles.columns,locked:!root.allowed,network:root.labelNetwork(),touch:root.touchLabel(),batteryCount:root.batteries.length})}
 }
 Ui.BarIconButton { id:barButton;anchors.fill:parent;bar:root.bar;text:"󰒓";onPressed:root.toggle() }
 Process {
  id: opener;command:["python",root.helper,"prepare-open"]
  stdout: StdioCollector { onStreamFinished: {
   try {const d=JSON.parse(text);if(d.ok===true&&root.wantOpen){root.allowed=true;root.controller.show()}else root.feedback="锁屏或键盘未收起，暂未打开"}catch(e){root.feedback="无法确认打开条件"}
  } }
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
  onRunningChanged: if(!running)stdinEnabled=true
  stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);root.feedback=d.ok?"请求已提交，状态以实际读回为准":d.reason || ({locked:"锁屏中，操作已拒绝",busy:"同类操作正在执行",cancelled:"认证已取消或已锁屏",confirmation:"请确认操作"}[d.stage] || "操作未完成")}catch(e){root.feedback="操作未完成"}}}
  onExited:root.refresh()
 }
 PanelWindow {
  id: window
  visible:root.opened
  screen:Quickshell.screens[0]
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
     Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:width;contentHeight:body.implicitHeight;boundsBehavior:Flickable.StopAtBounds
     ColumnLayout {
      id:body;width:parent.width;spacing:10
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
       id:tiles;Layout.fillWidth:true;columns:Model.layout(window.width,window.height).columns;columnSpacing:8;rowSpacing:8;visible:!root.expanded&&!root.flight.entertainment
       Repeater {
        model:[{name:"Wi-Fi／4G",sub:root.labelNetwork(),action:"network"},
          {name:"代理",sub:"TUN · "+root.b("tun").label,action:root.b("tun").value===true?"proxy-off":"proxy-on",available:root.b("tun").known&&root.b("proxy_core").known},
          {name:"ZeroTier",sub:root.b("zero").known?(root.b("zero").value?"服务在线":"等待连接"):root.b("zero").label,action:"zero"},
          {name:"触摸模式",sub:root.touchLabel(),action:readings.touchValue===1?"touch-normal":readings.touchValue===0?"touch-glove":"touch-refresh"},
          {name:"输入法",sub:"P1 同一入口",action:"keyboard"},
          {name:"夜间模式",sub:root.nightlightLabel(),action:"nightlight"},
          {name:"飞行模式",sub:typeof root.data.flight_active!=="boolean"?"待读取":"关闭无线 · 离线娱乐",action:root.data.flight_saved?"flight-off":"flight-on",available:typeof root.data.flight_active==="boolean"},
          {name:"电源模式",sub:root.data.power_profile||"读取中",action:"power-mode"},
          {name:"仅熄屏",sub:"任务继续 · 不挂起",action:"screen-off"}]
        CButton {
         required property var modelData
         Layout.fillWidth:true;Layout.minimumHeight:68
         objectName:"quick-"+modelData.action
         selected:modelData.action==="nightlight"&&root.b("nightlight").value===true
         text:modelData.name+"\n"+modelData.sub
         enabled:!actionProcess.running&&modelData.available!==false
         onClicked:{if(modelData.action==="zero"){root.expanded=true;root.page="连接"}else if(modelData.action==="power-mode"){root.expanded=true;root.page="设备"}else root.act(modelData.action,{})}
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
        Layout.fillWidth:true;columns:2;columnSpacing:8;rowSpacing:8
        Repeater {
         model:root.page==="连接"?[{label:"网络与 GPS 详情",op:"network"},{label:"蓝牙",op:"bluetooth"}]:
          root.page==="设备"?[{label:"双电池与充放电记录",op:"power"},{label:"夜间模式 · "+root.nightlightLabel(),op:"nightlight"},{label:"显示设置",op:"monitor"},{label:"省电",op:"power-saver"},{label:"均衡",op:"balanced"},{label:"手套／原装笔",op:"touch-glove"},{label:"普通触摸（本次）",op:"touch-normal"},{label:"刷新触摸模式",op:"touch-refresh"},{label:"锁屏",op:"lock"}]:
          root.page==="工作"?[{label:"输入法",op:"keyboard"},{label:"声音设置",op:"audio"},{label:"当前窗口操作",op:"windows"}]:[{label:"视频播放器",op:"player"},{label:"音乐播放器",op:"music"},{label:"小说阅读器",op:"reader"},{label:"离线街机",op:"games"},{label:"飞行模式…",op:"flight-on"}]
         CButton {required property var modelData;Layout.fillWidth:true;text:modelData.label;enabled:!actionProcess.running&&modelData.op!=="unavailable";onClicked:root.act(modelData.op,{})}
        }
       }
      }
      Text {Layout.fillWidth:true;color:root.fg;text:"亮度 "+(root.data.brightness===null||root.data.brightness===undefined?"不可用":Math.round(brightness.value)+"%");font.pixelSize:15}
      Slider {id:brightness;Layout.fillWidth:true;Layout.minimumHeight:48;from:0;to:100;stepSize:1;value:root.data.brightness||0;enabled:root.data.brightness!==null&&root.data.brightness!==undefined&&!actionProcess.running;onPressedChanged:if(!pressed&&enabled)root.act("brightness",{percent:Math.round(value)})}
      RowLayout {
       Layout.fillWidth:true
       Text {Layout.fillWidth:true;color:root.fg;text:"音量 "+(root.audioAvailable?Math.round(volumeSlider.value)+"%":"无输出设备");font.pixelSize:15}
       CButton {text:root.muted?"取消静音":"静音";enabled:root.audioAvailable&&!actionProcess.running;onClicked:root.act("mute",{})}
      }
      Slider {id:volumeSlider;Layout.fillWidth:true;Layout.minimumHeight:48;from:0;to:100;stepSize:1;value:root.volume;enabled:root.audioAvailable&&!actionProcess.running;onPressedChanged:if(!pressed&&enabled)root.act("volume",{percent:Math.round(value)})}
      Text {Layout.fillWidth:true;color:root.fg;opacity:.65;font.pixelSize:13;wrapMode:Text.Wrap;text:"麦克风："+(root.source&&root.source.audio?(root.source.audio.muted?"已静音":"可用 · 静音关闭"):"未知")+"  ·  "+(root.data.observed_at?new Date(root.data.observed_at*1000).toLocaleTimeString():"读取中")}
      Text {Layout.fillWidth:true;color:root.orange;font.pixelSize:14;wrapMode:Text.Wrap;visible:root.feedback!=="";text:root.feedback}
     }
    }
    ColumnLayout {
     visible:root.confirmation!==null;Layout.fillWidth:true
     Text {Layout.fillWidth:true;color:root.orange;font.pixelSize:15;wrapMode:Text.Wrap;text:root.confirmation&&root.confirmation.name==="touch-normal"?"切换普通模式后，原装无源笔可能不能使用；重启仍恢复手套模式。":root.confirmation&&root.confirmation.name==="proxy-off"?"关闭代理可能中断 ChatGPT 等应用的联网。":"进入离线娱乐：关闭 Wi-Fi、4G 射频和蓝牙，停止网络连接。蓝牙手柄和耳机也会断开；现有工作保留。退出后恢复原开关。"}
     RowLayout {Layout.fillWidth:true;CButton {Layout.fillWidth:true;text:"取消";onClicked:root.confirmation=null}CButton {Layout.fillWidth:true;text:"确认执行";onClicked:{const c=root.confirmation;root.confirmation=null;if(c)root.act(c.name,c.params,true)}}}
    }
   }
   focus:true
   Keys.onEscapePressed:root.close()
  }
 }
 component CButton: WB.TouchButton {
  foreground:root.fg;accent:root.purple;font.family:Style.font.family;font.pixelSize:15
 }
}
