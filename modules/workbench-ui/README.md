# 工作台共享触屏基础

权威来源：本机管理项目tools/workbench-ui；归工作台架构与共享UI维护。纯QML/JavaScript，不启动服务、不调用设备控制。颜色/字体由使用方传入Omarchy语义主题；TouchButton保留至少48逻辑像素点击区域，多行内容增长时不裁字；PanelHeader保留关闭入口。

Layout.panelSize只依赖屏幕尺寸，不依赖当前页内容。State.fieldState区分未知/不可用/过期和真实关闭；输入缺少有效时间时不能作为实际状态。显式health仅observed可以显示为已知；unknown/error/stale/unavailable或未知状态一律不显示实际值，非有限数值也不可用。未带health的旧字段仍沿时间/actual规则兼容。网络等没有逐字段时间的适配层须另外明确观察时间来源。

插件发行时将本目录的六份运行文件复制到发行目录Workbench/，与对应插件同版本切换与恢复。副本只由构建/发布生成，不单独编辑。共享基础不触及网络、解锁或电源控制器。

验证：node test-model.cjs；QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software /usr/lib/qt6/bin/qmltestrunner -input tests。真实插件渲染与触屏手感另验。

PanelBody固定标题和收起按钮，正文内部滚动；窗口低矮或正文很长时不让标题随正文滚走。

Theme.resolve(options) 是内部 schemaVersion=1 样式接口，只组合显式颜色、字体和尺寸；
未知版本回兼容默认，缩放限定 0.75–2，触摸高度至少48，typed QML color保留alpha。
PanelBody、PanelHeader、TouchButton 的 themeTokens 默认为null；旧显式属性可覆盖样式默认。
热换色只更新绑定，不能重建按钮或改变状态来源。

在仓库根运行 `python3 scripts/workbench-ui/sync.py --write` 生成四份副本；
`--check`只读检查。同步前检查四个固定目标，链接或未知文件会阻止整批写入，
不会删除未知文件。同步器只用于源码生成，不是生产安装器。
