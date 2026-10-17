# 本机双电池原生面板

归本机电池系统，来源任务w-0014。基于已安装Omarchy官方omarchy.power克隆；源文件/usr/share/omarchy只读。用户配置插件cat9999sss.power；源码在此，部署release-1/Panel.qml。调用官方omarchy-shell omarchy.power open。

UPower事件驱动提供独立BAT0/BAT1电量、状态、预计时间、净功率、能量及综合电量。保持原生省电/均衡/性能切换。合计电量与独立电量明确区分，避免原生首块电池百分比混入合计面板。循环次数不可靠则未知；PendingCharge不代表达到充电阈值，八小时以上ETA不作为限充证据。等待充电不显示旧的预计充满时间。功率来自电池端，并非充电器/墙上功率；时间受负载、分时充电、温度等影响。

不修改充电阈值、固件风扇、低电量保护。热事件临时处置用了官方omarchy powerprofiles set ac power-saver，记住接电省电；恢复原均衡：omarchy powerprofiles set ac balanced。

2026-10-16验证：未知时间/等待状态格式测试通过；插件校验通过；真实面板打开并截图检查，两块电池与模式按钮均在可见区域。实体触屏点击尚未验收。

恢复面板：备份backups/power-panel-2026-10-16/shell.json；或将bar.layout.right中的cat9999sss.power换回omarchy.power（只修改该项，保留后续其他配置），移除本机克隆。首次官方clone过程中IPC重载超时，脚本清理了目录但留下配置；已从原生源码按克隆清单重建，真实面板验证通过。

2026-10-17新增电池管理1.1.3（release-7）：BatteryHistory.qml接入本地每分钟记录器，三个页签提供本次计时、程序CPU活动和7天历史。整体面板可滚动，内部排行/历史可单独滚动。使用原Omarchy打开入口；额外IPC `timing`、`activity`、`history`可直达对应页，仅用于查看。数据不可读时独立降级，原UPower区域继续显示。源码../battery-manager；管理任务w-0025，恢复备份backups/battery-manager-2026-10-17。测试/软件截图已验，新增页签真实手指点击和完整电池周期未验。

## 共享界面 1.2.0

固定标题和收起按钮，长内容在内部滚动；采用共享触屏按钮与固定外框。三个页签实测切换不改变外框尺寸。完整电池周期和实体手感仍待验。
