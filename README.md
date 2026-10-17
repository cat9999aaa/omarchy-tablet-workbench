# Omarchy Tablet Workbench · Omarchy 触屏工作台

面向 Omarchy Linux 平板的开源中文管理与语音交互项目，首个验证设备为 Dell Latitude 7220。先把无实体键盘的日常操作做好，再扩展工作台、低延迟语音助理与硬件诊断。

## 目标体验

- 开机、解锁、中文输入、选择桌面和管理窗口，都能通过触屏或实体功能键完成。
- 工作台沿用 DeepSeek Harness 官方界面和插件机制，统一查看设备状态、任务、验证结果与恢复入口。
- 语音助理能够中文对话、显示识别文本、停止和打断；日常本机操作有清楚的执行反馈。
- 硬件能力按“已识别 / 软件检查通过 / 用户实际验收”分别标记。

## 当前阶段

本仓库已立项，尚未发布可安装的软件。原型来自一台 Omarchy 平板的本地实践；本仓库不会直接上传整台机器的配置、启动文件、日志或管理档案。

| 方向 | 本机已有基础 | 本仓库状态 |
| --- | --- | --- |
| 触屏输入 | 九宫格、全拼、内部候选、实体键呼出；离线中文听写 | [v0.2.3源码原型](modules/touch-ime-prototype/README.md)已同步；远程完整构建与平板隔离兼容已验，通用安装器待完成 |
| 桌面操作 | 固定底栏、实体键窗口菜单、上下边缘菜单 | 菜单动作通过；真实上下滑动尚待验收 |
| 解锁 | 锁屏触屏键盘、冷启动触屏解密已实测 | 设备与引导高度相关，暂不提供通用安装器 |
| 工作台 | DeepSeek Harness 本地服务已安装 | 真实模型会话、规则读取与插件尚待验收 |
| 语音助理 | 离线语音输入可用 | 实时对话、语音输出和打断待设计/实现 |
| 硬件工具盒 | 双电池详情；Dell原装无源笔手套模式实测通过 | [笔测试台](modules/hardware-toolbox/pen-test/README.md)与[触摸模式工具](modules/hardware-toolbox/touch-mode/README.md)已同步；实际重启/睡眠后保持待验 |

这些状态描述原型，不表示功能已移植到此仓库或适用于其他设备。

离线娱乐配置与中文字体修复见 [离线街机模块](modules/offline-arcade/README.md)，包含配置片段、恢复方式和实际验证范围。

## 开发原则

1. Omarchy 官方功能、配置和扩展优先；其次 Arch 官方机制/仓库，再考虑厂商上游，社区方案最后评估。
2. 不修改打包的 `/usr/share/omarchy`；通过用户配置和官方插件克隆扩展。
3. 前端适配横竖屏、手指操作和中文；正常动画遵循上游默认，性能调整应有测量依据。
4. 用 Superpowers 进行需求梳理、设计、计划、实现、评审和验证。仓库初始化不代表产品设计已审批。
5. 单机能力先做好；其他电脑的部署属于后续独立范围。
6. 编译、打包与批量软件测试优先使用授权的远程构建机；平板保留真实硬件验收。见[远程构建原则](docs/design/2026-10-17-remote-build-policy.md)。
7. 内核、驱动与电源优化纳入架构；先测量并复用官方方案，每次只改一个变量，保留可启动的原内核与恢复入口。

路线见 [ROADMAP](ROADMAP.md)，界面方向见 [设计简报](docs/design-brief.md)，贡献流程见 [CONTRIBUTING](CONTRIBUTING.md)。

现有模块的整合顺序、共享界面、语言选择与远程构建边界，统一见[平板增强系统总体方案](docs/superpowers/specs/2026-10-17-tablet-system-architecture-design.md)。该文档是整体设计；当前已验范围与未实现阶段分别列出。

## 开源许可

本项目原创代码与文档采用 [GNU GPL v3.0](LICENSE)（SPDX：GPL-3.0-only），可以依许可使用、修改和再分发。第三方代码、模型及派生部分保留各自许可与版权，详见[第三方声明](THIRD_PARTY_NOTICES.md)。

仓库公开的是源码、设计和脱敏验证资料。私人运行数据、账号、密钥、个人词库、代理节点和设备身份不属于发布内容。目前仍是开发中的原型集合，不能视为已经完成通用安装与整机兼容验证的发行版。

首个完整远程构建基线已通过：输入法9项CTest、12项构建边界测试、平板4项隔离兼容检查。见[构建入口](modules/remote-build/README.md)和[脱敏验证记录](docs/validation/2026-10-17-remote-ime-build.json)。没有用这批Debug产物替换运行输入法。共享UI首批已部署并通过远程回归与实机尺寸检查，见[验收记录](docs/validation/2026-10-17-shared-ui.md)。

统一的软件验收入口见 [验收工具](scripts/acceptance/README.md)，自动结果见 [GitHub Actions](https://github.com/cat9999aaa/omarchy-tablet-workbench/actions/workflows/acceptance.yml)。软件检查和真实设备验收分别记录。

输入法浏览器编辑与假密码框兼容问题已修复并部署，GTK/Qt/XWayland/Chromium实际矩阵见[跨应用验收](docs/validation/2026-10-17-ime-browser.md)。
