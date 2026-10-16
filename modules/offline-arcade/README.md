# 离线街机与中文字体配置

将现有游戏库放在内置盘，通过RetroArch和FBNeo使用中文菜单、手柄和键盘；MAME作为兼容补充。用户不喜欢游戏画面的虚拟按键，配置片段明确关闭覆盖层，菜单仍可触屏点选。

这是已部署原型的可移植配置摘要，提供手工合并片段和复核说明，没有通用安装器。另一台机器需要先检查发行版软件源、显示环境、现有配置和字体；不得把本机的验证当成跨设备验收。

## 文件与使用

| 文件 | 用途 |
| --- | --- |
| `retroarch.cfg.fragment` | 已部署设置的关键子集，使用通用用户目录；合并到备份后的用户配置 |
| `60-workbench-cjk.conf` | Fontconfig中文界面匹配修正，放入用户的`~/.config/fontconfig/conf.d/` |
| `mame.ini.example` | MAME中文界面、输入与ROM目录示例，路径需要适配 |
| `flight-arcade.desktop.example` | 中文应用入口示例，确认后复制为用户applications目录内的`.desktop`文件 |
| `verification.json` | 本机验证范围及待验项，含测试环境限制 |

先备份目标配置，再逐项合并。不要用片段整体覆盖已有RetroArch配置。执行`fc-cache -f`刷新字体，并重开需要应用新字体的程序；不需要重启整机。所有软件继续由Omarchy或Arch软件包维护，核心在线更新关闭。

本机已通过现有Omarchy源安装`libretro-fbneo-git`、`retroarch-joypad-autoconfig-git`、`libretro-database-git`，Arch提供`retroarch`、`retroarch-assets-glui`、`retroarch-assets-ozone`和`mame`。使用前以目标机器的实际仓库为准。中文字体依赖已安装的`noto-fonts-cjk`，不能仅靠语言设置保证字形存在。

## 中文方框的原因

本机Omarchy的`50-omarchy.conf`将通用无衬线与衬线字体强匹配到Liberation。RetroArch的FreeType后端在收到名字含`fallback`的字体路径时，会使用Fontconfig选择字体，而不直接加载该文件。结果中文界面选到了没有中文字形的Liberation Sans；仅补一个中文字体文件或设置菜单字体路径没有解决这一匹配问题。

用户规则在Omarchy规则之后为Liberation Sans和Serif加入Noto CJK优先项，并为中文等宽请求选择Noto Sans Mono CJK SC。英文等宽仍使用原Nerd Font，Emoji保留。此规则会改变通用界面字体选择，部署前应比较`fc-match 'sans-serif:lang=zh-cn'`、`serif:lang=zh-cn`、`monospace:lang=zh-cn`、`monospace:lang=en`与`Noto Color Emoji`。

字体修复后，本机RetroArch中文主菜单、快捷菜单和通知已有视觉验证。桌面时钟的`Qt.formatDateTime`格式字串也会产生英文星期名；本机使用官方clock插件设置`format: MM月dd日 HH:mm`与`formatAlt: yyyy年MM月dd日 HH:mm`，无需修改打包QML或另造时钟插件。

## 操作与金手指

手柄Back投币、Start开始，方向及动作键依游戏映射；Start加Back打开菜单。键盘配置为5投币、1开始、方向键移动、Z/X/A/S/Q/W动作、F1菜单、F2存档、F4读档、P暂停、Esc两次退出。实体键盘尚待接入验证。

FBNeo金手指使用[上游作弊库](https://github.com/finalburnneo/FBNeo-cheats)，在快捷菜单的核心选项里启用。原生作弊库与RetroArch通用作弊功能的目录和入口不同。本机安装了上游数据，并将常见显示标签改为中文，地址和值保持原样；模板不包含第三方作弊数据。所有金手指默认关闭，具体效果需按游戏和版本实玩确认。游戏内容语言由ROM版本决定。

游戏ZIP保持原短名，不批量解压或按“原版/克隆版”名称删除。[父ROM、BIOS和CHD](https://docs.mamedev.org/usingmame/aboutromsets.html)可能是运行依赖。迁移时先核对容量，再逐文件校验；原盘保留备份，存档放内置盘并另行备份。

## 稳定性和验证

本机RetroArch 1.22.2的独立Qt桌面设置窗口曾在`ViewsPage::widget → StringLineEdit::StringLineEdit → QString`出现无效指针崩溃。现有配置关闭备用桌面菜单、Qt companion启动及F5入口，日常使用正常中文菜单。这是避开有缺陷入口的措施，未修复上游二进制，也未证明无效指针的最初来源。

六款代表游戏通过MAME ROM审计，以及FBNeo的180帧启动/自动存档检查。无窗口测试必须将输入驱动改为SDL2；`video=null`搭配Wayland输入会在初始化阶段崩溃，这是测试配置限制。日常配置使用Wayland输入和OpenGL画面。恐龙快打另外在隔离网络命名空间中通过实际图形启动、存档和读档，用户已确认手柄实玩与无虚拟按键体验。

## 恢复与维护

撤回字体修正时移除自己新增的用户规则并运行`fc-cache -f`，然后重开应用。恢复模拟器时只恢复此次修改的键，保留期间新增设置。时钟只恢复clock的两个格式字段。升级前备份普通存档、即时存档与核心版本，升级后复测代表游戏；跨核心或跨版本的即时存档不保证兼容。

参考：[FBNeo核心说明](https://docs.libretro.com/library/fbneo/)、[RetroArch输入映射](https://docs.libretro.com/guides/input-and-controls/)、[FreeType字体选择实现](https://github.com/libretro/RetroArch/blob/v1.22.2/gfx/drivers_font_renderer/freetype.c)。第三方软件和字体沿用各自上游许可；仓库整体许可尚未选定。

## 2026-10-17 目录修复

[目录维护工具](catalog/README.md)：666主要游戏按玩法分类；1253个版本有中文标签和截图路径，389其他版本独立收纳，198兼容待确认。212同名拷贝及45资源项不重复作为游戏显示，原ROM保留。606款主要游戏找到INI/DAT金手指，恐龙快打无限时间RAM开关对照通过；60款尚无匹配代码，其余效果未逐项验。原生菜单的截图参数按RetroArch1.22.2枚举核对，完整菜单视觉/实体触屏待反馈。

金手指入口：加载游戏后快捷菜单→核心选项/选项→Cheats/金手指，默认关闭。FBNeo专用override隐藏通用空金手指菜单。截图/ROM/私人报告不随源码分发；部分改版复用基础版图片。
