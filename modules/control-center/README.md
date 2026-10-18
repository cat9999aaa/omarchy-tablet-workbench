# 启明 · 随身控制台 0.1.9

面向本机 Omarchy 平板的用户插件。沿用官方 bar-widget 注册方式，不修改打包文件，不添加 Hyprland 二进制插件。

## 使用

- 三根手指同时触屏，向下滑动约屏高8%以上，然后全部松开：打开控制台；已打开时再次下滑进入详情。
- 底栏“控制台”图标、原顶部边缘下拉也可唤起。点右上角收起、外侧或 Esc 关闭。
- 九个快捷磁贴、亮度和音量；详情分连接／设备／工作／旅途。亮度和音量在松手后提交，不逐像素启动进程。
- 关闭代理、飞行模式、切到普通触摸先确认。普通触摸仅本次生效，原装无源笔可能失效；开机和重连仍恢复手套模式。
- 快捷区原显示方向占位改为可用的夜间模式；显示方向仍未适配。AI任务和场景编排未接入，不提供假按钮。电池详情接现有充放电记录工具。

## 状态与权限

网络复用 network-center 的状态缓存；不新增外网测速循环，不更换代理核心或节点。物理出口、核心、TUN和网络健康分别显示。CPU温度来自具名thermal源，未知不补0。电池使用UPower实体设备，缺失估算仍在原电池详情中显示未知。

音频显示使用PipeWire及PwObjectTracker，修改通过白名单调度器调用pactl，目标由Omarchy官方 `audio output sink` 解析，避免误调DSP入口。亮度调用官方monitor IPC，当前内屏实际亮度读sysfs actual_brightness。命令exit0仅反馈请求已提交，绝不将异步IPC提交伪装成硬件验证完成。音量/静音共用audio-output锁，省电/均衡共用power-profile锁。

沿用已有Polkit授权，密码不进入控制台。用户进程在授权等待期间监测锁屏并取消请求；root拥有的privileged_control.py在授权后核对PKEXEC_UID对应的会话，固定调用既有控制器。触摸写入与飞行修改前再执行guard。network-center仅在控制台设置的PCADMIN_NETWORK_GUARDED=1时使用这一受控TUN入口，原网络面板保持原行为。

锁屏须明确false才能打开，动作执行前再核对；锁屏或查询失败关闭面板。打开前隐藏原生与旧键盘并检查layer消失；失败不强行叠加。面板关闭停止自身5秒状态刷新和500毫秒锁屏检查。后台手势只观察核对过名称和USB厂商/产品的触摸屏，读取ABS多点事件，永不grab、不创建虚拟输入、不读取键盘。坐标只保留在当前手势内，不写日志。仅固定gesture token通过本机Unix socket送给用户会话，接收器核对内核提供的root身份。

全屏触屏上的手势由观察器识别，应用也可能看到同一次三指移动；此版不承诺消费掉应用的触摸。原始坐标方向按本机默认屏幕方向适配，旋转后的三指方向尚未验证。

## 部署与恢复

权威源码是本机管理项目tools/control-center；便携源码在工作台modules/control-center。只保留一份TouchMode工具：modules/hardware-toolbox/touch-mode。便携副本需设置 `PCADMIN_CONTROL_HELPER` 到部署的适配器；network-center、IME及窗口菜单路径需按目标实例核对，不能沿用其他项目的启明身份。本模块没有跨设备通用安装器。

用户插件 `pcadmin.control-center` 的安装时使用版本化 entry，版本为 `0.1.9`，IPC `pcadmin.controlCenter` 提供ready/open/close/toggle/gesture/expand/state；不接受任意命令。官方plugin enable负责底栏注册，保留底栏原位置和P1/P2/P3/旋转键分工。

root安装只读触摸状态导出timer，以及只观察触屏的pcadmin-three-finger.service；后者recipient UID必须在安装时替换，不可复制本机UID到其他设备。用户服务pcadmin-control-gesture负责会话入口。既有TouchMode开机服务和udev默认不变。

