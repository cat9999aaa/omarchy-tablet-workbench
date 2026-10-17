# 启明 · 随身控制台 0.1.1

面向本机 Omarchy 平板的用户插件。沿用官方 bar-widget 注册方式，不修改打包文件，不添加 Hyprland 二进制插件。

## 使用

- 三根手指同时触屏，向下滑动约屏高8%以上，然后全部松开：打开控制台；已打开时再次下滑进入详情。
- 底栏“控制台”图标、原顶部边缘下拉也可唤起。点右上角收起、外侧或 Esc 关闭。
- 九个快捷磁贴、亮度和音量；详情分连接／设备／工作／旅途。亮度和音量在松手后提交，不逐像素启动进程。
- 关闭代理、飞行模式、切到普通触摸先确认。普通触摸仅本次生效，原装无源笔可能失效；开机和重连仍恢复手套模式。
- 显示方向尚未适配，保持禁用；AI任务和场景编排未接入，不提供假按钮。电池详情接现有充放电记录工具。

## 状态与权限

网络复用 network-center 的状态缓存；不新增外网测速循环，不更换代理核心或节点。物理出口、核心、TUN和网络健康分别显示。CPU温度来自具名thermal源，未知不补0。电池使用UPower实体设备，缺失估算仍在原电池详情中显示未知。

音频显示使用PipeWire及PwObjectTracker，修改通过白名单调度器调用pactl，目标由Omarchy官方 `audio output sink` 解析，避免误调DSP入口。亮度调用官方monitor IPC。沿用已有Polkit授权，密码不进入控制台。

锁屏须明确false才能打开，动作执行前再核对；锁屏或查询失败关闭面板。打开前隐藏原生与旧键盘并检查layer消失；失败不强行叠加。面板关闭停止自身5秒状态刷新和500毫秒锁屏检查。后台手势只观察核对过名称和USB厂商/产品的触摸屏，读取ABS多点事件，永不grab、不创建虚拟输入、不读取键盘。坐标只保留在当前手势内，不写日志。仅固定gesture token通过本机Unix socket送给用户会话，接收器核对内核提供的root身份。

全屏触屏上的手势由观察器识别，应用也可能看到同一次三指移动；此版不承诺消费掉应用的触摸。原始坐标方向按本机默认屏幕方向适配，旋转后的三指方向尚未验证。

## 部署与恢复

权威源码是本机管理项目tools/control-center；便携源码在工作台modules/control-center。只保留一份TouchMode工具：modules/hardware-toolbox/touch-mode。便携副本需设置 `PCADMIN_CONTROL_HELPER` 到部署的适配器；network-center、IME及窗口菜单路径需按目标实例核对，不能沿用其他项目的启明身份。本模块没有跨设备通用安装器。

用户插件 `pcadmin.control-center` 的versioned entry在 `release-0.1.1`，IPC `pcadmin.controlCenter` 提供ready/open/close/toggle/gesture/expand/state；不接受任意命令。官方plugin enable负责底栏注册，保留底栏原位置和P1/P2/P3/旋转键分工。

root安装只读触摸状态导出timer，以及只观察触屏的pcadmin-three-finger.service；后者recipient UID必须在安装时替换，不可复制本机UID到其他设备。用户服务pcadmin-control-gesture负责会话入口。既有TouchMode开机服务和udev默认不变。

恢复时先停用新三指system服务、用户gesture服务，恢复备份的edge_menu.py，再用官方plugin disable禁用pcadmin.control-center。只读TouchMode状态timer可停用；需要时恢复原root TouchMode工具。不要恢复整个shell.json覆盖后续修改，不停ZeroTier/TUN，不重置Omarchy，不改启动解密。用户配置备份在管理项目backups/control-center-*，root原件在/var/lib/pcadmin-control-center/recovery。

## 验证边界

Python适配器/调度/手势协议/入口回退、JS几何/状态、TouchMode导出均有测试。锁屏时实际IPC打开被拒绝，当前插件加载与触摸屏observer连接已验证。实体三指、未锁屏面板手感、音量亮度实调、冷启动/睡眠保持分别需要实际验证，软件测试不能代替触屏验收。测试不自动切网络、飞行、熄屏或重启。

运行：`python -m unittest discover -s tools/control-center -p 'test_*.py'`、`node tools/control-center/test-model.cjs`，并回归touch-mode与edge-gestures原测试。
