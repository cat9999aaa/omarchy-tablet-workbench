---
name: tablet-control-center
description: Use when developing, diagnosing, or maintaining this project's Omarchy tablet dropdown control center, touchscreen quick settings, or its device-control adapters.
---

# 随身控制台维护入口

限定当前拥有此Skill的项目。先确认项目根；管理项目的启明实例不能沿用到独立工作台仓库或其他设备。

## 按目标读取

- 产品约束与交互：[设计规格](../../../docs/superpowers/specs/2026-10-16-tablet-control-center-design.md)。
- 阶段A任务与验收：[实施计划](../../../docs/superpowers/plans/2026-10-16-tablet-control-center-phase-a.md)。
- 本机当前进度：若项目内存在`.qiming/work/w-0022.json`和`.qiming/members/control-center.json`，通过本项目Qiming规则读取；没有则只使用本仓库资料，不查宿主其他实例。
- 实现后权威源码为管理项目`tools/control-center`；工作台`modules/control-center`为便携副本。目录不存在说明尚未实现，不能据规格执行不存在的IPC。

## 易错处

顶部边缘MouseArea下滑不证明三指识别；实体测试与软件规则测试分开记录。

真实三指实现见`tools/control-center/gesture_daemon.py`及`gesture_model.py`：只观察已匹配触摸屏的多点事件，不grab/注入、不读键盘、不保存坐标。用户接收器只接受内核凭据UID0的固定事件。默认屏幕方向之外需重新验证方向；服务connected不证明实体三指验收。

TouchMode本次普通/手套设置与开机默认不同。默认服务与udev目前仍应用手套1；一次设置普通0不能宣称永久普通模式。查询读取缓存必须检查时间与verified，修改后以硬件读回为准。

网络、代理、输入法复用现有控制器。物理出口、代理核心、TUN、外网健康分别展示；不把虚拟网卡标成有线，不为验证UI自动关4G/代理、切飞行或重启。需要实断网验收时，先核对用户对该次测试的具体授权。

只在锁屏状态明确false时打开或执行；动作前再次核对。取消认证保持失败/取消，不能显示成功。密码、节点/root实际配置、SIM身份、位置不写Skill或GitHub。

授权等待期间也可能锁屏：用户进程应取消排队请求，root受控入口`privileged_control.py`必须在Polkit之后再检查原会话；触摸写入/飞行修改前仍调用guard。普通exit0只代表请求已提交，不能当硬件读回成功。音量/静音共用audio-output资源锁，电源模式共用power-profile锁。未知/过期状态不能映射成关闭或选择开启操作。

取消不能只靠终止pkexec：原请求的短期凭据文件需绑定用户、存活进程及启动标记、允许动作和期限；锁屏取消或进程退出后应失效，稍后解锁也不能复活旧请求。文件仅保存在用户runtime目录，不写启明或GitHub。

## 修改与交付

按已批准阶段和计划执行；核对安装版本的官方接口，备份后修改用户插件，不修改打包源文件。保留旧quickstatus入口回退；核对运行时IPC版本，manifest版本不足以证明新界面已加载。

验收分别记：设计批准、代码存在、单测、运行时、用户触屏。回退只恢复控制台与入口，不顺带停ZeroTier/TUN或重置整个shell。同步便携副本和本项目管理记录，保留未验证项。

部署、状态来源及恢复细节见[控制台README](../../../modules/control-center/README.md)；便携仓库对应`modules/control-center/README.md`。恢复只移除本次入口/服务，不能拿旧shell.json覆盖后续电池或游戏配置。
