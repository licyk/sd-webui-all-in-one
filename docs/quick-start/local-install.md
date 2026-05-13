# 本地安装快速开始

本地安装适合希望长期维护 WebUI 或训练工具的用户。安装前需要先确认系统环境和依赖组件，所以快速开始只给出入口和选择方式，具体步骤以各产品的“环境准备与安装”页面为准。

## 先选安装方式

| 安装方式 | 推荐场景 | 下一步 |
| --- | --- | --- |
| Windows GUI Launcher | 想用图形界面安装、启动和管理 | [Launcher 快速开始](./launcher.md) |
| Bash TUI / CLI Launcher | Linux / macOS 或终端用户 | [Bash TUI / CLI Launcher](../tools/launcher-tui.md) |
| 直接运行 Installer | 想手动下载并运行 PowerShell 安装器 | [安装器使用](../installer/index.md) 或选择下方产品安装页 |
| Windows 整合包下载器 | 想下载由 Installer 构建并管理的免安装整合包 | [AI 整合包下载器](../tools/portable-downloader.md) |

## 选择产品安装页

- [SD WebUI Installer 环境准备与安装](../installer/sd-webui/install.md)：Stable Diffusion WebUI、Forge、reForge、SD.Next 等。
- [ComfyUI Installer 环境准备与安装](../installer/comfyui/install.md)：ComfyUI 节点式工作流。
- [Fooocus Installer 环境准备与安装](../installer/fooocus/install.md)：Fooocus 及相关分支。
- [InvokeAI Installer 环境准备与安装](../installer/invokeai/install.md)：InvokeAI。
- [Qwen TTS WebUI Installer 环境准备与安装](../installer/qwen-tts-webui/install.md)：Qwen TTS WebUI。
- [SD Trainer Installer 环境准备与安装](../installer/sd-trainer/install.md)：训练 WebUI。
- [SD Trainer Script Installer 环境准备与安装](../installer/sd-trainer-script/install.md)：sd-scripts / kohya-ss 训练脚本。

## 安装前注意

- Windows 用户需要确认 PowerShell 脚本运行限制已解除。
- Linux / macOS 用户需要按安装页准备 Homebrew、PowerShell 或其他依赖。
- 安装路径建议避免中文、空格和权限受限目录。
- 如果只想少配置快速使用，优先考虑 [整合包快速开始](./portable.md)。整合包同样基于 Installer 构建，解压后主要通过 Installer 生成的管理脚本维护。

## 下一步

安装完成后，进入对应产品的“启动与使用”页面，或阅读 [启动后的下一步](./after-start.md)。
