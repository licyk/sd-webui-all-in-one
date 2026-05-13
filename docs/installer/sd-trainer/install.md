# SD Trainer Installer 环境准备与安装

## 快速流程

1. Windows 用户先在“环境配置脚本下载”中下载环境配置脚本 `configure_env.bat` 并运行；Linux / macOS 用户先安装 PowerShell，macOS 还需要安装 Homebrew。
2. 在“SD Trainer Installer 下载地址”中下载 SD Trainer Installer 安装脚本 `sd_trainer_installer.ps1`。
3. 将 SD Trainer Installer 安装脚本 `sd_trainer_installer.ps1` 放到希望安装 SD-Trainer 的位置；需要指定训练工具分支时，再在同一目录创建对应配置文件。
4. 右键 SD Trainer Installer 安装脚本 `sd_trainer_installer.ps1` 选择`使用 PowerShell 运行`，或在终端中使用 `pwsh sd_trainer_installer.ps1`。

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

**SD Trainer Installer 下载地址**

[GitHub Release 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1){ .md-button .md-button--primary }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1){ .md-button }
[GitHub Raw 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_installer.ps1){ .md-button }
[Gitee Raw 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_installer.ps1){ .md-button }
[GitLab Raw 下载 :material-download:](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/sd_trainer_installer.ps1){ .md-button }

SD Trainer Installer 默认情况下安装的是 [Akegarasu/SD-Trainer](https://github.com/Akegarasu/lora-scripts) 分支，如果需要指定安装的分支，需要在 SD Trainer Installer 所在路径创建配置文件，以下为不同配置文件对应的 SD-Trainer 分支。

|配置文件名|对应安装的分支|
|---|---|
|`install_sd_trainer_main.txt`|[Akegarasu/SD-Trainer](https://github.com/Akegarasu/lora-scripts)|
|`install_kohya_gui_main.txt`|[bmaltais/Kohya GUI](https://github.com/bmaltais/kohya_ss)|

上表使用当前代码中的 `InstallBranch` 分支标识作为配置文件名。旧版短名称配置文件仍由安装器兼容识别，新建配置时建议使用上表文件名。

如果创建了配置文件，将 SD Trainer Installer 和配置文件放在一起，如下所示。

```
.
├── 119966207_p0_master1200.jpg
├── 437A9AE81C043B83110F55316EC7789E.png
├── BaiduNetdiskDownload
├── BaiduNetdiskWorkspace
├── install_sd_trainer_main.txt    # 这是配置文件
├── QQDownloads
├── sd_trainer_installer.ps1  # 这是 SD Trainer Installer
├── z-noob_artist.csv
└── 得意黑_横屏.prtextstyle
```

右键`sd_trainer_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 SD Trainer Installer 将安装 SD-Trainer 至本地。

!!! info
    右键菜单中点击`使用 PowerShell 运行`为 Windows 平台上的使用方法，如果需要在 Linux / MacOS 平台中运行，请打开终端并使用`pwsh`命令去运行，例如：
    
    ```bash
    pwsh sd_trainer_installer.ps1
    ```
    对于其他 PowerShell 脚本也是类似的方法去运行。

!!! note
    SD Trainer Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：
    - [设置 Github 镜像源](config.md#github)
    - [设置 PyPI 镜像源](config.md#pypi)
    - [设置 uv 包管理器](config.md#uv)
    - [配置代理](config.md#_2)
    - [设置内核路径前缀](config.md#_5)
    - [设置模型下载源](resources.md#_3)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

在 SD Trainer Installer 成功安装 SD-Trainer 后，在`SD-Trainer`文件夹中可以看到 SD-Trainer 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 SD Trainer Installer。

!!! note
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](install.md#_1)中的方法进行解除。
    2. SD Trainer Installer 支持使用在命令行中通过参数配置 SD-Trainer 的安装参数，具体说明可阅读[使用命令运行 SD Trainer Installer](advanced.md#sd-trainer-installer_1)。
