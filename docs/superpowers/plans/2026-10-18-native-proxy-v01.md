# 原生代理管理 v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 推荐本会话顺序实施，最后独立评审；本计划尚待用户审阅。

**Goal:** 将已确认的七页代理界面落实为原生管理软件，具备统一实际状态、单一控制归属、候选配置与恢复，满足后述验收后才替换旧入口。

**Architecture:** Qt/QML 展示，Rust 用户服务拥有状态、命令协调和候选事务。过渡阶段复用当前网络控制入口及权限门禁，后续由能力矩阵逐项迁移 Xray/sing-box 生命周期；任何时刻仅一个控制归属、一个 TUN 拥有者。所有首次切换在隔离测试通过后进行。

**Tech Stack:** Rust、Qt6/QML、Quickshell 适配、systemd、既有 Python 权限桥、上游 Xray/sing-box、GitHub Actions、Arch 签名包；远程构建。

**Spec:** [确认的界面规格](../specs/2026-10-18-proxy-ui-design.md)、[代理总架构](../specs/2026-10-17-native-proxy-design.md)。用户于2026-10-18确认规格并要求今晚完成；此计划把完整目标拆成可验证阶段，不将时间要求当作降低验收标准的授权。

## Global Constraints

- “生产前端 Qt/QML，常驻管理层 Rust 优先，代理协议继续复用 Xray/sing-box 上游核心。”
- “触屏主按钮至少 48 个逻辑像素高，文字不依赖悬停；错误使用文字和颜色共同表达。”
- “完整管理和三指控制台快捷入口共用一份状态源。”
- “手动关闭优先于自动恢复。飞行模式暂停恢复和在线检测；熄屏本身不改变联网意图。”
- “不得自动覆盖包管理器文件，不将私人节点、订阅或凭据送入公共 CI。”
- Omarchy→Arch→官方上游；不修改 `/usr/share/omarchy`；新界面不得直接启动第二个核心或TUN。
- 编译、打包、批量测试只在已授权远程目录；本机仅编辑、轻量检查、安装与实机验收。远程失败不改为平板编译。
- 新模块权威源码为本仓库 `modules/proxy-manager/`。现有网络与控制台迁移前仍以管理项目 tools 对应目录为权威，受控修改后仅同步明确的公开源文件。
- 逐阶段交付，软件/部署/硬件实测分别标记。未通过验收的能力禁用并说明原因，不能用演示数据填充生产界面。

## Review Focus

1. 睡眠/断网/时钟异常后的旧健康缓存：超过45秒、未来时间或无时间戳均不能显示联网正常（任务1）。
2. 多个入口连点、授权超时或过程中锁屏：只执行一个操作、撤销未完成权限请求、旧配置仍可恢复（任务2）。
3. 订阅恶意或超大输入、未知协议字段：限制长度，禁止shell解释，不静默丢失字段或删除当前节点（任务4）。
4. 应用后程序崩溃、磁盘满、恢复也失败：持久事务日志识别阶段，明确报告失败，不能虚报恢复成功（任务5）。
5. 移动设备流量、计费和飞行状态：无后台全节点测速，不在飞行模式更新，不因网络恢复撤销手动关闭（任务6）。

## 已核对的基础与文件职责

2026-10-18只读核对：当前 `network.py` 的 `ensure_proxy()` 经文件锁协调 GUI、本地端口及托管 TUN；控制台 `prepare/execute` 提供锁屏门禁、请求令牌和网络资源锁；`cell_proxy_watch.py` 响应NetworkManager事件。不能在新服务中重复实现另一套互不相干的恢复循环。

本机已安装核心输出为 Xray 26.10.10、sing-box 1.14.3。此为现场基线，不是承诺支持所有版本。v2rayN SQLite 含 ProfileItem/SubItem/RoutingItem 表；只读取已核对字段，原始认证数据不进入日志或公开证据。远程已有 GCC/Qt6/tmux，Rust未安装；先用Arch签名包在专用目录构造工具覆盖层。

只读基线发现旧自启动unit为failed，但实际GUI/Xray/TUN各有一份。因此必须同时核对PID、可执行文件、cgroup和端口拥有者，不能仅按unit失败启动新进程。未受本模块管理的运行实例先显示“控制归属待确认”，禁止接管式开关；在任务7明确迁移并完成恢复准备后再改变归属。

