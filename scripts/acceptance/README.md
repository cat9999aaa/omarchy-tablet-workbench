# 统一软件验收

此入口检查仓库中的便携源码，不读取本机账号、节点、词库或硬件。使用 GitHub 托管运行器，或在已批准远程构建区的隔离环境运行；不要在正在使用的桌面会话中直接运行批量测试。

```sh
python3 scripts/acceptance/run.py --output /tmp/new-workbench-report
```

输出目录必须不存在，避免覆盖旧证据。`summary.json` 保存源码摘要、逐组结果、耗时和验收类型；每组有单独日志。任何一组失败、超时、缺工具都会返回失败；不会把跳过 Qt 当作成功。`--suite models` 和 `--suite qml` 用于定向复核，正式软件门禁运行默认 `all`。

覆盖网络、控制台、电池、远程构建边界、插件发布恢复边界、触摸模式、笔数据、离线目录、输入法控制、共享组件与几何模型。`Workbench` 的生成副本必须逐字节匹配共享权威源；缺少、过期或修改都会失败。

验收工具依赖：Python 3.11+（主题 TOML 校验使用标准库 tomllib）、Node.js、Qt 6 的 qmltestrunner 与 QtQuick/Controls/Layouts/QtTest 模块。现有产品 helper 的 Python 3.10 兼容底线不因此改变。测试权限门禁会在 `/run/user/<uid>` 创建临时请求，因此远程运行必须隔离 `/run`、`/tmp`、HOME、网络与真实桌面总线；GitHub 使用一次性托管机器。Linux 设备上的网络服务不在测试范围内。

C1 主题格式与失败检测、共享主题参数、对比度计算、生成副本同步器和网络/电池内容状态检查均为 `all` 的必需组。源码摘要包含 `themes/`，以及 `scripts/themes/` 的 Python/JS/QML 源码和 `scripts/workbench-ui/` 的 Python/Markdown；生成的 PNG、日志、结果 JSON 与 Python 缓存不进入这些工具目录的源码摘要。新增其他类型的测试输入时需要同步扩展摘要范围。

完整官方解析与 940 个实际内容截图案例另由 `scripts/themes/check_shell_theme.py` 和 `check_workbench_theme.py` 在授权隔离构建区执行，要求固定官方源码、Quickshell 和私有无头合成器。普通 CI 没有该环境，不能把基础 Qt 检查写成官方 Shell 或实机主题验收。

GitHub 的 push、pull request、手动运行使用相同入口。Action 固定提交，工作流令牌只读、不留 checkout 凭据；不连接私人构建机、不部署、不修改路由。Dependabot 每周提出 Action 更新 PR，需检查通过与审查后合入，不自动合并。依据 [GitHub 权限说明](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions) 和 [安全使用指南](https://docs.github.com/en/actions/reference/security/secure-use)。

Ubuntu 云端验收证明可移植逻辑/Qt 基础布局；目标 Arch 的完整输入法编译仍使用 [远程构建器](../../modules/remote-build/README.md)。它们都不代表真实触摸、网络断开恢复、开机解密、待机续航或其他型号硬件已验。完整输入法后端、语音识别与真实应用测试有独立流程，本入口不会向正在使用的应用输入文字。

维护归属：仓库 `scripts/acceptance/` 为权威源，属于工作台的发布与验收能力。新增测试组先确认其不会触及真实硬件或账号，再加入 `checks_for`；不要使用递归发现把真实输入测试混入软件门禁。
