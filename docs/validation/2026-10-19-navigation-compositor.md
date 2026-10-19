# C2 Hyprland动作边界验证

状态：未通过，阻止C2生产交付。软件单元检查不替代本项。

平板与授权构建机均为Hyprland 0.56.2（构建机提交efb50993780079460b0cbed1363e2166a2de1d9f）。测试仅在构建区私有mount/PID/network/runtime命名空间中运行，没有宿主Wayland/DBus/输入设备；尝试渲染时仅映射renderD128与只读sysfs，未映射DRM card/KMS设备，没有修改系统包、服务或桌面。

证据位于本机.qiming/evidence/navigation-stage-c2-20261019与对应远程job：

- compositor-probe：无渲染设备的嵌套环境无法创建Aquamarine backend；同时发现Unix socket路径过长，已缩短测试根。
- compositor-probe3：render节点需要sysfs识别；补只读sysfs后进入实际协议协商。
- compositor-probe4/5：隔离sway父合成器的xdg_wm_base最大版本5，当前Aquamarine请求6；后者使用官方签名sway1.12/wlroots0.20仍未解决。
- compositor-weston：官方签名Weston15.0.1的wl_compositor最大版本5，当前Aquamarine请求6，backend创建失败。
- compositor-renderonly：不接任何父桌面、只给render节点的模式仍无法创建backend。未为了通过而映射宿主KMS、切换远程桌面或修改官方源代码。

官方软件包只从Omarchy stable镜像下载到授权构建job，gpgv验证发行签名及撤销名单，摘要/版本保留在modern-sway目录；没有pacman安装或系统升级。

`check_navigation_compositor.py`保留匹配版本、两个输出/两个实际窗口、过期输出、错误PID/窗口身份、单次正常动作、引号屏幕名称的检查路径。当前在backend启动前失败，后面的行为断言尚未执行，不能称此检查已验证。需要能安全运行该匹配版本的隔离图形环境后继续；独立审查也不能替代该证据。

软件侧已实现：新UI传context.output；缺上下文拒绝；window/switch/restore在同次eval先核对monitor，再核对窗口并dispatch；Lua字符串拒绝控制字符并转义引号/反斜杠。外部应用入口在固定命令交接前复核上下文，该跨进程步骤不承诺原子性。官方菜单的真实落点、搜索取消与返回原应用仍未验。
