import QtQuick
Rectangle {
 id: root
 property string label: ""
 property color foreground: "#eeeeee"
 property color baseColor: "#30343b"
 property color accentColor: "#5477b9"
 property bool repeatKey: false
 property bool clearGesture: false
 property bool clearArmed: false
 property bool heldLong: false
 property bool gestureVisited: false
 property real pressY: 0
 signal clearTriggered()
 signal pressStarted()
 property bool triggerOnRelease: false
 property bool inputActive: true
 property int inputGeneration: 0
 property int heldGeneration: -1
 property int fontSize: 19
 signal triggered()
 function stopRepeat() { delay.stop(); repeatTimer.stop() }
 function cancelGesture() {stopRepeat();clearArmed=false;heldLong=false;gestureVisited=false}
 radius: 9
 border.width: 1
 border.color: Qt.rgba(foreground.r,foreground.g,foreground.b,0.12)
 color: mouse.pressed && inputActive ? accentColor : baseColor
 opacity: enabled ? 1 : 0.45
 Text { anchors.centerIn: parent; text: root.clearArmed ? "松手清空" : root.label; color: root.foreground; font.pixelSize: root.clearArmed ? 14 : root.fontSize; horizontalAlignment: Text.AlignHCenter }
 MouseArea {
  id: mouse; anchors.fill: parent; preventStealing: !root.triggerOnRelease
  onPressed: mouse => { if(!root.inputActive)return; root.cancelGesture();root.pressY=mouse.y;root.heldGeneration=root.inputGeneration;root.pressStarted();if(!root.triggerOnRelease){root.triggered();if(root.repeatKey)delay.start()} }
  onClicked: {if(root.triggerOnRelease && root.inputActive && root.heldGeneration===root.inputGeneration)root.triggered()}
  onPositionChanged: mouse => {
   if(root.clearGesture && root.heldLong && root.heldGeneration===root.inputGeneration && root.inputActive) {
    root.clearArmed=root.pressY-mouse.y>=44 && mouse.x>=0 && mouse.x<=width
    if(root.clearArmed){root.gestureVisited=true;root.stopRepeat()}
   }
  }
  onReleased: {
   if(root.clearArmed && root.inputActive && root.enabled && root.heldGeneration===root.inputGeneration)root.clearTriggered()
   root.cancelGesture()
  }
  onCanceled: root.cancelGesture()
 }
 Timer { id: delay; interval: 450; onTriggered: if(mouse.pressed && root.inputActive && root.enabled && root.heldGeneration===root.inputGeneration){root.heldLong=true;repeatTimer.start()} }
 Timer { id: repeatTimer; interval: 80; repeat: true; onTriggered: { if(mouse.pressed && root.inputActive && root.enabled && !root.gestureVisited && root.heldGeneration===root.inputGeneration)root.triggered();else root.stopRepeat() } }
 onInputGenerationChanged: {heldGeneration=-1;cancelGesture()}
 onEnabledChanged: if(!enabled)cancelGesture()
 onInputActiveChanged: if(!inputActive)cancelGesture()
 onVisibleChanged: if(!visible)cancelGesture()
}
