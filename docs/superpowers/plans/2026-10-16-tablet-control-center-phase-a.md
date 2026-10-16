# 随身控制台 Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可回退的原生触屏紧凑控制台，提供真实设备状态、常用控制与现有详情入口。

**Architecture:** Omarchy用户bar-widget插件承载独立面板。Python适配器复用现有网络、输入法和TouchMode工具，QML复用官方音频/显示及UPower对象。唯一调度器处理白名单动作、确认和读回，保留旧quickstatus回退。

**Tech Stack:** 现有QtQuick/Quickshell、JavaScript纯模型、Python3标准库、已有Gio/UPower/PipeWire；不新增软件源与二进制插件。

**Spec:** `docs/superpowers/specs/2026-10-16-tablet-control-center-design.md`（用户已批准）。本计划待用户审阅及选择执行方式；尚未实施。

## Global Constraints

- 不修改打包源文件，不加Hyprland二进制插件。
- 紧凑态宽不超过屏幕，横屏最大760逻辑像素，高不超过可用高度70%；磁贴触控高度至少64，间隔至少8。
- 不自动关Wi-Fi、关4G、关代理、切飞行模式、休眠或重启做测试。
- 当前4G/TUN保持不变；首版不添加网络探测定时器，复用现有缓存。
- 普通/手套切换仅影响本次硬件状态；开机默认仍手套，不伪造持久设置。
- 现有顶部边缘下滑不是已验证三指识别；不得用全屏透明层抓取应用触摸。
- P1/P2/P3与实体旋转键分工保持；锁屏或锁屏状态未知时拒绝唤起/执行。
- 源码权威tools/control-center；GitHub副本modules/control-center；本机凭据、root实际配置和私人网络数据不上传。
- 阶段A包含紧凑态及详细页导航框架；场景编排、语音AI、真实三指适配、旋转控制不在本阶段实现。

## Review Focus

- 温度/电池/音频设备不存在或状态过期：显示未知/不可用而不是0或正常；Task1/4覆盖。
- 锁屏发生在打开面板或排队认证期间：关闭界面且拒绝后续动作；Task2/4覆盖。
- 一次触摸切换与开机默认冲突：明确本次状态与默认手套，读回失败不报成功；Task3覆盖。
- 横竖屏小高度、字体增大、输入法同时存在：操作区可滚动且收起可达，不向其他窗口漏输入；Task4覆盖。
- 快速重复点按/滑杆连续拖动/用户取消认证：串行资源操作，取消不改状态，不创建重复进程；Task2/4覆盖。

## 文件与交付边界

新建tools/control-center/{manifest.json,Panel.qml,ControlModel.js,control_center.py,adapters.py,test_control_center.py,test_adapters.py,test-model.cjs,README.md}。
现有tools/touch-mode/touch_mode.py只扩展状态导出，不改变HID协议或硬件匹配；新增同目录read-only export service/timer用于受限状态读取，设置动作沿用现有授权。
部署副本在用户插件目录<user>.control-center/release-0.1.0；用户配置、菜单和bar manifest修改前逐个备份。仓库源码副本适配HOME/环境变量路径，不硬编码本机用户名。

### Task 1: 真实状态契约与现有接口适配

**Files:** Create tools/control-center/adapters.py, test_adapters.py, ControlModel.js, test-model.cjs。
**Interfaces:** `snapshot(now: float, network: dict, touch: dict, thermal: list) -> dict`；`field(capability: str, available: bool, actual: object, observed_at: float, stale_after: float, source: str, reason: str='') -> dict`。输出保留网络原始physical_uplink/core/tun/internet，不读取节点配置。JS导出`displayField(field, now)`、`layout(width,height)`。

- [ ] 写失败测试：网络缓存显示physical4g而不是tun；TUN运行但internet失败显示异常；温度源空列表actual=null；过期状态标stale；电池剩余时间缺失保持null。布局测试宽500高800和宽1536高829，满足760/70%/64/8约束。
- [ ] 运行`python -m unittest discover -s tools/control-center -p 'test_adapters.py'`及`node tools/control-center/test-model.cjs`，确认测试因缺少实现失败。
- [ ] 实现上述契约。网络通过已有network.py status读取；温度只读取已命名thermal_zone*/type及temp，返回来源，不推断传感器不存在时的温度。
- [ ] 实现显示转换：actual=null、available=false、stale三者分别呈现；desired不覆盖actual。
- [ ] 重跑测试至通过；对已有network.py status执行一次只读实测，不改变连接。输出证据不包含SIM/私网地址。
- [ ] 只提交本任务源码与测试：`feat(control-center): add verified state contracts`。

