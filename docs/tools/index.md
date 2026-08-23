# 下载器与启动器

本板块介绍项目中面向用户的辅助工具：全平台桌面管理器 Hanafubuki、AI 整合包下载器和 Bash TUI / CLI Launcher。需要图形界面时优先使用 Hanafubuki；下载器负责获取整合包；TUI / CLI 适合终端环境和训练脚本。

## 如何选择

| 目标 | 推荐工具 | 适用平台 |
| --- | --- | --- |
| 用图形界面安装、导入、启动和维护 WebUI | [Hanafubuki](./hanafubuki.md) | Windows / Linux / macOS |
| 下载已构建好的整合包，下载后解压使用 | [AI 整合包下载器](./portable-downloader.md) | Windows |
| 在终端中安装、启动和维护 WebUI / 训练工具，或管理 SD Scripts / Musubi Tuner | [Bash TUI / CLI Launcher](./launcher-tui.md) | Linux / macOS / 终端环境 |

## 推荐路径

1. 想从零安装并长期管理：在 Windows、macOS 或 Linux 上优先阅读 [Hanafubuki](./hanafubuki.md)。
2. 只想下载整合包：阅读 [AI 整合包下载器](./portable-downloader.md)，下载后再阅读 [整合包下载与使用](../portable/portable.md)。受支持的整合包解压后直接运行内置 `hanafubuki-launcher.exe`。
3. 偏好终端，或需要管理 SD Scripts / Musubi Tuner：阅读 [Bash TUI / CLI Launcher](./launcher-tui.md)。
4. 成功启动 WebUI 后，需要学习界面使用、绘图流程、模型和工作流：阅读 [SD Note](https://licyk.github.io/SDNote/)。
5. 遇到刷新、下载、解压、启动或代理问题：阅读 [故障排查](./troubleshooting.md)。

## 工具关系

- Hanafubuki 使用本项目的安装和管理核心，同时提供实例、运行环境、版本、扩展、模型、快照、任务和诊断等桌面管理能力。
- AI 整合包下载器只负责下载和解压整合包，不直接做安装参数配置或后续维护。
- Bash TUI / CLI Launcher 借助 `sd-webui-all-in-one` 的 PowerShell 安装器完成安装，并运行安装目录中的管理脚本。
- [旧版 Windows GUI Launcher](./launcher-gui.md) 仅保留给现有用户查阅，新用户不再推荐安装。
