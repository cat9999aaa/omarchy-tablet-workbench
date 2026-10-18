# Dell Latitude 7220 原装无源笔模式

只适用于已实测的 eGalax `0eef:c003`、产品名
`eGalaxTouch P80H84 0710 vA1_N k47_45`。其他控制器拒绝写入。
这是本项目自己实现的模式设置工具，使用从戴尔官方 TouchMode 应用核对的 HID 命令；不是厂商发布的 Linux 驱动。
保留原生 hid-multitouch/libinput，不刷固件，不安装厂商守护程序。

2026-10-16 实测：模式0时原装无电池、机身收纳笔无反应；模式1（手套）下用户确认画线正常。
仅笔画板捕获4次接触、1103个touch事件，未提供压力/倾斜。用户提前结束测试，结果complete=false；划线成功不代表30秒协议完整完成或性能测量。
服务运行成功并读回1；udev语法检查、实际匹配通过。真实冷启动、控制器重连、睡眠唤醒后的实体效果尚未验收。

## 安装与核对

需要系统 Python3、systemd/udev 与管理员权限。先备份下列目标文件；已有同名部署时保留其启用状态。
在本模块目录执行：

```sh
sudo install -Dm644 touch_mode.py /usr/local/libexec/pcadmin-touch-mode.py
sudo install -Dm644 pcadmin-touch-mode.service /etc/systemd/system/pcadmin-touch-mode.service
sudo install -Dm644 80-pcadmin-touch-mode.rules /etc/udev/rules.d/80-pcadmin-touch-mode.rules
sudo systemctl daemon-reload
sudo udevadm control --reload-rules
sudo systemctl enable --now pcadmin-touch-mode.service
sudo python3 /usr/local/libexec/pcadmin-touch-mode.py status
```

应读回actual=1、verified=true。该服务仅执行一次，成功后inactive正常；检查`Result=success`和`ExecMainStatus=0`。
服务在开机和控制器重新枚举时应用模式，不常驻；未安装睡眠恢复钩子。
系统更新后复核USB型号、读回及仅笔划线，不自动放宽型号匹配。

## 恢复

```sh
sudo systemctl disable --now pcadmin-touch-mode.service
sudo rm /etc/udev/rules.d/80-pcadmin-touch-mode.rules
sudo udevadm control --reload-rules
sudo python3 /usr/local/libexec/pcadmin-touch-mode.py normal
```

确认actual=0后可移除专用service/helper并daemon-reload，或恢复安装前备份。
不要改动原生输入设备的通用规则。

## 命令依据

64字节输出：`03 04 3f 65 selector value`后补零，selector0读当前模式、1设模式；只使用已验0/1。
每次设置读回，不识别的设备/模式拒绝写入；设置失败尝试恢复旧模式。
不记录输入坐标、笔迹或设备序列号。

来源：本机排障原型，源码权威保留在本机管理项目的tools/touch-mode；此目录为脱敏同步副本。
厂商二进制、固件、个人管理档案不随仓库分发。本项目原创源码随仓库以 GPL-3.0-only 发布，厂商原件不包含在该授权中。

- [戴尔官方 TouchMode A06](https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=jxxy8)
- [EETI Linux 驱动](https://www.eeti.com/drivers_Linux.html)
- [同控制器原装笔无响应的上游报告](https://lists.openwall.net/linux-kernel/2026/09/04/1886)

## 只读缓存时间证据（阶段 A 候选）

原有30秒状态timer的生产者在查询前取CLOCK_BOOTTIME，并由本机boot_id生成不透明marker；只在`/run/pcadmin-touch-mode/state.json`追加observation，不输出到CLI公开结果。接收者还必须核对root拥有、不可由普通用户改写的缓存及当前boot，不能只相信JSON字段。时间包括休眠，查询开始到导出之间的耗时保守计入观测年龄。

原state_payload与read_apply接口不变，旧消费者可忽略新增字段。既有授权动作调用export_state未传observation时仍生成旧格式，可信年龄保持未知，等待原timer自然刷新。不需要修改服务、timer或udev，不为升级测试重启服务或切模式。读取时钟/启动标识失败、设备查询失败均不沿用成功时间证据。本节为软件候选说明，尚未据此宣称本机已安装或休眠/冷启动已验。
