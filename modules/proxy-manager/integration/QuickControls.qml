import QtQuick
import QtQuick.Layouts
import "../../workbench-ui" as WB
import "../ui"
ColumnLayout {
 id:root;required property var model
 signal manageRequested()
 PText {Layout.fillWidth:true;text:"当前网络："+root.model.physicalLabel+" · 代理："+root.model.proxyLabel}
 WB.TouchButton {Layout.fillWidth:true;text:"打开代理管理";onClicked:root.manageRequested()}
 WB.TouchButton {Layout.fillWidth:true;text:root.model.pending?"处理中…":"开启代理";enabled:root.model.allowed("enable");onClicked:root.model.submit("enable",true)}
}
