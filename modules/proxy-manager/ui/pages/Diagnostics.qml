import QtQuick
import QtQuick.Layouts
import ".."
Page {id:root;title:"诊断";description:"先看物理出口，再看代理与 TUN，最后看目标访问。"
 PText {Layout.fillWidth:true;color:root.foreground;text:"当前仅展示已有检测结果，不额外测速。"}

 PText {Layout.fillWidth:true;color:root.foreground;text:model.lastError||"暂无新的操作错误"}
 PText {Layout.fillWidth:true;color:root.foreground;text:"状态版本  "+(model.snapshot.revision||"未知")+"\n访问检测  "+(model.online?"正常":"待确认")} 
}
