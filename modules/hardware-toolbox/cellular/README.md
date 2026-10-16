# DW5821e 短信网络注册只读诊断

原型来源：pcadmin tools/cellular；仅本机Dell DW5821e USB413c:81d7，Omarchy/Arch官方libqmi1.38、Python PyGObject。此模块不是通话或短信修复器。

`pkexec /usr/bin/python wms_registration_probe.py` 核对USB型号，通过MBIM proxy分配临时WMS客户端、读取短信传输网络注册、释放客户端。不改路由/固件/CarrierConfig，不读取号码或短信正文。

2026-10-16实际运行返回DeviceNotReady；不等于硬件永久不支持。尚无WMS subscription binding，因此上下文因素未排除。详见仓库docs/hardware/2026-10-16-cellular-capabilities.md。
