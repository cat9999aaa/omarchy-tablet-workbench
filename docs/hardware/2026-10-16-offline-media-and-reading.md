# 飞机影音、电子书与长期游戏

本机已安装：Celluloid 0.30-2（Arch官方）、Quod Libet 4.7.1-3（Arch官方）、KOReader 2026.07.1-2（AUR koreader-bin）。随Omarchy/Arch/yay维护，不使用应用内更新覆盖发行版文件，不做自定义内容或菜单翻译。系统原有中文环境与应用自带译文保留。

## 日常使用

- 电影：应用菜单搜索Celluloid，点“打开”选择本地视频。目录为`~/Videos/Flight`。窗口默认最大化、保留窗口按钮与原生播放控制。MP4/MKV及字幕需提前准备；具体影片与字幕兼容性逐文件确认。
- 音乐：搜索Quod Libet，添加`~/Music/Flight`中的本地音乐。保留原生播放、进度条和曲库界面，默认最大化。首次使用可从Music菜单打开插件列表；部分附加功能依赖额外软件，并非全部内置插件都已启用或验收。
- 电子书：搜索KOReader，起始目录设为`~/Books/Flight`。使用原生点击翻页/菜单和字号设置；无须实体键盘来阅读。EPUB已经用本地生成测试书打开，具体PDF和个人书库尚未逐本验收。
- PDF也可继续使用已有Evince。原有“飞机游戏厅”及手柄设置不改。

测试样本只用于验收，不等于已替用户准备电影、歌曲或书籍。出发前准备文件，并断网试播、核对字幕、耳机和阅读进度。

## 自己写插件

三款最终选型都有插件机制，已在本机验证，不把“开源可改源码”等同插件支持。

| 应用 | 编写方式与入口 | 本机验证 |
| --- | --- | --- |
| Celluloid / mpv | Lua；`~/.config/celluloid/scripts/`，参数在`~/.config/celluloid/script-opts/` | 用户脚本实际加载并产生标记；本地视频Playing、位置推进、可暂停/定位 |
| Quod Libet | Python；`~/.config/quodlibet/plugins/`，通过Music→Plugins刷新/管理 | 原生ModuleScanner导入自定义EventPlugin，无加载失败；本地MP3状态playing |
| KOReader | Lua；`~/.config/koreader/plugins/名称.koplugin/`内`_meta.lua`与`main.lua` | 自定义用户插件在真实KOReader启动中加载并产生标记 |

测试插件已清理，未部署第三方插件。改插件只动用户目录；不要直接改`/usr/lib`和发行版应用文件。复杂插件需要按其依赖和API另做验证。

- [mpv脚本与API手册](https://mpv.io/manual/stable/)
- [Celluloid项目](https://github.com/celluloid-player/celluloid)
- [Quod Libet插件开发](https://quodlibet.readthedocs.io/en/latest/development/plugins.html)
- [KOReader插件加载接口](https://koreader.rocks/doc/modules/pluginloader.html)

Rhythmbox曾作为候选安装，但当前本机libpeas 1.38.1-1缺少Python加载器，实际加载失败。已移除Rhythmbox并换用Quod Libet，没有为此升级全系统或混装其他发行版依赖。

## 触屏与验证边界

通过用户Hyprland配置为三款主应用设maximize，保留底栏；Celluloid和Quod Libet实际窗口已读回1512×805逻辑尺寸、最大化状态1。Hyprland配置重载无错误。KOReader原生支持触摸阅读和手势，但此轮未获得用户实际手指点按/翻页反馈；不将接口和启动检查记为实体触屏验收。

本地测试视频能播放；音乐为生成的静音MP3，验证解码与播放状态，不证明耳机音质。电子书为本地生成英文测试EPUB，不包含下载书籍或内容翻译。未改变全机缩放、语言、网络或输入法。

修改前备份保存在本机`backups/flight-media-2026-10-16`。恢复时撤销hyprland.lua中pcadmin触屏影音规则、还原对应dconf配置及KOReader设置；只恢复有关字段，保留其他任务后续修改。

## 养老游戏候选

用户已明确触屏加现有手柄都可，优先中文种田或RPG。以下只调研，未购买、安装或在本机验收。

| 候选 | 适合的玩法 | 已核实/仍需验证 |
| --- | --- | --- |
| 星露谷物语 Stardew Valley | 长期种田、养动物、社交、下矿战斗 | 官方商店列简体中文与Linux；官方FAQ确认PC Xbox360/One手柄。首选手柄，纯触屏未验 |
| 帕夏灵田 Roots of Pacha | 偏放松的种田、驯养、发展部落 | 官方商店列简繁中文、Linux与单人模式；本机性能与手柄实际操作待验 |
| 守墓人 Graveyard Keeper | 经营、采集与制作，偏黑色幽默 | 官方商店列简中/Linux；流程较复杂，不优先作为最轻松的养老选择；本机手柄与性能未验 |

优先星露谷；更看重轻松种田则优先帕夏灵田。电脑版和手机版触屏交互有差异，不能将Android触屏体验套到Linux版。飞机上使用前应实际断网启动、存读档；商店兼容标签不能替代本机验收。

- [星露谷官方商店](https://store.steampowered.com/app/413150/Stardew_Valley/?l=schinese)
- [星露谷官方FAQ/手柄](https://www.stardewvalley.net/faq/)
- [帕夏灵田官方商店](https://store.steampowered.com/app/1245560/Roots_of_Pacha/?l=schinese)
- [守墓人官方商店](https://store.steampowered.com/app/599140/Graveyard_Keeper/?l=schinese)
