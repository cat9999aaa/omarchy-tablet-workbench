# 0.2.6 手动键盘与短暂失焦

用户确认的行为：同一个前台窗口的输入框短暂失焦时保留手动打开的键盘，立即禁止输入；有效焦点恢复后可以继续。切换窗口、锁屏、主动收起关闭面板，恢复焦点不自动打开。

QML通过Omarchy已有的ToplevelManager API跟踪窗口对象身份，以私有stdin传递surface epoch；Hyprland空activewindowv2事件也主动关闭，覆盖输入框已经失焦后的锁屏。没有新增闲置轮询。

后端将显示许可与输入许可分离。surface变更隐藏面板、废弃操作与旧UI generation，并等待新的Fcitx通知或切换后的State回读。FocusLink revision拒绝此前在途的查询。继续保留桥端focus/generation校验、NoOnScreenKeyboard及服务owner变化门禁。窗口身份没有与Fcitx context建立强映射。

临时失焦仍沿用现有的预编辑、手写和语音取消语义；本修复不承诺保留未提交草稿。

验证包括旧生产二进制上的预期失败、远程完整回归、本机隔离ABI检查和临时GTK输入框。实体触屏、Paseo持续使用和锁屏解锁序列单独验收，不由软件测试推定。

发布使用独立版本目录，保留0.2.5界面及0.2.4后端；通过恢复上一manifest入口回退，仅重载本插件。
