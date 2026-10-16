# 飞机游戏厅目录维护

本机离线街机会员的子工具。按原始ROM目录、已有中文列表、FBNeo父子关系和CatVer分类生成RetroArch原生列表。
只改用户列表、配置和缩略图链接，原ROM及BIOS文件保留；未知兼容性不标作可玩。

2026-10-17：日常入口666款，地区/修订版本389款、兼容待验198款；45种依赖/非游戏资源不显示为游戏，212份同名跨合集拷贝不重复展示。
1253个游戏短名均有中文显示标签和截图路径。中文名优先采用用户原合集，补充常用显示译名；旧短名使用明确别名映射，不据别名推断ROM兼容。
部分旧版/改版复用同族基础版本截图。606款主要游戏找到同名INI或DAT金手指来源；60款尚无匹配来源。
“恐龙快打”无限时间已通过关闭→开启→关闭的实际RAM对照；不是全部606款效果验收。

## 使用

```sh
python3 -m unittest discover -s modules/offline-arcade/catalog -p 'test_*.py'
python3 modules/offline-arcade/catalog/catalog.py --metadata FBNEO_ARCADE_XML --catver CATVER_INI --report REPORT_JSON
# 关闭正在运行的RetroArch，复核预览，再应用；备份目录必须全新。
python3 modules/offline-arcade/catalog/catalog.py --metadata FBNEO_ARCADE_XML --catver CATVER_INI --report REPORT_JSON --apply --backup NEW_BACKUP_DIRECTORY
```

元数据、ROM目录与完整结果保留本机；本仓库只同步工具、维护说明和脱敏验证摘要。
缺图补充位于`~/.local/share/pcadmin-arcade/assets/snap/`，来源清单为任务证据`art-downloads.json`。
旧列表备份以第一次`backups/arcade-catalog-2026-10-17`为原始恢复点。后续带后缀目录为各轮配置修正前快照。

缩略图参数必须区分全局与列表枚举：RetroArch1.22.2列表2截图/3标题，全局1截图/2标题。
源代码依据：上游`gfx/gfx_thumbnail_path.c`、`playlist.h`。不要将其他列表值或默认封面值套入。

FBNeo金手指入口为加载游戏后“快捷菜单→核心选项/选项→Cheats/金手指”，不是通用“金手指”。
本机核心override隐藏容易混淆的通用空菜单，原生核心金手指入口保留。该override备份见首次备份中的fbneo-override，回滚时一并恢复。
用户存档及金手指默认开关未改。启动失败按ROM/核心版本另查，不能改原ROM文件名来匹配中文标签。

恢复：关闭RetroArch，移走本工具生成的数字前缀列表，再将首次备份的playlists恢复；只恢复retroarch.cfg相关缩略图字段，保留其他任务后续修改。恢复或移除专用FBNeo override。
缩略图是可重建链接，删除生成列表对应图片目录即可，不删除链接指向的源图和ROM。

## 来源

- [RetroArch原生列表与缩略图](https://docs.libretro.com/guides/roms-playlists-thumbnails/)
- [FBNeo核心/金手指说明](https://docs.libretro.com/library/fbneo/)
- [FBNeo上游DAT目录](https://github.com/libretro/FBNeo/tree/master/dats)
- [CatVer作者资源](https://github.com/AntoPISA/MAME_SupportFiles)
- [Libretro FBNeo缩略图](https://github.com/libretro-thumbnails/FBNeo_-_Arcade_Games)
- [FBNeo金手指库](https://github.com/finalburnneo/FBNeo-cheats)
