# ComfyUI Installer 环境准备与安装

## 快速流程

1. Windows 用户先在“环境配置脚本下载”中下载环境配置脚本 `configure_env.bat` 并运行；Linux / macOS 用户先安装 PowerShell，macOS 还需要安装 Homebrew。
2. 在“ComfyUI Installer 下载地址”中下载 ComfyUI Installer 安装脚本 `comfyui_installer.ps1`。
3. 将 ComfyUI Installer 安装脚本 `comfyui_installer.ps1` 放到希望安装 ComfyUI 的位置，按需创建镜像、代理或模型下载源配置文件。
4. 右键 ComfyUI Installer 安装脚本 `comfyui_installer.ps1` 选择`使用 PowerShell 运行`，或在终端中使用 `pwsh comfyui_installer.ps1`。

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

**ComfyUI Installer 下载地址**

[GitHub Release 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1){ .md-button .md-button--primary }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1){ .md-button }
[GitHub Raw 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/comfyui_installer.ps1){ .md-button }
[Gitee Raw 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/comfyui_installer.ps1){ .md-button }
[GitLab Raw 下载 :material-download:](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/comfyui_installer.ps1){ .md-button }

将 ComfyUI Installer 下载至本地，右键`comfyui_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 ComfyUI Installer 将安装 ComfyUI 至本地。

!!! info
    右键菜单中点击`使用 PowerShell 运行`为 Windows 平台上的使用方法，如果需要在 Linux / MacOS 平台中运行，请打开终端并使用`pwsh`命令去运行，例如：
    
    ```bash
    pwsh comfyui_installer.ps1
    ```
    对于其他 PowerShell 脚本也是类似的方法去运行。

!!! note
    ComfyUI Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：
    - [设置 Github 镜像源](config.md#github)
    - [设置 PyPI 镜像源](config.md#pypi)
    - [设置 uv 包管理器](config.md#uv)
    - [配置代理](config.md#_2)
    - [设置内核路径前缀](config.md#_5)
    - [设置模型下载源](resources.md#_3)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

在 ComfyUI Installer 成功安装 ComfyUI 后，在`ComfyUI`文件夹中可以看到 ComfyUI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 ComfyUI Installer。

??? note "查看 ComfyUI Installer 为 ComfyUI 预装的扩展"
    
    |ComfyUI 扩展|
    |---|
    |[Comfy-Org/ComfyUI-Manager](https://github.com/Comfy-Org/ComfyUI-Manager)|
    |[Fannovel16/comfyui_controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux)|
    |[Kosinkadink/ComfyUI-Advanced-ControlNet](https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet)|
    |[cubiq/ComfyUI_IPAdapter_plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus)|
    |[kijai/ComfyUI-Marigold](https://github.com/kijai/ComfyUI-Marigold)|
    |[pythongosssss/ComfyUI-WD14-Tagger](https://github.com/pythongosssss/ComfyUI-WD14-Tagger)|
    |[BlenderNeko/ComfyUI_TiledKSampler](https://github.com/BlenderNeko/ComfyUI_TiledKSampler)|
    |[pythongosssss/ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts)|
    |[LEv145/images-grid-comfy-plugin](https://github.com/LEv145/images-grid-comfy-plugin)|
    |[ssitu/ComfyUI_UltimateSDUpscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale)|
    |[AlekPet/ComfyUI_Custom_Nodes_AlekPet](https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet)|
    |[talesofai/comfyui-browser](https://github.com/talesofai/comfyui-browser)|
    |[ltdrdata/ComfyUI-Inspire-Pack](https://github.com/ltdrdata/ComfyUI-Inspire-Pack)|
    |[Suzie1/ComfyUI_Comfyroll_CustomNodes](https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes)|
    |[crystian/ComfyUI-Crystools](https://github.com/crystian/ComfyUI-Crystools)|
    |[shiimizu/ComfyUI-TiledDiffusion](https://github.com/shiimizu/ComfyUI-TiledDiffusion)|
    |[huchenlei/ComfyUI-openpose-editor](https://github.com/huchenlei/ComfyUI-openpose-editor)|
    |[licyk/ComfyUI-Restart-Sampler](https://github.com/licyk/ComfyUI-Restart-Sampler)|
    |[weilin9999/WeiLin-Comfyui-Tools](https://github.com/weilin9999/WeiLin-Comfyui-Tools)|
    |[licyk/ComfyUI-HakuImg](https://github.com/licyk/ComfyUI-HakuImg)|
    |[yolain/ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use)|
    |[rgthree/rgthree-comfy](https://github.com/rgthree/rgthree-comfy)|
    

!!! note
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](install.md#_1)中的方法进行解除。
    2. ComfyUI Installer 支持使用在命令行中通过参数配置 ComfyUI 的安装参数，具体说明可阅读[使用命令运行 ComfyUI Installer](advanced.md#comfyui-installer_1)。
