import QtQuick
import QtQuick.Layouts
import ".."
ProxyPage {id:root;title:"设置";description:"手动关闭优先；熄屏不改变联网意图。"
 PText {Layout.fillWidth:true;color:root.foreground;text:"工作台、控制台和网络面板共用一个控制服务。代理核心由 systemd 管理，关闭窗口后继续运行；手动关闭代理则停止核心和 TUN。"}

}
