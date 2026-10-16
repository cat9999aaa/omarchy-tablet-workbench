# 本机蜂窝网络与流量管理

本机模块 Dell DW5821e / Foxconn T77W968，当前固件 T77W968.F1.0.0.5.2.GC.013。SIM为用户确认的中国电信4G/5G卡；卡在手机中通话正常。模块实际只报告UMTS/LTE，不支持5G NR。

## 2026-10-16实测

- 中国电信LTE本地注册、PS attached、无漫游。APN由官方运营商数据库自动选择ctnet。
- curl强制绑定蜂窝网卡，百度HTTPS200；运营商DNS绑定同一网卡返回有效答案；1MiB HTTPS下载完成。Wi-Fi保持连接且路由优先。
- IPv6地址已下发，但独立IPv6出站未验收。跨境1MiB样本平均约114KB/s，包含连接开销，不是4G峰值带宽测量。
- 电话：GNOME Calls/ModemManager提供语音接口，但实际来电无法接通、去电失败；日志dialing→terminated，没有接通状态。接口存在不能证明语音能力。NTT公布的同系列认证固件明确无CS Voice/VoLTE；与本机GC固件不同，不能据此证明所有变体硬件都绝对不可能。当前组合无可用电话方案。
- 短信：MBIM存储已初始化，PDU，40条容量；AT+CSMS返回0,1,1,1，模块报告发送/接收能力。用户发送测试短信后，ModemManager及直接MBIM读取均为0条。接收尚未通过。
- 独占读取两AT口：CNMI=0,0,0,0,0，CPMS=ME且0条，CGSMS=1，CIREG查询ERROR。CNMI描述AT通知；不能直接推断MBIM事件订阅也关闭，尚未确认为根因。未改这些值。

## 已部署的官方工具与设置

Arch官方仓库：ModemManager、vnStat、GNOME Calls；未新增源。ModemManager和vnstat服务已启用自动启动。
NetworkManager连接“平板蜂窝网络”：auto-config=yes、home-only=yes、metered=yes、autoconnect=no；IPv4/IPv6路由metric=2000，Wi-Fi现有600。新建独立连接，没有覆盖Wi-Fi配置。
Omarchy当前原生网络面板主要为Wi-Fi，不能把新增蜂窝连接视为已完成触屏控制面板。

```sh
# 手动连接／断开数据，不移除SIM或设置
nmcli connection up '平板蜂窝网络'
nmcli connection down '平板蜂窝网络'
# 电话客户端（当前实测通话不通）
gnome-calls --plugins=mm
# 日／月累计，按本机蜂窝网卡单独统计
vnstat -i wwp0s20f0u2c2 -d
vnstat -i wwp0s20f0u2c2 -m
# 按需实时速率
vnstat -i wwp0s20f0u2c2 --live
```

vnStat只统计安装启用以来本机网卡用量；不能追溯此前SIM用量，也不等于运营商账单或套餐剩余。默认自然月，套餐结算日/额度未配置。默认每30秒采样、5分钟落盘；不是每次查询都立即变化。

## 下一步和恢复

先围绕已有硬件短信能力查证接收路由/运营商固件；自定义实验必须保留原值，避免串口与ModemManager争用。语音缺少厂商明确支持证据，不以新增界面替代协议、IMS和音频通路。
AT只读检查后已重启ModemManager，连接恢复命令一度返回未成功，但稍后现场NetworkManager显示connected；验收以最终现场与实际联网复核为准。
恢复新增配置：断开并删除“平板蜂窝网络”；如不再使用，停用本次新增的ModemManager/vnstat服务。统计数据库保留；卸载依赖前核对其他软件使用，不自动删除。

## 主要来源

- https://www.ntt.com/business/iot/product/m089.html （特定认证固件的数据/SMS及语音边界）
- https://modemmanager.org/docs/libmbim/mbim-protocol/ （MBIM Voice扩展名称不代表电话语音）
- https://github.com/GNOME/calls （官方ModemManager后端）
- https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html
- https://man.archlinux.org/man/vnstat.1

详细现场证据归本项目启明蜂窝网络会员；不保存SIM身份、号码、序列号或短信正文。
