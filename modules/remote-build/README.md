# 输入法远程构建工具 0.1.0

把当前输入法的 C++ / Qt / Rime / 手写模块编译和九项 CTest 交给已授权的 Omarchy / Arch 远程主机。平板只生成源码快照、校验回传文件和做隔离兼容检查。工具不安装产物，不重启输入法，也不会在远程不可达时退回本机编译。

## 前置条件

两端已有 Python、OpenSSH；本机 pacman 能读取目标依赖版本。远程已有 GCC、Qt6、Fcitx5、Python测试依赖、Bubblewrap、tmux、pacman、curl、GnuPG和bsdtar。先核对关键ABI版本。构建所缺的CMake、Ninja、Rime依赖从远程现有发行版仓库解析，缓存到专用目录并验证Arch签名与撤销列表；不全局安装、不自动更新系统或添加软件源。

SSH连接配置保存在本机，不放进本模块。使用已有的密钥认证别名与已批准的绝对构建根；根目录必须预先存在 `build-scope.json` 范围标记。工具不会自行把任意远程目录认作已授权目录。

## 四步操作

下面的 `build-host`、`/home/builder/project-build` 是占位值，使用前换成已授权配置。

```sh
python client.py prepare ../touch-ime-prototype /tmp/ime-input-001
python client.py submit --host build-host --root /home/builder/project-build --job ime-001 --input /tmp/ime-input-001
python client.py status --host build-host --root /home/builder/project-build --job ime-001
python client.py fetch --host build-host --root /home/builder/project-build --job ime-001 --input /tmp/ime-input-001 --output /tmp/ime-result-001
```

每次使用新的job和输出目录。失败任务原样保留供诊断，修正后用新job，避免旧成功产物冒充新结果。`submitted`只是任务已交给tmux；只有最终 `passed` 表示九项测试实际通过。`download_verified`表示源码身份、目标ABI、测试报告和归档hash已核对，**不表示安装或触屏验收通过**。

任务在独立tmux socket `pcadmin-build`下运行。断开SSH后继续执行；主机关机或重启会中断。没有自动队列重启恢复，发现只有progress而没有result时应核对该job的tmux会话与runner.log，不把旧progress视为进程仍存活。

## 隔离与产物

- 白名单包含源码、测试、五份固定Rime配置、第三方模型和许可；排除build、用户数据库、私人词典、短语导出和链接。
- 每个job独立源码、HOME/runtime和新覆盖层。只有build、私有HOME/runtime可写；宿主状态和日志不向编译进程开放。编译/测试没有网络、真实桌面总线或硬件访问。
- `/usr`来自只读宿主加已验签包。它是有版本记录的受控构建环境，**不是完整干净chroot，也不承诺位级可复现**。精确包清单和hash随结果保存；系统升级后必须重新验证。
- 两并发、Debug断言开启、禁用针对构建机CPU的本机优化。返回产物用于兼容验证，不是正式优化发布包。
- 九项CTest必须名称齐全、实际执行、无失败/跳过，才生成passed。结果包含源码逐文件hash、依赖、构建日志、JUnit和产物hash。
- `fetch`不自动解压或运行文件。部署需要独立的备份、安装和真实输入验收步骤。

远程目录结构：`jobs/<id>/`保存本次输入、runner副本、只读source与可写build、日志、覆盖层、结果和产物；`toolchain/ime-v1/`保存签名包缓存和Arch公钥转换文件。仅缓存复用，覆盖层不叠加旧版本残留文件。现有账号对其他目录可能仍有权限；本工具的操作约束不等同于隔离的SSH账号。

## 检查与维护

```sh
python -m unittest discover -s . -v
```

测试覆盖源码范围、路径穿越/链接、篡改、任务边界、验签失败、撤销/过期签名、跳过测试、状态软链接和错误回传。更新固定Rime配置或CTest集合时同步修改白名单与对应回归。运行日志和本机完整软件包清单留本地，不直接同步到公开仓库。

官方机制：[Bubblewrap](https://man.archlinux.org/man/bwrap.1.en)、[pacman](https://man.archlinux.org/man/pacman.8.en)。

回传后在平板执行轻量兼容检查：

```sh
python check_local.py --input /tmp/ime-input-001 --download /tmp/ime-result-001
```

它在临时沙箱中运行九键/全拼引擎、Fcitx桥、私有总线后端及动态模块加载，结束后清除临时词库和测试目录。不调用真实麦克风，不向当前应用输入，不修改已安装输入法。语音后端检查使用测试桩，仅验证程序链路；真实识别率和实体触屏手感仍需另外验收。

本机检查失败时保留 `local-check.log`；修复原因后，先把旧日志和旧 `local-check.json` 移入本次结果目录的独立归档子目录再重试。检查器不会覆盖旧日志，也不会因失败而安装或切换版本。