新增文件分工：

| 路径 | 责任 |
| --- | --- |
| `modules/proxy-manager/Cargo.toml`, `Cargo.lock` | Rust二进制与固定依赖 |
| `src/model.rs`, `state.rs`, `redact.rs` | 公开状态、状态合并、敏感字段过滤 |
| `src/legacy.rs`, `command.rs`, `ipc.rs`, `main.rs` | 现有控制适配、串行命令、本地IPC、服务入口 |
| `src/catalog.rs`, `subscription.rs`, `routing.rs` | 节点/订阅模型、受限导入、分流草稿 |
| `src/core.rs`, `transaction.rs`, `update.rs` | 核心校验、候选激活/恢复、更新提案 |
| `ui/Main.qml`, `ui/ProxyModel.qml`, `ui/pages/*.qml` | 七页原生界面与共享数据绑定 |
| `integration/`, `packaging/`, `tests/` | 现有入口适配、用户服务/安装恢复、测试夹具 |
| `scripts/remote-build/`, `.github/workflows/proxy-*.yml` | 受限远程任务、代理专项测试与版本提案 |

## Task 1：远程工具链与真实只读状态

**Files:** 新建 `scripts/remote-build/proxy-build.py`、`modules/proxy-manager/{Cargo.toml,Cargo.lock,src/model.rs,src/state.rs,src/legacy.rs,src/redact.rs,src/main.rs,tests/state.rs}`。

**Interfaces:** `Snapshot` 包含 `schema=1, revision:u64, observed_at:u64, physical:Field<String>, proxy:Field<bool>, tun:Field<bool>, health:Field<String>, user_enabled:Option<bool>, flight:Option<bool>, capabilities:Vec<String>`；`Field<T>`包含value、observed_at、health枚举 observed/stale/unknown/unavailable。`normalize(raw:Value, now:u64)->Snapshot`；`snapshot` CLI 输出单个脱敏JSON，不执行控制动作。

- [ ] 写 `stale_never_connected`、`future_timestamp_unknown`、`missing_fields_unknown`、`secret_fields_not_serialized`：缓存年龄46秒不正常，45秒可用；未来时间未知；输入含Password/Url/Address时公开输出不含其值。
- [ ] 远程从现有Arch仓库获取Rust及依赖包，核对签名，解到专用工具层；设置项目内 CARGO_HOME/目标目录；测试 RED（缺实现）。不新增系统源、不全局安装Rust。
- [ ] 实现上述模型与只读适配；复用 `network.py status`，只选取允许字段，12秒超时；状态读取失败降级，不擅自操作网络。远程编译与测试必须记录工具版本、包签名和源码SHA。
- [ ] `cargo test --locked --test state` 全部通过；`cargo build --locked --release -j2` 成功；回传核对SHA，平板运行 `snapshot` 与既有缓存做轻量比对，不输出凭据。
- [ ] 提交 `feat: add native proxy state model and remote build`。

## Task 2：单一控制接口与事件服务

**Files:** 新建 `src/{command,ipc}.rs`、`tests/command.rs`、`integration/legacy-control.py`、`packaging/omt-proxy.service`；修改 `src/main.rs`。现有控制台/网络入口只有在任务7部署时才切换。

**Interfaces:** 本地Unix socket位于用户runtime目录，0600，核对同UID；请求 `Command{id, expected_revision, action, confirmed}`，action初期仅 Status/Enable/Disable；响应 `Outcome{id,stage,verified,error_code,revision}`。`dispatch(command,state)->Outcome`。阶段 accepted/awaiting_auth/applying/verified/failed/cancelled/busy/conflict；命令已提交不等于已验证。

- [ ] 写测试：同ID重试不重复执行；并发操作busy；旧revision拒绝；锁屏或锁屏未知拒绝；127/126授权取消；超时撤销；用户关闭后网络恢复不启用；帧超过64KiB拒绝；unit失败但外部GUI/端口仍存活时返回ownership_conflict且不启动或停止进程。
- [ ] 远程运行 `cargo test --locked --test command`，确认针对缺功能失败。
- [ ] 实现服务独占锁、幂等最近请求记录、有界串行命令队列；过渡控制只调用既有控制台 `action` JSON入口，不绕过其令牌与锁屏检查。订阅现有健康文件变化和NetworkManager状态；无客户端不额外测速；周期仅作低频事件丢失兜底。
- [ ] 远程测试通过；两隔离客户端并发操作只触发一次测试桩；服务退出重启读回真实状态；新UI崩溃不停止代理。
- [ ] 提交 `feat: serialize proxy control through one local service`。

