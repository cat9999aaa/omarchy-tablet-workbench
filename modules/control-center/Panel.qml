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

Ui.Panel {
 id: root
 moduleName: "pcadmin.control-center"
 manageIpc: false
 property var data: ({})
 property bool expanded: false
 property string page: "连接"
 property string feedback: ""
 property var confirmation: null
 property bool allowed: false
 readonly property string helper: Quickshell.env("PCADMIN_CONTROL_HELPER") || Quickshell.env("HOME")+"/.local/lib/omarchy-tablet-workbench/control-center/control_center.py"
 readonly property color bg: "#181b24"
 readonly property color fg: "#e7e9f0"
 readonly property color purple: "#b59cf5"
 readonly property color green: "#a6dd83"
 readonly property color orange: "#f0b875"
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
 function f(key) { return Model.displayField(data[key],Date.now()/1000) }
 function b(key) { return Model.booleanState(data[key],Date.now()/1000) }
 function labelNetwork() {return ({"4g":"中国电信 4G",wifi:"Wi-Fi",ethernet:"有线网络",none:"未连接"})[f("physical_uplink")] || f("physical_uplink")}
 function batteryText() {
  return batteries.map((x,i)=>"电池"+(i+1)+" "+Math.round(x.percentage*100)+"%"+(x.state===UPowerDeviceState.Charging?" ↑":"")).join("  ·  ") || "电池状态未知"
 }
 function refresh() { if(opened&&!poll.running)poll.running=true; if(opened&&!sinkPoll.running)sinkPoll.running=true }
 function open() { if(!opener.running&&!opened)opener.running=true }
 function toggle() { if(opened)close();else open() }
 function close() { controller.hide();confirmation=null;allowed=false }
 function gesture() { if(!opened)open();else {expanded=true;refresh()} }
 function act(name,params,confirmed) {
  if(actionProcess.running || !allowed)return
  if(!confirmed && (name==="proxy-off" || name==="flight-on" || name==="touch-normal")) {
   confirmation={name:name,params:params||{}};return
  }
  feedback="正在处理…"
  actionProcess.request=JSON.stringify({action:name,params:params||{},confirmed:confirmed===true})
  actionProcess.running=true
  if(["network","power","audio","monitor","bluetooth","keyboard","windows","player","reader","games","screen-off","lock"].indexOf(name)>=0)close()
 }
 function touchLabel() {const v=f("touch");return v==="1"?"手套／原装笔":v==="0"?"普通触摸":v==="2"?"笔模式":v}
 function summary() {
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
  function state(): string {return JSON.stringify({version:"0.1.3",opened:root.opened,expanded:root.expanded,width:card.width,height:card.height,columns:tiles.columns,locked:!root.allowed,network:root.labelNetwork(),touch:root.touchLabel(),batteryCount:root.batteries.length})}
 }
 Ui.BarIconButton { anchors.fill:parent;bar:root.bar;text:"󰒓";onPressed:root.toggle() }
 Process {
  id: opener;command:["python",root.helper,"prepare-open"]
  stdout: StdioCollector { onStreamFinished: {
   try {const d=JSON.parse(text);if(d.ok===true){root.allowed=true;root.controller.show();root.refresh()}else root.feedback="锁屏或键盘未收起，暂未打开"}catch(e){root.feedback="无法确认打开条件"}
  } }
 }
 Process {
  id: poll;command:["python",root.helper,"status"]
  stdout: StdioCollector { onStreamFinished: {try {root.data=JSON.parse(text);if(root.data.locked!==false)root.close()}catch(e){root.feedback="状态读取失败"}} }
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
   width:Model.layout(window.width,window.height).width
   height:Model.layout(window.width,window.height).height
   color:root.bg;radius:14;border.color:root.purple;border.width:2
   opacity:root.opened?1:0
   Behavior on opacity {NumberAnimation {duration:120}}
   MouseArea {anchors.fill:parent}
   ColumnLayout {
    anchors.fill:parent;anchors.margins:16;spacing:10
    RowLayout {
     Layout.fillWidth:true
     Text {Layout.fillWidth:true;Layout.minimumWidth:0;elide:Text.ElideRight;text:"启明 · 随身控制台";color:root.fg;font.pixelSize:22;font.bold:true}
     CButton {text:root.expanded?"简洁":"详情";onClicked:root.expanded=!root.expanded}
     CButton {text:"收起 ↑";onClicked:root.close()}
    }
    Text {Layout.fillWidth:true;text:root.summary();color:root.green;font.pixelSize:15;wrapMode:Text.Wrap}
    Text {Layout.fillWidth:true;text:root.batteryText()+"  ·  温度 "+root.f("temperature")+(root.data.temperature&&root.data.temperature.available?" °C":"");color:root.fg;font.pixelSize:14;wrapMode:Text.Wrap}
    Flickable {
     Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:width;contentHeight:body.implicitHeight;boundsBehavior:Flickable.StopAtBounds
     ColumnLayout {
      id:body;width:parent.width;spacing:10
      GridLayout {
       id:tiles;Layout.fillWidth:true;columns:Model.layout(window.width,window.height).columns;columnSpacing:8;rowSpacing:8;visible:!root.expanded
       Repeater {
        model:[{name:"Wi-Fi／4G",sub:root.labelNetwork(),action:"network"},
          {name:"代理",sub:"TUN · "+root.b("tun").label,action:root.b("tun").value===true?"proxy-off":"proxy-on",available:root.b("tun").known&&root.b("proxy_core").known},
          {name:"ZeroTier",sub:root.b("zero").known?(root.b("zero").value?"服务在线":"等待连接"):root.b("zero").label,action:"zero"},
          {name:"触摸模式",sub:root.touchLabel(),action:root.f("touch")==="1"?"touch-normal":root.f("touch")==="0"?"touch-glove":"touch-refresh"},
          {name:"输入法",sub:"P1 同一入口",action:"keyboard"},
          {name:"显示方向",sub:"尚未适配旋转",action:"rotation"},
          {name:"飞行模式",sub:typeof root.data.flight_active!=="boolean"?"待读取":root.data.flight_active?"已开启":"关闭无线需确认",action:root.data.flight_saved?"flight-off":"flight-on",available:typeof root.data.flight_active==="boolean"},
          {name:"电源模式",sub:root.data.power_profile||"读取中",action:"power-mode"},
          {name:"仅熄屏",sub:"任务继续 · 不挂起",action:"screen-off"}]
        CButton {
         required property var modelData
         Layout.fillWidth:true;Layout.minimumHeight:68
         text:modelData.name+"\n"+modelData.sub
         enabled:!actionProcess.running&&modelData.action!=="rotation"&&modelData.available!==false
         onClicked:{if(modelData.action==="zero"){root.expanded=true;root.page="连接"}else if(modelData.action==="power-mode"){root.expanded=true;root.page="设备"}else root.act(modelData.action,{})}
        }
       }
      }
      GridLayout {
       visible:root.expanded;Layout.fillWidth:true;columns:window.width<620?2:4;columnSpacing:8;rowSpacing:8
       Repeater {model:["连接","设备","工作","旅途"];CButton {required property string modelData;Layout.fillWidth:true;text:modelData;onClicked:root.page=modelData}}
      }
      ColumnLayout {
       Layout.fillWidth:true;visible:root.expanded;spacing:8
       Text {Layout.fillWidth:true;color:root.purple;font.pixelSize:18;text:root.page;wrapMode:Text.Wrap}
       Text {Layout.fillWidth:true;color:root.fg;font.pixelSize:14;wrapMode:Text.Wrap;text:root.page==="连接"?"网络详情保留 Wi-Fi、4G、有线、代理、ZeroTier 和 GPS。打开详情不会切网。":root.page==="设备"?"触摸模式仅影响本次。重启或触屏重连后默认恢复手套／原装笔模式。":root.page==="工作"?"输入法、声音与窗口操作沿用已有入口。AI 对话与任务编排尚未接入。":"已有离线播放器、阅读器和游戏。飞行模式会关闭 Wi-Fi、4G 和蓝牙，后台任务继续但网络会断开。"}
       GridLayout {
        Layout.fillWidth:true;columns:2;columnSpacing:8;rowSpacing:8
        Repeater {
         model:root.page==="连接"?[{label:"网络与 GPS 详情",op:"network"},{label:"蓝牙",op:"bluetooth"}]:
          root.page==="设备"?[{label:"双电池与充放电记录",op:"power"},{label:"显示设置",op:"monitor"},{label:"省电",op:"power-saver"},{label:"均衡",op:"balanced"},{label:"手套／原装笔",op:"touch-glove"},{label:"普通触摸（本次）",op:"touch-normal"},{label:"刷新触摸模式",op:"touch-refresh"},{label:"锁屏",op:"lock"}]:
          root.page==="工作"?[{label:"输入法",op:"keyboard"},{label:"声音设置",op:"audio"},{label:"当前窗口操作",op:"windows"}]:[{label:"视频播放器",op:"player"},{label:"小说阅读器",op:"reader"},{label:"离线街机",op:"games"},{label:"飞行模式…",op:"flight-on"}]
         CButton {required property var modelData;Layout.fillWidth:true;text:modelData.label;enabled:!actionProcess.running&&modelData.op!=="unavailable";onClicked:root.act(modelData.op,{})}
        }
       }
      }
      Text {Layout.fillWidth:true;color:root.fg;text:"亮度 "+(root.data.brightness===null||root.data.brightness===undefined?"不可用":Math.round(brightness.value)+"%");font.pixelSize:15}
      Slider {id:brightness;Layout.fillWidth:true;Layout.minimumHeight:42;from:0;to:100;stepSize:1;value:root.data.brightness||0;enabled:root.data.brightness!==null&&root.data.brightness!==undefined&&!actionProcess.running;onPressedChanged:if(!pressed&&enabled)root.act("brightness",{percent:Math.round(value)})}
      RowLayout {
       Layout.fillWidth:true
       Text {Layout.fillWidth:true;color:root.fg;text:"音量 "+(root.audioAvailable?Math.round(volumeSlider.value)+"%":"无输出设备");font.pixelSize:15}
       CButton {text:root.muted?"取消静音":"静音";enabled:root.audioAvailable&&!actionProcess.running;onClicked:root.act("mute",{})}
      }
      Slider {id:volumeSlider;Layout.fillWidth:true;Layout.minimumHeight:42;from:0;to:100;stepSize:1;value:root.volume;enabled:root.audioAvailable&&!actionProcess.running;onPressedChanged:if(!pressed&&enabled)root.act("volume",{percent:Math.round(value)})}
      Text {Layout.fillWidth:true;color:root.fg;opacity:.65;font.pixelSize:13;wrapMode:Text.Wrap;text:"麦克风："+(root.source&&root.source.audio?(root.source.audio.muted?"已静音":"可用 · 静音关闭"):"未知")+"  ·  "+(root.data.observed_at?new Date(root.data.observed_at*1000).toLocaleTimeString():"读取中")}
      Text {Layout.fillWidth:true;color:root.orange;font.pixelSize:14;wrapMode:Text.Wrap;visible:root.feedback!=="";text:root.feedback}
     }
    }
    ColumnLayout {
     visible:root.confirmation!==null;Layout.fillWidth:true
     Text {Layout.fillWidth:true;color:root.orange;font.pixelSize:15;wrapMode:Text.Wrap;text:root.confirmation&&root.confirmation.name==="touch-normal"?"切换普通模式后，原装无源笔可能不能使用；重启仍恢复手套模式。":root.confirmation&&root.confirmation.name==="proxy-off"?"关闭代理可能中断 ChatGPT 等应用的联网。":"将关闭 Wi-Fi、4G 和蓝牙，网络会中断。"}
     RowLayout {Layout.fillWidth:true;CButton {Layout.fillWidth:true;text:"取消";onClicked:root.confirmation=null}CButton {Layout.fillWidth:true;text:"确认执行";onClicked:{const c=root.confirmation;root.confirmation=null;if(c)root.act(c.name,c.params,true)}}}
    }
   }
   focus:true
   Keys.onEscapePressed:root.close()
  }
 }
 component CButton: Button {
  implicitHeight:46;implicitWidth:100
  background:Rectangle {color:parent.down?"#44395b":parent.enabled?"#292c39":"#20222c";border.width:1;border.color:parent.enabled?root.purple:"#454653";radius:8}
  contentItem:Text {text:parent.text;color:parent.enabled?root.fg:"#7e8190";font.pixelSize:15;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;wrapMode:Text.Wrap}
 }
}
