# 地图中文入口验收 · 2026-10-17

Marble Maps26.08.0-4 / Kirigami6.29.0-1 / Qt6.11.2。现有GPS插件二进制不变，新增启动器0.1.1。

- 当前版本复现：中文区域环境中SearchField初始占位仍为Search…；稍后同上下文qsTranslate返回搜索…。说明翻译存在，但初始绑定未得到它。
- 同一组件只增加进程专用LD_PRELOAD=/usr/lib/libKirigami.so.6后，两个行为测试均通过；报告4项包含初始化/清理。这是兼容处理的实验证据，不声称定位了上游具体C++缺陷。
- 启动器原4项加新3项：先缺失函数失败，最小实现后远程隔离7/7通过。输入环境不变、保留原预加载值、空格/冒号去重、依赖缺失明确失败。
- 本机真实地图窗口截图确认搜索栏“搜索…”，地图与私有GPS插件正常加载，GPS服务前后inactive；没有读取真实位置。
- 用户地图入口已切至版本目录0.1.1，--check通过；0.1.0保留。回退只恢复原用户入口，不改系统库、Qt全局环境或GPS服务。
- 真实卫星fix、地图定位居中、底图地名语言、手指操作和长期稳定性仍待验。

上游依据：[Marble入口](https://github.com/KDE/marble/blob/v26.08.0/src/apps/marble-maps/main.cpp)、[Kirigami SearchField](https://github.com/KDE/kirigami/blob/v6.29.0/src/controls/SearchField.qml)。没有复制上游实现；仅复用系统包现有库。

私有截图和运行日志留在本机；公开测试只使用临时库文件和人工组件，不包含定位或个人数据。
