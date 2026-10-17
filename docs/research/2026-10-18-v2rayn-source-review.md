# v2rayN 源码研究与 Omarchy 重构建议

日期：2026-10-18。状态：第一轮源码研究与方案建议；不是已实现的原生客户端，不是运行版本故障根因诊断。现有网络未修改，自动更新未启用。

## 用户目标与本轮范围

以 v2rayN 为功能和源码参照，重构为 Omarchy 原生体验，统一平板控制台、网络面板和后台代理控制。延续已定 Qt/QML 共享 UI、新常驻 Rust 优先、官方代理核心、远程编译、系统渠道优先与可回退原则。用户特别要求研究核心与规则的 GitHub 自动化更新。

固定研究版本：2dust/v2rayN master `673283da4b8666c65c258a1949882ec41b6b5cad`，提交时间 2026-10-17T11:37:43Z。获取 21 份相关源码/工程/工作流文件并记录摘要，重点阅读下面的模块。这是当前开发源码，不等同本机已安装版本；没有重编译、复现崩溃或证明语言与历史崩溃的因果关系。

## 源码证据与迁移含义

| 源码 | 已核对事实 | 本项目意义 |
|---|---|---|
| [Desktop.csproj](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/v2rayN.Desktop/v2rayN.Desktop.csproj) | Linux 桌面使用 Avalonia、ReactiveUI，引用 ServiceLib | QML 原生界面不是更换皮肤；需明确业务接口 |
| [ServiceLib.csproj](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/ServiceLib.csproj) | 共享 C# 业务库仍依赖 ReactiveUI，含配置/数据库/下载等依赖 | 不能假设现有业务库可零改动成为纯后台服务 |
| [CoreManager](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Manager/CoreManager.cs) 与 [ProcessService](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Services/ProcessService.cs) | 主进程/前置进程分开管理，配置生成后停旧启新，子进程有输出与停止处理 | 用一个控制归属和 systemd 生命周期管理；不是看到多个不同角色进程就判重复 |
| [CoreConfigHandler](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Handler/CoreConfigHandler.cs) | 按核心类型分派不同配置生成器；自定义配置另走路径 | 保留核心适配器边界，用固定输入/预期输出做兼容测试 |
| [SubscriptionHandler](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Handler/SubscriptionHandler.cs) | 逐订阅校验、下载、处理与汇报；支持请求头等配置 | 建能力矩阵，迁移私有配置时不能丢字段或输出认证信息 |
| [SingboxRoutingService](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Services/CoreConfig/Singbox/SingboxRoutingService.cs) | 分流作为专门服务生成 | 分流/DNS/TUN整体校验，不仅做一个开关 |
| [Linux代理脚本](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Sample/proxy_set_linux_sh) | GNOME/KDE 设置；有 gsettings 回退，没有专门 Hyprland 分支 | 系统代理的设置状态不能代替应用联网结果；维持现有已验TUN优先路径 |
| [UpdateService](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/v2rayN/ServiceLib/Services/UpdateService.cs) | 有应用/核心检查下载、版本解析和Geo文件更新 | 四类更新分别管理，不直接照搬二进制覆盖到系统包目录 |
| [Linux工作流](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/.github/workflows/build-linux.yml) 与 [测试工作流](https://github.com/2dust/v2rayN/blob/673283da4b8666c65c258a1949882ec41b6b5cad/.github/workflows/test.yml) | 上游已有构建发布和共享业务测试 | 参考其职责划分；本项目已有软件验收CI，不等于已有核心更新CI |

## 三条可选路线

1. 保留 C#/Avalonia 做 Omarchy 风格皮肤：复用最多、迁移最快，但不能达到 QML 原生共享界面的目标。
2. QML 界面接过渡 C# 服务，逐模块迁移 Rust：短期保留业务实现，但要承受桥接、双运行时和后续删除过渡层的成本。
3. **推荐：以源码和兼容样例为参照，按模块重构 QML + Rust 管理层，继续运行上游 Xray/sing-box。** 不承诺首版全量兼容；先做目前本机必需的单实例、TUN、分流、节点和订阅。

第3条是语言迁移与架构重构，不能称为低成本换皮肤。先形成当前版本的行为基线与功能对照表，成熟算法和必要片段按原许可复用、标明来源。无需为分析立即建立另一个仓库；原生代理仍归现有工作台网络模块。

## 技术栈与边界

| 技术 | 用途与取舍 |
|---|---|
| Qt/QML、Quickshell | Omarchy主题、触屏组件、固定框架与状态，复用现有面板 |
| Rust | 新增控制服务、配置模型、订阅校验、状态机、更新事务；UI只发命令 |
| Go | 上游Xray-core与sing-box已有核心；首阶段跟随稳定发行版，不重写协议 |
| C/C++ | 仅必要Qt/系统桥接和已验代码，不增加第二套通用控制层 |
| bpftrace/perf | 按需观察CPU热点/唤醒/阻塞，不作为持续常驻功能 |
| Zig/汇编 | 测量发现适合的热点后再评估；不预设语言更换可加速网络 |
| Lua | 仅用于明确的Omarchy/Hyprland扩展点 |
| Elixir等其他运行时 | 本单机模块当前没有需要它的独立职责，暂不引入 |

数据通路直接交给核心；Rust管理层不逐包转发。事件驱动展示状态，隐藏面板停非必要图表刷新；订阅解析与规则候选缓存，测速按需/限并发。要比较空闲CPU、PSS、唤醒、切换时间、吞吐与实际耗电；没有测量不宣称重写后必然省电或解决闪退。

## 更新自动化建议

1. GitHub定期或手动检查官方稳定发行版；[Actions事件文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)。日程只是版本发现，不保证准点。
2. 更新版本清单并形成PR，记录来源、版本、摘要和可用签名；checksum本身不是独立来源认证。
3. 云端验证配置生成、分流/DNS、核心版本兼容、单TUN、损坏更新与恢复；使用模拟节点，不上传私人订阅。外部PR不在私人构建机执行。
4. GitHub或授权Arch远程构建机产生候选与结果；Omarchy/Arch已提供的核心优先通过原渠道更新，不能定时覆盖pacman管理的文件。确需自有测试包时明确包归属与版本冲突。
5. 本机下载/预检通过后，在可恢复窗口激活。备份配置与兼容版本，检查直连、代理、DNS和ZeroTier旁路，失败恢复上一已验组合。不能保证已有TCP连接在核心重启后不断线。
6. 订阅、本项目程序、代理核心、分流数据四种更新各有状态。规则更新不必更换核心；应用更新不强制刷新私人订阅。飞行模式暂停网络更新，电池/流量环境延后大下载。

## 建议实施顺序与验收

- 阶段A：补齐当前安装版与研究版差异、节点/订阅/规则能力矩阵和可重复基线；记录本机支持的协议，不收集私人节点到公共仓库。
- 阶段B：一个Rust控制服务管理候选核心，QML总览显示物理网络/代理/分流/TUN；先隔离运行，只有一个生产控制者。关闭UI不终止代理。
- 阶段C：节点、订阅、分流页面，旧配置只读迁移预览与核对，遇不支持字段明确阻止迁移。
- 阶段D：核心/规则更新流水线、旧版恢复、远程Arch兼容与本机4G/Wi-Fi实际测试。
- 阶段E：完成可安装包、上下游边界与复现证据后，再准备Omarchy上游贡献。

界面建议：固定总览显示“当前网络／代理状态／分流模式／TUN／诊断”，内容页分节点、订阅、分流、更新，使用同一尺寸和中文状态语言。代理开关与窗口关闭分开；用户手动关闭后不自动复活。ZeroTier继续独立旁路。

本轮完成源码研究和技术建议；原生代理、核心自动更新、实机迁移都未实施。下一步需将选定路线细化为书面实现计划，再进入产品代码与隔离验收。
