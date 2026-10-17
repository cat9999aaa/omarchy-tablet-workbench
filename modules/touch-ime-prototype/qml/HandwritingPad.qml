import QtQuick
import QtQuick.Layouts
Rectangle {
 id: root
 property color foreground: "#dddddd"
 property color background: "#222733"
 property int generation: 0
 property int revision: 0
 property var strokes: []
 property var currentStroke: []
 property bool tooMuchInk: false
 signal recognize(var strokes, real w, real h, int revision)
 color: background; radius: 10
 function undoStroke() {settle.stop();strokes=strokes.slice(0,-1);currentStroke=[];inkChanged()}
 function reset() { settle.stop();strokes=[];currentStroke=[];tooMuchInk=false;revision++;ink.requestPaint() }
 function inkChanged() { revision++;ink.requestPaint();if(strokes.length>0)settle.restart() }
 onGenerationChanged: reset()
 onVisibleChanged: if(!visible)reset()
 onEnabledChanged: if(!enabled)reset()
 Timer { id: settle; interval: 400; onTriggered: if(root.enabled&&root.visible&&root.strokes.length>0)root.recognize(root.strokes,ink.width,ink.height,root.revision) }
 ColumnLayout {
  anchors.fill: parent; anchors.margins: 8; spacing: 6
  Canvas {
   id: ink; Layout.fillWidth: true; Layout.fillHeight: true
   onPaint: {
    var c=getContext("2d");c.clearRect(0,0,width,height)
    c.strokeStyle=Qt.rgba(root.foreground.r,root.foreground.g,root.foreground.b,0.13);c.lineWidth=1;c.setLineDash([4,5]);c.beginPath();c.moveTo(width/2,0);c.lineTo(width/2,height);c.moveTo(0,height/2);c.lineTo(width,height/2);c.stroke();c.setLineDash([])
    c.strokeStyle=root.foreground;c.lineWidth=4;c.lineCap="round";c.lineJoin="round"
    var all=root.strokes.concat(root.currentStroke.length>0?[root.currentStroke]:[])
    for(var i=0;i<all.length;i++){var s=all[i];if(!s.length)continue;c.beginPath();c.moveTo(s[0].x,s[0].y);for(var j=1;j<s.length;j++)c.lineTo(s[j].x,s[j].y);c.stroke()}
   }
   Text { anchors.centerIn: parent; visible: root.strokes.length===0&&root.currentStroke.length===0; text: root.tooMuchInk ? "笔画过多，请重写" : "在这里写一个字"; color: root.foreground; opacity: 0.4; font.pixelSize: 20 }
   MouseArea {
    anchors.fill: parent; preventStealing: true
    function point(mouse) {return {x:Math.max(0,Math.min(width,mouse.x)),y:Math.max(0,Math.min(height,mouse.y))}}
    onPressed: mouse => {settle.stop();root.revision++;root.currentStroke=[point(mouse)];ink.requestPaint()}
    onPositionChanged: mouse => {
     if(!pressed||root.currentStroke.length===0)return
     var p=point(mouse),last=root.currentStroke[root.currentStroke.length-1]
     if(root.currentStroke.length<256&&Math.hypot(p.x-last.x,p.y-last.y)>=2){root.currentStroke=root.currentStroke.concat([p]);ink.requestPaint()}
    }
    onReleased: {
     var total=root.currentStroke.length;for(var i=0;i<root.strokes.length;i++)total+=root.strokes[i].length
     if(root.strokes.length>=64||total>1024){root.reset();root.tooMuchInk=true;return}
     if(root.currentStroke.length>0)root.strokes=root.strokes.concat([root.currentStroke])
     root.currentStroke=[];root.inkChanged()
    }
    onCanceled: {root.currentStroke=[];root.inkChanged()}
   }
  }
  RowLayout {
   Layout.fillWidth: true
   TouchKey { label: "撤销一笔"; Layout.fillWidth: true; Layout.preferredHeight: 38; fontSize: 16; foreground: root.foreground; baseColor: Qt.lighter(root.background,1.25); onTriggered: root.undoStroke() }
   TouchKey { label: "重写"; Layout.fillWidth: true; Layout.preferredHeight: 38; fontSize: 16; foreground: root.foreground; baseColor: Qt.lighter(root.background,1.25); onTriggered: root.reset() }
  }
 }
}
