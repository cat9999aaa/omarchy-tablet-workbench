import QtQuick
import QtQuick.Layouts
RowLayout {
 id: root
 property var labels: []
 property int keyHeight: 50
 property color foreground: "#eeeeee"
 property color baseColor: "#30343b"
 property color accentColor: "#5477b9"
 property bool inputActive: true
 signal selected(string value)
 spacing: 4
 Repeater {
  model: root.labels
  TouchKey {
   required property string modelData
   Layout.fillWidth: true; Layout.preferredHeight: root.keyHeight
   label: modelData; foreground: root.foreground; baseColor: root.baseColor; accentColor: root.accentColor
   inputActive: root.inputActive; enabled: root.inputActive
   onTriggered: root.selected(modelData)
  }
 }
}
