import QtQuick
import QtQuick.Controls
Button {
 id:root
 property var themeTokens:null
 property color foreground:themeTokens?themeTokens.colors.foreground:palette.buttonText
 property color accent:themeTokens?themeTokens.colors.accent:palette.highlight
 property bool selected:false
 property bool bordered:true
 property real minimumTouchHeight:themeTokens?Math.max(48,themeTokens.metrics.minimumTouchHeight):48
 font.family:themeTokens?themeTokens.font.family:Qt.application.font.family
 font.pixelSize:themeTokens?themeTokens.font.body:Qt.application.font.pixelSize
 implicitWidth:Math.max(96,contentItem.implicitWidth+leftPadding+rightPadding)
 implicitHeight:Math.max(minimumTouchHeight,contentItem.implicitHeight+topPadding+bottomPadding)
 leftPadding:themeTokens?themeTokens.metrics.paddingX:12;rightPadding:leftPadding
 topPadding:themeTokens?themeTokens.metrics.paddingY:10;bottomPadding:topPadding
 Accessible.name:text
 background:Rectangle {
  radius:root.themeTokens?root.themeTokens.metrics.radius:8
  color:Qt.rgba(root.accent.r,root.accent.g,root.accent.b,root.down?(root.themeTokens?root.themeTokens.states.pressedAlpha:.28):root.selected?(root.themeTokens?root.themeTokens.states.selectedAlpha:.18):(root.themeTokens?root.themeTokens.states.normalAlpha:.05))
  border.width:root.activeFocus&&root.themeTokens?root.themeTokens.states.focusBorderWidth:root.bordered||root.activeFocus?1:0
  border.color:root.activeFocus||root.selected?root.accent:Qt.rgba(root.foreground.r,root.foreground.g,root.foreground.b,root.enabled?0.35:0.15)
 }
 contentItem:Text {
  text:root.text;textFormat:Text.PlainText;color:root.foreground;opacity:root.enabled?1:root.themeTokens?root.themeTokens.states.disabledTextAlpha:.45
  font:root.font;wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
 }
}