恢复时先停用新三指system服务、用户gesture服务，恢复备份的edge_menu.py，再用官方plugin disable禁用pcadmin.control-center。只读TouchMode状态timer可停用；需要时恢复原root TouchMode工具。不要恢复整个shell.json覆盖后续修改，不停ZeroTier/TUN，不重置Omarchy，不改启动解密。用户配置备份在管理项目backups/control-center-*，root原件在/var/lib/pcadmin-control-center/recovery。

## 验证边界

Python适配器/调度/手势协议/入口回退、JS几何/状态、TouchMode导出均有测试。锁屏时实际IPC打开被拒绝，当前插件加载与触摸屏observer连接已验证。实体三指、未锁屏面板手感、音量亮度实调、冷启动/睡眠保持分别需要实际验证，软件测试不能代替触屏验收。测试不自动切网络、飞行、熄屏或重启。

运行：`python -m unittest discover -s tools/control-center -p 'test_*.py'`、`node tools/control-center/test-model.cjs`，并回归touch-mode与edge-gestures原测试。

## 飞行娱乐模式（0.1.5）

飞行请求存在时只呈现离线游戏、视频、音乐、阅读入口及必要的电池/输入/音量/亮度/锁屏控制。退出恢复原网络开关；未知或部分关闭状态保留重试和恢复入口。它是控制台场景，不会杀死应用或限制整个系统的程序运行。

复用网络中心严格飞行控制器。软件故障回归与运行IPC已验；实机关闭/恢复、真实触屏及冷启动待验。安装更新不会自动启用飞行模式。蓝牙外设在飞行模式中断开。

## 共享界面 0.1.6

已接入工作台共享触屏按钮、固定标题和尺寸模型；颜色沿Omarchy当前主题。状态时间无效/过期显示待读取。实际界面已打开检查，物理手势与手感仍需分别验收。

## 夜间模式 0.1.7

快捷九宫格的“夜间模式”、设备详情和飞行娱乐页调用同一个 Omarchy 官方 `omarchy toggle nightlight`，没有另起色温控制器。有效色温小于 6000 K 显示暖色开启，6000 K 及以上显示关闭；状态读取失败或温度为 null 显示待确认，按钮仍明确执行“切换”。沿用同类动作互斥、锁屏复查和请求后刷新。

本机已通过实际 4000 K 开启、6500 K 关闭及控制台状态读回；38 项远程 Python、JS 和独立代码审查通过。新按钮的实体触屏手感、自动时段和冷启动不在此次验收范围。

## 状态显示 0.1.8

共享状态工具保留来源的未知、错误、过期和不可用状态，不把残留actual显示为已知；既有缺少health字段的数据仍按时间规则兼容。

## 阶段 A 固定只读依赖（候选）

`contracts_loader.py`仅装载相邻`vendor/dashen-contracts-0.1.0`中的公共契约快照，固定总库969cd18647f59bc3072a877a87ce1c4f054351f0。来源清单记录每个源码文件和原GPL许可证的SHA256；缺失、链接、内容变化或版本不符返回固定错误码。loader执行刚核验的源码字节，不读取缓存字节码、不从cwd/PYTHONPATH找同名包，不联网安装。依赖原件不能单独修改；升级需更新明确的版本锁定与验证。

这些检查用于可信开发者安装后的内容一致性，不是签名或抵抗同用户改写安装目录的安全边界。候选源码已加入同次采样的 `status-readonly`：固定两项温度/触摸契约，保留 legacy 状态与原动作；不把软件通过写成设备已接入。

只读请求总预算20秒、UTF-8输出上限64KiB，超时或SIGTERM只回收本次请求启动的读取子进程组。温度从实际读取前的CLOCK_BOOTTIME开始计龄；触摸仅接受同一启动、root普通文件且父目录不可由普通用户写入的私有缓存观测时间。缺失或不可信年龄降为未知，UTC不证明新鲜度，启动标识不进入公共响应。没有权限票据、注册、订阅或远程写接口。

