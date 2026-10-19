# 平板导航与按键配置

旋转键导航四页：开始、桌面、窗口、按键。复用Omarchy原生用户插件和共享触屏组件，不启用额外标题栏。当前源码为tools/window-controls，公共副本modules/window-controls。原应用窗口菜单保留为恢复入口。

默认P1输入法，P2同一面板语音，P3仅现有系统授权，旋转键导航；电源音量和长按行为不改。按键设置保存在用户配置omarchy-tablet-workbench/buttons.json，白名单动作，原子替换，错误配置退回固定默认。P3只能授权或停用，其他键不能执行授权。配置不包含密码或shell命令。

导航在打开前读取窗口地址与PID；操作前检查会话未锁屏且仍是该窗口，避免误关后来活动的应用。仅菜单显示时检查锁屏，关闭后没有轮询。布局固定外框、内部滚动；桌面内容来自实际窗口计数，不伪造截图。

软件与现场验收分别记录。安装需先验证overlay加载及IPC，再备份并替换用户四个短按绑定，执行官方配置检查；恢复只恢复四个绑定，不恢复整个桌面配置、不停网络、不恢复hyprbars。P2归并要求输入法提供omtInput.voice；未就绪前不得切换P2。

## 默认窗口操作与桌面直达（0.1.1）

旋转实体键默认直接打开“窗口”页：放大/还原、浮动/平铺、暂存、找回、居中、关闭，下方为桌面 1–9 直达。移动当前窗口到其他桌面保留在“桌面”页。现有自定义绑定保留；恢复默认时采用新默认。

远程布局检查覆盖 640×604 和 480×540：九个桌面按钮无需滚动，按钮至少 48 像素且合成点击分发正确。生产入口打开窗口页已读回；此次未代替实体按键验收。

## C2 候选的只读快照

`navigation_read.py` 为一次snapshot提供共享5秒墙钟预算；每次外部读取最多1秒，输出最多1MiB，超限/超时终止并回收读取进程，错误不包含原始子进程输出。准备前后检查实际锁屏、唯一聚焦输出和窗口address/PID。无活动窗口以target=null表示；失败给出reason_code及中文说明，不写回按键偏好。

这是候选读取接口；导航页面现已接入共享组件、会话代次与唯一输出绑定，关闭会取消读取并回收底层读取进程。动作提交的同边界输出保护仍待任务5，不能把此说明当作C2已安装或全部窗口操作已受保护。

## C3 task center (candidate)

The Start page gains a fixed task/notification entry. The same overlay package
hosts a separate panel, sharing Workbench components with navigation. It reads
local Paseo CLI metadata on open/refresh, filters the configured project and
projects anonymous status. Detail is explicit, limited to five rows and five
seconds cumulative query time per round. Idle/closed never mean task success.

The local task-center.json under the workbench XDG config directory contains
schema=1 and an existing absolute project_root. Missing/invalid config keeps
application links available without querying Paseo. No personal path is shipped.
Official notification history is replayed only on explicit click; approvals
remain in Paseo. No new daemon or automatic message/approval control is added.
