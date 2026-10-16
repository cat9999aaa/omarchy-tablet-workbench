# Carrier IMS 参考与 DW5821e 适配边界

调研日期：2026-10-16。仅针对本机 Omarchy + Dell DW5821e / T77W968，中国电信 SIM。结论是可参考诊断与配置验证方法，尚无已验证的本机通话/短信修复。

## 上游项目实际做什么

- [NKU100/carrier-ims](https://github.com/NKU100/carrier-ims/blob/main/README.en.md)：Android LSPosed 模块，在 com.android.phone 读取 CarrierConfig 时合并覆盖项。依赖 Android 电话框架和 LSPosed，不能作为 Linux 调制解调器驱动直接运行。
- [CarrierOverrides.java](https://github.com/NKU100/carrier-ims/blob/main/app/src/main/java/io/github/nku100/carrierims/CarrierOverrides.java)：有 VoLTE 可用、Wi-Fi Calling、UT、跨 SIM、VoNR/NR 展示等项。所读文件没有中国电信专用 modem MBN/IMS APN/SIP 实现，也没有通用 Linux 短信栈。显示开关不是向 LTE 模块增加 5G 无线能力。
- [ryfineZ/carrier-ims-for-pixel](https://github.com/ryfineZ/carrier-ims-for-pixel)：面向 Pixel Tensor / Android 13+，通过 Shizuku 调整 CarrierConfig；参考其配置读回对照、注册状态、失败回退及脱敏诊断交互，不能据 README 声称本机已兼容。
- [AOSP IMS 架构](https://source.android.com/docs/core/connect/ims)：ImsService 是 Android 与厂商/运营商 IMS 实现之间的接口；语音与 SMS over IMS 需要实际 IMS 实现。框架配置与模块固件/运营商网络应分层检查。

## 本机证据

- 中国电信 home LTE、PS attached，绑定蜂窝网卡的 HTTPS/DNS/下载已通过；模块报告 UMTS/LTE，无 NR。
- 普通手机可通话；本机来去电失败。MBIM/MM 短信初始化成功但实发未收到。
- IMSA 正确绑定 subscription 0 后，注册状态成功返回 not-registered。此前未绑定查询的 InvalidOperation 不能证明硬件无 IMS。
- IMS Settings 同样绑定 0 成功，但读取 services-enabled-setting 返回 QMI error54 WmsCauseCode。未得到 enabled/disabled 值，不能推断 IMS/SMS 开关关闭。
- PDC 读取到12套软件配置，GCF active；未见明确标注中国电信的配置。缺运营商适配只是待证假设，没有切换配置。
- 仅把 point/class-none 短信路由临时改为 nv/store-and-notify，用户重发后独立 MBIM CLI 返回 No messages found；未修复。原六条路由已完整恢复并读回一致。
- 第一版采样器错误匹配 Message index，不能据其零计数判断未收到；独立原始 CLI 证据有效。已按 libmbim1.34 实际 Got N messages / PDU on index 格式修正并增加测试。
- fwupd 现已枚举模块；当前元数据 get-releases 返回空，不等于已证明最新。戴尔 RX8NT 是 Windows 驱动包，未验证存在本机中国电信 IMS 修复；没有刷写。

## 值得移植的方法

1. 分开显示数据连接、IMS 注册、语音服务、短信传输/存储、真实收发验收。
2. 读取实际消费者通道的有效配置，不把配置页面/图标/静态开关当作注册成功。
3. 每次只改一个有文档支持的选项，先保存原值，限时自动恢复，读回核对。
4. 先验证模块固件的语音能力和音频通道；短信优先调查 SMS over IMS 与其他 LTE 短信承载，不能仅凭 IMS 未注册断言所有短信必须失败。

下一步：优先从官方 libqmi/MM 与厂商文档确认 WMS transport/network-registration 查询及该固件的 IMS 支持；证据充分后才设计可逆配置实验。尚不移植 Android APK、不刷其他地区配置、不把拨号 UI 开发当作解决注册的前提。

## 用户转来的换模块建议核对

- 戴尔[7220通信规格](https://www.dell.com/support/manuals/en-in/latitude-12-7220-tablet/lat7220_ret_specs/communications?guid=guid-dfacccf4-6bf4-4db9-8d4a-9edcc8dd4cc6&lang=en-us)列出DW5821e和DW5930e，但不能把数据规格清单当成语音能力证明。
- 微雪[SIM7600G-H-M2 4G HAT](https://www.waveshare.com/wiki/SIM7600G-H-M2_4G_HAT)官方资料确有通话、短信和耳麦接口说明；[M.2模块资料](https://www.waveshare.com/wiki/SIM7600G-H-M.2)说明其Cat4、Linux支持。直接页面此次403，搜索索引提供正文；未取得最新完整硬件尺寸/引脚/厚度核对，不据此批准内置替换。
- [SIM7600G-H USB模块语音例程](https://www.waveshare.com/wiki/SIM7600G-H_4G_Module)说明可经USB Audio端口传二进制语音、由主机音频设备处理。因此“通话必须额外外置音频编解码器”不是所有SIM7600方案的通用结论；具体M.2版本/固件及主机接口仍需确认。
- 候选需确认：卖家实际SKU/固件、中国电信本SIM的IMS注册与LTE-only双向电话实测、USB语音数据路径、短信收发，以及7220卡槽供电/尺寸/散热/天线。M.2 B-Key和42mm只覆盖部分兼容条件。没有核验价格；不据用户转文中的美元价格建议购买。
- 已核对本机mmcli1.24.2提供messaging-status与voice-status，转文中的基础命令存在。但本机早已安装并实测，不需用户再次贴包含个人标识的整机输出。

新增现场结果见README：CNMI-only与SIM-store+CNMI两轮均未收到用户测试短信，设置完整恢复，绑定蜂窝HTTPS200。IMS测试模式两个只读查询均Disabled；CREG3与CEREG1并存。不能将“只要改CNMI就一定解决”作为本机结论。
