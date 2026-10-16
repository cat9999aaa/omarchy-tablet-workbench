# 双电池记录与后台活动（本机原型）

来源：本机pcadmin电池工具，2026-10-17实现；不是所有设备通用安装包。

recorder为Python标准库记录器与用户级systemd模板；panel为Omarchy官方omarchy.power用户克隆的扩展。功能包括双电池独立计时、接电/放电会话、7天曲线和本次/24h CPU活动排行。后台排行不是精确应用耗电比例。

已验证：27个Python测试、11个JS格式化检查、原图标回归；真实每分钟定时记录、Qt三页界面和数据库不可读降级。独立代码审查发现的边界问题已加回归修复。实际插拔/睡眠唤醒、完整充放电周期、新页签实体触屏和长期运行尚未验收。

没有复制任何本机数据库、原始进程样本、私人管理档案、凭据或截图。最新进程计数只保留在运行机器本地，用于下一次活动增量；90天历史保存电池样本和按程序名聚合的CPU活动。

## 检查

在此模块目录运行：

```
python3 -m unittest discover -s recorder/tests -v
node panel/test_history.js
node panel/test_icon.js
systemd-analyze --user verify recorder/systemd/pcadmin-battery-record.service recorder/systemd/pcadmin-battery-record.timer
```

## 部署边界

仅验证过Omarchy4.0.4/Quickshell本机环境；依赖现有Omarchy官方克隆接口。systemd的ExecStart和BatteryHistory.qml.helper默认对应本机管理源码布局`~/Projects/pcadmin/tools/battery-manager`，迁移部署必须按实际源码位置调整。不是运行本仓库目录就会自动接管系统。

面板部署先备份现有用户克隆，将Panel.qml、Model.js、Details.js、BatteryHistory.qml放到一个新的release目录，再调整manifest入口；使用官方plugin validate/rescanPlugins，不修改/usr/share/omarchy。用户定时器每分钟执行一次，不唤醒睡眠机器。记录器与恢复细节见recorder/README.md；面板说明见panel/README.md。

原电源面板源自Omarchy，保留其上游许可与作者归属。新记录器无第三方Python依赖。本目录为源码备份，未声称拥有上游代码或经过跨设备适配。
