# C2 导航交付记录

状态：执行已批准计划，未整体完成、未安装。基线bef842c（含bc8b740实机尺寸修复），分支feat/navigation-c2。C1实机和用户体验未验项仍独立保留。

## 任务进度

| 任务 | 实现与证据 | 状态 |
|---|---|---|
| 1 共享展示 | ThemeContext/StyledText/ActionGrid、gapSmall、九份共享源与四消费者生成副本；先失败后通过 | 软件完成，fac61da；任务4已接导航页面、未安装 |
| 2 有预算快照 | 5秒总预算、单次1秒、1MiB输出上限、锁屏/输出/窗口复核、结构校验及进程组清理 | 软件完成；定向20通过、含新读取组的统一34组通过 |
| 3 会话代次 | 关闭/新请求/旧动作结果隔离；无副作用纯模型 | 软件完成，定向生命周期及统一35组通过；任务4已接真实qs窗口 |
| 4 页面与输出 | 共享组件重组四页、唯一输出匹配、真实qs双输出、进程回收 | 实现与36组/150布局/186渲染通过；未安装 |
| 5 动作与应用 | 同次eval的输出/身份保护已实现，定向28通过 | 真实compositor环境未启动；官方菜单未验，阻止安装 |
| 6 审查与交付 | 0.1.3候选包含全部UI导入与2个helper摘要；漏文件/篡改拒绝 | 定向31通过；统一38组通过；独立审查无Critical/Important，组合恢复和生产未验 |

## 共享组件验证

- 旧实现分别在小间距角色、组件缺失、发行副本缺失、真实官方主题适配检查失败。
- 实现后Node主题测试、Qt25项（包含测试初始化/清理）、同步4项、真实qs官方解析与adapter热更新通过；任务1统一33组通过。
- 真实qs使用固定官方Color/Style，用户字号覆盖18映射为共享正文24，撤销覆盖回到16；热更新保留观察对象。不以Qt假对象代替官方适配验证。
- QML createObject传入数组会包装成QVariantList，Array.isArray返回false；校验兼容这种输入，同时拒绝只有length/索引的普通对象。
- 主题值31.5在Qt font.pixelSize表现为32，这是原生取整；令牌不改变。动作网格换主题保持同一按钮、按下状态与焦点，释放只发一次原动作。
- 状态表持续更新：[前端样式与组件清单](../frontend-style-catalog.md)。

## 快照验证

初始新测试确认旧snapshot没有有界读取接口。成功快照携带唯一输出及可空窗口目标；空窗口不当作错误，非法结构不当作零窗口。锁屏前后均需明确false，输出和窗口身份在读取前后保持一致才返回成功。

真实子进程测试覆盖1MiB合法JSON与超1字节拒绝、单次1秒上限、总预算剩余缩短、无效JSON/非有限数、退出失败及超时回收。追加测试先复现父进程退出但子进程持有管道仍在运行；错误路径改为终止原进程组，不仅检查父进程是否运行。修复后定向20项通过。

本机只读候选snapshot实际返回locked/设备已锁屏；没有打开窗口或改配置。该结果仅证明当前拒绝分支，不证明解锁导航、真实输出绑定或动作安全。

## 未验边界

共享组件的软件通过不是四页迁移完成；snapshot输出检查不是动作提交时的原子检查。真实Hyprland动作与官方菜单落点、手动中文输入交接、手指/笔、旋转/竖屏、冷热启动、睡眠、完整性能、生产安装与恢复均尚未由C2验收。

## 会话模型验证

NavigationSession.reduce返回新state和effects，不执行进程或设备命令。测试覆盖关闭后迟到读取、A/B并发、无效页保持、旧错误不清新反馈、重复动作拒绝、动作提交后关闭不伪装撤销、打开新会话时旧动作结果失效、绑定保存保持打开、输出移除清目标；同时检查输入state/event不被修改。缺模块红例已观察，完成后定向及统一35组通过。真实进程取消与屏幕生命周期见下方任务4验证。

## 四页接入与真实会话验证

任务4的Navigation.qml直接消费ThemeContext／StyledText／ActionGrid／PanelBody，开始和窗口动作来自数据；桌面编号/数量保留专用数据网格，按键使用原Qt ComboBox。所有按钮继续走原业务动作入口。每次读/动作进程保留创建时的generation，取消读取不取消已经提交的动作；旧结果不能改写新会话。state保留旧字段并追加phase/generation/reason_code，不公开输出名或窗口身份。

