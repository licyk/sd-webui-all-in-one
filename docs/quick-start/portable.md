# 整合包快速开始

整合包适合 Windows 用户下载后直接解压使用。它基于 Installer 构建，并包含 Installer 生成的管理脚本；解压后默认通过这些脚本启动和维护，也可以交给 Launcher 接管管理。

## 最快流程

1. 下载 [AI 整合包下载器](../tools/portable-downloader.md)。
2. 在下载器中优先选择 `Nightly` 版本，`Stable` 版本相对较旧。
3. 选择需要的 WebUI 或训练工具整合包，确认保存路径后开始下载。
4. 保持“下载完成后自动解压到当前目录”启用，等待下载和解压完成。
5. 进入解压目录，按整合包说明运行启动脚本。

完整整合包列表和各产品脚本说明见 [整合包下载与使用](../portable/portable.md)。

## 启动和管理方式

整合包解压后主要由 Installer 生成的脚本管理，也可以选择其他入口：

- 使用 Installer 管理脚本：首次使用先运行 `configure_env.bat`，之后运行 `launch.ps1` 启动。
- 使用绘世启动器：部分整合包包含 `hanamizuki.bat`，可通过绘世启动器启动对应 WebUI。
- 使用 Windows GUI Launcher：把安装路径指向整合包解压目录，由 Launcher 接管 Installer 生成的启动、更新、终端、模型下载和版本管理脚本。

想用 Launcher 接管整合包，继续阅读 [Launcher 快速开始](./launcher.md)。

## AMD 显卡用户

如果使用 AMD RX 系列、780M、680M 等显卡，并希望在 Windows 上运行 WebUI，整合包解压后继续阅读 [AMD ZLUDA 使用](../portable/zluda.md)。

## 下一步

- 下载器界面和下载失败排查：阅读 [AI 整合包下载器](../tools/portable-downloader.md)。
- 整合包脚本和各产品入口：阅读 [整合包下载与使用](../portable/portable.md)。
- WebUI 已经打开后：阅读 [启动后的下一步](./after-start.md)。
