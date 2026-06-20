# InvokeAI Installer 环境准备与安装

## 快速流程

1. Windows 用户先在“环境配置脚本下载”中下载环境配置脚本 `configure_env.bat` 并运行；Linux / macOS 用户先安装 PowerShell，macOS 还需要安装 Homebrew。
2. 在“InvokeAI Installer 下载地址”中下载 InvokeAI Installer 安装脚本 `invokeai_installer.ps1`。
3. 将 InvokeAI Installer 安装脚本 `invokeai_installer.ps1` 放到希望安装 InvokeAI 的位置，按需创建镜像、代理或模型下载源配置文件。
4. 右键 InvokeAI Installer 安装脚本 `invokeai_installer.ps1` 选择 `使用 PowerShell 运行`，不要左键双击 `.ps1` 脚本；或在终端中使用 `pwsh invokeai_installer.ps1`。

## 环境配置
该脚本在 Windows / Linux / MacOS 系统上需要进行不同的环境配置，以下为不同平台配置环境的方法。

### Windows
下载环境自动配置脚本，双击运行`configure_env.bat`后将会弹出管理员权限申请提示，选择`是`授权管理员权限给环境配置脚本，这时将自动配置运行环境。

**环境配置脚本下载**

[GitHub Release 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat){ .md-button .md-button--primary }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat){ .md-button }
[GitHub Raw 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/configure_env.bat){ .md-button }
[Gitee Raw 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/configure_env.bat){ .md-button }
[GitLab Raw 下载 :material-download:](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/configure_env.bat){ .md-button }

### Linux
参考该文档安装 PowerShell：[在 Linux 上安装 PowerShell - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/scripting/install/install-powershell-on-linux?view=powershell-7.5)

### MacOS
参考该文档安装 PowerShell：[在 macOS 上安装 PowerShell - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/scripting/install/install-powershell-on-macos?view=powershell-7.5)

再参考该文档安装 HomeBrew：[macOS（或 Linux）缺失的软件包的管理器 — Homebrew](https://brew.sh/zh-cn)

## 安装

**InvokeAI Installer 下载地址**

[GitHub Release 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1){ .md-button .md-button--primary }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1){ .md-button }
[GitHub Raw 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/invokeai_installer.ps1){ .md-button }
[Gitee Raw 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/invokeai_installer.ps1){ .md-button }
[GitLab Raw 下载 :material-download:](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/invokeai_installer.ps1){ .md-button }

将 InvokeAI Installer 下载至本地，右键`invokeai_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 InvokeAI Installer 将安装 InvokeAI 至本地。

!!! info
    Windows 平台运行 `.ps1` 脚本时，不要左键双击；左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。正确方式是右键脚本，在右键菜单中点击 `使用 PowerShell 运行`。如果右键运行后窗口闪退，先运行本页“环境配置”中的 `configure_env.bat` 后再重试。Linux / MacOS 平台请打开终端并使用 `pwsh` 命令运行，例如：
    
    ```bash
    pwsh invokeai_installer.ps1
    ```
    对于其他 PowerShell 脚本也是类似的方法去运行。

!!! note
    InvokeAI Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：

    - [设置 PyPI 镜像源](config.md#pypi)
    - [设置 uv 包管理器](config.md#uv)
    - [配置代理](config.md#_2)
    - [设置内核路径前缀](config.md#_5)
    - [设置模型下载源](resources.md#_3)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

在 InvokeAI Installer 成功安装 InvokeAI 后，在`InvokeAI`文件夹中可以看到 InvokeAI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 InvokeAI Installer。

!!! note
    1. 如果右键运行 PowerShell 脚本后窗口闪退，先运行本页“环境配置”中的 `configure_env.bat` 解除 Windows 运行限制，再右键 `.ps1` 脚本选择 `使用 PowerShell 运行`。不要左键双击 `.ps1` 脚本，左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。
    2. InvokeAI Installer 支持使用在命令行中通过参数配置 InvokeAI 的安装参数，具体说明可阅读[使用命令运行 InvokeAI Installer](advanced.md#invokeai-installer_1)。
