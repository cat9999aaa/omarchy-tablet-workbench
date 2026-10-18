import QtQuick
import QtQuick.Layouts
import ".."
import "../../../workbench-ui" as WB
ProxyPage {
 id:root;title:"分流";description:"规则、全局、直连均保留局域网与 ZeroTier 的传输保护。"
 PText {Layout.fillWidth:true;color:root.foreground;text:model.draft.node_id?"已选择候选节点，修改尚未生效":"先在节点页选择一个候选节点"}
 Repeater {model:[{value:"rules",name:"规则模式 · 按规则分流"},{value:"global",name:"全局模式 · 业务流量走代理"},{value:"direct",name:"直连模式 · 业务流量直连"}]
  WB.TouchButton {required property var modelData;Layout.fillWidth:true;foreground:root.foreground;accent:root.accent;text:modelData.name;selected:root.model.draft.mode===modelData.value;onClicked:root.model.selectMode(modelData.value)}
 }
 WB.TouchButton {Layout.fillWidth:true;text:"校验并保存草稿";foreground:root.foreground;accent:root.accent;enabled:!!model.draft.node_id&&!model.catalogPending;onClicked:model.saveRoutingDraft()}
 PText {Layout.fillWidth:true;color:root.foreground;text:model.catalogFeedback}
 PText {Layout.fillWidth:true;color:root.foreground;text:"运行配置尚未切换。候选通过核心校验和恢复检查后，才开放应用入口。"}
}
