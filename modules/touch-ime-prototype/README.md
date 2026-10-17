# 本机 Omarchy 触屏输入法 v0.2.3

仅用于本机 Omarchy 4.0.4 / Fcitx5 / Quickshell。右侧独立面板，仅P1或应用入口手动呼出，点输入框不会自动弹出。真正失焦仍隐藏；Chromium密码框提交后同窗口的短暂焦点重置可保留面板，期间输入禁用。

## 输入与操作

- 九键拼音：点 ABC/DEF 等字母组，再点紧贴键区上方的中文候选。组合栏中的64426是拼音按键编码，不是已输入的数字。独立123页才用于直接输入数字。
- 大退格位于九键右上；候选翻页、英文数字符号混输、离线单字手写保留。
- 下方编辑栏提供全选、剪切、复制、粘贴和左右光标。先结束拼音组合再操作；复制需先选中文字。敏感字段禁用全选/复制/剪切，粘贴仍可用。应用自身是否支持这些快捷键取决于应用。
- 模式切换、语音、设置、收起集中下方。固定问候快捷短语已移除；自定义短语与个人词库仍可在设置中管理，未删除用户词库。
- 语音为本机PipeWire录音和Voxtype/SenseVoice离线识别，结果先预览，再点输入文字。修改预览只支持末尾编辑。
- P1只控制这套桌面输入法，旧wvkbd不会自动回退。旧桌面入口和原型已归档，兼容旧隐藏调用的名称不再启动旧键盘。
- 锁屏键盘、首次开机LUKS触屏键盘独立保留；P2听写/P3授权保持原用途。

## 性能改造

焦点改为Fcitx事件通知，启动和重连异步读取初始状态；稳定空闲不再每100ms查询。唯一服务所有者与独立UI代次隔离旧请求。详细协议、测量边界及恢复见[事件驱动说明](docs/v022-event-driven.md)。此版本仍依赖Fcitx，原生Wayland后端尚未实现。

## 构建与验证

优先使用本项目[远程构建工具](../remote-build/README.md)，把编译和完整测试交给已授权构建主机。下面命令仅说明构建接口：

```bash
cmake -S tools/omarchy-touch-ime -B tools/omarchy-touch-ime/build -G Ninja
cmake --build tools/omarchy-touch-ime/build -j2
ctest --test-dir tools/omarchy-touch-ime/build --output-on-failure
omarchy plugin validate tools/omarchy-touch-ime
```

真实Qt离屏布局、Rime九键/全拼、Fcitx焦点与快捷键、敏感字段、手写、词库等9项测试。测试不等同实体手感验收。

## 部署与恢复

源码权威为本目录；部署插件 `~/.config/omarchy/plugins/pcadmin.touchime` 使用 `qml/release-0.2.3/TouchIme.qml`，避免旧QML缓存。焦点桥配置 `~/.local/share/fcitx5/addon/omtbridge.conf` 指向本目录构建库。本次仅启用独立的`build/releases/0.2.3/omt-backend`及同目录手写程序，未重启Fcitx或替换桥库。旧`build/omt-backend`及0.2.2入口保留；之后修改桥库才需要单独安排服务重启。

本次备份 `backups/touch-ime-20261017-reach`：旧QML/C++/入口及清单、retired-keyboard/retired-wvkbd。旧方案不在工作入口中；恢复须明确重新部署，不能只恢复旧清单造成版本混用。
用户词库 `~/.local/share/pcadmin-touch-ime/rime` 和短语配置保持原样，未覆盖。临时录音使用运行时目录，结束后删除。

设计参考：[Android官方触控目标说明](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views)。Qt逻辑像素不等于Android dp，实体触屏手感仍需体验后调整。

## v0.2.3 浏览器兼容验收

Fcitx Wayland前端的四个Ctrl编辑组合键使用本机Omarchy已有的Hyprland显式按下/释放方式，固定键白名单、焦点代次、敏感状态、锁屏及窗口地址/PID共同检查。捕获目标与发送目标不一致就拒绝，失败不退回裸字母。普通文字和其他前端仍走原输入链路，无闲置轮询。

Chromium密码框首字提交时会暂时重置输入焦点。仅本面板敏感文字提交后的短暂变化允许150ms外观暂留；同窗口核验前界面和后台输入都禁用。不同窗口、超时或主动收起会隐藏，已隐藏面板不自动弹出。

远程9组、本机4项隔离兼容通过；实际QML到GTK、Qt Wayland、Qt XWayland及Chromium的九键、混输、剪贴板、合成手写、收起均通过。Chromium假密码字段连续输入、敏感复制/剪切/全选禁用、显式粘贴及收起通过。这里没有使用真实密码，也不是手指触感或个人手写识别率验收。

恢复0.2.2：恢复本次备份中的原manifest，按官方插件入口重新扫描/启用；旧QML与旧build/omt-backend保留，个人词库不回滚。发布时先在插件目录外准备完整文件再一次性切换入口，避免复制过程反复触发上游热加载。
