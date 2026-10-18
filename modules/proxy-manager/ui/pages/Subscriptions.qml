import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import ".."
import "../../../workbench-ui" as WB
ProxyPage {
 id:root;title:"订阅与导入";description:"先预览差异，再明确保存；不会自动开启代理或切换节点。"
 WB.TouchButton {Layout.fillWidth:true;text:"预览现有 v2rayN 节点";foreground:root.foreground;accent:root.accent;enabled:!model.catalogPending;onClicked:model.catalogAction({action:"migrate"})}
 WB.TouchButton {Layout.fillWidth:true;text:"从本地订阅文件导入";foreground:root.foreground;accent:root.accent;enabled:!model.catalogPending;onClicked:files.open()}
 FileDialog {id:files;title:"选择 URI 或 base64 订阅文件";onAccepted:model.catalogAction({action:"preview-file",path:selectedFile.toString()})}
 TextField {id:alias;Layout.fillWidth:true;Layout.preferredHeight:52;placeholderText:"订阅别名";maximumLength:80;color:root.foreground}
 TextField {id:url;Layout.fillWidth:true;Layout.preferredHeight:52;placeholderText:"HTTPS 订阅链接（仅本机保存）";echoMode:TextInput.Password;maximumLength:2048;color:root.foreground}
 WB.TouchButton {Layout.fillWidth:true;text:"下载并预览订阅";foreground:root.foreground;accent:root.accent;enabled:!model.catalogPending&&url.text.length>0&&alias.text.length>0;onClicked:downloadConfirm.open()}
 ConfirmDialog {id:downloadConfirm;title:"下载订阅？";description:"这次下载最多 8 MiB，可能使用蜂窝流量。不会自动应用节点。";onAccepted:{model.catalogAction({action:"preview-url",url:url.text,alias:alias.text,confirmed:true});url.text=""}}
 PText {Layout.fillWidth:true;color:root.foreground;text:model.catalogFeedback}
 PText {Layout.fillWidth:true;visible:!!model.preview.preview_id;color:root.foreground;text:"导入差异：新增 "+(model.preview.diff?model.preview.diff.added:0)+"，删除 "+(model.preview.diff?model.preview.diff.removed:0)+"，保留 "+(model.preview.diff?model.preview.diff.retained:0)}
 PText {Layout.fillWidth:true;visible:!!model.preview.preview_id;color:root.foreground;text:model.preview.diff&&model.preview.diff.current_removed?"注意：这份目录会移除当前节点。运行配置暂时保留，下一次切换需重新选择。":"原始 v2rayN 数据库保持不变。"}
 Repeater {model:(root.model.preview.nodes||[]).slice(0,8);PText {required property var modelData;Layout.fillWidth:true;color:root.foreground;text:modelData.name+" · "+modelData.transport}}
 WB.TouchButton {Layout.fillWidth:true;visible:!!model.preview.preview_id;text:"确认保存这份节点目录";foreground:root.foreground;accent:root.accent;enabled:!model.catalogPending;onClicked:saveConfirm.open()}
 ConfirmDialog {id:saveConfirm;title:"保存预览目录？";description:"按上方差异替换本机原生目录。原始客户端和当前连接保持。";onAccepted:model.commitPreview(true)}
}
