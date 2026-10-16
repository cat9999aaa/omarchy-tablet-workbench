# 本机统一网络入口调研

2026-10-16，用户要求先调研，下午出行。仅本机Omarchy 4.0.4，不涉及替换蜂窝模块；短信/电话修复暂停。本文是调研与待确认方案，尚未部署新面板、安装gpsd/ZeroTier或改变联网/代理设置。

## 现场

- NetworkManager识别wlp3s0为wifi、cdc-wdm0为gsm，两者当前connected。4G连接及独立出站前序已实测。
- 官方omarchy.network manifest明确描述Wi-Fi list and connection state；Panel.qml只处理wifi/ethernet，Model.js没有cellular图标。官方omarchy-network-status对非wireless的默认网卡一律返回ethernet。因此LTE默认出口可能被误标为有线。
- 可通过官方omarchy plugin clone克隆现有网络面板，不修改/usr/share/omarchy。保留原Wi-Fi密码/连接流程与底部固定栏，仅替换对应网络widget。
- v2rayN7.25.6及Xray运行，127.0.0.1:10808本地入站监听；gsettings系统代理mode=none，GUI配置SysProxyType=0、EnableTun=false。不能由此断言所有应用均直连，应用可能单独配置代理。未读取/保留节点凭据或订阅。
- 未确认v2rayN具有适合本版的稳定外部路由模式控制API；当前所检查核心配置没有api.services。不能改运行中自动生成config.json或数据库来冒充可靠控制。
- vnStat服务运行，蜂窝网卡累计RX1233225/TX96044字节（调研时读数），仅启用以来本机用量。
- 本机独立u-blox GNSS 1546:01a8、ttyACM0仍在；此前未实测fix。WWAN另有gps-raw/nmea能力，但仅3gpp-lac-ci开启，不把蜂窝基站位置当GPS fix。gpsd未装。
- zerotier-one未装；本机Arch extra仓库有1.16.2-1客户端包，无需第三方源。用户说稍后由浏览器登录账号，再加入所选网络；当前没有指定Network ID，不新建或猜测网络。

## 出行版建议

1. 连接区：Wi-Fi/有线/4G分别展示；4G大触摸开关、运营商/信号/连接中/故障提示。区分开启无线电、连接某profile、选择默认出口。默认保留现有Wi-Fi优先、4G计量连接；切换出口须实际读回路由，失败恢复旧优先级。提供独立蜂窝关闭与Wi-Fi开关，以适合旅途中操作。
2. 流量区：本机蜂窝今日/本月、实时速率、统计起点。不把虚拟隧道字节叠加进蜂窝总量。电信套餐剩余没有查到直接可用官方公开接口；官方账户网页需登录，短信路径当前不通，首版显示未接入并提供官方查询入口即可。
3. 代理区：分开显示本地核心、系统代理和TUN状态；提供打开v2rayN入口。系统代理开关采用其受支持系统设置路径并读回；全局/规则/直连是核心路由策略，需核对本版官方IPC或快捷键后再实现切换，不能把端口监听当成全局代理开启。不得自动替换用户订阅或核心。
4. ZeroTier区：Arch官方包，服务状态/加入网络/授权中/网络IP/连接断开。加入用户选定网络，默认allowDefault=0、allowDNS=0，保持普通互联网出口；管理仅本机服务，不把本地API令牌写入QML或仓库。与代理TUN排除虚拟网段的配合另验，不能承诺永不冲突。
5. GPS区：优先独立u-blox+Arch gpsd，按需启动；展示搜星/定位成功、可见与参与卫星、精度、定位年龄，明确未知。打开地图是单独操作；无卫星fix不显示虚构位置，不保存轨迹/坐标。GNSS能力不等于地图已集成，在线地图与离线地图分开验收。

## 实现与验证边界

建议先扩展已有官方网络面板的4G/流量/入口，后续分别实现代理控制、ZeroTier及GPS。界面保持Omarchy原生风格，所有常用操作可点按，收起后停止高频刷新。屏幕窄时纵向滚动，不新增挤占应用空间的永久侧栏。此前用户拒绝的hyprbars不涉及。

实施前备份shell.json及克隆插件；验证4G-only/Wi-Fi-only/双连接与失败恢复、默认路由识别、代理状态真实读回、ZeroTier授权前后及退出、GPS无fix/有fix，保留恢复官方omarchy.network入口。真实断网测试需有回退通道。当前仅调研，以上验收均未执行。

## 官方参考

- NetworkManager无线与WWAN独立开关：https://networkmanager.dev/docs/api/latest/gdbus-org.freedesktop.NetworkManager.html
- v2rayN系统代理与核心路由区别：https://github.com/2dust/v2rayn/wiki/Description-of-system-proxy-routing
- v2rayN配置文件说明（运行生成配置不能直接维护）：https://github.com/2dust/v2rayN/wiki/Description-of-some-parameters
- ZeroTier配置/默认路由与DNS：https://docs.zerotier.com/config/
- ZeroTier加入与控制器授权：https://docs.zerotier.com/quickstart/
- Arch客户端包文件：https://archlinux.org/packages/extra/x86_64/zerotier-one/files/
- gpsd状态与客户端：https://gpsd.gitlab.io/gpsd/client-howto.html
- 中国电信官方账户流量查询（省份/套餐需以实际账户为准）：https://m.gd.189.cn/consumeInfo/myHisConsume/myHisConsume.html

## ZeroTier实施进展（同日）

用户随后明确要求先配置本机ZeroTier。已从Arch extra安装1.16.2-1（包完整性检查25文件0改动），启动并启用systemd服务。通过用户自行登录旧版控制台，逐网核对已授权活跃数量，按用户“最多在线设备”标准选定既有私人网络；仅在用户当场确认后授权本机，未授权其他待接入节点。

本机网络状态OK、获得地址、持久网络文件存在。allowManaged=true、allowGlobal=false、allowDefault=false、allowDNS=false；普通默认路由保留Wi-Fi600/4G2000。经虚拟网口ping手机和一台Linux成员均2/2成功，普通HTTPS200。主路由首次ICMP无响应，不能宣称所有远端LAN均通。未做Wi-Fi/4G切换后的隧道重连或重启验收。私有网络ID、成员IP、账号及截图仅在本机管理记录，不上传仓库。

实施中修正了首次手工建networks.d的所有权：目录和local.conf使用软件服务账户，而非root；服务正常、网络配置已持久化。核心身份/认证令牌未导出，未新增软件源。网络面板UI、代理控制、GPS仍未部署。
