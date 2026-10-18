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
 WB.TouchButton {Layout.fillWidth:true;text:model.corePending?"准备中…":"准备候选配置";foreground:root.foreground;accent:root.accent;enabled:!!model.draft.node_id&&!model.corePending;onClicked:model.prepareCore()}
 PText {Layout.fillWidth:true;color:root.foreground;text:model.coreFeedback}
 WB.TouchButton {Layout.fillWidth:true;text:"应用候选配置…";foreground:root.foreground;accent:root.accent;enabled:!!model.coreCandidate.candidate_hash&&model.allowed("apply");onClicked:confirm.open()}
 PText {Layout.fillWidth:true;color:root.foreground;text:"当前分流："+model.modeLabel+"。先开启代理后才能切换运行配置。"}
 ConfirmDialog {id:confirm;title:"应用节点与分流？";description:"将短暂重启代理核心。先建立独立恢复计时器，访问检查失败会恢复上一配置。Wi-Fi／4G 保持。";onAccepted:model.applyCandidate(true)}
}
