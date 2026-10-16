# 触屏网络中心原型 1.2.2

基于本机 Omarchy 4.0.4 的官方 `omarchy.network` 插件克隆。Panel.qml / Model.js 派生自 Omarchy，保留 MIT 许可（LICENSE.omarchy）。不修改打包源文件。

## 用户行为

六个独立页：Wi-Fi、4G、有线／本地、ZeroTier、V2Ray、GPS。切页只更改显示，只有明确点击选网按钮才调整线路。没有负载均衡或定时改路由。未选线路保留为较低优先级，遵循 NetworkManager 的正常路由行为。

ZeroTier 常驻，显示服务、服务器在线状态、网络授权结果、地址。只读状态经 root 管理的固定脚本导出到 /run/pcadmin-network/status.json；不导出认证令牌。状态超过45秒会标为过期。服务与网络授权不同，授权成功不保证所有远端服务/转发都可用。

飞行模式二次确认后关闭 Wi-Fi / WWAN / Bluetooth 软件无线开关。原状态保存于 root 专用 /var/lib/pcadmin-network/flight.json，退出时恢复，原先关闭的 WWAN 不会自动开启。开启失败尝试恢复。GPS 接收不受影响。ZeroTier 服务仍运行，等待恢复连接。

## 部署边界

这是这台平板的已部署原型，尚无通用安装器。蜂窝接口和默认 profile 对应目标设备；仓库 QML 默认读取 ~/.local/lib/omarchy-tablet-workbench/network-center/network.py，也可通过 PCADMIN_NETWORK_HELPER 设置；本机已部署版仍使用原管理目录。自定义扩展使用用户插件版本目录，root 控制器是 /usr/local/libexec/pcadmin-radio-control。系统状态 timer 每15秒刷新；界面只在打开时读取完整状态。

必须备份旧 manifest / Panel / helper / 同名 unit，先审查和测试后以官方插件克隆方式安装，禁止覆盖 /usr/share/omarchy。不要直接运行来源不明的 root 代码。飞行模式操作经正常 Polkit 认证。

## 验证与限制

13项单元测试通过，覆盖授权与服务的区分、脱敏、飞行模式原状态保留和失败恢复、路由切换避免重连、有线设备目标选择。六页运行时切换和截图检查通过，Wi-Fi选路实际更新成功，ZeroTier真实网络状态OK。GPS此前真实定位通过。

本轮未实际切断无线测试飞行模式；未测试新有线硬件；4G保持用户原来的关闭状态，没有宣称本轮重新连网成功。屏幕关闭后联网故障尚未复现。软件与实体手指测试分别记录。

运行测试：`python -m unittest discover -s tools/network-center -p 'test_*.py'`（源码仓库模块路径按实际位置替换）。

恢复 UI：把插件 manifest entryPoints.barWidget 恢复为备份的 release-1.1.4/Panel.qml，执行 omarchy-shell shell rescanPlugins。此操作不改无线连接。恢复原生面板只替换对应网络 widget，不整份重置 shell 配置。不要因为恢复UI而停止用户要求常驻的 ZeroTier。
