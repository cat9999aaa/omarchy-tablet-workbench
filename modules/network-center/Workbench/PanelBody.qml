import QtQuick
Item {
 id:root
 default property alias body:content.data
 property string title:""
 property string subtitle:""
 property var themeTokens:null
 property color foreground:themeTokens?themeTokens.colors.foreground:"white"
 property color accent:themeTokens?themeTokens.colors.accent:foreground
 property string fontFamily:themeTokens?themeTokens.font.family:"sans-serif"
 property alias contentY:scroll.contentY
 signal closeRequested()
 PanelHeader {
  id:header;themeTokens:root.themeTokens;anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
  title:root.title;subtitle:root.subtitle;foreground:root.foreground;accent:root.accent;fontFamily:root.fontFamily
  onCloseRequested:root.closeRequested()
 }
 Flickable {
  id:scroll;objectName:"workbenchScroll"
  anchors.top:header.bottom;anchors.topMargin:root.themeTokens?root.themeTokens.metrics.paddingY:10;anchors.left:parent.left;anchors.right:parent.right
  height:Math.max(0,root.height-header.height-(root.themeTokens?root.themeTokens.metrics.paddingY:10))
  clip:true;contentWidth:width;contentHeight:content.implicitHeight;boundsBehavior:Flickable.StopAtBounds
  Column {id:content;width:scroll.width;spacing:root.themeTokens?root.themeTokens.metrics.gap:12}
 }
}
