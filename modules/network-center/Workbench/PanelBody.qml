import QtQuick
Item {
 id:root
 default property alias body:content.data
 property string title:""
 property string subtitle:""
 property color foreground:"white"
 property color accent:foreground
 property string fontFamily:"sans-serif"
 property alias contentY:scroll.contentY
 signal closeRequested()
 PanelHeader {
  id:header;anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
  title:root.title;subtitle:root.subtitle;foreground:root.foreground;accent:root.accent;fontFamily:root.fontFamily
  onCloseRequested:root.closeRequested()
 }
 Flickable {
  id:scroll;objectName:"workbenchScroll"
  anchors.top:header.bottom;anchors.topMargin:10;anchors.left:parent.left;anchors.right:parent.right
  height:Math.max(0,root.height-header.height-10)
  clip:true;contentWidth:width;contentHeight:content.implicitHeight;boundsBehavior:Flickable.StopAtBounds
  Column {id:content;width:scroll.width;spacing:12}
 }
}
