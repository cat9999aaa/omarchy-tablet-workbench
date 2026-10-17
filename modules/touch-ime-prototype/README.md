# 本机 Omarchy 触屏输入法 v0.2.1

仅用于本机 Omarchy 4.0.4 / Fcitx5 / Quickshell。右侧独立面板，仅P1或应用入口手动呼出，点输入框不会自动弹出。失焦仍隐藏。

## 输入与操作

- 九键拼音：点 ABC/DEF 等字母组，再点紧贴键区上方的中文候选。组合栏中的64426是拼音按键编码，不是已输入的数字。独立123页才用于直接输入数字。
- 大退格位于九键右上；候选翻页、英文数字符号混输、离线单字手写保留。
- 下方编辑栏提供全选、剪切、复制、粘贴和左右光标。先结束拼音组合再操作；复制需先选中文字。敏感字段禁用全选/复制/剪切，粘贴仍可用。应用自身是否支持这些快捷键取决于应用。
- 模式切换、语音、设置、收起集中下方。固定问候快捷短语已移除；自定义短语与个人词库仍可在设置中管理，未删除用户词库。
- 语音为本机PipeWire录音和Voxtype/SenseVoice离线识别，结果先预览，再点输入文字。修改预览只支持末尾编辑。
- P1只控制这套桌面输入法，旧wvkbd不会自动回退。旧桌面入口和原型已归档，兼容旧隐藏调用的名称不再启动旧键盘。
- 锁屏键盘、首次开机LUKS触屏键盘独立保留；P2听写/P3授权保持原用途。

## 构建与验证

```bash
cmake -S tools/omarchy-touch-ime -B tools/omarchy-touch-ime/build -G Ninja
cmake --build tools/omarchy-touch-ime/build -j2
ctest --test-dir tools/omarchy-touch-ime/build --output-on-failure
omarchy plugin validate tools/omarchy-touch-ime
```

真实Qt离屏布局、Rime九键/全拼、Fcitx焦点与快捷键、敏感字段、手写、词库等9项测试。测试不等同实体手感验收。

## 部署与恢复

源码权威为本目录；部署插件 `~/.config/omarchy/plugins/pcadmin.touchime` 使用 `qml/release-0.2.1/TouchIme.qml`，避免旧QML缓存。焦点桥配置 `~/.local/share/fcitx5/addon/omtbridge.conf` 指向本目录构建库。更新库后需重启用户omarchy-fcitx5服务。

本次备份 `backups/touch-ime-20261017-reach`：旧QML/C++/入口及清单、retired-keyboard/retired-wvkbd。旧方案不在工作入口中；恢复须明确重新部署，不能只恢复旧清单造成版本混用。
用户词库 `~/.local/share/pcadmin-touch-ime/rime` 和短语配置保持原样，未覆盖。临时录音使用运行时目录，结束后删除。

设计参考：[Android官方触控目标说明](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views)。Qt逻辑像素不等于Android dp，实体触屏手感仍需体验后调整。
