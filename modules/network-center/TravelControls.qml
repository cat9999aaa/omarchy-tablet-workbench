import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Ui as Ui
import qs.Commons
import "Workbench" as WB
import "Workbench/State.js" as SharedState

Item {
    id: hub
    default property alias wifiContent: wifiSlot.data
    signal closeRequested()
    property var themeTokens:null
    property bool opened: false
    property real observedAt: 0
    property real now: Date.now()/1000
    readonly property bool stateFresh:SharedState.freshSnapshot({observed_at:observedAt},now,15)
    readonly property bool stateReady:stateFresh && typeof state.wifi_enabled==="boolean" && typeof state.wwan==="boolean"
    property string selectedTab: "wifi"
    property bool confirmFlight: false
    property var state: ({})
    property string feedback: ""
    readonly property bool busy: action.running
    readonly property string helper: (Quickshell.env("PCADMIN_NETWORK_HELPER") || Quickshell.env("HOME") + "/.local/lib/omarchy-tablet-workbench/network-center/network.py")
    readonly property string currentNetwork: ({wifi:"Wi-Fi",ethernet:"有线网络",'4g':"中国电信 4G",virtual:"虚拟网络",none:"未连接"}[state.primary] || "读取中")
    readonly property string internetState: ({ok:"可上网",failed:"联网检测失败",unavailable:"未联网"}[(state.health || {}).internet] || "检测中")
    readonly property string proxyState: !stateFresh || typeof (state.policy || {}).proxy_enabled!=="boolean" ? "待读取" : !(state.policy || {}).proxy_enabled ? "已手动关闭" : !state.proxy_available ? "未就绪" : state.proxy_tun ? ({ok:"TUN 已接管 · 可联网",failed:"TUN 已开启 · 检测异常"}[(state.health || {}).tun] || "TUN 已接管 · 检测中") : "TUN 未开启"
    readonly property var page: pageData(selectedTab,state)
    function refresh() { if (!poll.running && opened) poll.running=true }
    function act(op) { if(busy || !stateFresh)return; feedback="正在操作…";action.command=["/usr/bin/python",helper,op];action.running=true }
    function bytes(n) { if(n===null || n===undefined)return "—";return n>=1073741824 ? (n/1073741824).toFixed(2)+" GB" : (n/1048576).toFixed(1)+" MB" }
    function responseText(key) {
        const health=state.health || {}, n=(health.latency_ms || {})[key]
        if(health[key]==="failed")return "检测失败／超时"
        if(health[key]!=="ok" || n===null || n===undefined)return "等待检测"
        return n<1000 ? Math.round(n)+" 毫秒" : (n/1000).toFixed(2)+" 秒"
    }
    function zeroDetails(s) {
        const peers=s.zero_peers || {}
        if(peers.active_devices===undefined)return s.zero_peer_error || "设备连接：等待检测"
        return "有活动路径的设备："+peers.active_devices+"\n最低响应："+(peers.best_latency_ms===null || peers.best_latency_ms===undefined ? "未测得" : Math.round(peers.best_latency_ms)+" 毫秒")
    }
    function ownState(connected,type) { return connected ? (hub.state.primary===type ? "已连接 · 正在上网" : "已连接 · 备用") : "未连接" }
    function pageData(tab,s) {
        if(!stateFresh)return {title:({wifi:"Wi-Fi",cell:"4G",local:"有线／本地",zero:"ZeroTier",proxy:"V2Ray",gps:"GPS"})[tab]||"网络",status:"待读取",info:"尚未取得有效设备状态",hint:"等待状态刷新后再操作。",actions:[]}
        const addresses=(s.local_addresses || []).map(x=>x.interface+" · "+(x.addresses || []).join(" / ")).join("\n")
        const policy=s.policy || {}
        if(tab==="wifi")return {title:"Wi-Fi",status:typeof s.wifi_enabled!=="boolean"?"无线状态未知":s.wifi_enabled ? ownState(s.wifi_state==="connected","wifi") : "无线已关闭",info:(s.wifi_connection || "尚未连接热点")+"\n"+((s.local_addresses || []).filter(x=>x.interface==="wlp3s0").map(x=>(x.addresses || []).join(" / ")).join("\n")),hint:"选择下方热点可连接；固定线路会退出自动选网。",actions:[{text:s.wifi_enabled?"关闭 Wi-Fi":"开启 Wi-Fi",op:s.wifi_enabled?"wifi-off":"wifi-on",enabled:typeof s.wifi_enabled==="boolean"},{text:"固定用 Wi-Fi",op:"prefer-wifi",enabled:s.wifi_state==="connected"}]}
        if(tab==="cell")return {title:"中国电信 4G",status:typeof s.wwan!=="boolean"?"蜂窝状态未知":s.wwan ? ownState(s.cell_connected,"4g") : "蜂窝无线已关闭",info:"信号："+(s.wwan ? (s.signal===null||s.signal===undefined?"未知":s.signal+"%") : "—")+"\n今日用量："+bytes((s.traffic || {}).day)+"\n本月用量："+bytes((s.traffic || {}).month),hint:"流量是本机统计。自动模式下可保持备用；V2Ray 的手动关闭选择始终有效。",actions:[{text:"固定用 4G",op:"prefer-cell",enabled:true},{text:s.cell_connected?"断开 4G 数据":"连接 4G 数据",op:s.cell_connected?"cell-off":"cell-on",enabled:true},{text:s.wwan?"关闭蜂窝无线":"开启蜂窝无线",op:s.wwan?"cell-radio-off":"cell-radio-on",enabled:typeof s.wwan==="boolean"}]}
        if(tab==="local")return {title:"有线／本地网络",status:(s.wired || []).some(x=>x.state==="connected") ? ownState(true,"ethernet") : "未连接有线网卡",info:addresses || "尚无本地网络地址",hint:"Wi-Fi 也能访问它所在的局域网。有线网卡接入后在这里操作。",actions:[{text:"固定用有线",op:"prefer-wired",enabled:(s.wired || []).some(x=>x.state==="connected")},{text:(s.wired || []).some(x=>x.state==="connected")?"断开有线":"连接有线",op:(s.wired || []).some(x=>x.state==="connected")?"wired-off":"wired-on",enabled:(s.wired || []).length>0}]}
        if(tab==="zero")return {title:"ZeroTier",status:s.flight_active?"飞行模式 · 等待网络":s.zero_online?"服务在线 · 设备连接见下方":s.zero_enabled?"服务已开 · 等待连接":"服务未运行",info:((s.zero_networks || []).map(x=>x.name+" · "+x.state+"\n"+(x.addresses || []).join("\n")).join("\n") || s.zero_error || "等待授权状态")+"\n\n"+zeroDetails(s),hint:"保持常驻，不接管默认出口或 DNS。活动路径不等于所有设备互通，也不代表应用服务可访问。",actions:[{text:"恢复连接服务",op:"zero-on",enabled:!s.zero_enabled},{text:"核对网络授权",op:"zero-refresh",enabled:true}]}
        if(tab==="proxy")return {title:"V2Ray",status:!policy.proxy_enabled?"已手动关闭":s.proxy_available&&s.proxy_tun?"TUN 应用接管已开启":"代理未就绪",info:"本地入口：127.0.0.1:10808\n系统代理："+(s.proxy_system?"已开启":"已关闭")+"\n应用接管："+(s.proxy_tun?"TUN 已开启":"未开启")+"\n联网检测："+hub.proxyState+"\n\n国内直连响应："+responseText("internet")+"\n代理响应："+responseText("proxy")+"\nTUN 响应："+responseText("tun"),hint:"响应为小请求完成时间，不是下载速度。唯一实例常驻，切网不重启；手动关闭会关闭 TUN、客户端和核心。",actions:[{text:policy.proxy_enabled?"关闭 V2Ray":"开启 V2Ray",op:policy.proxy_enabled?"proxy-off":"proxy-on",enabled:true},{text:"打开节点设置",op:"proxy-open",enabled:true}]}
        return {title:"GPS 卫星定位",status:(s.gps || {}).state || "读取中",info:"可见卫星："+((s.gps || {}).satellites===null || (s.gps || {}).satellites===undefined ? "—" : s.gps.satellites)+"\n参与定位："+((s.gps || {}).used===null || (s.gps || {}).used===undefined ? "—" : s.gps.used),hint:"定位按需开启。打开地图不会自动开启 GPS；卫星位置需等待有效定位。",actions:[{text:(s.gps || {}).state==="关闭"?"开始定位":"停止定位",op:(s.gps || {}).state==="关闭"?"gps-on":"gps-off",enabled:true},{text:"打开地图",op:"gps-map",enabled:true},{text:"卫星详情",op:"gps-details",enabled:true}]}
    }
    Timer { interval:4000;repeat:true;running:hub.opened;triggeredOnStart:true;onTriggered:{hub.now=Date.now()/1000;hub.refresh()} }
    Process { id:poll;command:["/usr/bin/python",hub.helper,"status"];stdout:SplitParser {onRead:line=>{try{const d=JSON.parse(line);if(!d || d.ok===false || !d.policy)throw new Error("invalid snapshot");hub.state=d;hub.observedAt=Date.now()/1000;hub.now=hub.observedAt}catch(e){hub.observedAt=0;hub.feedback="状态读取失败，等待重试"}}} }
    Process { id:action;stdout:SplitParser {onRead:line=>{try{let d=JSON.parse(line);hub.feedback=d.message || "检测已更新"}catch(e){hub.feedback="操作未完成"}}}onExited:hub.refresh() }
    Process {id:entertainment;command:["omarchy-shell","pcadmin.controlCenter","open"]}
    component Label: Text {color:Color.foreground;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;wrapMode:Text.Wrap;width:parent.width}
    WB.PanelBody {
        themeTokens:hub.themeTokens
        id:body;anchors.fill:parent;title:"网络中心";foreground:Color.foreground;accent:Color.accent;fontFamily:Style.font.family
        onCloseRequested:hub.closeRequested()
        Column {width:parent.width;spacing:8
        Rectangle {width:parent.width;height:Math.max(76,summaryColumn.implicitHeight+20);radius:6;color:"transparent";border.width:1;border.color:Color.foreground
            Column {id:summaryColumn;anchors.fill:parent;anchors.margins:10;spacing:5
                Label {text:hub.stateFresh?"当前上网："+hub.currentNetwork+" · "+hub.internetState:"当前上网：待读取";font.bold:true}
                Label {text:"代理："+hub.proxyState+" · "+((hub.state.policy || {}).mode==="auto"?"自动选网":"手动固定");opacity:0.8}
            }
        }
        GridLayout {width:parent.width;columns:3;columnSpacing:6
            WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;Layout.fillWidth:true;bordered:true;enabled:hub.stateReady&&!hub.busy&&!hub.state.flight_saved;text:"自动选网";selected:(hub.state.policy || {}).mode==="auto";onClicked:hub.act("auto-mode")}
            WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;Layout.fillWidth:true;bordered:true;enabled:hub.stateFresh&&!hub.busy;text:hub.state.flight_saved?"退出飞行模式":"飞行模式…";onClicked:{if(hub.state.flight_saved)hub.act("flight-off");else hub.confirmFlight=!hub.confirmFlight}}
            WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;Layout.fillWidth:true;bordered:true;enabled:hub.stateReady&&!hub.busy&&!hub.state.flight_saved;text:"检测网络";onClicked:hub.act("health")}
        }
        Column {width:parent.width;visible:hub.confirmFlight;spacing:6
            Label {text:"关闭 Wi-Fi、4G 射频、蓝牙和网络连接，进入离线娱乐。蓝牙外设断开；退出后恢复原开关。"}
            GridLayout {width:parent.width;columns:2;columnSpacing:6
                WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;Layout.fillWidth:true;bordered:true;text:"确认开启";onClicked:{hub.confirmFlight=false;hub.act("flight-on")}}
                WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;Layout.fillWidth:true;bordered:true;text:"取消";onClicked:hub.confirmFlight=false}
            }
        }
        Label {visible:!!hub.state.flight_saved;text:hub.state.flight_active===true?"飞行娱乐 · 无线关闭已确认":(hub.state.flight_error || "无线状态待确认");color:Color.accent}
        WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;visible:!!hub.state.flight_saved;width:parent.width;bordered:true;text:"打开离线娱乐";onClicked:entertainment.running=true}
        GridLayout {width:parent.width;columns:3;columnSpacing:6;rowSpacing:6
            Repeater {model:[{key:"wifi",name:"Wi-Fi"},{key:"cell",name:"4G"},{key:"local",name:"有线／本地"},{key:"zero",name:"ZeroTier"},{key:"proxy",name:"V2Ray"},{key:"gps",name:"GPS"}]
                WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;required property var modelData;Layout.fillWidth:true;bordered:true;selected:hub.selectedTab===modelData.key;text:modelData.name;onClicked:{hub.selectedTab=modelData.key;hub.feedback="";body.contentY=0}}
            }
        }
        Ui.PanelSeparator {foreground:Color.foreground}
    }
        Column {id:content;width:parent.width;spacing:12
            Label {text:hub.page.title;font.pixelSize:hub.themeTokens?hub.themeTokens.font.title:18;font.bold:true}
            Rectangle {width:parent.width;height:Style.space(48);radius:6;color:"transparent";border.width:1;border.color:Color.foreground
                Text {anchors.fill:parent;anchors.margins:10;text:hub.page.status;color:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:15;wrapMode:Text.Wrap;verticalAlignment:Text.AlignVCenter}
            }
            Label {text:hub.page.info}
            GridLayout {width:parent.width;columns:2;columnSpacing:8;rowSpacing:8
                Repeater {model:hub.page.actions
                    WB.TouchButton {themeTokens:hub.themeTokens;foreground:Color.foreground;accent:Color.accent;font.family:Style.font.family;font.pixelSize:hub.themeTokens?hub.themeTokens.font.body:14;required property var modelData;Layout.fillWidth:true;bordered:true;enabled:hub.stateFresh && !hub.busy && !hub.state.flight_saved && modelData.enabled;text:modelData.text;onClicked:hub.act(modelData.op)}
                }
            }
            Label {text:hub.page.hint;opacity:0.7}
            Label {visible:hub.feedback!=="";text:hub.feedback;color:Color.accent}
            Column {id:wifiSlot;width:parent.width;visible:hub.selectedTab==="wifi"&&!hub.state.flight_saved}
        }
    }
}
