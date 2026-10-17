# 远程输入法完整构建基线 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. Steps use checkboxes for tracking.

**Goal:** 在已授权构建区重复构建现有输入法，执行完整9项CTest，回传校验产物并在平板隔离检查ABI；不替换正在用的输入法。
**Architecture:** 固定白名单源码快照；远程官方签名包覆盖层 + 只读宿主/usr；Bubblewrap隔离HOME、总线、网络及进程；tmux独立任务。保持现有C++/Qt/Rime链路。
**Tech Stack:** Python3、OpenSSH、tmux、Bubblewrap、pacman只读解析、Arch签名包、CMake/Ninja、CTest。
**Spec:** ../specs/2026-10-17-tablet-system-architecture-design.md 阶段1。

## Global Constraints
- 写入仅远程项目专用目录；无全局包安装/升级，无用户词库或节点上传，不重启当前输入法。
- 首次2并发，禁-march=native；记录本机/远程ABI及完整依赖版本；远程不可用不退回平板重编译。
- 现有tools原型权威不迁移；便携副本只同步审核过的源码。
- 本轮继续用户已授权总方案的第一阶段，按“开始干”内联执行；不重复请求同一范围审批。

## Review Focus
- 源码软链接/构建产物/私人词库：拒绝或不入包，用白名单与边界测试验证。
- 签名错误/依赖下载失败：停止，不修改系统或继续编译。
- SSH断线：tmux任务继续；失败状态不可留下旧成功结果。
- CTest失败：不发布成功产物，不隐瞒断言失败；隔离D-Bus，不连接真实桌面。
- 回传损坏或ABI不符：校验失败拒绝使用，不替换现有库。

## Task 1: 源码与产物边界
**Files:** modules/remote-build/snapshot.py、test_snapshot.py。
**Interface:** create_snapshot(source, archive)保存白名单tar和逐文件sha256清单；verify_archive只接受正常相对文件，拒绝链接和路径穿越。
- [x] 写白名单排除私人缓存、拒绝符号链接/路径穿越、篡改校验用例；快照模块红绿验证，后续边界回归通过。
- [x] 生成唯一任务源码包及manifest，不上传build和运行数据。

## Task 2: 隔离远程构建
**Files:** modules/remote-build/build_ime.py、README.md。
**Interface:** python build_ime.py ROOT JOB_ID；ROOT已显式授权，JOB_ID严格字母数字连字符；仅jobs/JOB_ID与toolchain目录写入。
- [x] 官方pacman输出依赖清单，下载到专用cache，使用系统Arch keyring验签；只读overlay构建。
- [x] 独立HOME/runtime/dbus，关闭网络，清空继承环境，CMake/Ninja -j2，9项CTest全部通过后才产生artifact与result.json。
- [x] tmux断开后继续构建；测试日志和失败结果完整保存。

## Task 3: 回传、验证与归档
**Files:** docs/remote-build/使用说明.md、本地维护记录、GitHub模块及阶段路线。
- [x] 下载artifact，验证远程hash与tar成员；本机隔离运行测试不替换现有输入法。
- [x] 独立审查；修复重要问题并回归；记录真实范围，GitHub同步脱敏工具和文档。
- [x] 更新阶段1实际进度与下一阶段共享UI任务边界。

## Ledger
- Pre-flight: Task1 archive/manifest由Task2消费；Task2 artifact/result由Task3校验，同一sha256算法。
- Ruling: 使用现有宿主只读/usr加官方包覆盖层，先做到可审计的受控基线；不是完整干净chroot，不宣称构建已不依赖宿主。精确版本清单用于复核，后续可升级Arch完整chroot。
- Ruling: 管理源非Git，新增工具在tools独立目录；保留现有工作分支并审查同步便携仓库，不移动运行路径。

## 实际结果（2026-10-17）

- job ime-baseline-03：56源码文件，21官方包验签，2并发Debug构建，9/9CTest无跳过。缓存依赖就绪后本次任务约34.6秒，不含首轮下载和上传耗时。
- 本机回传hash/源码身份/ABI/JUnit核对通过；engine、bridge、backend、module_load四项隔离运行通过，没有安装/重启原输入法。
- 12项边界测试通过；独立审查提出的整个job可写、私人词库白名单、JUnit未验证三项Important已修，复审无Important/Critical。
- 01失败：Arch公钥为ASCII格式，已转换后验签；02失败：sandbox缺UID0记录，生成最小passwd/group后03的完整测试通过。未跳过失败测试。
- 新增client.py四步入口和check_local.py；每job保存runner，覆盖层新建，源码只读，控制/日志与sandbox写入隔离。
- 本轮验证现有C++/Qt/Rime完整构建；Rust、全新chroot、位级可复现、安装/恢复、冷启动和实体输入手感不属于已验范围。
- 下一阶段：共享UI与状态，先控制台再网络/电池；每次只切换一个运行模块。
