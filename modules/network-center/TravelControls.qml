import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Ui as Ui
import qs.Commons

Column {
    id: hub
    property bool opened: false
    property string selectedTab: "wifi"
    property bool confirmFlight: false
    property var state: ({})
    property string feedback: ""
    readonly property bool busy: action.running
    readonly property string helper: Quickshell.env("PCADMIN_NETWORK_HELPER") || (Quickshell.env("HOME") + "/.local/lib/omarchy-tablet-workbench/network-center/network.py")
    width: parent.width
    spacing: 10
    function refresh() { if (!poll.running && opened) poll.running = true }
    function act(op) { if (busy) return; feedback="正在操作…系统认证时可按 P3"; action.command=["/usr/bin/python",helper,op]; action.running=true }
    function bytes(n) { if(n===null || n===undefined) return "—"; return n>=1073741824 ? (n/1073741824).toFixed(2)+" GB" : (n/1048576).toFixed(1)+" MB" }
    Timer { interval: 4000; repeat: true; running: hub.opened; triggeredOnStart: true; onTriggered: hub.refresh() }
    Process { id: poll; command:["/usr/bin/python",hub.helper,"status"]; stdout: SplitParser { onRead: line=>{try { hub.state=JSON.parse(line) } catch(e) {} } } }
    Process { id: action; stdout: SplitParser { onRead: line=>{try {hub.feedback=JSON.parse(line).message || ""}catch(e){hub.feedback="操作未完成"}} } onExited: hub.refresh() }
    component Label: Text { color:Color.foreground; font.family:Style.font.family; font.pixelSize:14; wrapMode:Text.Wrap; width:parent.width }
    component Action: Ui.Button { required property string operation; Layout.fillWidth:true; implicitHeight:46; bordered:true; enabled:!hub.busy; onClicked:hub.act(operation) }
    Label { text:"网络中心"; font.pixelSize:21; font.bold:true }
    Label { text: "当前上网："+({wifi:"Wi-Fi",ethernet:"有线",'4g':"中国电信 4G",virtual:"虚拟网络",none:"未连接"}[hub.state.primary] || "读取中…")+" · 手动选择线路" }
    GridLayout {
        width:parent.width; columns:2; columnSpacing:8
        Ui.Button { Layout.fillWidth:true; implicitHeight:44; bordered:true; enabled:!hub.busy; text:hub.state.flight_saved ? "退出飞行模式" : "飞行模式…"; onClicked:{ if(hub.state.flight_saved) hub.act("flight-off"); else hub.confirmFlight=!hub.confirmFlight } }
        Ui.Button { Layout.fillWidth:true; implicitHeight:44; bordered:true; text:"刷新状态"; onClicked:hub.refresh() }
    }
    Column {
        width:parent.width; visible:hub.confirmFlight; spacing:8
        Label { text:"开启后关闭 Wi-Fi、4G、蓝牙，网络和 ZeroTier 暂时离线；GPS 接收不受影响。退出后恢复原无线开关。" }
        GridLayout { width:parent.width; columns:2; columnSpacing:8
            Action { text:"确认开启飞行模式"; operation:"flight-on"; onClicked:hub.confirmFlight=false }
            Ui.Button { text:"取消"; Layout.fillWidth:true; implicitHeight:44; bordered:true; onClicked:hub.confirmFlight=false }
        }
    }
    Label { visible:!!hub.state.flight_active; text:"飞行模式已开启 · 无线网络已关闭"; color:Color.accent }
    GridLayout {
        width:parent.width; columns:3; columnSpacing:6; rowSpacing:6
        Repeater {
            model:[{key:"wifi",name:"Wi-Fi"},{key:"cell",name:"4G"},{key:"local",name:"有线／本地"},{key:"zero",name:"ZeroTier"},{key:"proxy",name:"V2Ray"},{key:"gps",name:"GPS"}]
            Ui.Button { required property var modelData; Layout.fillWidth:true; implicitHeight:46; bordered:true; selected:hub.selectedTab===modelData.key; text:modelData.name; onClicked:{hub.selectedTab=modelData.key;hub.feedback=""} }
        }
    }
    Ui.PanelSeparator { foreground:Color.foreground }
    Column { width:parent.width; spacing:10; visible:hub.selectedTab==="wifi"
        Label { text:"Wi-Fi · "+(hub.state.wifi_enabled ? hub.state.wifi_state || "读取中" : "无线已关闭") }
        GridLayout { width:parent.width; columns:2; columnSpacing:8
            Action { text:hub.state.wifi_enabled ? "关闭 Wi-Fi" : "开启 Wi-Fi"; operation:hub.state.wifi_enabled ? "wifi-off" : "wifi-on" }
            Action { text:"用 Wi-Fi 上网"; operation:"prefer-wifi"; enabled:!hub.busy && hub.state.wifi_state==="connected" }
        }
        Label { text:"在下方选择热点。切换标签不会更改连接。"; opacity:0.7 }
    }
    Column { width:parent.width; spacing:10; visible:hub.selectedTab==="cell"
        Label { text:"中国电信 4G · "+(hub.state.wwan ? (hub.state.cell_connected ? "已连接" : hub.state.cell || "读取中") : "蜂窝无线已关闭")+(hub.state.wwan && hub.state.signal!==null && hub.state.signal!==undefined ? " · 信号 "+hub.state.signal+"%" : "") }
        GridLayout { width:parent.width; columns:2; columnSpacing:8; rowSpacing:8
            Action { text:"用 4G 上网"; operation:"prefer-cell" }
            Action { text:hub.state.cell_connected ? "断开 4G" : "连接 4G"; operation:hub.state.cell_connected ? "cell-off" : "cell-on" }
            Action { text:hub.state.wwan ? "关闭蜂窝无线" : "开启蜂窝无线"; operation:hub.state.wwan ? "cell-radio-off" : "cell-radio-on" }
        }
        Label { text:"今日流量："+hub.bytes((hub.state.traffic || {}).day)+"\n本月流量："+hub.bytes((hub.state.traffic || {}).month)+"\n本机统计，非电信套餐剩余" }
    }
    Column { width:parent.width; spacing:10; visible:hub.selectedTab==="local"
        Label { text:(hub.state.wired || []).length ? "有线设备："+hub.state.wired.map(x=>x.interface+" · "+x.state).join("\n") : "未接入有线网卡。USB 网卡或底座接入后会显示在这里。" }
        Repeater { model:hub.state.local_addresses || []; Label { required property var modelData; text:modelData.interface+" · "+(modelData.addresses || []).join(" / ") } }
        Label { text:"本地网络不等于有线：连接 Wi-Fi 时，也可直接访问当前 Wi-Fi 的局域网。" }
        GridLayout { width:parent.width; columns:1
            Action { text:"用有线上网"; operation:"prefer-wired"; enabled:!hub.busy && (hub.state.wired || []).some(x=>x.state==="connected") }
            Action { text:(hub.state.wired || []).some(x=>x.state==="connected") ? "断开有线" : "连接有线"; operation:(hub.state.wired || []).some(x=>x.state==="connected") ? "wired-off" : "wired-on"; enabled:!hub.busy && (hub.state.wired || []).length>0 }
        }
    }
    Column { width:parent.width; spacing:10; visible:hub.selectedTab==="zero"
        Label { text:"ZeroTier · "+(hub.state.zero_enabled ? "服务运行中" : "服务未运行")+"\n服务器连接："+(hub.state.flight_active ? "离线（飞行模式）" : hub.state.zero_online ? "在线" : "离线／等待连接") }
        Repeater { model:hub.state.zero_networks || []
            Label { required property var modelData; text:modelData.name+" · "+modelData.state+"\n"+(modelData.addresses || []).join("\n") }
        }
        Label { visible:!(hub.state.zero_networks || []).length; text:hub.state.zero_error || "正在读取网络授权状态…" }
        Label { text:"已授权才能加入私有网络。保持常驻，不接管默认上网出口或 DNS；飞行模式期间等待无线恢复。"; opacity:0.75 }
        GridLayout { width:parent.width; columns:2; columnSpacing:8
            Action { text:"恢复连接服务"; operation:"zero-on"; enabled:!hub.busy && !hub.state.zero_enabled }
            Action { text:"重新核对授权"; operation:"zero-refresh" }
        }
    }
    Column { width:parent.width; spacing:10; visible:hub.selectedTab==="proxy"
        Label { text:"V2Ray · 本地代理 "+(hub.state.proxy_available ? "可用" : "未启动")+"\n系统代理："+(hub.state.proxy_system ? "开启" : "关闭") }
        GridLayout { width:parent.width; columns:2; columnSpacing:8
            Action { text:hub.state.proxy_system ? "关闭系统代理" : "开启系统代理"; operation:hub.state.proxy_system ? "proxy-off" : "proxy-on" }
            Action { text:"节点／模式设置"; operation:"proxy-open" }
        }
        Label { text:"节点、规则／全局与 TUN 使用 v2rayN 原生界面设置。系统代理只影响遵循系统代理设置的应用。"; opacity:0.75 }
    }
    Column { width:parent.width; spacing:10; visible:hub.selectedTab==="gps"
        Label { text:"GPS · "+((hub.state.gps || {}).state || "读取中…")+(((hub.state.gps || {}).satellites!==null && (hub.state.gps || {}).satellites!==undefined) ? "\n使用卫星 "+hub.state.gps.used+" / 可见 "+hub.state.gps.satellites : "") }
        GridLayout { width:parent.width; columns:2; columnSpacing:8
            Action { text:((hub.state.gps || {}).state==="关闭") ? "开始定位" : "停止定位"; operation:((hub.state.gps || {}).state==="关闭") ? "gps-on" : "gps-off" }
            Action { text:"卫星详情"; operation:"gps-details" }
        }
        Label { text:"独立卫星定位，按需开启；不保存位置轨迹。GPS 不是上网线路。"; opacity:0.75 }
    }
    Label { visible:hub.feedback!==""; text:hub.feedback; color:Color.accent }
}