- runtime-red3先确认旧版绑定第一屏；runtime-full验证行为同时抓到targetScreen回调同步写状态的绑定循环，改为延迟检查后通过。
- task4-integrated2：真实隔离qs＋双输出sway八类检查通过：第二输出/旧IPC、读进程回收且不重开、旧动作不关闭新页、同输出缩放保持会话、输出移除不迁移、找不到输出关闭、准备阶段上下文变化拒绝、锁屏关闭。设备helper为合成输入，屏幕生命周期和IPC为真实实现。
- 原实际内容矩阵抓到480×540长窗口标题挤压桌面直达；标题限制单行省略后148项通过，增加无窗口禁用和共享动作组热更新按压检查后150项通过。
- 官方Color/Style下导航186场景渲染通过；统一35组通过，控制台/网络/电池共享回归保持。
- cancel-red真实子进程测试证明结束snapshot留下正在读取的子进程；SIGTERM改为展开Python清理，cancel-green定向21项通过。task4-final-all统一36组通过，包含新增navigation-cancel。

C2尚未安装；动作提交时的Hyprland原子边界、官方菜单交接及实体体验仍由后续任务验证，不由以上隔离渲染代替。

## 最终软件候选审查

2026-10-19，独立代理review_navigation_c2_final只读审查bef842c至a4e65ee及未提交候选文件；没有在平板运行测试或改文件。结论：未发现可确定的Critical/Important，可保留可审阅的软件候选，尚不具备生产安装条件。测试执行证据来自主代理远程运行。task6-all统一38组通过；candidate-green定向31通过。

三项Minor：样式表断行已修正；准备失败的reason_code可通过state查询，但中文reason未形成可见用户反馈，仍会表现为未打开；关闭停止新锁屏检查，但已有检查最多等待1秒watchdog清理，不承诺立即进程归零。后两项保留体验待办，需实际关闭后进程测量，不写成已经验收。

真实Hyprland、官方菜单/中文交接、helper/UI组合恢复、生产安装和实体性能门槛仍未通过；独立静态审查及38组软件结果都不能替代这些证据。

## GitHub兼容性回归

7b542ce的GitHub acceptance在Qt 6.4.2执行navigation-layout时SIGSEGV，地图检查通过；远程Qt 6.11.2的38组通过不能替代该失败。新增红例确认旧ActionGrid在同数量数据替换时销毁按钮；现改为数量模型按位置保留delegate，非法或越界数据安全回退，items替换递增revision取消在途点击。主题变更不取消按压；深层原地修改不在通知契约内。新增替换、重排、禁用、缩小和非法模型回归，保留原navigation-layout顺序与断言。此为兼容性修复候选，尚无native backtrace证明SIGSEGV根因。

stable-model-all：远程统一38组通过，包括原navigation-layout。独立复审未发现新增Critical/Important；按建议加强重排测试，使两个项目均启用，排除仅禁用导致零动作。GitHub Qt 6.4.2仍待本修复提交后复验。

2ccd274的GitHub run39161867126：原导航崩溃未再发生，但导航146通过/4失败，均为320宽/1.5字号数字标签裁切；shared-qml在新增模型删除边界测试异常退出。bc2bcf9添加失败时gdb诊断，不放宽门槛。数字布局改为两网格共用TextMetrics与主题padding计算列数，numeric-layout-green远程150项通过，等待旧Qt复验。

run39162098702的失败后gdb捕获shared-qml SIGSEGV：qmlAttachedPropertiesObject → Qt6QuickLayouts → QGridLayoutEngine::fillRowData/setGeometries → QQuickGridLayoutBase::rearrange/geometryChange → QQuickColumn::doPositioning。栈定位到布局重排路径，尚不足以证明底层释放机制。ActionGrid改用基础Grid positioner等宽排列，保留数量模型、索引安全回退及revision防误触；原回归断言全部保留。

grid-positioner-all远程38组通过。独立复审发现过多columns可能失去48触摸宽度，新grid-columns-red复现；加入按宽度限制列数及不足48禁用，保持无负宽度和无横向溢出。

2a5c65d在GitHub run39162420543通过Software acceptance（Qt 6.4.2含原失败序列）及map-gps。远程grid-final-integrated通过真实qs双输出8类、统一38组及官方主题导航186场景。独立复审确认最小触摸宽度问题已闭合。

临时HOME组合文件恢复演练：recovery-rehearsal导航34项通过，新增3项验证真实candidate/ReleaseManager与手工helper顺序、偏好/文件模式/原缺失状态恢复、helper编辑保留、UI冲突停止helper恢复。shell探针为合成输入，不执行真实桌面命令；该证据不代表生产安装器、事务原子性或真实桌面恢复已验。navigation-recovery单独接入统一组。

recovery-final-all统一39组通过。独立复审确认演练无真实桌面/生产路径操作；按意见将偏好fixture调整为生产相对路径.config/omarchy-tablet-workbench/buttons.json。helper冲突案例只覆盖UI回退后、helper恢复前，不能扩大为所有阶段并发操作保证。
