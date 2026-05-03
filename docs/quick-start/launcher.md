# Launcher 快速开始

Launcher 是安装、启动和维护 WebUI / 训练工具的统一入口。它可以借助安装器完成新安装，也可以接管已经解压的整合包或已有安装目录。

## Windows GUI Launcher

适合 Windows 用户使用图形界面完成安装和管理：

1. 阅读 [Windows GUI Launcher](../tools/launcher-gui.md)，下载并启动 Launcher。
2. 在“软件选择”中选择要安装或管理的 WebUI / 工具。
3. 如果是新安装，在“一键启动”中运行安装流程。
4. 如果是已有整合包或已有安装目录，在“高级选项”中把安装路径指向对应目录。
5. 返回“一键启动”，运行 `launch.ps1` 启动，或运行 `update.ps1`、`terminal.ps1`、`download_models.ps1`、`version_manager.ps1` 做维护。

## Bash TUI / CLI Launcher

适合 Linux / macOS 或终端用户。它提供 TUI 菜单和 CLI 命令，可用于选择项目、下载安装器、运行管理脚本和调整配置。使用方式见 [Bash TUI / CLI Launcher](../tools/launcher-tui.md)。

## Launcher 能管理什么

- 安装 WebUI / 训练工具。
- 启动已安装项目或已解压整合包。
- 运行更新、终端、模型下载、版本管理等管理脚本。
- 调整安装器参数、管理脚本参数和代理等配置。

## 下一步

- 想下载整合包再用 Launcher 接管：阅读 [整合包快速开始](./portable.md)。
- 想从零安装到本地：阅读 [本地安装快速开始](./local-install.md)。
- WebUI 已经打开后：阅读 [启动后的下一步](./after-start.md)。
