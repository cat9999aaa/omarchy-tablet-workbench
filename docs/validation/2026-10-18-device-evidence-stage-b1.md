# B1设备证据与纯模式判定

按总库已批准规格38aec0e、计划351f929实施。移动起点01cb6b9，候选f7bc2da；状态：软件候选、独立审查与本机一次只读验证已完成，未部署。

## 行为

独立device-evidence命令只读sysfs能力与udev白名单，返回存在/不存在/未知三态、完整性和固定原因码。所有子查询共享5秒用户态预算，节点128、文件/查询16KiB、响应64KiB；不打开事件流、不输出设备身份。

纯分类器分别核对按键能力、虚拟路径、输入bus、udev类型和USB/蓝牙父链。Pogo/platform未验证则未知；完整枚举无物理键盘且无未知候选才允许false。纯模式函数保留手动选择，自动desktop500ms/tablet1000ms，间断超过2秒或无效时间清空候选。没有实际布局切换调用链。

旧status/status-readonly不新增设备探测，ReadBudget默认64KiB保持。没有新服务、依赖、系统设置或root写入。

## 软件证据

- 各任务已观察缺失模块/命令或预算参数失败，再实现绿色；新增分类、收集、模式和入口测试。
- f7bc2da控制模块102项通过，全量远程隔离24组通过。32/64位位图、虚拟/未知/混合来源、超限、FIFO、链接越界、设备消失、权限、时间边界和原入口兼容有覆盖。
- 本机native_client隔离整合候选全量24组通过，保留既有代理转交，未安装。
- 独立审查01cb6b9..f7bc2da无Critical/Important；两项Minor远程复现并暂缓：超大Python int时间可抛OverflowError；子查询TimeoutExpired目前显示read_failed/error。后者仍incomplete且存在性全null，不误报无键盘，回收路径保持。
- 本机候选只运行一次：complete=true、health=unknown、reason_code=unclassified_keyboard；keyboard=null、touch=true、tablet_switch=false、virtual_count=0、unclassified_count=1，采样289.77ms。这是单次耗时，不是P50/P95；与本轮候选计数一致，不证明实体键盘连接。
- 该读回没有修改tools/插件/服务，也没有读取输入事件。单次快照不能观察两次枚举间出现又完全消失的设备；持续事件语义属于B2。可信sysfs边界不涵盖特权攻击者改写整个路径树。

## 部署与实体边界

本批不安装到tools或插件。生产控制台仍0.1.9。恢复候选只涉及源码版本，不涉及停服务或恢复系统配置。USB/蓝牙/Pogo实际插拔、B2输出归属和真实布局、B/C后续功能未验/未实现；阶段A手指/笔/竖屏/冷启动/睡眠/生产回滚缺口保持。
