# 工作台插件版本发布与恢复

用于已经安装的 Omarchy 用户插件：触屏输入法、网络中心、电池面板、控制台和平板导航。低频运行，无常驻服务。首次安装仍走 Omarchy 官方流程。

导航使用 `--plugin-id pcadmin.navigation --profile navigation`，通过现有 `pcadmin.navigation state` IPC 的 JSON `version` 字段核对运行版本；仅接受该固定插件 ID。测试中的发布和恢复不代表导航已在真实桌面升级或回退。

提供 `pack`、只读 `plan`、`apply` 和 `rollback`。候选包由 `manifest.json`、`files.json` 与 `files/` 组成，入口在 files 内相对定位；来源需可信。摘要用于检查完整性，不是签名，也不把插件代码变成安全沙箱。不打包或替换常驻后端；控制台版本目录可携带其生命周期内使用的只读设备观察程序，不迁移私人数据库，不升级系统服务、启动镜像或代理核心。

```sh
python3 release.py pack --manifest candidate/manifest.json --payload candidate/files --output new-bundle
python3 release.py plan --plugin-id pcadmin.touchime --profile ime --bundle new-bundle
python3 release.py apply --plugin-id pcadmin.touchime --profile ime --bundle new-bundle
python3 release.py rollback --plugin-id pcadmin.touchime --profile ime --transaction TRANSACTION_ID
```

`plan` 不写文件、不调用桌面控制命令。输出 `would_change: false` 只表示版本相同，不能用作任意内容一致的证明；`apply` 拒绝覆盖同版本。输出包应在源目录与插件监视目录之外。

发布先对原 manifest 的同一份字节取得身份、版本和备份摘要；在监视目录外准备完整候选，官方 `omarchy plugin validate` 通过后，移入独立版本目录，再原子切换 manifest 并调用官方 `rescanPlugins`。探针确认版本后还会复核 manifest。输入法还要求 ready。插件须已启用并能通过旧版本探针。

事务位于 `~/.local/state/omarchy-tablet-workbench/plugin-releases/`，每个插件独立加锁。等待前后发现并发修改会拒绝覆盖；该锁协调本工具的发布，不锁住所有外部编辑器，文件检查也不是文件系统级比较交换。操作期间不要同时手动编辑同一插件。

失败时，只有当前 manifest 仍是本次写入的内容，工具才自动恢复并核对旧版本。显式恢复同样校验备份和当前摘要。恢复保留所有版本文件，既不删除插件，也不清理个人数据。`applied` 和 `rolled-back` 均要求运行探针及最后文件核对通过；`rollback-unverified`、`conflict-preserved` 不是成功。进程/主机意外中断后保留事务证据，下一次人工恢复使用原事务 ID；无自动开机恢复服务。

官方命令使用固定参数，包不能指定执行命令；符号链接、越界路径、重复 JSON 键、清单缺失/多余/篡改文件被拒绝。只读探针不能证明完整业务体验，发布后仍需对应模块验收。

测试使用临时目录和注入命令执行器，覆盖发布、恢复、内容校验、初始等待/准备/发布后/恢复后的并发修改、恢复失败和并行发布锁。批量测试在授权远程隔离环境或 GitHub CI 运行。真实桌面已验证网络面板1.3.7→1.3.8→恢复1.3.7→再次1.3.8；各次运行版本与manifest读回一致，旧版本保留。其他插件、后端和系统服务不因这次UI验证自动算作通过。

本项目 `tools/plugin-release` 是本机权威源，公开仓库 `modules/plugin-release` 为便携同步副本。Python 3.10+，Linux。源码遵循项目 GPL-3.0-only。

C1 多插件交付按控制台、导航、网络、电池、官方主题的顺序逐项执行。每项保留事务 ID；任一步失败立即停止后续发布，按反序恢复本批已成功的插件。恢复出现并发修改则保留冲突，继续核对其他独立事务，不宣称整批原子回退。主题恢复另走原官方主题入口，先核对本批写入后的摘要；个人主题选择、shell 配置和背景不能整份无条件覆盖。

`test_batch_recovery.py` 在临时目录使用真实单插件发布器和注入命令演练第三插件失败、主题步骤失败、manifest 并发编辑与主题并发编辑。主题文件是合成标记，测试不执行生产主题钩子，也不代表提供了自动批量发布或崩溃恢复工具。正式应用前仍需审阅官方后置命令、用户钩子，并完成备份和只读计划。
