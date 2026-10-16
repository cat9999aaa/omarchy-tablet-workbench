# 本机双电池记录器

归本机电池管理会员与w-0025。Python标准库实现；不需要root，不安装依赖，不自动修改电源策略或关闭应用。界面沿用Omarchy官方电源插件的用户克隆，源码位于../battery-panel。

每约60秒记录BAT0/BAT1槽位、电量、状态、电池端功率和时钟。数据库位于`~/.local/state/pcadmin-battery/history.sqlite3`（或XDG_STATE_HOME），目录0700、文件0600，保留90天。schema2按程序名称保存相邻采样间的CPU活动增量；仅为计算下次增量而保留最新一份PID/start_ticks/CPU计数。不读写argv、环境变量、序列号、窗口标题或聊天内容。

## 使用

用户服务`pcadmin-battery-record.timer`每分钟唤起oneshot记录器，不唤醒睡眠机器。CLI在此目录运行：

```
python3 battery.py status
python3 battery.py history --days 7
python3 battery.py apps --period session
python3 battery.py apps --period 24h
```

上述接口只读，不创建数据库。`record`执行一次采样；`--db PATH`隔离测试。JSON包含schema=1接口版本；SQLite schema=2，与接口版本不是同一编号。status使用增量缓存，开面板不扫描90天进程历史；apps直接用SQL聚合活动。history只读所选时段的紧凑电池样本。

systemd模板默认源码路径`%h/Projects/pcadmin/tools/battery-manager/battery.py`；迁移机器时按真实源码位置调整ExecStart及BatteryHistory.qml.helper。面板清单需将Panel.qml、Model.js、Details.js、BatteryHistory.qml一起放入对应release子目录；修改清单entryPoint前先完整写入新目录，再通过官方`omarchy plugin validate`和`omarchy-shell shell rescanPlugins`加载。不要改/usr/share/omarchy。

## 数据边界

- 槽位不是永久电池身份。不存序列号，无法识别所有不断电热替换；移除、在位变化和电量异常只会标跳变/缺口。
- 从首次记录起计时；插拔只能知道发生在相邻观察之间，正常约一分钟，关机/休眠/断采样期间误差更宽。
- 已接电时间包含等待；实际充电只累相邻均为Charging的可确认运行区间。睡眠期间无法确认全程充电，暂不累计，计时可能低估。
- awake/sleep基于单调时钟与启动时钟差；长清醒采样缺口记未知。亮屏是相邻显示状态的采样估计，未知单列。
- average_power_w是有效放电区间的时间加权电池端功率，不是充电器输入功率。当前硬件没有energy_now时Wh为空，未用瞬时电压伪算精确Wh。
- 既有充电上限只有实际可读阈值且电量已达到时才显示“已到设置上限”；等待状态本身不证明限充。
- CPU秒数可以超过经过时间；多核和多个同名进程会累加。不代表程序真实耗电比例。“曾无可见窗口”也不等于应用不必要；同名子进程可能负责可见主窗口。
- 进程退出、PID复用、跨boot不补猜CPU增量；分钟内的短进程可能漏采。24h按记录墙钟筛选，系统大幅校时可能影响这个日期窗口；本次会话按样本ID，不受墙钟倒退筛选丢失影响。
- 记录期间界面可关闭，计时继续；用户退出登录后记录可能停止。是否跨注销继续取决于既有user-manager生命周期，不自动启用linger。

## 测试

```
python3 -m unittest discover -s tools/battery-manager/tests -v
node tools/battery-panel/test_history.js
node tools/battery-panel/test_icon.js
systemd-analyze --user verify tools/battery-manager/systemd/pcadmin-battery-record.service tools/battery-manager/systemd/pcadmin-battery-record.timer
```

从pcadmin根运行。真实插拔、睡眠唤醒、完整充放电周期和手指操作必须另行实测；固定样本测试不替代硬件验收。

## 恢复

先`systemctl --user disable --now pcadmin-battery-record.timer`，等待正在执行的oneshot结束，再按本次备份恢复/移除两个目标用户单元并daemon-reload。只恢复电源插件目标manifest与其对应release文件，保留其他网络/输入法配置；重新validate/rescanPlugins。数据库独立保留，不随回退删除。

本机备份：backups/battery-manager-2026-10-17；包含部署前面板、单元存在性及迁移前数据库。数据库备份仅本机保留，绝不上传GitHub。
