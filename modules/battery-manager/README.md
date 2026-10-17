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


## 2026-10-17 智能电源策略可行性复核

现有Omarchy官方电源命令与PPD可执行省电/均衡/性能；UPower分别提供双电池对象，现有每分钟记录器已运行。无需增加第二套底层电源管理器。

Jev经[TypeSafe官方文档](https://docs.typesafe.ai/introduction/quickstart)核实是Choice/Score/Noul决策模型，可接结构化状态作为可选建议层；本次未调用API，未实测延迟/判断准确率/节电收益，也未安装SDK或模型Skill。

- 熄屏继续工作与睡眠分开：[内核睡眠文档](https://cdn.kernel.org/doc/html/latest/admin-guide/pm/sleep-states.html)说明s2idle也会冻结用户态。本机列出`s2idle/deep`，默认s2idle；列出不等于设备恢复兼容已测。不能默认闲置就睡眠中断Agent和网络。
- 需要任务保持凭据/明确工作模式；现有NM/MM等delay inhibitor不是永久禁止挂起。手动选择优先，AI低置信/离线/超时维持本地规则，禁止AI直接执行任意命令/断网/结束任务。
- 接电自动性能不符合本机降温偏好。现有AC与电池保存power-saver；CPU仍允许动态升频，未设置固定低最大频率，收益未测。
- 双电池温度接口缺失；cycle_count=0不能据此认定新电池。曾发生底层百分比跳变，健康/续航仍待自然放电与BIOS/ePSA核实。
- BAT0阈值接口读到50/90，BAT1未暴露对应接口；未修改阈值，实际执行效果未测，不宣称两块都可分别控制。
- 按[TLP官方冲突说明](https://linrunner.de/tlp/faq/ppd.html)保持单一PPD控制，不并装竞争控制器、不运行PowerTOP auto-tune，不自动改变蜂窝/触屏/GPS USB省电。

建议顺序：现有记录器做固定亮度/网络/负载的对照测量→原生事件规则→Jev仅影子建议与规则比较→有实测收益后再开放少量白名单动作。睡眠/包内模式需要单独验收。当前仅验证接口和文档，未启动智能控制守护进程。
