# 第三方来源与许可证

项目原创代码与文档采用根目录LICENSE中的GNU GPL v3.0（GPL-3.0-only）。下列内容保留原有许可；根目录声明不更改第三方权利或删除其版权声明。

| 内容 | 来源 | 许可证与记录 |
| --- | --- | --- |
| Omarchy派生面板和界面片段 | [Omarchy](https://github.com/basecamp/omarchy) | MIT；[原版权声明](LICENSES/Omarchy-MIT.txt)，另保留network-center/LICENSE.omarchy与battery-manager/panel/LICENSE.upstream |
| 手写识别封装和测试 | [MSIME-Engine](https://github.com/metasequoiaime/MSIME-Engine)，提交1a428e2a83a94ff3837ec9eae6299ead5e457c37 | GPLv3；[来源清单](modules/touch-ime-prototype/vendor/source.json)与vendor/MSIME-Engine-LICENSE |
| Zinnia识别器源码 | [Zinnia](https://github.com/taku910/zinnia)，提交581faa8f6f15e4a7b21964be3a5ec36265c80e5b | BSD三条款；vendor/handwriting/third_party/zinnia/Zinnia-LICENSE.txt |
| Tegaki简体中文手写模型0.3 | 上游源码压缩包及模型哈希见[provenance.json](modules/touch-ime-prototype/vendor/handwriting/provenance.json) | LGPL-2.1；vendor/handwriting/models/HandwritingModel-LICENSE.txt；对应训练XML、元数据和构建说明的来源在同一记录中 |

模型属于可选的本地单字识别资源。再分发时保留许可、版权和对应源码信息。系统依赖如Qt、Fcitx、Rime、GTK、NetworkManager、ModemManager和播放器由发行版安装，具有各自许可证；本仓库的声明不替代其分发义务。

游戏ROM、商业游戏资源、私人词库、录音及代理订阅不包含在本仓库中。新增第三方资源时一并更新来源、许可和所需声明。
