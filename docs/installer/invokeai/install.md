# InvokeAI Installer 环境准备与安装

## 环境配置
该脚本在 Windows / Linux / MacOS 系统上需要进行不同的环境配置，以下为不同平台配置环境的方法。

### Windows
下载环境自动配置脚本，双击运行`configure_env.bat`后将会弹出管理员权限申请提示，选择`是`授权管理员权限给环境配置脚本，这时将自动配置运行环境。

|环境配置脚本下载|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/configure_env.bat)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/configure_env.bat)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/configure_env.bat)|

### Linux
参考该文档安装 PowerShell：[在 Linux 上安装 PowerShell - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/scripting/install/install-powershell-on-linux?view=powershell-7.5)

### MacOS
参考该文档安装 PowerShell：[在 macOS 上安装 PowerShell - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/scripting/install/install-powershell-on-macos?view=powershell-7.5)

再参考该文档安装 HomeBrew：[macOS（或 Linux）缺失的软件包的管理器 — Homebrew](https://brew.sh/zh-cn)

## 安装
将 InvokeAI Installer 下载至本地，右键`invokeai_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 InvokeAI Installer 将安装 InvokeAI 至本地。

!!! info
    右键菜单中点击`使用 PowerShell 运行`为 Windows 平台上的使用方法，如果需要在 Linux / MacOS 平台中运行，请打开终端并使用`pwsh`命令去运行，例如：
    
    ```bash
    pwsh invokeai_installer.ps1
    ```
    对于其他 PowerShell 脚本也是类似的方法去运行。

!!! note
    InvokeAI Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：
    - [设置 PyPI 镜像源](config.md#设置-pypi-镜像源)
    - [设置 uv 包管理器](config.md#设置-uv-包管理器)
    - [配置代理](config.md#配置代理)
    - [设置内核路径前缀](config.md#设置内核路径前缀)
    - [设置模型下载源](resources.md#设置模型下载源)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

|InvokeAI Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/invokeai_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/invokeai_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/invokeai_installer.ps1)|

在 InvokeAI Installer 成功安装 InvokeAI 后，在`InvokeAI`文件夹中可以看到 InvokeAI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 InvokeAI Installer。

!!! note
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](install.md#环境配置)中的方法进行解除。
    2. InvokeAI Installer 支持使用在命令行中通过参数配置 InvokeAI 的安装参数，具体说明可阅读[使用命令运行 InvokeAI Installer](advanced.md#使用命令运行-invokeai-installer)。
