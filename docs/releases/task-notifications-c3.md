# 任务与通知候选 0.1.5

沿用 pcadmin.navigation overlay，新增匿名任务面板；没有新插件或常驻服务。运行时必须完整交付 candidate.py 的 UI 与 HELPERS 白名单。共享 Workbench 文件由既有同步器维护。

## 发布

1. 在授权远程隔离构建区运行完整验收、两套实际 Quickshell 生命周期和候选 build。回传后运行 candidate.py verify；不能用源码目录冒充候选。
2. 核对锁屏为 false、实际生产版本及当前文件摘要。支持从 0.1.3/0.1.4 升级，不假设 C2 候选已安装。记录 UI/helper 原字节、模式和原先不存在的文件，保留按键偏好。
3. 使用 task_config.prepare 只在 task-center.json 缺失时创建 schema=1/project_root；project_root 由调用者明确传入已授权项目的绝对路径。权限 0600，原配置保留，不根据 HOME 推断项目。保存 created/sha256 收据。
4. 原子替换 tools/window-controls 的候选 helper 和源码镜像，记录每个写后摘要。使用现有 ReleaseManager.apply 发布 bundle，沿用官方插件验证、rescan 和 IPC 版本探测，不重启服务。
5. 核对 pcadmin.navigation 与 pcadmin.tasks 版本 0.1.5；匿名实测打开、关闭、刷新和详情。通知历史必须用户明确点击，不作为自动验收副作用。

## 组合恢复

先收起两个面板，再调用原 ReleaseManager.rollback 恢复 UI，确认旧 IPC 版本。只有 UI 恢复成功，才恢复 helper/源码镜像：当前摘要必须仍等于本次写后摘要；恢复备份字节与模式，原先不存在则删除。最后 task_config.restore 恢复本次创建配置的“原先不存在”状态；已有配置从不回写。任一摘要冲突停止该步骤并保留用户新修改。此流程用于正常单用户安装事务，并非针对恶意并发文件替换的原子 CAS。

发布失败时先核对发布器是否已恢复旧 UI；未确认前不能撤走新 UI 可能需要的 helper。保留候选、事务收据和恢复记录。生产回退演练后再安装同一已核验候选。

## 状态与数据边界

列表只在打开或刷新时读取，详情点击才读取，单轮最多五个不同详情、累计五秒。单次来源命令最多两秒，响应 1 MiB。可见期间的 500ms 守卫只核对锁屏、输出和 CLOCK_BOOTTIME，不查询 Paseo；关闭后撤销自有读取。十五秒后显示“上次读取”。idle/closed 不表示完成，未读权限计数保持未知。

配置和原 CLI 响应不发布；界面及诊断 IPC 不暴露标题、路径、完整 ID、消息或权限内容。原始响应仅在 helper 内存中按项目范围投影。官方入口只交回 Paseo 或通知历史，不批准权限或发送消息。