## 阶段 A 界面读取（候选）

温度与触摸只显示经固定契约验证的最近一次采样结果；未知/失败不附温度单位，不以UTC回拨恢复已知状态。5秒刷新开始时清除这两项旧显示，关闭/锁屏使请求代次失效，20秒超时取消本次读取。原白名单动作及未知时的触摸刷新入口保留。采样后的连续实时年龄与真实休眠恢复尚需实体对照，不能从QML定时器推定。

远程纯Qt测试运行 `tests/tst_contractstate.qml` 与实际Panel布局提取检查 `check_panel_layout.py`；安装Quickshell的隔离构建机另运行 `check_read_transport.py`，验证真实Process的成功、非零退出、超限、截断、锁屏、取消和20秒超时。后者不要求普通Qt CI安装完整桌面。

## B1：按需设备证据（软件候选）

`python3 modules/control-center/control_center.py device-evidence` 独立读取 sysfs 能力与 udev 白名单属性。输出固定 schema JSON；`complete=false` 表示枚举不完整，存在性字段为 `null`，不能当作没有键盘。未知来源候选保持 `unknown`，不说明硬件损坏。`tablet_switch_capability` 只表示开关能力，不能当作当前模式。

最多128个event节点、单文件/udev输出16KiB、共享5秒用户态预算；仅回收该请求创建的进程。正常与失败通过 health/reason_code 区分，参数错误退出非零；不输出设备身份或输入正文，不打开输入事件流。无新依赖/服务，不进入原status轮询。

`device_mode.reduce_mode` 提供纯模式建议，手动选择优先；自动desktop/tablet分别稳定500/1000ms，观察间断超过2秒清空候选。该库不读取时钟、持久化偏好或实际改变布局。B2布局/输出接入及真实USB/蓝牙/Pogo插拔仍待实施/验收；本批不安装到生产。

## B2：设备模式与双布局（0.2.0 软件候选）

面板只在实际承载输出上打开。全局入口按官方 moduleWidgets 与聚焦屏幕选择唯一实例；无附着、重复实例或已移除输出拒绝打开。跨屏打开先关闭并回收旧实例，保留 ready/open/close/toggle/gesture/expand/state IPC；state 追加模式字段且不返回连接器身份。

自动模式仅在本机 DRM 物理输出匹配后启用。Rust/libudev 观察器只随面板存在；ready 后采样，变化合并100ms，单次触发最多两轮/四次读取，超时、失序、关闭或输出移除使旧结果失效。没有周期全设备扫描、后台常驻服务或自动代理切换。手动模式不依赖设备识别，输入法入口始终保留。

自动／平板／桌面选择按输出配置键保存在用户状态目录；坏文件、链接或写入失败显示未保存。手动选择在本会话立即有效。平板九宫格与桌面分组列表共享动作表及原授权入口；确认、动作或按压/拖动期间不重排，安全后应用最新建议。回车、Tab 和焦点滚动可用。

内部命令 `mode-step`、`mode-preference-read`、`mode-preference-write`、`output-policy` 从 stdin 接收严格白名单 JSON，最多4KiB，读入截止2秒。mode-step 的5秒采样预算和6秒前端截止独立；时钟由宿主 CLOCK_BOOTTIME 提供。偏好文件最多16项/4KiB、0600、无链接、受限 flock、fsync/原子替换和失败恢复。输出配置键仅区分本地偏好，不是硬件身份或认证。

[观察器构建与许可](device-observer/BUILD.md)；[完整软件/部署证据边界](../../docs/validation/2026-10-18-device-layout-stage-b2.md)。普通 CI 覆盖 Python/Rust/JS/Qt；真实 Quickshell 进程和双输出测试另在隔离构建区运行。隔离测试用 sway headless/pixman，不接宿主显示或输入设备，测试依赖使用官方渠道签名软件包覆盖层，不安装进宿主系统。
