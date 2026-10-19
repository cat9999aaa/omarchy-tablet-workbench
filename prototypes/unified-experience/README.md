# DASHEN // OVERDRIVE · U1 原生体验原型

独立Qt/QML原型，所有状态均为演示数据。没有设备控制、真实窗口操作、录音、摄像头、模型推理或网络连接；没有安装到生产Shell。示例温度、窗口和锁屏时间均不是实测。

## 查看

从仓库根，在已有Qt6（Quick/Controls/Layouts/SVG）和中文字体的环境运行：

```sh
/usr/lib/qt6/bin/qml prototypes/unified-experience/Main.qml
```

若发行版提供`qml6`或`qml`，使用其对应Qt6入口；不要为预览修改系统默认Qt或安装另一套桌面。点击顶部“退出预览”或关闭窗口即可退出，无后台服务；窄屏工具栏自动换为两行。

顶部工具栏切换指挥台/桌面/窗口/锁屏视觉预览、常规/过期/离线/缺硬件示例和深浅配色。工具栏是原型评审工具，不是最终桌面入口。侧栏六分类固定，窄屏通过“分类”展开；底部指挥台可收起/打开，MAGI只展示建议示例。

工作页的隐藏/恢复、关闭窗口/退出应用仅改变内存中的虚构对象；切换数据场景可重置。锁屏预览无密码框，不是真实锁屏。会议和感知只显示规划说明。

## 复用与维护

直接导入`../../modules/workbench-ui`，使用共享Theme/StyledText/TouchButton/ActionGrid/PanelBody。PreviewTokens仅集中原型候选值，不改生产主题；业务页不复制UI库。原创SVG无第三方图形/字体嵌入。源码与原创资产GPL-3.0-only。

状态模型只处理白名单演示事件。替换目标期间取消旧按压；失效观测保留示例值与过期标签。导航/界面不承担设备I/O。前端记账见[共享清单](../../docs/frontend-style-catalog.md)。

## 软件核验

模型：`node prototypes/unified-experience/tests/test_model.cjs`。

Qt交互：`QT_QUICK_BACKEND=software /usr/lib/qt6/bin/qmltestrunner -input prototypes/unified-experience/tests/tst_experience.qml -platform offscreen`。

截图夹具`tst_capture.qml`输出到测试沙箱的`/evidence`，需由测试调度器绑定可写目录；不得为运行测试在宿主根目录创建目录。运行该夹具生成四场景横竖屏及MAGI/窄屏及浅色桌面/指挥台/锁屏共13张图。测试环境无网络、真实桌面总线或设备权限；截图不含用户工作内容。

批量核验使用已授权远程环境；本机只预览。具体证据、审查和未验范围见[交付报告](../../docs/validation/2026-10-19-unified-experience-u1.md)。
