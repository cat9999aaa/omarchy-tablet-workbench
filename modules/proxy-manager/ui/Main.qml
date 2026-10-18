import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../workbench-ui" as WB
import "pages" as Pages
Rectangle {
 id:root;width:960;height:720;color:background;clip:true
 property ProxyModel model:ProxyModel{}
 property color foreground:"#d5d8dc"
 property color background:"#161a20"
 property color accent:"#82b788"
 property int page:0
 property bool leavePrompt:false
 property int requestedPage:0
 property bool closeAfterDiscard:false
 readonly property var pageNames:["总览","节点","订阅","分流","更新","诊断","设置"]
 signal closeRequested()
 Connections {target:root.model;function onEditRoutingRequested(){root.page=3}}
 function choosePage(index){if(index<0||index>6||index===page)return;if(model.draft.dirty){requestedPage=index;closeAfterDiscard=false;leavePrompt=true;leave.open()}else page=index}
 function requestClose(){if(model.draft.dirty){closeAfterDiscard=true;leavePrompt=true;leave.open()}else closeRequested()}
 function discardAndContinue(){model.draft={dirty:false,mode:"rules"};leavePrompt=false;leave.close();if(closeAfterDiscard)closeRequested();else page=requestedPage}
 ColumnLayout {
  anchors.fill:parent;anchors.margins:16;spacing:12
  RowLayout {Layout.fillWidth:true
   ColumnLayout {Layout.fillWidth:true;spacing:2
    PText {text:"网络 · 代理工作台";color:root.foreground;font.pixelSize:24;font.bold:true;Layout.fillWidth:true}
    PText {text:"OMARCHY TABLET WORKBENCH";color:root.foreground;opacity:.55;font.pixelSize:12;Layout.fillWidth:true}
   }
   WB.TouchButton {objectName:"closeProxy";text:"收起";foreground:root.foreground;accent:root.accent;onClicked:root.requestClose()}
  }
  Rectangle {Layout.fillWidth:true;implicitHeight:statusText.implicitHeight+24;radius:10;color:Qt.rgba(root.accent.r,root.accent.g,root.accent.b,.10)
   PText {id:statusText;anchors.fill:parent;anchors.margins:12;color:root.foreground;text:"当前网络："+model.physicalLabel+"    代理："+model.proxyLabel+"    TUN："+model.tunLabel+"\n分流：待核对    ·    "+(model.online?"最近检测正常":"访问状态待确认")}
  }
  RowLayout {Layout.fillWidth:true;Layout.fillHeight:true;spacing:16
   ColumnLayout {visible:root.width>=1000;Layout.preferredWidth:136;Layout.fillHeight:true;spacing:8
    Repeater {model:root.pageNames;WB.TouchButton {required property int index;required property string modelData;Layout.fillWidth:true;text:modelData;foreground:root.foreground;accent:root.accent;selected:root.page===index;onClicked:root.choosePage(index)}}
    Item {Layout.fillHeight:true}
   }
   ColumnLayout {Layout.fillWidth:true;Layout.fillHeight:true;spacing:12
    ComboBox {objectName:"pageSelector";visible:root.width<1000;Layout.fillWidth:true;Layout.preferredHeight:52;model:root.pageNames;currentIndex:root.page;palette.button:root.background;palette.base:root.background;palette.window:root.background;palette.text:root.foreground;palette.buttonText:root.foreground;palette.highlight:root.accent;onActivated:function(i){root.choosePage(i);currentIndex=Qt.binding(function(){return root.page})}}
    ScrollView {objectName:"pageBody";id:scroll;Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:availableWidth;ScrollBar.horizontal.policy:ScrollBar.AlwaysOff
     Loader {id:pageLoader;width:scroll.availableWidth;sourceComponent:[overview,nodes,subscriptions,routing,updates,diagnostics,settings][root.page]}
    }
   }
  }
  PText {Layout.fillWidth:true;color:root.foreground;text:model.pending?"正在执行并检查结果…":model.lastError||"收起界面不会停止代理。";font.pixelSize:14}
 }
 Component{id:overview;Pages.Overview{model:root.model;foreground:root.foreground;accent:root.accent}}
 Component{id:nodes;Pages.Nodes{model:root.model;foreground:root.foreground;accent:root.accent}}
 Component{id:subscriptions;Pages.Subscriptions{model:root.model;foreground:root.foreground;accent:root.accent}}
 Component{id:routing;Pages.Routing{model:root.model;foreground:root.foreground;accent:root.accent}}
 Component{id:updates;Pages.Updates{model:root.model;foreground:root.foreground;accent:root.accent}}
 Component{id:diagnostics;Pages.Diagnostics{model:root.model;foreground:root.foreground;accent:root.accent}}
 Component{id:settings;Pages.Settings{model:root.model;foreground:root.foreground;accent:root.accent}}
 ConfirmDialog {id:leave;title:"有未应用的修改";description:"确认离开将放弃草稿；取消可继续编辑。";onAccepted:root.discardAndContinue();onRejected:root.leavePrompt=false}
}
