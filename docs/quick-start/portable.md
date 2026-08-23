# 整合包快速开始

整合包适合 Windows 用户下载后直接解压使用。它基于 Installer 构建，并包含 Installer 生成的管理脚本；受 Hanafubuki 支持的整合包还内置 `hanafubuki-launcher.exe`，作为优先推荐的启动和管理入口。

## 最快流程

1. 下载 [AI 整合包下载器](../tools/portable-downloader.md)。
2. 在下载器中优先选择 `Nightly` 版本，`Stable` 版本相对较旧。
3. 选择需要的 WebUI 或训练工具整合包，确认保存路径后开始下载。
4. 保持“下载完成后自动解压到当前目录”启用，等待下载和解压完成。
5. 如果解压目录中存在 `hanafubuki-launcher.exe`，优先双击运行并等待 Hanafubuki 完成首次准备；没有该文件时，再按产品说明运行 `configure_env.bat` 和对应 `.ps1` 脚本。

完整整合包列表和各产品脚本说明见 [整合包下载与使用](../portable/portable.md)。

## 启动和管理方式

整合包解压后可以选择以下入口：

- 使用 Hanafubuki：Stable Diffusion WebUI、ComfyUI、InvokeAI、Fooocus、SD Trainer、Qwen TTS WebUI 六类产品及其受支持变体的整合包，优先运行内置 `hanafubuki-launcher.exe`。首次运行会下载并校验应用本体，然后发现旁边的 WebUI。
- 使用 Installer 管理脚本：首次使用先运行 `configure_env.bat`，之后右键 `launch.ps1`，选择 `使用 PowerShell 运行` 启动。不要左键双击 `.ps1` 脚本，左键双击通常会用记事本或默认编辑器打开脚本；如果右键运行后窗口闪退，也先重新运行 `configure_env.bat`。
- 使用绘世启动器：部分整合包包含 `hanamizuki.bat`，可通过绘世启动器启动对应 WebUI。

SD Scripts 和 Musubi Tuner 当前不属于 Hanafubuki 支持的六类产品，继续使用 Installer 管理脚本或 [Bash TUI / CLI Launcher](../tools/launcher-tui.md)。Hanafubuki 的完整说明见 [Hanafubuki 快速开始](./launcher.md)。

## AMD 显卡用户

如果使用 AMD RX 系列、780M、680M 等显卡，并希望在 Windows 上运行 WebUI，整合包解压后继续阅读 [AMD ZLUDA 使用](../portable/zluda.md)。

## 下一步

- 下载器界面和下载失败排查：阅读 [AI 整合包下载器](../tools/portable-downloader.md)。
- 整合包脚本和各产品入口：阅读 [整合包下载与使用](../portable/portable.md)。
- WebUI 已经打开后：阅读 [启动后的下一步](./after-start.md)。
