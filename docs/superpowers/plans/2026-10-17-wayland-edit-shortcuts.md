# Wayland浏览器编辑快捷键兼容修复

现有输入功能正式验收中的缺陷修复，沿用已授权方案inline实施。

## 已复现

生产v0.2.2：GTK/Qt Wayland/Qt XWayland九键、混输、剪贴板、合成手写均过；Chromium原生Wayland中文/混输正常，但Control+a/c实际追加ac，剪贴板3秒仍未改变。Fcitx5 5.1.22 Wayland v2源码forwardKeyDelegate未为虚拟组合键更新修饰状态。

Omarchy现有clipboard.lua使用Hyprland send_key_state down/up与50ms单次timer。只向独立测试窗口发送该方式，浏览器完整测试通过；只是候选路由实验，还未部署。

## 修复与约束

- 只替换Wayland前端四个Ctrl编辑快捷键，GTK/Qt直接Fcitx路径与中文提交保持。
- 使用Qt/C++、现有官方Omarchy/Hyprland接口；不改系统源文件，不引入后台服务或闲置轮询。
- 固定命令与键名白名单；读取当前窗口地址/PID、锁状态，核对最新Fcitx代次/敏感字段；Lua在compositor执行时再核对目标，显式绑定窗口。未知、失败或超时拒绝，不回退成裸字母。
- 依照官方显式down/up，释放由compositor一次性timer负责，避免后台进程终止留下按键。编辑快捷键串行保留短释放间隔；不影响普通输入/候选热路径。
- 先测试拒绝未知键/无窗口/锁屏/代次改变/非法地址/命令失败，再实现。远程完整9项CTest；本机隔离兼容与实际GTK/Qt/浏览器矩阵通过后版本化启用，旧二进制可单独恢复。
- 真实输入测试禁止向用户文档写入，临时应用PID/窗口/焦点每步核对；还原生产面板与剪贴板。

## 文件

tools/omarchy-touch-ime/src/hypr_shortcut.h：原生固定命令编排、输入验证、注入Runner便于隔离测试。
src/backend.cpp：Wayland前端路由及新的焦点再核对。
tests/test_bridge.cpp：复用已有测试二进制加入边界检查。
既有测试/版本QML/manifest按实际部署同步；新源仍tools权威。

## Review Focus

焦点切换与敏感字段是否漏过；参数可否变成任意命令；失败是否误回退为字母；down之后是否总有up；超时影响是否有界；隐藏是否出现新轮询。

## Ledger

Ruling: 接受低频剪贴板操作约70ms释放间隔，采用Omarchy已有50ms down/up模式；不将它放入普通文字输入或焦点事件路径。代价是快速连续编辑动作有有界延迟，需实测。

审查补充：独立审查指出当前窗口不能在编辑请求时才接纳为目标。已改为面板显示/焦点代次变化时异步捕获地址与PID；ticket/代次/owner变化使捕获失效，隐藏清空。编辑请求只接受保存的目标并再次核对当前窗口；新增A请求、B当前、Fcitx仍旧代次拒绝测试。权限判断提取可测函数覆盖旧代次、owner、失焦、敏感复制与允许粘贴、畸形状态。异步捕获只在面板可见且Wayland焦点变化时执行，不添加常驻轮询。

边界：Fcitx和compositor的焦点通知不是原子协议；不能承诺消除同一窗口内所有字段切换的IPC时序窗口。hyprctl返回ok表示初始脚本成功、释放定时器已安排，不是应用处理完毕或异步up完成的回执。接受上游官方实现的这项边界，实机以最终文本和剪贴板验收。

第一轮远程编译发现测试包含Qt头早于Fcitx导致宏冲突，已恢复Fcitx优先包含顺序；这轮不记通过。第二轮包含目标绑定补丁重新完整构建。

## 假密码字段新增缺陷

Chromium原生Wayland假密码框中，每次commit后Fcitx短暂focus-out/in；实测generation2→4、focused与sensitive恢复true但visible保持false，导致一字即收起。两次红测试复现，未触及真实密码。

修复仅对本面板敏感字段commit后100ms内的短暂失焦提供150ms外观暂留；已保存compositor目标必须有效。失焦权限立即撤销，恢复焦点后仍阻止全部输入直到同地址/PID确认；目标变化、未知、超时、NoOnScreenKeyboard和主动收起均隐藏，不把隐藏面板自动显示。暂留期间保留abc外观。独立审查指出异步校验期间文字输入提前开放，已同时在backend current门禁和对外focused状态拒绝，补充回归断言。

job03为未包含最后门禁修复的候选，不可部署。job04沿用job02的已验源码归档，仅上传4份变化文件，在远程按新清单全部校验文件hash并重新打包、完整隔离构建；不复用旧二进制。标准fetch仍校验新source manifest、产物hash、ABI及完整9项清单。
