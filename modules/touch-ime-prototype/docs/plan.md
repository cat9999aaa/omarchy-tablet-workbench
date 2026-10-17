# Omarchy 触屏输入法 Implementation Plan

> 执行方式：superpowers:executing-plans，本聊天内执行。用户已要求直接开干。

**Goal:** 在本机完成独立右侧九宫格/候选/离线语音输入闭环。

**Architecture:** 原生Fcitx5焦点桥接模块、独立Qt/Rime后端、Omarchy QML overlay。桥接负责输入目标，后端负责组字和录音，界面负责显示与触屏。

**Tech Stack:** C++20、Qt6 Core/DBus、librime、Fcitx5 Core/DBus、Quickshell QML、PipeWire、Voxtype。

**Spec:** spec.md

## Global Constraints

- 基线版本、用户范围、密码回退与官方插件机制遵循spec.md。
- v0.1保留旧P1；用户继续要求完成成果后，v0.1.1以自动测试通过为依据接入P1，新服务不可用自动回退；P2/P3与锁屏不改。
- 不记录输入文本或音频到持久日志；不新加软件源。

## Review Focus

- 输入对象切换时旧候选/语音结果不得提交。
- 输入对象销毁/失焦时不得使用悬空指针。
- 用户收起后同一输入焦点不得重复弹出。
- 敏感字段禁止学习和语音。
- 依赖不可用/后端崩溃时释放面板，现有输入路径保留。

## Tasks

1. [x] 写Rime九键/全拼与焦点代次测试，先观察失败；实现最小引擎与代次检查，验证通过。
2. [x] 实现Fcitx5模块，编译并用独立D-Bus/合成输入上下文验证失焦、销毁、陈旧代次与提交。
3. [x] 实现后端JSON协议、焦点变更和语音预览；测试模式切换、退格、候选选择和敏感限制。
4. [x] 实现QML原生面板、内部候选、自动/手动弹收；验证QML加载和独占区域释放。
5. [x] 使用官方插件机制部署试用入口，验证合成编辑器与触屏；记录缺陷、回退和后续手写。

## Ledger

- 2026-10-16：本机已有编译库，不需要安装新依赖。桥接采用Fcitx模块而非替换现有UI：虚拟键盘的中文组字在独立Rime会话内进行，因此候选只在本面板显示；实体键盘继续现有Fcitx引擎。

- Task 1: 缺失引擎/配置失败→标准Rime默认配置与隔离用户数据修复→T9/full/reset测试通过。
- Task 2: 实际 Fcitx context 测试发现 PasswordOrSensitive 使用 test() 要求两个位同时存在；改为任一位命中后，密码、普通能力变化、失焦、销毁测试通过。测试使用私有会话总线与合成键盘/输入框。
- Task 3: 后端隔离测试通过组字提交、手动收起保持、陈旧目标/候选拒绝、语音先预览/末尾编辑/显式提交、录音拒绝SIGTERM时超时清理及密码限制。
- Task 4: QML加载通过；原生右侧440x829，收起释放区域；官方插件验证通过。用户触屏验收仍在等待。
- Ruling: 编译标准从C++17调整到C++20 — 本机Fcitx5头文件实际要求ranges/span/concepts — 代价是旧编译器不能直接构建。
- Ruling: 本机已安装开发库但缺CMake，按Omarchy官方命令补装cmake/ninja — P3认证后安装成功，无新增源 — 代价约104MiB磁盘。
- Ruling: 独立面板使用已安装本项目的明确路径 — Quickshell对外部resolvedUrl返回blackhole — 代价是搬迁项目后需要调整入口路径。
- Ruling: 候选每页3项并提供上一页/下一页 — 给下半部按键与语音预览留空间，减少长矩形按钮 — 代价是翻页次数增多。
- Final review: 独立只读评审 ime_review，未发现Critical；3项Important均已修复并回归（停止录音超时、候选翻页、能力变化不重新弹出）。
- Final: minor (deferred): 长语音预览不能滚动查看全部；首版用短句，后续补可滚动预览。
- 用户追加熄屏任务继续需求已记录battery-system.json，沿用Omarchy原生DPMS方案，未改电源配置。

- Task 5: 用户明确委托全部可自动执行测试；真实QML按钮处理→backend→原生Fcitx→独立GTK Wayland编辑器输入“你好”、翻页、收起释放层面验证通过。用户手指触感不能由自动测试代替，保留未验证。
- Final verification: CMake构建成功；CTest 3/3通过；真实离线SenseVoice公开中文音频2.54秒通过；部署QML与源码一致；Omarchy插件验证通过；Hyprland configerrors为空。
- Power verification: 官方allow-idle已恢复；缩短时限的自动锁屏/DPMS测试35次连续心跳通过，最大间隔1.34秒；已恢复150秒屏保/300秒锁屏，当前锁屏且DPMS关闭。原生亮屏命令通过，触屏唤醒未实测。
- No Git integration: 项目无Git仓库，源码按用户批准的本机项目保留并已登记启明会员，不擅自建立仓库/发布/删除工作目录。

- Follow-up v0.1.1：用户“明天睡醒看到成果”，继续按已批准交互收尾；P1新入口带旧键盘互斥/失败回退/锁屏不打开桌面键盘，3项控制测试通过；物理按键手指未重测。
- Follow-up修复：发现部署的旧QML在前一轮布局编辑中丢失语音预览组件，恢复为独立VoicePreview并加短句/长句滚动测试；长预览Minor已解决。
- Follow-up布局：字母改三行QWERTY，按键加轮廓；离屏实际渲染测试覆盖带长语音的九键/全拼/ABC/数字/符号5种布局，无溢出。
- Ruling: 部署采用qml/release-0.1.1版本化URL — 原生插件重新加载后仍命中旧QML组件缓存，不能在锁屏时重启整个shell — 代价是每次版本保留一份小型部署目录，后续按维护周期清理。
- Final verification v0.1.1：CTest 6/6通过，官方manifest验证通过，运行时ready()=true确认新QML已加载，Hyprland configerrors为空；当前会话锁定、DPMS关闭且idle启用。
