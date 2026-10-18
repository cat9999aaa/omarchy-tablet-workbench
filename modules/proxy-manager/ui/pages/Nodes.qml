import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../../../workbench-ui" as WB
ProxyPage {
 id:root;title:"节点";description:"选择节点进入分流草稿；应用并验证之前，现有连接继续使用原配置。"
 TextField {id:search;Layout.fillWidth:true;Layout.preferredHeight:52;placeholderText:"搜索节点名称";color:root.foreground}
 PText {Layout.fillWidth:true;color:root.foreground;text:model.catalog.nodes.length?"本机目录 · "+model.catalog.nodes.length+" 个节点":"还没有原生节点目录。到订阅页预览迁移现有配置。"}
 ListView {id:list;objectName:"nodeList";Layout.fillWidth:true;Layout.preferredHeight:Math.min(480,Math.max(180,count*80));clip:true;spacing:8;cacheBuffer:80
  model:search.text?root.model.catalog.nodes.filter(function(n){return n.name.toLowerCase().indexOf(search.text.toLowerCase())>=0}):root.model.catalog.nodes
  delegate:WB.TouchButton {required property var modelData;width:list.width;height:80;foreground:root.foreground;accent:root.accent;selected:root.model.draft.node_id===modelData.id
   text:modelData.name+"\n"+modelData.protocol+" · "+modelData.transport+" · "+modelData.status
   onClicked:{root.model.selectNode(modelData.id);root.model.editRoutingRequested()}
  }
 }
 WB.TouchButton {Layout.fillWidth:true;text:"刷新本机目录";foreground:root.foreground;accent:root.accent;enabled:!model.catalogPending;onClicked:model.catalogAction({action:"list"})}
 PText {Layout.fillWidth:true;color:root.foreground;text:model.catalogFeedback}
}
