import QtQuick
import "Theme.js" as Theme
Text {
 id:root
 property var themeTokens:null
 property string role:"body"
 property string tone:"normal"
 readonly property var resolved:themeTokens||Theme.resolve()
 textFormat:Text.PlainText
 wrapMode:Text.Wrap
 font.family:resolved.font.family
 font.pixelSize:role==="title"?resolved.font.title:role==="subtitle"?resolved.font.subtitle:resolved.font.body
 color:tone==="urgent"?resolved.colors.urgent:tone==="muted"?resolved.colors.muted:resolved.colors.foreground
}
