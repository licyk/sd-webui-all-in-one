# Qwen TTS WebUI Installer 安装

## 安装
右键`qwen_tts_webui_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 Qwen TTS WebUI Installer 将安装 Qwen TTS WebUI 至本地。

!!! info
    右键菜单中点击`使用 PowerShell 运行`为 Windows 平台上的使用方法，如果需要在 Linux / MacOS 平台中运行，请打开终端并使用`pwsh`命令去运行，例如：
    
    ```bash
    pwsh qwen_tts_webui_installer.ps1
    ```
    对于其他 PowerShell 脚本也是类似的方法去运行。

!!! note
    Qwen TTS WebUI Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：
    - [设置 Github 镜像源](config.md#设置-github-镜像源)
    - [设置 PyPI 镜像源](config.md#设置-pypi-镜像源)
    - [设置 uv 包管理器](config.md#设置-uv-包管理器)
    - [配置代理](config.md#配置代理)
    - [设置内核路径前缀](config.md#设置内核路径前缀)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

|Qwen TTS WebUI Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1)|

在 Qwen TTS WebUI Installer 成功安装 Qwen TTS WebUI 后，在`qwen-tts-webui`文件夹中可以看到 Qwen TTS WebUI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 Qwen TTS WebUI Installer。

!!! note
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](environment.md#环境配置)中的方法进行解除。
    2. Qwen TTS WebUI Installer 支持使用在命令行中通过参数配置 Qwen TTS WebUI 的安装参数，具体说明可阅读[使用命令运行 Qwen TTS WebUI Installer](advanced.md#使用命令运行-qwen-tts-webui-installer)。
