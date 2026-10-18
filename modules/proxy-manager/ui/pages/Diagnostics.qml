import QtQuick
import QtQuick.Layouts
import ".."
ProxyPage {id:root;title:"诊断";description:"按连接链路逐层确认；只展示现有检测，不持续测速。"
 Repeater {model:[{name:"物理出口",value:root.model.physicalLabel},{name:"本地代理",value:root.model.proxyLabel},{name:"TUN 转发",value:root.model.tunLabel},{name:"目标访问",value:root.model.online?"最近检测正常":"未知或待恢复"},{name:"用户意图",value:root.model.snapshot.user_enabled===true?"保持开启":root.model.snapshot.user_enabled===false?"手动关闭":"未知"},{name:"飞行模式",value:root.model.snapshot.flight===true?"开启":root.model.snapshot.flight===false?"关闭":"未知"}]
  delegate:RowLayout {required property var modelData;Layout.fillWidth:true;Layout.minimumHeight:48
   PText {Layout.preferredWidth:100;color:root.foreground;text:modelData.name}
   PText {Layout.fillWidth:true;color:root.foreground;text:modelData.value}
  }
 }
 PText {Layout.fillWidth:true;color:root.foreground;text:model.lastError||"暂无新的操作错误"}
 PText {Layout.fillWidth:true;color:root.foreground;text:"状态版本  "+(model.snapshot.revision||"未知")+"\n状态过期会显示未知；端口开启不代表互联网可用。"}
}
