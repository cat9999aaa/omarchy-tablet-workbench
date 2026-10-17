import QtQuick
import QtQuick.Layouts
Item {
 id:root
 property string title:""
 property string subtitle:""
 property color foreground:"white"
 property color accent:foreground
 property string fontFamily:"sans-serif"
 signal closeRequested()
 implicitHeight:Math.max(48,titles.implicitHeight)
 RowLayout {
  anchors.fill:parent;spacing:12
  Column {
   id:titles;Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
   Text {width:parent.width;text:root.title;textFormat:Text.PlainText;color:root.foreground;font.family:root.fontFamily;font.pixelSize:21;font.bold:true;elide:Text.ElideRight}
   Text {visible:root.subtitle!=="";width:parent.width;text:root.subtitle;textFormat:Text.PlainText;color:root.foreground;opacity:.7;font.family:root.fontFamily;font.pixelSize:13;wrapMode:Text.Wrap}
  }
  TouchButton {objectName:"workbenchClose";Layout.preferredWidth:88;Layout.minimumWidth:88;Layout.minimumHeight:48;text:"收起 ↑";foreground:root.foreground;accent:root.accent;font.family:root.fontFamily;font.pixelSize:15;onClicked:root.closeRequested()}
 }
}
