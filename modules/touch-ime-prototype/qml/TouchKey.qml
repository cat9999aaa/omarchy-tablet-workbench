import QtQuick
Rectangle {
 id: root
 property string label: ""
 property color foreground: "#eeeeee"
 property color baseColor: "#30343b"
 property color accentColor: "#5477b9"
 property bool repeatKey: false
 property bool triggerOnRelease: false
 property bool inputActive: true
 property int inputGeneration: 0
 property int heldGeneration: -1
 property int fontSize: 19
 signal triggered()
 function stopRepeat() { delay.stop(); repeatTimer.stop() }
 radius: 9
 border.width: 1
 border.color: Qt.rgba(foreground.r,foreground.g,foreground.b,0.12)
 color: mouse.pressed && inputActive ? accentColor : baseColor
 opacity: enabled ? 1 : 0.45
 Text { anchors.centerIn: parent; text: root.label; color: root.foreground; font.pixelSize: root.fontSize; horizontalAlignment: Text.AlignHCenter }
 MouseArea {
  id: mouse; anchors.fill: parent; preventStealing: !root.triggerOnRelease
  onPressed: { if(!root.inputActive)return; root.heldGeneration=root.inputGeneration;if(!root.triggerOnRelease){root.triggered();if(root.repeatKey)delay.start()} }
  onClicked: {if(root.triggerOnRelease && root.inputActive && root.heldGeneration===root.inputGeneration)root.triggered()}
  onReleased: root.stopRepeat()
  onCanceled: root.stopRepeat()
 }
 Timer { id: delay; interval: 450; onTriggered: if(mouse.pressed && root.inputActive && root.enabled && root.heldGeneration===root.inputGeneration)repeatTimer.start() }
 Timer { id: repeatTimer; interval: 80; repeat: true; onTriggered: { if(mouse.pressed && root.inputActive && root.enabled && root.heldGeneration===root.inputGeneration)root.triggered();else root.stopRepeat() } }
 onInputGenerationChanged: {heldGeneration=-1;stopRepeat()}
 onEnabledChanged: if(!enabled)stopRepeat()
 onInputActiveChanged: if(!inputActive)stopRepeat()
 onVisibleChanged: if(!visible)stopRepeat()
}
