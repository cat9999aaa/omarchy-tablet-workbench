# C2导航0.1.3候选与恢复

当前是未安装的软件候选。匹配Hyprland的隔离动作验收、官方菜单交接、独立审查和真实解锁验收均是交付门槛；其中匹配图形环境目前不能启动，见[证据](../validation/2026-10-19-navigation-compositor.md)。不要因普通统一组通过而执行生产切换。

## 形成候选

在已验证的源提交上运行：

```sh
python3 modules/window-controls/candidate.py build /absolute/path/to/new-candidate
python3 modules/window-controls/candidate.py verify /absolute/path/to/new-candidate
```

输出bundle（供原plugin-release使用）、helpers/navigation.py与navigation_read.py、candidate.json摘要。UI包含NavigationSession.js和九份Workbench运行文件；测试、个人按键配置、凭据和用户数据不进入包。构建及verify都不会安装，不会启动桌面命令。摘要不是签名，候选仍需来自受信任来源。

## 完成门槛后的准备顺序

1. 核对候选摘要及审查结果；完成真实compositor、官方菜单取消/返回、中文输入交接的验证。确认Omarchy lock IPC精确返回false，保持原服务、输入法与应用。
2. 逐文件备份现有tools/window-controls/navigation.py、可能存在的navigation_read.py、插件manifest及按键偏好，记录缺失文件状态与哈希。备份不进入公开仓库。不能把候选helpers整体覆盖个人目录。
3. 先用既有plugin-release的navigation profile对bundle执行只读plan，记录当前插件身份/版本和候选差异。未通过任何门槛则只交付候选。
4. 解锁状态下先准备匹配helper，再通过既有发布器切UI。新helper拒绝旧UI不带context的窗口/桌面请求，因此中间过渡期间不操作旧面板；必须在可恢复的同一维护窗口完成。原key入口保持固定白名单。helper切换与UI不是原子事务。
5. 记录每个helper前后摘要、UI事务ID与运行state版本，核对ready、四页打开/关闭、9个桌面入口、按键偏好与原应用身份。版本探针不能代替真实功能。

## 逆序恢复

先用原UI事务rollback并确认0.1.2运行版本，再恢复helper；回滚不需解锁但仍须验证。helper只在当前内容仍匹配本次候选摘要时恢复，原来缺失的navigation_read.py也仅在匹配本次写入时撤回。任何并发编辑保持原样并记录conflict-preserved，不删除用户偏好、不覆盖整个目录，不把恢复命令退出成功写成恢复已验。

临时HOME下完整helper/UI升级与逆序恢复演练目前未完成；既有发布器的导航发布/恢复与并发冲突测试已在统一组中执行，但不能替代新增helper组合事务的证据。该项继续阻止正式安装。

## 体验验收

旧/新各10次同条件开页与切页，报告P50/P95、CPU/PSS和关闭后的进程数；真实手指、笔、中文输入、冷启动、睡眠分别记录。当前没有这些C2数据。保持C1生产版本，不宣称C2或整个DASHEN生态达到100%。
