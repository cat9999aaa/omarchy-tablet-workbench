import QtQuick
import QtQuick.Controls
Button {
 id:root
 property color foreground:palette.buttonText
 property color accent:palette.highlight
 property bool selected:false
 property bool bordered:true
 property real minimumTouchHeight:48
 implicitWidth:Math.max(96,contentItem.implicitWidth+leftPadding+rightPadding)
 implicitHeight:Math.max(minimumTouchHeight,contentItem.implicitHeight+topPadding+bottomPadding)
 leftPadding:12;rightPadding:12;topPadding:10;bottomPadding:10
 Accessible.name:text
 background:Rectangle {
  radius:8
  color:Qt.rgba(root.accent.r,root.accent.g,root.accent.b,root.down?0.28:root.selected?0.18:0.05)
  border.width:root.bordered||root.activeFocus?1:0
  border.color:root.activeFocus||root.selected?root.accent:Qt.rgba(root.foreground.r,root.foreground.g,root.foreground.b,root.enabled?0.35:0.15)
 }
 contentItem:Text {
  text:root.text;textFormat:Text.PlainText;color:root.foreground;opacity:root.enabled?1:0.45
  font:root.font;wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
 }
}
