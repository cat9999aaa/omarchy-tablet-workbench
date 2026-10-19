import QtQuick
import QtQuick.Layouts
Item {
 id:root
 property string title:""
 property string subtitle:""
 property var themeTokens:null
 property color foreground:themeTokens?themeTokens.colors.foreground:"white"
 property color accent:themeTokens?themeTokens.colors.accent:foreground
 property string fontFamily:themeTokens?themeTokens.font.family:"sans-serif"
 signal closeRequested()
 implicitHeight:Math.max(48,titles.implicitHeight)
 RowLayout {
  anchors.fill:parent;spacing:root.themeTokens?root.themeTokens.metrics.gap:12
  Column {
   id:titles;Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
   Text {width:parent.width;text:root.title;textFormat:Text.PlainText;color:root.foreground;font.family:root.fontFamily;font.pixelSize:root.themeTokens?root.themeTokens.font.title:21;font.bold:true;elide:Text.ElideRight}
   Text {visible:root.subtitle!=="";width:parent.width;text:root.subtitle;textFormat:Text.PlainText;color:root.foreground;opacity:.7;font.family:root.fontFamily;font.pixelSize:root.themeTokens?root.themeTokens.font.subtitle:13;wrapMode:Text.Wrap}
  }
  TouchButton {themeTokens:root.themeTokens;objectName:"workbenchClose";Layout.preferredWidth:root.themeTokens?Math.max(88,implicitWidth):88;Layout.minimumWidth:root.themeTokens?Math.max(88,implicitWidth):88;Layout.minimumHeight:48;text:"收起 ↑";foreground:root.foreground;accent:root.accent;font.family:root.fontFamily;font.pixelSize:root.themeTokens?root.themeTokens.font.body:15;onClicked:root.closeRequested()}
 }
}
