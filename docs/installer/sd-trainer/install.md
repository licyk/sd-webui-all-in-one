# SD Trainer Installer 安装

## 安装
SD Trainer Installer 默认情况下安装的是 [Akegarasu/SD-Trainer](https://github.com/Akegarasu/lora-scripts) 分支，如果需要指定安装的分支，需要在 SD Trainer Installer 所在路径创建配置文件，以下为不同配置文件对应的 SD-Trainer 分支。

|配置文件名|对应安装的分支|
|---|---|
|`install_sd_trainer.txt`|[Akegarasu/SD-Trainer](https://github.com/Akegarasu/lora-scripts)|
|`install_kohya_gui.txt`|[bmaltais/Kohya GUI](https://github.com/bmaltais/kohya_ss)|

创建配置文件后，将 SD Trainer Installer 下载至本地，和配置文件放在一起，如下所示。

```
.
├── 119966207_p0_master1200.jpg
├── 437A9AE81C043B83110F55316EC7789E.png
├── BaiduNetdiskDownload
├── BaiduNetdiskWorkspace
├── install_sd_trainer.txt    # 这是配置文件
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
    - [设置 Github 镜像源](config.md#设置-github-镜像源)
    - [设置 PyPI 镜像源](config.md#设置-pypi-镜像源)
    - [设置 uv 包管理器](config.md#设置-uv-包管理器)
    - [配置代理](config.md#配置代理)
    - [设置内核路径前缀](config.md#设置内核路径前缀)
    - [设置模型下载源](resources.md#设置模型下载源)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

|SD Trainer Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/sd_trainer_installer.ps1)|

在 SD Trainer Installer 成功安装 SD-Trainer 后，在`SD-Trainer`文件夹中可以看到 SD-Trainer 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 SD Trainer Installer。

!!! note
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](environment.md#环境配置)中的方法进行解除。
    2. SD Trainer Installer 支持使用在命令行中通过参数配置 SD-Trainer 的安装参数，具体说明可阅读[使用命令运行 SD Trainer Installer](advanced.md#使用命令运行-sd-trainer-installer)。
