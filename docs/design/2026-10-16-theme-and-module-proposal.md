# EVA 氛围主题与模块组织提案

状态：设计提案；未安装、未切换系统主题。输入法v0.2为已部署的本机原型，实体笔书写正在诊断。

## 目的与范围

在本机 Omarchy 上获得 EVA 初号机氛围，同时保持中文可读、触屏好点、低后台负载。桌面和平板共用设计语言，布局按屏幕比例适配。用户要求字体、配色和图标协调；不把所有第三方应用内部界面强行覆盖为统一主题。

## 项目组织选择

建议继续使用 omarchy-tablet-workbench 一个仓库，各模块有独立版本、安装和回退流程。当前原型仍在本机管理项目的 tools 目录；迁移经过许可与隐私检查后才改变源码权威位置。

|拟定模块|责任|阶段|
|---|---|---|
|modules/ime|P1九键、英文、词库、离线语音、单字手写|本机v0.2已部署，实体笔待查，待提取源码|
|modules/workbench|扩展DeepSeek Harness原有界面、任务和模型管理|接口及真实会话待验|
|modules/hardware-toolbox|双电池、温度、输入设备诊断与传感器状态|复用本机已有工具后逐项验收|
|modules/shell-plugins|底栏、边缘手势、应用操作菜单等适配|部分本机原型已验，待模块化|
|themes/eva-inspired|Omarchy原生主题文件和横竖屏背景|设计提案|
|assets/icons|原创SVG图标、freedesktop图标主题与回退|设计提案|

另拆多个仓库会增加弱性能设备上的构建和版本协调成本；一个不可拆卸的大插件又会令主题与输入功能互相影响。建议单仓库、可单独装卸模块，主题不成为输入法工作的必要依赖。

## 视觉设计

- 深炭黑背景、暗紫面板、紫色主体、荧光绿选中态；橙红仅表示告警、危险动作或异常。
- 色值初稿：背景 #101117，面板 #1C1828，正文 #E9E6EF，主体紫 #9B6DDF，强调绿 #B8F05A，告警 #FF875C；最终对比度在实际界面验证。
- 工业仪表感来自细线、少量编号和清晰状态，常用操作仍使用中文。避免大段装饰文字和闪烁干扰输入。
- 中文以现有 Noto Sans CJK 为主，数字/终端沿用现有 JetBrains Mono Nerd Font。主题不自动更改系统全局字体；额外字体单独可选。
- 图标先覆盖工作台、输入法、语音、手写、电池、温度、网络、设备和常用入口。使用原创几何SVG，普通应用图标回退到已安装主题。
- 不承诺改写应用内嵌图标、网页图标、绝对路径图标或每个托盘图标，不改打包文件。
- 横屏保留右侧输入面板；竖屏减少工具列，保持候选和按键可触及，不单纯等比缩小。

## 官方集成边界

采用本机安装版本实际支持的 colors.toml、shell.toml 或 shell.<section>.toml、icons.theme 和 backgrounds。用户侧主题目录可覆盖，系统源目录只读。机器专属 shell.toml 的优先级需在预览中核对。

icons.theme 指向已经安装的图标主题名；原创图标包使用 index.theme 和 Inherits，保留 Yaru/hicolor 回退。主题安装器会读取仓库根并立即应用，因此不能把整个工具仓库直接交给 theme install。发布时应导出仅含主题的目录或专用发布产物。

先静态预览横屏、竖屏、输入法、双电池面板和告警状态；确认后创建独立用户主题，保存当前主题名和配置备份，按模块应用并测试回退。保留已经正常工作的锁屏、磁盘解密、P1/P2/P3和底栏位置。

## 硬件工具箱

- CPU/内存复用官方 system stats；温度读取现有 hwmon/sensors，双电池复用现有面板及sysfs/UPower。
- USB-C单独供电充电已实机确认；显示协商功率与电池净充电功率时明确区分，不能把45W合同值标成实时功耗。
- 触控笔先验证内核接触/压力事件，再验证桌面点击与手写；仅枚举设备不能作为验收。
- 方向/光线传感器先查实际IIO暴露与上游支持，再考虑Arch官方iio-sensor-proxy，不凭型号直接承诺自动旋转。
- 面板关闭时停止高频采样。缺失数据写“未提供”，不填零；不为主题自动启动录音、相机、定位或固件升级。

## 验收

预览与实际中文文本清晰；正常/告警状态可区分；横竖屏不裁切常用操作；底栏保持底部；输入法可P1开关；图标缺失时可回退；主题切换和卸载可恢复。主题性能以同机前后空闲占用、打开面板响应及温度测量，不用视觉印象代替测试。

## 官方参考

- https://github.com/omacom/omarchy/blob/quattro/docs/theming.md
- https://github.com/omacom/omarchy/blob/quattro/docs/omarchy-shell.md
- https://specifications.freedesktop.org/icon-theme/0.11/
- https://archlinux.org/packages/extra/x86_64/upower/
- https://archlinux.org/packages/extra/x86_64/lm_sensors/
- https://archlinux.org/packages/extra/x86_64/iio-sensor-proxy/
