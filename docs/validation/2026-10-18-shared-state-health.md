# 共享状态显示尊重来源健康状态

问题：显式health为unknown/error/stale时，只要旧actual有值且UTC时间未过期，State.fieldState仍返回known=true，可能把来源失败显示成运行/关闭。新契约消费者也会遭遇同一问题。

修复：显式health只有observed可进入实际值显示；未知/错误/过期/不可用均保留降级，不显示旧actual。缺少health的旧字段按既有时间规则兼容；actual为NaN/Infinity不显示为已知。false/0仍有效，未知不会变成关闭。无设备控制、布局、网络或权限协议变更。

权威开发入口modules/workbench-ui/State.js，四处插件Workbench目录为同一生成副本，shared-copies检查保证一致；本机tools权威副本与安装另记，不把源码修复直接当部署。

远程RED：新增显式health=unknown断言返回true，预期false，复现错误。GREEN：21组完整Software acceptance均通过，包括共享JS模型、Qt组件、导航和IME布局、49项控制Python检查及既有其他模块。

测试环境：远程授权构建区，bubblewrap无网络/宿主HOME/设备会话，源码只读。首次隔离环境缺Node，已只读绑定现有Node二进制；首轮完整检查因runtime目录UID不匹配有一项控制测试失败，修正测试隔离配置后21组全通过，未改生产代码来绕过测试。

独立审查无Critical/Important或阻塞Minor，认可合并；可选补充完整标签断言留作后续覆盖增强。初始修复f2c44fe的GitHub acceptance与map-gps通过（39119525093）。控制台补丁版本0.1.8用于版本化运行路径切换，其他插件运行版本不随源码副本变化。最终GitHub CI与本机部署记录另记。实体触屏、冷启动和真实新契约宿主不由本次软件测试代替。
