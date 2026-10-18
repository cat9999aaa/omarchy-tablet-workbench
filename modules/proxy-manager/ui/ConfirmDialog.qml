import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../workbench-ui" as WB
Dialog {
 id:root;modal:true;focus:true;parent:Overlay.overlay;anchors.centerIn:parent;implicitWidth:440;width:parent?Math.max(280,Math.min(440,parent.width-32)):440;property string description:"";closePolicy:Popup.CloseOnEscape
 contentItem:ColumnLayout {
  PText {Layout.fillWidth:true;text:root.description}
  WB.TouchButton {Layout.fillWidth:true;text:"确认";onClicked:root.accept()}
  WB.TouchButton {Layout.fillWidth:true;text:"取消";onClicked:root.reject()}
 }
}
