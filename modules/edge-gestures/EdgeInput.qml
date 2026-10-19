import QtQuick
import "Gesture.js" as Gesture

MouseArea {
    id: root
    required property string edge
    property bool available: false
    property int contextGeneration: 0
    property int pressedGeneration: -1
    property real startX: 0
    property real startY: 0
    signal routed(string route)
    enabled: available
    acceptedButtons: Qt.LeftButton
    preventStealing: true
    onAvailableChanged: { contextGeneration++; pressedGeneration = -1 }
    onEdgeChanged: { contextGeneration++; pressedGeneration = -1 }
    onPressed: mouse => {
        startX = mouse.x; startY = mouse.y
        pressedGeneration = contextGeneration
    }
    onReleased: mouse => {
        const valid = available && pressedGeneration === contextGeneration
        pressedGeneration = -1
        const route = Gesture.route(edge, mouse.x - startX, mouse.y - startY, !valid)
        if (route) routed(route)
    }
    onCanceled: { pressedGeneration = -1 }
}
