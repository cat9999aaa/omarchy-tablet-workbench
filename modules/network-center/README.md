# 触屏网络中心原型 1.3.4

基于 Omarchy 4.0.4 官方 omarchy.network 插件克隆，保留上游 MIT 许可，不修改打包源文件。固定顶部显示真实物理出口、直接联网和 TUN 状态；六个标签共用固定尺寸与内部滚动，切标签不修改连接。

## 选网与代理

NetworkManager 自动优先级为有线100、Wi-Fi600、4G700；蜂窝计费且自动连接待命。保留 Arch 官方检测地址，间隔15秒、超时5秒。固定线路会进入手动模式；不做负载均衡。TUN 网卡不会被当成物理上网出口。

v2rayN 由唯一用户 systemd 实例管理，使用现有节点和127.0.0.1:10808；切网不重启GUI。policy.py 保存手动关闭意图，网络事件不会重新开启已手动关闭的代理。

应用接管使用 v2rayN 自带的官方 sing-box 核心。原生GUI启用TUN在Linux下每次重启需要重新输入sudo密码；本机改为由系统级 pcadmin-v2ray-tun.service 托管其已生成的TUN前端，连接现有10808，不增加节点或第二个GUI。GUI内置TUN开关保持关闭，避免重复创建同一虚拟网卡。请使用网络面板统一开关。

root拥有的 /etc/pcadmin-network/tun.json 来源于客户端生成的 configPre.json，已验证只含本地SOCKS出口与direct，不含节点凭据；规则文件改为读取打包目录，保留用户与打包Xray进程绕行，排除私有网段。服务限制文件系统写入，仅保留NET_ADMIN、NET_RAW及进程识别所需SYS_PTRACE能力；启动前等待10808就绪。不会保存sudo密码。配置属于本机外部资源，不上传仓库。

面板关闭代理时先停止TUN，再关闭系统代理和GUI；退出GUI的事件也会请求停止TUN。这些系统服务操作可能需要P3系统认证。启动服务已enable，但冷启动实际效果尚未验收。更改客户端端口、TUN规则或升级核心后，需要重新核对和生成root配置；当前没有自动迁移器。

## 其他入口

ZeroTier常驻，显示在线及授权状态，不接管默认出口或DNS。GPS按需开启，不保存位置。飞行模式需确认，保存无线状态后恢复。

### ZeroTier 与 TUN 分离

`zero_bypass.py` 与 `pcadmin-zerotier-bypass.service` 使用 Linux 策略路由：仅将独立 `zerotier-one` 账户的外层连接送入主路由表，优先级8990早于TUN的9000系列规则；IPv4/IPv6均处理。不按全局UDP端口绕过，不绕过root或普通应用，也不改ZeroTier网络规则、代理节点及国内外分流。适用于本机已确认会降权到独立账户的ZeroTier版本；其他机器必须先核对实际运行UID，不能直接照装。

部署脚本至 `/usr/local/libexec/pcadmin-zerotier-bypass.py`（root拥有、0644），安装并启用配套服务。ZeroTier和托管TUN的用户维护systemd drop-in使用Wants/After依赖该服务。应用无需重启代理或蜂窝连接。脚本会拒绝占用的优先级、识别重复规则、在部分添加失败时撤销本次添加；执行前检查IPv4/IPv6两侧冲突。停止只删除匹配本账户和主路由表的规则。部署后必须用该账户UID查询实际路由，并对比普通应用仍走TUN；服务active不能代替路由验证。

恢复时先移除两个服务的 `30-pcadmin-zero-bypass.conf` drop-in，daemon-reload，再disable --now配套bypass服务；不停止ZeroTier或TUN。原件备份在本机 `/var/lib/pcadmin-network/recovery/zerotier-bypass-*`。规则绕过代理不保证NAT穿透、远端在线或所有成员互通；P2P连接状态须单独验证。2026-10-16实测路由分离通过，重复应用无新增规则，37项模块测试通过；冷启动尚未实测。

蜂窝信号百分比不能独立用作优化依据。本次22%同时对应RSRP -74dBm、RSRQ -12dB、S/N 4dB，说明信号强度与质量应分开看。临时开启详细信号轮询后已恢复关闭。国内/国外小请求响应不能代替带宽测试，也不能把前后波动当成因果提速证据。

本机权威源码是管理项目 tools/network-center；仓库副本默认使用 ~/.local/lib/omarchy-tablet-workbench/network-center/network.py，可通过 PCADMIN_NETWORK_HELPER 覆盖。本模块尚无通用安装器。仓库服务模板中的 __USER__/__UID__ 必须在部署前替换，本机蜂窝接口/profile也需按目标适配。

## 实际验证与边界

30项单测通过，覆盖单实例联动、手动关闭意图、GSM重新连接、TUN退出顺序和真实物理出口识别。此前六页运行时尺寸一致。

4G直连国内HTTPS200；开启TUN后，不指定代理的Google检测204，内置浏览器Google搜索实际刷新通过。用户随后确认体验良好。Wi-Fi恢复后四次TUN检测204，最后按用户要求关闭Wi-Fi并固定4G。先前五轮切换仅验证显式10808请求，不能当作应用接管证据。

ZeroTier服务运行，但最新成员ping未通过，当前跨网段互通不能宣称通过。真实飞行模式、冷启动TUN、GUI退出/面板开关完整认证流程、Wi-Fi关联但外网断开、十分钟息屏联网未验收。不承诺切网时既有TCP会话完全无中断。

运行测试：python -m unittest discover -s 模块目录 -p 'test_*.py'。verify_handover.py 必须显式 --run，会临时关闭Wi-Fi并自动恢复，仅验证链路/代理核心。

## 恢复

先停止并禁用 pcadmin-v2ray-tun.service，确认singbox_tun及其策略路由退出，再恢复客户端原来的系统代理模式。恢复前备份位于本机管理项目 backups/network-center-2026-10-16 和 /var/lib/pcadmin-network/recovery；TUN最初不存在的文件应按记录移除。不要同时打开GUI内置TUN与系统托管TUN。

UI可回退manifest到之前release入口后执行 omarchy-shell shell rescanPlugins，不重置整个shell。NetworkManager检测配置恢复后仅reload conf，不重启网络服务。恢复UI不停止ZeroTier。不提交节点、凭据或私人网络地址。