### Task 2: 白名单操作与确认/锁屏状态机

**Files:** Create tools/control-center/control_center.py, test_control_center.py。
**Interfaces:** `prepare(action: str, params: dict, locked: bool|None) -> dict`返回resource、argv、requires_confirmation；`execute(request: dict, confirmed: bool, read_lock: callable, run: callable) -> dict`返回request_id/stage/result/reason；CLI只有status与action JSON两类输入，参数尺寸限制4096字节。

- [ ] 写失败测试：未知action或注入参数拒绝；locked=true/None拒绝；prepare后锁屏拒绝执行；network/proxy/flight关闭未确认不运行；同资源重复请求busy；认证退出126/127显示取消/失败，不伪造成功。
- [ ] 跑`python -m unittest discover -s tools/control-center -p 'test_control_center.py'`确认RED。
- [ ] 实现白名单与run参数列表，不使用shell=True。详情仅允许既有omarchy.network/power/audio/monitor/bluetooth open；IME调用现有control.py；网络控制调用既有network.py，禁止创建第二套core。
- [ ] 文件锁按资源名放XDG_RUNTIME_DIR，权限0600，非阻塞；执行前再次调用lock.isLocked，任何非false均拒绝。状态请求不触发授权弹窗。
- [ ] 滑杆只接受整数0–100，拒绝NaN/负值/越界；亮度低值保护沿用官方面板。每次进程完成才返回执行阶段；硬件readback独立。
- [ ] 重跑测试至通过，提交`feat(control-center): serialize authorized device actions`。

### Task 3: TouchMode只读导出与可验证的本次切换

**Files:** Modify tools/touch-mode/touch_mode.py；Create同目录test_state_export.py、pcadmin-touch-state.service、pcadmin-touch-state.timer；Modify tools/control-center/adapters.py及test_adapters.py。
**Interfaces:** 导出`/run/pcadmin-touch-mode/state.json`，root拥有0644；内容仅mode(0/1/2)、verified、observed_at、error、boot_default=1，不含hidraw路径或设备身份。`read_touch_state(path,now)->dict`；现有glove/normal设置成功后原子更新导出。

- [ ] 写失败测试：成功/读回不符/设备消失的导出内容；旧文件不会在失败后继续显示正常；普通模式仍boot_default1；状态超过45秒变stale；普通用户不能通过参数指定任意导出路径。
- [ ] 跑测试确认RED。
- [ ] 为现有工具增加固定路径原子导出选项，保持status/glove/normal原行为；只读导出命令失败仍写error快照。服务调用固定工具路径，timer每30秒执行一次查询，不写HID模式。
- [ ] service采用Type=oneshot、TimeoutStartSec=15，timer同一unit不能重入；不新增开机默认设置，不扩大hidraw权限。已有开机glove与udev规则不改。
- [ ] pytest依赖不新增，使用unittest；跑测试与`systemd-analyze verify`。未获实际模式切换测试授权时只查询当前模式，真实来回切换保持待验。
- [ ] 提交`feat(control-center): export fresh touch mode state without UI authentication`。

### Task 4: 原生紧凑面板与音量亮度

**Files:** Create tools/control-center/Panel.qml、manifest.json；Modify ControlModel.js、test-model.cjs、README.md。
**Interfaces:** plugin bar-widget生命周期沿用官方音频/网络面板模式；IPC target `pcadmin.controlCenter`暴露open/close/toggle/expand/state，state返回opened/expanded/geometry及脱敏状态；QML不提供任意执行接口。