## Task 3：七页QML界面和共享快捷入口

**Files:** 新建 `ui/{Main,ProxyModel}.qml`、`ui/pages/{Overview,Nodes,Subscriptions,Routing,Updates,Diagnostics,Settings}.qml`、`tests/qml/tst_proxy.qml`、`integration/QuickControls.qml`。

**Interfaces:** ProxyModel提供 `snapshot, pending, draft, lastError` 以及 `submit(action,confirmed)`、`refresh()`；界面只消费任务2响应。首版未有后端能力时对应操作禁用，明确“尚未接入”，不显示模拟成功。

- [ ] 写QML测试：七页外框尺寸相同；状态未知不显示绿色；主按钮高度≥48；收起不调用Disable；草稿切页提醒；busy不能重复提交；640×604、1280×800、800×1280内容不越界。
- [ ] 远程QML测试先失败；依据项目共享Workbench组件和Omarchy主题桥实现界面，状态常驻，内容内部滚动；快捷入口复用ProxyModel，不另造控制状态。
- [ ] 远程Qt Test通过并回传截图；平板仅预览真实只读状态，确认日志无绑定错误、七页可切、横竖屏不挡操作。
- [ ] 提交 `feat: implement native touch proxy management UI`。

## Task 4：节点、订阅与分流草稿

**Files:** 新建 `src/{catalog,subscription,routing}.rs`、`tests/catalog.rs`、`tests/routing.rs`、`docs/compatibility.md`；连接任务3页面。

**Interfaces:** `import_preview(bytes:&[u8], format:ImportFormat)->Result<ImportPreview>`；`Catalog`使用内部ID，UI仅见名称/组/能力状态；秘密在0600本地库。`validate_draft(draft:&RoutingDraft, capabilities:&Capabilities)->Result<Candidate>`；模式 Rules/Global/Direct，传输旁路独立不可由普通订阅覆盖。

- [ ] 写测试：8MiB输入上限、未知协议/字段明确失败、HTML不是节点、空列表不覆盖、当前节点消失需确认、认证值不入错误；模式改动不影响运行版本、局域网/ZeroTier保护不消失。
- [ ] 远程测试RED后实现只读 v2rayN迁移预览。首批协议以当前节点实际所需能力为准，未知/未测试类型留原客户端；兼容矩阵逐项列已验/未验/不支持，绝不默默降级TLS认证。
- [ ] 实现标准URI列表及受限base64订阅解析，订阅URL仅本地保存；HTTPS下载具超时、长度上限与重定向策略，不执行订阅提供的命令。更新先展示新增/修改/删除，再提交目录，不自动启用代理。
- [ ] `cargo test --locked --test catalog --test routing`通过；只用脱敏夹具进CI；本机迁移仅预览，不更改旧库。
- [ ] 提交 `feat: add validated proxy catalog and routing drafts`。

## Task 5：核心适配与候选配置事务

**Files:** 新建 `src/{core,transaction}.rs`、`tests/transaction.rs`、`tests/core_matrix.rs`、`integration/owned-core.py`、`packaging/omt-proxy-core.service`；更新能力矩阵。

**Interfaces:** `CoreAdapter::check(candidate)->CheckResult`、`activate(candidate)->Activation`、`probe(activation)->Health`、`restore(previous)->RestoreResult`；`Transaction`持久记录 prepared/validated/activating/committed/restoring/failed，含配置代次和文件hash，不含秘密内容。

- [ ] 写故障注入：无效配置不碰运行态；核心启动失败恢复；激活后崩溃重启恢复；磁盘满/部分写入/恢复失败准确报错；恢复失败不标verified；冲突代次拒绝。
- [ ] 远程隔离测试RED；实现已安装版本的原生配置校验、候选目录原子写入、上一可用快照、只撤销自己拥有的网络资源。核心支持矩阵决定由sing-box单核心或Xray+sing-box前端运行，不同时维护两个TUN。
- [ ] 在隔离网络命名空间测试直连/代理/DNS/IPv6/局域网/ZeroTier外层旁路，固定本地测试目标；证明退出不遗留自建规则。旧GUI与watcher的接管/恢复顺序在迁移脚本中显式处理。
- [ ] 远程 `cargo test --locked --test transaction --test core_matrix`及隔离网络脚本通过；本机先以旁路候选端口验证，不占10808、不设默认路由。只有候选全部通过才安排一次受监控切换，带独立超时恢复。
- [ ] 提交 `feat: add recoverable core configuration transactions`。

