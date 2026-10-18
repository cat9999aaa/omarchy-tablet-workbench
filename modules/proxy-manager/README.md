# Omarchy 原生代理工作台 v0.1

Qt/QML 七页界面，Rust 状态服务与配置事务；协议由已安装 Xray 26.10.10 和 sing-box 1.14.3 执行。首批适配本项目 Dell 7220 / Omarchy。关闭界面保留后台，手动关闭代理优先于网络恢复事件。未知状态不会显示为已连接。

## 入口与边界

- `omt-proxy` 打开工作台；网络面板、控制台开关统一调用 `omt-proxy.service` 的同用户 Unix socket。
- `omt-proxy-core.service` 是唯一 Xray 归属；现有 `pcadmin-v2ray-tun.service` 保持唯一 TUN 归属。
- 节点／分流：先生成候选，确认后校验、切换、发起新的显式代理及 TUN 请求；失败恢复。独立 systemd 计时器绑定事务代次与配置哈希。
- 更新页只生成提案。Omarchy → Arch 渠道优先，4G／飞行／未知出口延后检查，不自动下载核心覆盖包管理器。
- 首批 VLESS raw/Reality/vision、WS/TLS。未知字段拒绝，不能把迁移成功当成全部节点均可用。详见 `docs/compatibility.md`。
- 私人目录 `~/.local/state/omt-proxy` 0700，配置 0600。日志、UI、CI 不包含凭据和原始节点配置。

## 构建与安装

耗电工作在授权的远程构建目录内运行 `scripts/remote-build/proxy-build.py`；隔离签名 Arch 工具链、固定 Cargo.lock、离线构建。不得因为远程失败而自动在平板编译。

回传二进制并核对 SHA256 后，默认只读检查：

```sh
python modules/proxy-manager/packaging/bundle.py --source "$PWD" --binary /path/to/verified/omt-proxy --sha256 VERIFIED_SHA256
```

增加 `--apply` 发布用户文件、独立原件备份及事务编号。此步不接管网络、不创建 owner.json，也不启用服务。需要系统授权的 `packaging/install-root.py` 只安装两个固定 root helper，不改网络。

`integration/prepare_runtime.py` 从当前实际节点生成私有配置，执行旁路端口10818原生校验和新请求验证后准备状态目录；不会创建控制归属或改旧配置。运行配置必须先通过旁路端口 10818 测试；正式接管前需要解锁桌面、健康的原连接、独立评审。`integration/handover.py apply TOKEN` 中 TOKEN 是新的32位十六进制随机事务编号。先单独验证并接受兼容旧核心的 transport-only TUN 前端，再切换用户核心归属。原 GUI 停止；旧自启动单元通过 owner 条件与新核心互斥，保留发行版包与旧数据库。不能同时运行旧 GUI 控制与新核心。

## 恢复

- 每次启动首先由 once-per-boot recovery unit 恢复未完成配置；离线恢复只检查文件，不递归启动核心。迁移前建立两套互斥启动条件，用一个原子 owner 标记选择归属，断电中断时仍保留一个可启动入口。
- 每次节点应用的独立用户计时器在150秒后恢复未完成的匹配事务；过期计时器不会撤销另一代配置。
- TUN 前端转换有180秒 root 计时器，先用旧核心验证后才提交；保留 root 原件备份。
- 归属迁移有240秒用户计时器，失败恢复旧 GUI 单元与原启用状态；已经独立验证的 TUN 前端可以保留。手动关闭／飞行状态优先，不强行重新联网。
- `handover.py recover TOKEN` 仅恢复该未提交迁移。用户文件可用 `packaging/rollback.py INSTALL_TRANSACTION` 精确恢复，检测外部修改冲突；先处理运行归属，不能在新核心仍在运行时直接撤销文件。
- 保留原 v2rayN 包不等于保留第二个自动控制者。冷启动、用户手指与长期稳定需要单独验收。

GitHub workflow 使用固定 Action 提交、只读权限与脱敏 fixtures。上游版本扫描产生提案，不会自动合并或部署到本机。
