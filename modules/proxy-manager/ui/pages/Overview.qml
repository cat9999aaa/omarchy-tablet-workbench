import QtQuick
import QtQuick.Layouts
import ".."
import "../../../workbench-ui" as WB
ProxyPage {
 id:root;title:"连接总览";description:"物理网络、代理进程和访问检测分别确认。收起窗口后，网络继续工作。"
 PText {Layout.fillWidth:true;color:root.foreground;text:model.online?"最近访问检测正常":"访问状态待确认";font.pixelSize:24}
 PText {Layout.fillWidth:true;color:root.foreground;text:"物理出口  "+model.physicalLabel+"\n代理  "+model.proxyLabel+"    ·    TUN  "+model.tunLabel+"\n当前节点  "+model.nodeLabel;lineHeight:1.5}
 WB.TouchButton {objectName:"proxyToggle";Layout.fillWidth:true;foreground:root.foreground;accent:root.accent;text:model.pending?"处理中，请稍候…":model.proxyLabel==="开启"?"关闭代理":"开启代理";enabled:model.allowed(model.proxyLabel==="开启"?"disable":"enable");onClicked:if(model.proxyLabel==="开启")confirm.open();else model.submit("enable",true)}
 PText {Layout.fillWidth:true;color:root.foreground;text:(model.snapshot.capabilities||[]).indexOf("enable")<0?"只读状态：控制归属或桌面状态尚未确认，当前连接保持。":"开关操作由统一服务串行执行，系统授权完成后再检查实际状态。"}
 PText {Layout.fillWidth:true;color:root.foreground;text:"局域网与 ZeroTier 外层流量保留独立通路；物理网络仍由 NetworkManager 管理。"}
 ConfirmDialog {id:confirm;title:"关闭代理？";description:"使用代理的应用可能暂时无法联网。物理网络不关闭。";onAccepted:model.submit("disable",true)}
}
