import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property string value: ""
    property color foreground: "#eeeeee"
    property color backgroundColor: "#30343b"
    readonly property real contentHeight: contents.contentHeight
    readonly property real scrollPosition: contents.contentY
    function scrollToEnd() { contents.contentY = Math.max(0, contents.contentHeight - contents.height) }
    radius: 10
    color: backgroundColor
    clip: true
    Flickable {
        id: contents
        anchors.fill: parent; anchors.margins: 10
        contentWidth: width
        contentHeight: text.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        clip: true
        Text {
            id: text; width: contents.width - 8
            text: root.value; color: root.foreground
            wrapMode: Text.Wrap; font.pixelSize: 19
        }
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    }
    onValueChanged: contents.contentY = 0
}
