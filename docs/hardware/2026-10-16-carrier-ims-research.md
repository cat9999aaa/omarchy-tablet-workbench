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