- [ ] 写模型失败测试：缺少音频设备、过期电池、键盘可见时的打开互斥、拖动提交合并、取消确认、锁屏关闭、宽500高600大字布局。
- [ ] 跑`node tools/control-center/test-model.cjs`确认RED。
- [ ] 实现固定摘要、九磁贴、两滑杆、收起/展开；纯展示/未来入口禁用说明原因；详情态提供四页固定导航，未实现能力不放可执行假按钮。
- [ ] 音频复用Quickshell.Services.Pipewire的默认sink及PwObjectTracker，音量0–1、mute独立，不写应用流音量。拖动结束提交，点击静音读回audio.muted。默认sink切换立即换绑定。
- [ ] 亮度通过现有`omarchy-shell omarchy.monitor state`及`brightness <percent>`；来源brightnessAvailable=false时禁用。UPower.devices提供双电池，不将displayDevice合计当两块实体。
- [ ] QML通过Process请求聚合状态，opened才刷新本地状态（最多每5秒）；后台原服务事件由官方对象驱动。现有网络健康检测不重复启动；关闭后停止界面刷新与峰值监测。
- [ ] 打开前明确未锁定，隐藏键盘并记录是否隐藏成功；失败不强行打开叠加层。关闭释放键盘焦点。减少动画跟随系统可用设置，设置不可读则使用短暂非循环动画。
- [ ] 模型测试通过；独立加载测试插件并核对QML日志。IPC验证横/竖屏模拟几何，不修改实机显示方向；实际手感标待验。
- [ ] 提交`feat(control-center): add native touch-first compact panel`。

### Task 5: 有回退的部署与现有下拉入口接入

**Files:** Modify tools/edge-gestures/edge_menu.py；Create tools/control-center/test_entry.py；部署用户插件与shell配置前备份，GitHub不提交完整本机shell.json。
**Interfaces:** `quickstatus`在新控制台ready/未锁定时toggle，否则调用原`omarchy menu summon quickstatus`；不改变desktops动作或手势阈值。

- [ ] 写失败测试：新IPC不存在/超时/锁屏未知时保留安全行为；旧桌面菜单不受影响；toggle失败回退原菜单；模拟误触取消不执行。
- [ ] 跑测试确认RED；实现有限超时IPC探测与回退，失败不重启整个shell。
- [ ] 备份当前菜单、shell.json、bar manifest和edge helper；通过官方插件生命周期注册新bar-widget作为备用按钮，不改底栏固定位置、不添加标题栏。
- [ ] 新插件独立open/close/lock检查通过后才切下拉入口。版本化release路径避免旧缓存；rescan后核对IPC版本，不把manifest版本当运行时版本。
- [ ] 保持4G/TUN进行只读网络状态和真实网页复核；不测试断网、飞行或重启。检查没有第二个GUI/重复探测服务。实际三指与手感测试列为用户待验。
- [ ] 提交`feat(control-center): integrate safe dropdown entry and rollback`。

### Task 6: 验收记录、Skill与便携同步

**Files:** Update .qiming/work/w-0022.json、members/control-center.json及其技能子会员、START/startup；Update .agents/skills/tablet-control-center/SKILL.md、tools/control-center/README.md；同步工作台modules/control-center与docs，属于独立仓库不沿用本机Qiming身份。

- [ ] 跑全部Python/JS测试及QML运行时验证，检查只读状态和取消确认；对每项标记代码/软件测试/运行时/用户手感，未运行不补“通过”。
- [ ] 更新Skill引用真实入口、IPC版本与已验恢复方式；用户同意前不进行额外云端发布或官方上游PR。
- [ ] 仓库副本去除本机路径、用户名、私网地址与节点/凭据，仅携带模板与适配说明；独立跑副本测试及git diff --check。
- [ ] 经本实例plan→apply保存任务、会员、证据；源码不因有文件就标working。控制中心与维护Skill各有独立用途，Skill登记为控制中心子会员。
- [ ] 只提交本次文件并推既有feature分支，核对远端HEAD。为用户给出入口、已验范围和待实触项目。

## 自审结论与执行建议

目标/接口/状态字段在各任务间一致；五项Review Focus均有对应测试。阶段B–D不计入A完成。没有关闭当前网络的自动验收步骤；root导出独立于交互授权；每任务均有RED→实现→GREEN与提交。建议本会话直接执行：任务共享状态契约与现有本机接口，顺序实现更便于保持当前使用状态；最终按可用审查工具做独立代码审查，不另起用户聊天。