## Task 6：更新、诊断与GitHub自动化

**Files:** 新建 `src/update.rs`、`tests/update.rs`、`.github/workflows/proxy-check.yml`、`.github/workflows/proxy-upstream.yml`、`scripts/proxy-upstream.py`；连接更新/诊断页面。

**Interfaces:** `UpdateProposal{kind,source,version,digest,verification,compatibility}`，kind为application/core/rules/subscription；`plan_update(proposal,network_policy)->Decision`只给候选，不隐式安装。诊断固定枚举阶段与脱敏原因，报告无完整域名访问历史。

- [ ] 写测试：飞行暂停、4G计费延后、手动关闭保持、旧缓存不可作成功证据、来源/摘要错误拒绝、无签名不伪称来源认证、上游预发布不自动进入稳定通道。
- [ ] 远程测试RED后实现更新提案及诊断；核心遵守发行版包渠道，更新失败保留可用组合；规则更新要走任务5事务；后台不持续测速。
- [ ] GitHub工作流固定Action提交、默认只读权限，定时发现稳定版本形成审查提案；发布最小写权限独立job；外部PR不访问私人构建机/秘密。任务不自动合并或在平板安装。
- [ ] `cargo test --locked --test update`、脚本离线fixtures测试与workflow校验通过；记录一次实际CI结果，未跑则不称CI通过。
- [ ] 提交 `ci: validate proxy compatibility and propose upstream updates`。

## Task 7：发布、入口迁移和恢复验收

**Files:** 新建 `packaging/{PKGBUILD,install.py,rollback.py}`、`tests/install_test.py`、`README.md`；修改现有网络/控制台适配（仅相关公开文件）；新增 `docs/validation/2026-10-18-native-proxy-v01.md`。

**Interfaces:** 安装器输出版本/hash/原入口备份/恢复入口；默认 `--check` 只读；`--apply`仅使用通过验证的产物。恢复明确还原旧控制归属，禁止新旧watcher同时控制核心。

- [ ] 写测试：重复安装幂等、备份不覆盖、软链接路径拒绝、权限失败回退、旧服务恢复、新入口状态一致；在临时根与模拟服务中运行RED。
- [ ] 实现安装与恢复，复用现有版本发布器；生产入口通过Omarchy用户插件接入。部署前记录当前单实例、物理网络与最近健康样本，保留旧入口。
- [ ] 远程全部软件测试与独立代码评审通过后，平板部署候选。先界面与只读验收，再做经门禁的控制；不为测试主动关4G、开飞行或重启。涉及连接切换要有独立恢复监控。
- [ ] 分别验证新浏览器请求、显式本地代理、TUN和ZeroTier旁路/可达性；测试期间连接不可用即恢复。旧连接存活不等于新流量可用；未能实测的项目保留未验状态。
- [ ] 公共仓库提交脱敏源码与结果；启明归网络中心及本任务，新可独立维护组件再登记子会员；不得公开私人节点数据库。软件、部署、手指验收各记一栏。

## 交付门槛与执行安排

推荐本会话顺序实施，各任务共享状态/事务接口，不适合同时各写一套；最终由独立审阅者检查整个变更。编译和回归交远程机，平板保留实机验证。

阶段A（任务1–3）交付原生真实状态和统一控制基础；阶段B（任务4–5）交付节点/分流事务；阶段C（任务6–7）交付更新提案、正式入口与验收。三阶段都完成并通过实际检查才能称本次原生代理v0.1完成，不能把阶段A冒充整体完成。冷启动、长期稳定和真实触摸若尚未测试，继续明确列出。

本计划自检：七页、状态、权限、单实例、节点/分流、更新/恢复、GitHub、隐私、远程构建均有对应任务；高级协议完整兼容不作未经实测的承诺。若现场能力矩阵显示某项无法按已确认架构实现，记录具体证据和替代方案，不暗中换栈或覆盖当前可用网络。
