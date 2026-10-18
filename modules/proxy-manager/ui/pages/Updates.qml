import QtQuick
import QtQuick.Layouts
import ".."
import "../../../workbench-ui" as WB
ProxyPage {id:root;title:"更新";description:"稳定版本先审查，当前连接保持运行。"
 PText {Layout.fillWidth:true;color:root.foreground;text:model.updates.observed_at?"上次检查  "+new Date(model.updates.observed_at*1000).toLocaleString(Qt.locale("zh_CN"),"MM-dd hh:mm")+(model.now-model.updates.observed_at>86400?" · 缓存已过期":""):"尚未检查上游版本"}
 RowLayout {Layout.fillWidth:true;spacing:12
  WB.TouchButton {Layout.fillWidth:true;foreground:root.foreground;accent:root.accent;text:"读取本机记录";enabled:!model.updatesPending;onClicked:model.updateAction("list")}
  WB.TouchButton {Layout.fillWidth:true;foreground:root.foreground;accent:root.accent;text:model.updatesPending?"处理中…":"检查稳定版本";enabled:!model.updatesPending;onClicked:model.updateAction("check")}
 }
 ColumnLayout {objectName:"updateItems";Layout.fillWidth:true;spacing:12
  Repeater {model:root.model.updates.proposals||[]
   delegate:Rectangle {required property var modelData;Layout.fillWidth:true;implicitHeight:info.implicitHeight+32;color:Qt.rgba(root.accent.r,root.accent.g,root.accent.b,0.08);radius:12;border.color:Qt.rgba(root.foreground.r,root.foreground.g,root.foreground.b,0.15)
    PText {id:info;anchors.fill:parent;anchors.margins:16;color:root.foreground
     text:({application:"工作台",core:"代理核心",rules:"分流规则",subscription:"私人订阅"}[modelData.proposal.kind]||"组件")+"  ·  "+modelData.proposal.version+"\n"+(modelData.proposal.source||"")+"\n"+({review:"待审查，尚未安装",deferred:"计费网络，延后下载",paused:"飞行模式，暂停",rejected:"元数据未通过检查"}[modelData.decision.status]||"状态未知")+"\n"+(modelData.decision.verification==="digest_only"?"摘要一致；未认证签名":"未下载，也未验证安装包签名")
    }
   }
  }
 }
 PText {Layout.fillWidth:true;color:root.foreground;text:model.updatesFeedback}
 PText {Layout.fillWidth:true;color:root.foreground;text:"程序、核心、规则分别维护。GitHub 自动检查只生成提案；订阅仍在订阅页预览后保存。"}
}
