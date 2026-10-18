import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
ColumnLayout {
 id:root
 property var model
 property color foreground:"#d5d8dc"
 property color accent:"#82b788"
 property string title:""
 property string description:""
 spacing:16
 PText {Layout.fillWidth:true;text:root.title;font.pixelSize:26;font.bold:true;color:root.foreground}
 PText {Layout.fillWidth:true;text:root.description;color:root.foreground;opacity:.7}
}
