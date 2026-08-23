# Hanafubuki 快速开始

Hanafubuki 是本项目优先推荐的图形化管理入口，支持 Windows、macOS 和 Linux。它可以完成全新安装，也可以导入或扫描已有 WebUI，并在统一工作区中管理启动、版本、模型、扩展、PyTorch、快照、任务和诊断信息。

[立即下载 Hanafubuki :material-download:](https://hanafubuki.netlify.app/download){ .md-button .md-button--primary }
[查看完整说明](../tools/hanafubuki.md){ .md-button }

## 最快流程

1. 从 [Hanafubuki 下载页](https://hanafubuki.netlify.app/download)选择安装包或便携版。长期固定使用推荐安装包；移动使用或需要多套隔离环境时选择便携版。
2. 首次启动后等待应用准备 Python、Micromamba 和 Git 等运行组件。
3. 在首页选择“添加实例”。没有现成 WebUI 时选择“全新安装”；已有目录时选择“导入现有实例”或“扫描系统”。
4. 打开实例并启动 WebUI；需要维护时进入实例管理页选择版本、扩展、模型、PyTorch、快照或路径等功能。
5. 长时间安装和维护任务可从右下角状态区或标题栏任务中心查看输出。

## 使用 Windows 整合包

受支持的整合包已经包含 Hanafubuki 便携版。解压后优先运行 `hanafubuki-launcher.exe`，首次运行时等待它下载、校验并启动应用本体；不需要另外安装旧版 GUI Launcher。

SD Scripts、Musubi Tuner 等训练脚本目前继续使用整合包内的 Installer 管理脚本，或使用 [Bash TUI / CLI Launcher](../tools/launcher-tui.md)。

## Bash TUI / CLI Launcher

适合偏好终端、需要管理训练脚本或无法使用桌面应用的用户。它提供 TUI 菜单和 CLI 命令，可用于选择项目、下载安装器、运行管理脚本和调整配置。使用方式见 [Bash TUI / CLI Launcher](../tools/launcher-tui.md)。

## Hanafubuki 能管理什么

- 安装或导入 WebUI / 训练工具。
- 启动已安装项目或已解压整合包。
- 管理版本、扩展、模型、PyTorch、快照和路径。
- 跟踪安装、启动和维护任务，查看日志并导出诊断信息。

## 下一步

- 想下载整合包并直接使用内置 Hanafubuki：阅读 [整合包快速开始](./portable.md)。
- 想从零安装到本地：阅读 [本地安装快速开始](./local-install.md)。
- WebUI 已经打开后：阅读 [启动后的下一步](./after-start.md)。
