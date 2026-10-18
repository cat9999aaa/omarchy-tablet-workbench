import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import "Workbench" as WB
import "Workbench/Layout.js" as LayoutModel
import "Workbench/Theme.js" as Theme
Item {
 id:root
 property bool opened:false
 property string page:"窗口"
 property var data:({})
 property string feedback:""
 property string nextPage:"窗口"
 readonly property string helper:Quickshell.env("PCADMIN_NAVIGATION_HELPER") || Quickshell.env("HOME")+"/Projects/pcadmin/tools/window-controls/navigation.py"
 readonly property color fg:Color.foreground
 readonly property var themeTokens:Theme.resolve({schemaVersion:1,foreground:Color.foreground,
  background:Color.popups.background,accent:Color.accent,urgent:Color.urgent,muted:Color.muted,
  fontFamily:Style.font.family,fontScale:Style.font.body/12,cornerRadius:Style.cornerRadius})
 readonly property color bg:Color.popups.background
 function openPage(value) {if(["开始","桌面","窗口","按键"].indexOf(value)<0)return;nextPage=value;if(!loader.running)loader.running=true}
 function close(){opened=false}
 function act(action,extra) {
  if(command.running)return
  var value=Object.assign({action:action,target:root.data.target},extra||{})
  command.request=JSON.stringify(value);command.running=true;feedback="正在处理…"
 }
 IpcHandler {
  target:"pcadmin.navigation"
  function ready():bool{return true}
  function toggle(page:string):void {if(root.opened)root.close();else root.openPage(page)}
  function open(page:string):void {root.openPage(page)}
  function close():void {root.close()}
  function state():string{return JSON.stringify({version:"0.1.2",opened:root.opened,page:root.page,width:card.width,height:card.height})}
 }
 Process {
  id:loader;command:["python",root.helper,"snapshot"]
  stdout:StdioCollector {onStreamFinished:{try{var d=JSON.parse(text);if(d.ok){root.data=d;root.page=root.nextPage;root.feedback="";root.opened=true}else{root.feedback=d.reason;root.close()}}catch(e){root.close()}}}
 }
 Process {
  id:lockCheck;command:["omarchy-shell","lock","isLocked"]
  stdout:StdioCollector {onStreamFinished:if(text.trim()!=="false")root.close()}
  onExited:function(code){if(code!==0)root.close()}
 }
 Timer {interval:500;repeat:true;running:root.opened;onTriggered:if(!lockCheck.running)lockCheck.running=true}
 Process {
  id:command;property string request:"";command:["python",root.helper,"action"];stdinEnabled:true
  onStarted:{write(request);stdinEnabled=false}
  onRunningChanged:if(!running)stdinEnabled=true
  stdout:StdioCollector {onStreamFinished:{try{var d=JSON.parse(text);if(d.ok){if(d.bindings){root.data=Object.assign({},root.data,{bindings:d.bindings});root.feedback="按键设置已保存"}else root.close()}else root.feedback=d.reason||"操作未完成"}catch(e){root.feedback="操作未完成"}}}
 }
 PanelWindow {
  id:window;visible:root.opened;screen:Quickshell.screens[0]
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
   color:root.bg;radius:14;border.width:2;border.color:Color.accent
   MouseArea{anchors.fill:parent}
   ColumnLayout {
    anchors.fill:parent;anchors.margins:16;spacing:12
    WB.PanelHeader{themeTokens:root.themeTokens;Layout.fillWidth:true;title:"平板导航";subtitle:"应用 · 桌面 · 当前窗口";foreground:root.fg;accent:Color.accent;fontFamily:Style.font.family;onCloseRequested:root.close()}
    Flickable {
     Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:width;contentHeight:body.implicitHeight;boundsBehavior:Flickable.StopAtBounds
     ColumnLayout {
      id:body;width:parent.width;spacing:12
    RowLayout {
     Layout.fillWidth:true;spacing:6
     Repeater{model:["开始","桌面","窗口","按键"]
      WB.TouchButton{themeTokens:root.themeTokens;required property string modelData;objectName:"navigation-tab-"+modelData;Layout.fillWidth:true;text:modelData;foreground:root.fg;accent:Color.accent;selected:root.page===modelData;onClicked:{root.page=modelData;root.feedback=""}}
     }
    }
    Text{visible:!!root.feedback;Layout.fillWidth:true;text:root.feedback;color:Color.urgent;wrapMode:Text.Wrap;font.pixelSize:root.themeTokens.font.body}
      ColumnLayout {
       visible:root.page==="开始";Layout.fillWidth:true;spacing:12
       Text{Layout.fillWidth:true;text:"开始使用";color:root.fg;font.pixelSize:root.themeTokens.font.body*24/16}
       Text{Layout.fillWidth:true;text:"设备状态和网络设置仍在三指下滑的随身控制台。";color:root.fg;wrapMode:Text.Wrap;font.pixelSize:root.themeTokens.font.body}
       GridLayout {
        Layout.fillWidth:true;columns:2;rowSpacing:12;columnSpacing:12
        Repeater{model:[{label:"全部应用",action:"launcher"},{label:"文件",action:"files"},{label:"浏览器",action:"browser"},{label:"触屏输入法",action:"keyboard"},{label:"语音输入",action:"voice"},{label:"随身控制台",action:"control-center"}]
         WB.TouchButton{themeTokens:root.themeTokens;required property var modelData;Layout.fillWidth:true;Layout.minimumHeight:72;text:modelData.label;foreground:root.fg;accent:Color.accent;enabled:!command.running;onClicked:root.act(modelData.action)}
        }
       }
      }
      ColumnLayout {
       visible:root.page==="桌面";Layout.fillWidth:true;spacing:12
       Text{Layout.fillWidth:true;text:"点选桌面 · 当前桌面带 ✓";color:root.fg;font.pixelSize:root.themeTokens.font.body}
       GridLayout{Layout.fillWidth:true;columns:2;rowSpacing:10;columnSpacing:10
        Repeater{model:root.data.workspaces||[]
         WB.TouchButton{themeTokens:root.themeTokens;required property var modelData;Layout.fillWidth:true;Layout.minimumHeight:66;text:(root.data.current===modelData.id?"✓ ":"")+"桌面 "+modelData.id+" · "+modelData.count+" 个窗口";foreground:root.fg;accent:Color.accent;enabled:!command.running;onClicked:root.act("switch",{workspace:modelData.id})}
        }
       }

       Text{Layout.fillWidth:true;text:"移动当前窗口到桌面";color:root.fg;font.pixelSize:root.themeTokens.font.body}
       GridLayout{Layout.fillWidth:true;columns:5;rowSpacing:8;columnSpacing:8
        Repeater{model:10
         WB.TouchButton{themeTokens:root.themeTokens;required property int index;Layout.fillWidth:true;text:String(index+1);foreground:root.fg;accent:Color.accent;enabled:!command.running;onClicked:root.act("move",{workspace:index+1})}
        }
       }
      }
      ColumnLayout {
       visible:root.page==="窗口";Layout.fillWidth:true;spacing:12
       Text{Layout.fillWidth:true;text:root.data.windowLabel||"当前窗口";elide:Text.ElideRight;color:root.fg;font.pixelSize:root.themeTokens.font.title}
       GridLayout{Layout.fillWidth:true;columns:3;rowSpacing:10;columnSpacing:10
        Repeater{model:[{label:"放大 / 还原",action:"maximize"},{label:"浮动 / 平铺",action:"float"},{label:"暂存窗口",action:"hide"},{label:"找回暂存",action:"restore"},{label:"浮动窗口居中",action:"center"},{label:"关闭当前窗口",action:"close"}]
         WB.TouchButton{themeTokens:root.themeTokens;required property var modelData;Layout.fillWidth:true;Layout.minimumHeight:60;text:modelData.label;foreground:root.fg;accent:modelData.action==="close"?Color.urgent:Color.accent;enabled:!command.running;onClicked:root.act(modelData.action)}
        }
       }
       Text{Layout.fillWidth:true;text:"切换桌面";color:root.fg;font.pixelSize:root.themeTokens.font.body}
       GridLayout{Layout.fillWidth:true;columns:width>=550?9:5;rowSpacing:8;columnSpacing:6
        Repeater{model:9
         WB.TouchButton{themeTokens:root.themeTokens;required property int index;objectName:"quickDesktop"+(index+1);Layout.fillWidth:true;Layout.minimumHeight:52;text:String(index+1);selected:root.data.current===index+1;foreground:root.fg;accent:Color.accent;enabled:!command.running;onClicked:root.act("switch",{workspace:index+1})}
        }
       }
      }
      ColumnLayout {
       visible:root.page==="按键";Layout.fillWidth:true;spacing:12
       Text{Layout.fillWidth:true;text:"自定义短按 · 长按暂保留原行为";color:root.fg;font.pixelSize:root.themeTokens.font.body}
       Repeater{model:["P1","P2","P3","rotation"]
        RowLayout{
         required property string modelData;Layout.fillWidth:true
         Text{text:parent.modelData==="rotation"?"旋转键":parent.modelData;Layout.preferredWidth:Math.max(72,implicitWidth);color:root.fg;font.pixelSize:root.themeTokens.font.title}
         ComboBox{
          id:choice;Layout.fillWidth:true;Layout.minimumHeight:52
          property string button:parent.modelData
          property var actions:button==="P3"?["authorize","disabled"]:["keyboard","voice","navigation","desktops","windows","control-center","disabled"]
          model:actions.map(a=>(root.data.labels||{})[a]||a)
          currentIndex:actions.indexOf((root.data.bindings||{})[button])
          enabled:!command.running
          onActivated:{var b=Object.assign({},root.data.bindings);b[button]=actions[currentIndex];root.act("bindings",{bindings:b})}
         }
        }
       }
       Text{Layout.fillWidth:true;text:"P3 只用于已有系统授权；电源与音量键保持系统原有行为。";color:root.fg;font.pixelSize:root.themeTokens.font.body;wrapMode:Text.Wrap}
       WB.TouchButton{themeTokens:root.themeTokens;Layout.fillWidth:true;text:"恢复这台平板的默认按键";foreground:root.fg;accent:Color.accent;enabled:!command.running;onClicked:root.act("defaults")}
      }
     }
    }
   }
  }
 }
}
