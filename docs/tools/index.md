# 下载器与启动器

本板块介绍项目中面向用户的辅助工具：AI 整合包下载器、Windows GUI Launcher、Bash TUI / CLI Launcher。下载器负责获取整合包；Launcher 则是安装、启动和维护 WebUI / 训练工具的统一入口。

Launcher 的 GUI / TUI 工具在独立仓库维护，项目地址：[licyk/sd-webui-all-in-one-launcher](https://github.com/licyk/sd-webui-all-in-one-launcher)。

## 如何选择

| 目标 | 推荐工具 | 适用平台 |
| --- | --- | --- |
| 下载已构建好的整合包，下载后解压使用 | [AI 整合包下载器](./portable-downloader.md) | Windows |
| 用图形界面安装、启动和维护 WebUI / 训练工具，或接管已解压整合包 | [Windows GUI Launcher](./launcher-gui.md) | Windows |
| 在终端中安装、启动和维护 WebUI / 训练工具，或接管已有安装目录 | [Bash TUI / CLI Launcher](./launcher-tui.md) | Linux / macOS / 终端环境 |

## 推荐路径

1. 只想下载整合包：阅读 [AI 整合包下载器](./portable-downloader.md)，下载后再阅读 [整合包下载与使用](../portable/portable.md)。
2. 下载并解压整合包后，Windows 用户可以用 [Windows GUI Launcher](./launcher-gui.md) 选择对应产品，并把安装路径指向整合包解压目录来启动和管理。
3. 想从零安装并后续管理项目：Windows 用户阅读 [Windows GUI Launcher](./launcher-gui.md)，Linux / macOS 用户阅读 [Bash TUI / CLI Launcher](./launcher-tui.md)。
4. 成功启动 WebUI 后，需要学习界面使用、绘图流程、模型和工作流：阅读 [SD Note](https://licyk.github.io/SDNote/)。
5. 遇到刷新、下载、解压、启动或代理问题：阅读 [故障排查](./troubleshooting.md)。

## 工具关系

- AI 整合包下载器负责下载和解压整合包，不直接做安装参数配置或后续维护。
- Launcher 借助 `sd-webui-all-in-one` 的 PowerShell 安装器完成安装，并继续管理安装目录中的启动、更新、终端、模型下载、重装 PyTorch 和版本管理脚本。
- 整合包内部包含安装器生成的管理脚本，例如 `launch.ps1`、`update.ps1`、`terminal.ps1`、`download_models.ps1` 和 `version_manager.ps1`。把 Launcher 的安装路径指向整合包解压目录后，也可以由 Launcher 接管启动和管理。
