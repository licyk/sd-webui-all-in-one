<div align="center">

# ComfyUI Installer

_✨一键安装 ComfyUI_

</div>

# 目录
- [ComfyUI Installer](#comfyui-installer)
- [目录](#目录)
- [简介](#简介)
- [环境配置](#环境配置)
  - [1. 使用自动环境配置脚本](#1-使用自动环境配置脚本)
  - [2. 手动使用命令配置](#2-手动使用命令配置)
    - [2.1 解除脚本限制](#21-解除脚本限制)
    - [2.2 启用 Windows 长路径支持](#22-启用-windows-长路径支持)
- [安装](#安装)
- [使用](#使用)
  - [启动 ComfyUI](#启动-comfyui)
  - [更新 ComfyUI](#更新-comfyui)
  - [更新 ComfyUI 自定义节点](#更新-comfyui-自定义节点)
  - [设置 ComfyUI 启动参数](#设置-comfyui-启动参数)
  - [进入 ComfyUI 所在的 Python 环境](#进入-comfyui-所在的-python-环境)
  - [获取最新的 ComfyUI Installer 并运行](#获取最新的-comfyui-installer-并运行)
  - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
  - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
  - [设置 Github 镜像源](#设置-github-镜像源)
  - [设置 PyPI 镜像源](#设置-pypi-镜像源)
  - [配置代理](#配置代理)
    - [1. 使用系统代理](#1-使用系统代理)
    - [2. 使用配置文件](#2-使用配置文件)
    - [禁用自动设置代理](#禁用自动设置代理)
  - [共享 Stable Diffusion WebUI 的模型](#共享-stable-diffusion-webui-的模型)
  - [下载模型](#下载模型)
  - [ComfyUI 使用方法](#comfyui-使用方法)
  - [使用绘世启动器](#使用绘世启动器)
  - [使用 ComfyUI Installer 管理已有的 ComfyUI](#使用-comfyui-installer-管理已有的-comfyui)
  - [重装 ComfyUI](#重装-comfyui)
  - [重装 Python 环境](#重装-python-环境)
  - [重装 Git](#重装-git)
  - [重装 PyTorch](#重装-pytorch)
  - [卸载 ComfyUI](#卸载-comfyui)
  - [移动 ComfyUI 的路径](#移动-comfyui-的路径)
  - [更新 ComfyUI 管理脚本](#更新-comfyui-管理脚本)
    - [1. 直接更新](#1-直接更新)
    - [2. 使用 ComfyUI Installer 配置管理器进行更新](#2-使用-comfyui-installer-配置管理器进行更新)
    - [3. 运行 ComfyUI Installer 进行更新](#3-运行-comfyui-installer-进行更新)
    - [4. 使用命令更新](#4-使用命令更新)
    - [禁用 ComfyUI Installer 更新检查](#禁用-comfyui-installer-更新检查)
  - [设置 uv 包管理器](#设置-uv-包管理器)
  - [创建快捷启动方式](#创建快捷启动方式)
  - [管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)
  - [ComfyUI Installer 对 Python / Git 环境的识别](#comfyui-installer-对-python--git-环境的识别)
  - [使用命令运行 ComfyUI Installer](#使用命令运行-comfyui-installer)
  - [ComfyUI Installer 构建模式和普通安装模式](#comfyui-installer-构建模式和普通安装模式)
  - [运行脚本时出现中文乱码](#运行脚本时出现中文乱码)
  - [无法使用 PowerShell 运行](#无法使用-powershell-运行)
  - [PowerShell 中出现 xFormers 报错](#powershell-中出现-xformers-报错)
  - [ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE](#error-these-packages-do-not-match-the-hashes-from-the-requirements-file)
  - [CUDA out of memory](#cuda-out-of-memory)
  - [DefaultCPUAllocator: not enough memory](#defaultcpuallocator-not-enough-memory)
  - [以一种访问权限不允许的方式做了一个访问套接字的尝试](#以一种访问权限不允许的方式做了一个访问套接字的尝试)
  - [Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.](#microsoft-visual-c-redistributable-is-not-installed-this-may-lead-to-the-dll-load-failure)
  - [命令的使用](#命令的使用)
    - [1. 使用自动环境激活脚本](#1-使用自动环境激活脚本)
    - [2. 手动输入命令激活](#2-手动输入命令激活)
  - [常用命令](#常用命令)
    - [清理安装时产生的 Pip 缓存](#清理安装时产生的-pip-缓存)
    - [安装某个 Python 软件包](#安装某个-python-软件包)
    - [更新某个软件包](#更新某个软件包)
    - [重装某个软件包](#重装某个软件包)
    - [卸载某个软件包](#卸载某个软件包)
    - [使用 uv 安装软件包](#使用-uv-安装软件包)
    - [更新仓库](#更新仓库)
    - [运行某个 Python 脚本](#运行某个-python-脚本)
    - [下载文件](#下载文件)
    - [更新 uv](#更新-uv)
    - [更新 Aria2](#更新-aria2)
    - [测试可用的 Github 镜像源并应用](#测试可用的-github-镜像源并应用)
    - [安装 ComfyUI 自定义节点](#安装-comfyui-自定义节点)
    - [Git 下载命令](#git-下载命令)
    - [安装绘世启动器并自动配置绘世启动器所需的环境](#安装绘世启动器并自动配置绘世启动器所需的环境)
    - [列出 ComfyUI 已存在的自定义节点](#列出-comfyui-已存在的自定义节点)
    - [列出 ComfyUI Installer 内置命令](#列出-comfyui-installer-内置命令)
    - [检查 ComfyUI Installer 更新](#检查-comfyui-installer-更新)
    - [查看并切换 ComfyUI 的版本](#查看并切换-comfyui-的版本)
    - [查看 Git / Python 命令实际调用的路径](#查看-git--python-命令实际调用的路径)

***

# 简介
一个在 Windows 系统上部署 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 的 PowerShell 脚本，并提供不同的管理工具。

***

# 环境配置
如果是初次使用 PowerShell 脚本，需要解除 Windows 系统对脚本的限制。

Windows 系统默认未启用长路径支持，这可能会导致部分功能出现异常，需要启用 Windows 长路径支持来解决该问题。

下面提供 2 种方法进行环境配置。

## 1. 使用自动环境配置脚本
下载环境自动配置脚本，双击运行`configure_env.bat`后将会弹出管理员权限申请提示，选择`是`授权管理员权限给环境配置脚本，这时将自动配置运行环境。

|环境配置脚本下载|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/configure_env.bat)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/configure_env.bat)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/configure_env.bat)|

>[!NOTE]  
>[使用自动环境配置脚本](#1-使用自动环境配置脚本)的方法和[手动使用命令配置](#2-手动使用命令配置)的方法效果一致。


## 2. 手动使用命令配置

### 2.1 解除脚本限制
使用管理员权限打开 PowerShell，运行以下命令：

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

>[!NOTE]  
>关于 PowerShell 执行策略的说明：[关于执行策略 ### PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)


### 2.2 启用 Windows 长路径支持
在刚刚的 PowerShell 中运行下面的命令：

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

>[!NOTE]  
>关于 Windows 长路径支持的说明：[最大路径长度限制 ### Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)

***

# 安装
将 ComfyUI Installer 下载至本地，右键`comfyui_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 ComfyUI Installer 将安装 ComfyUI 至本地。

>[!NOTE]  
>ComfyUI Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：
>- [设置 Github 镜像源](#设置-github-镜像源)
>- [设置 PyPI 镜像源](#设置-pypi-镜像源)
>- [设置 uv 包管理器](#设置-uv-包管理器)
>- [配置代理](#配置代理)
>
>通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

|ComfyUI Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1)|

在 ComfyUI Installer 成功安装 ComfyUI 后，在`ComfyUI`文件夹中可以看到 ComfyUI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 ComfyUI Installer。

<details>
<summary><strong><h3>查看 ComfyUI Installer 为 ComfyUI 预装的扩展</h3></strong></summary>

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
|[weilin9999/WeiLin-ComfyUI-prompt-all-in-one](https://github.com/weilin9999/WeiLin-ComfyUI-prompt-all-in-one)|
|[licyk/ComfyUI-HakuImg](https://github.com/licyk/ComfyUI-HakuImg)|

</details>

>[!NOTE]  
>1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](#环境配置)中的方法进行解除。
>2. ComfyUI Installer 支持使用在命令行中通过参数配置 ComfyUI 的安装参数，具体说明可阅读[使用命令运行 ComfyUI Installer](#使用命令运行-comfyui-installer)。

***

# 使用
在`ComfyUI`文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。在`ComfyUI`文件夹中也有 PowerShell 脚本，但不建议使用该文件夹中的脚本进行运行。


## 启动 ComfyUI
运行`launch.ps1`脚本。


## 更新 ComfyUI
运行`update.ps1`脚本，如果遇到更新 ComfyUI 失败的情况可尝试重新运行`update.ps1`脚本。


## 更新 ComfyUI 自定义节点
运行`update_node.ps1`脚本，如果遇到更新 ComfyUI 自定义节点失败的情况可尝试重新运行`update_node.ps1`脚本。


## 设置 ComfyUI 启动参数
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

要设置 ComfyUI 的启动参数，可以在和`launch.ps1`脚本同级的目录创建一个`launch_args.txt`文件，在文件内写上启动参数，运行 ComfyUI 启动脚本时将自动读取该文件内的启动参数并应用。


## 进入 ComfyUI 所在的 Python 环境
如果需要使用 Python、Pip、ComfyUI 的命令时，请勿将 ComfyUI 的`python`文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行`terminal.ps1`脚本，这将打开 PowerShell 并自动执行`activate.ps1`，此时就进入了 ComfyUI 所在的 Python。

或者是在 ComfyUI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 ComfyUI Env：

```powershell
.\activate.ps1
```

这样就进入 ComfyUI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。


## 获取最新的 ComfyUI Installer 并运行
运行`launch_comfyui_installer.ps1`脚本，如果下载成功将会把 ComfyUI Installer 下载到`cache`目录中并运行。


## 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次`launch_comfyui_installer.ps1`重新生成这些脚本。

```
$ tree -L 2
.
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── ComfyUI                           # 这是 ComfyUI 文件夹
│   ├── configure_env.bat             # 配置环境的脚本
│   ├── activate.ps1                  # 进入 ComfyUI Env 的脚本
│   ├── cache                         # 缓存文件夹
│   ├── download_models.ps1           # 下载模型的脚本
│   ├── launch_comfyui_installer.ps1  # 获取最新的 ComfyUI Installer 并运行的脚本
│   ├── git                           # Git 目录
│   ├── help.txt                      # 帮助文档
│   ├── launch.ps1                    # 启动 ComfyUI 的脚本
│   ├── ComfyUI                       # ComfyUI 路径
│   ├── python                        # Python 目录
│   ├── reinstall_pytorch.ps1         # 重新安装 PyTorch 的脚本
│   ├── settings.ps1                  # 管理 ComfyUI Installer 设置的脚本
│   ├── terminal.ps1                  # 自动打开 PowerShell 并激活 ComfyUI Installer 的虚拟环境脚本
│   ├── update_node.ps1               # 更新 ComfyUI 自定义节点
│   └── update.ps1                    # 更新 ComfyUI 的脚本
├── comfyui_installer.ps1             # ComfyUI Installer 一般放在 ComfyUI 文件夹外面，和 ComfyUI 文件夹同级
└── QQ Files

8 directories, 9 files
```


## 设置 HuggingFace 镜像
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

ComfyUI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`hf_mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源|
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_hf_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。


## 设置 Github 镜像源
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

ComfyUI Installer 为了加速访问 Github 的速度，加快下载和更新 ComfyUI 的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建`gh_mirror.txt`文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

|可用的 Github 镜像源|
|---|
|https://ghfast.top/https://github.com|
|https://mirror.ghproxy.com/https://github.com|
|https://gh.api.99988866.xyz/https://github.com|
|https://gitclone.com/github.com|
|https://gh-proxy.com/https://github.com|
|https://ghps.cc/https://github.com|
|https://gh.idayer.com/https://github.com|
|https://ghproxy.1888866.xyz/github.com|
|https://slink.ltd/https://github.com|
|https://github.boki.moe/github.com|
|https://github.moeyy.xyz/https://github.com|
|https://gh-proxy.net/https://github.com|
|https://gh-proxy.ygxz.in/https://github.com|
|https://wget.la/https://github.com|
|https://kkgithub.com|
|https://ghproxy.net/https://github.com|

如果需要禁用设置 Github 镜像源，在和脚本同级的目录中创建`disable_gh_mirror.txt`文件，再次启动脚本时将禁用 Github 镜像源。


## 设置 PyPI 镜像源
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

ComfyUI Installer 默认启用了 PyPI 镜像源加速下载 Python 软件包，如果需要禁用 PyPI 镜像源，可以在脚本同级目录创建`disable_pypi_mirror.txt`文件，再次运行脚本时将 PyPI 源切换至官方源。


## 配置代理
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

如果出现某些文件无法下载，比如在控制台出现`由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败`之类的报错时，可以尝试配置代理，有以下 2 种方法。

### 1. 使用系统代理

在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。


### 2. 使用配置文件

在和脚本同级的路径中创建一个`proxy.txt`文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

>[!NOTE]  
>**配置文件**的优先级高于**系统代理**配置，所以当同时使用了两种方式配置代理，脚本将优先使用**配置文件**中的代理配置。


### 禁用自动设置代理
在和脚本同级的路径中创建一个`disable_proxy.txt`文件，再次启动脚本时将禁用设置代理。


## 共享 Stable Diffusion WebUI 的模型
在 ComfyUI 启动一次后，在 ComfyUI 的根目录会生成一个 extra_model_paths.yaml.example 共享目录示例文件，通过修改这个文件可以使 ComfyUI 共享 Stable Diffusion WebUI 的模型文件。

这是一个例子，我的 Stable Diffusion WebUI 路径在`E:/Softwares/stable-diffusion-webui`，则将这个示例文件的`base_path:`后面的路径改成 Stable Diffusion WebUI 的路径。

```yaml
#Rename this to extra_model_paths.yaml and ComfyUI will load it


#config for a1111 ui
#all you have to do is change the base_path to where yours is installed
a111:
    base_path: E:/Softwares/stable-diffusion-webui # 填写 Stable Diffusion WebUI 的路径, 注意冒号后面必须有空格

    checkpoints: models/Stable-diffusion # 大模型
    configs: models/Stable-diffusion # 大模型配置文件
    vae: models/VAE # VAE 模型
    loras: | # LoRA 模型
         models/Lora
         models/LyCORIS
    upscale_models: | # 放大模型
                  models/ESRGAN
                  models/RealESRGAN
                  models/SwinIR
    embeddings: embeddings # Embedding 模型
    hypernetworks: models/hypernetworks # Hypernetwork 模型
    controlnet: models/Controlnet # ControlNet 模型
    ipadapter: models/Controlnet # IP Adapter 模型
    clip_vision: extensions/sd-webui-controlnet/annotator/downloads/clip_vision # clip_vision 模型
    # AnimateDiff 模型共享的说明: https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved?tab=readme-ov-file#model-setup
    animatediff_models: extensions/sd-webui-animatediff/model # AnimateDiff 模型
    animatediff_motion_lora: extensions/sd-webui-animatediff/model # AnimateDiff LoRA 模型


#config for comfyui
#your base path should be either an existing comfy install or a central folder where you store all of your models, loras, etc.

comfyui:
#     base_path: path/to/comfyui/
#     checkpoints: models/checkpoints/
#     clip: models/clip/
#     configs: models/configs/
#     controlnet: models/controlnet/
#     embeddings: models/embeddings/
#     loras: models/loras/
#     upscale_models: models/upscale_models/
#     vae: models/vae/
#     classifiers: models/classifiers/
#     clip_vision: models/clip_vision/
#     diffusers: models/diffusers/
#     diffusion_models: models/diffusion_models/
#     gligen: models/gligen/
#     hypernetworks: models/hypernetworks/
#     photomaker: models/photomaker/
#     style_models: models/style_models/
#     unet: models/unet/
#     vae_approx: models/vae_approx/
#     animatediff_models: models/animatediff_models/
#     animatediff_motion_lora: models/animatediff_motion_lora/
#     animatediff_video_formats: models/animatediff_video_formats/
#     ipadapter: models/ipadapter/
#     liveportrait: models/liveportrait/
#     insightface: models/insightface/
#     layerstyle: models/layerstyle/
#     LLM: models/LLM/
#     Joy_caption: models/Joy_caption/
#     sams: models/sams/
#     blip: models/blip/
#     CogVideo: models/CogVideo/
#     xlabs: models/xlabs/
#     instantid: models/instantid/
#     custom_nodes: custom_nodes/


#other_ui:
#    base_path: path/to/ui
#    checkpoints: models/checkpoints
#    gligen: models/gligen
#    custom_nodes: path/custom_nodes
```


## 下载模型
可以使用`download_models.ps1`脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。


## ComfyUI 使用方法
推荐的哔哩哔哩 UP 主：
- 只剩一瓶辣椒酱：https://space.bilibili.com/35723238
- 秋葉aaaki：https://space.bilibili.com/12566101

ComfyUI 的使用教程：
- https://sdnote.netlify.app/guide/comfyui
- https://sdnote.netlify.app/help/comfyui
- https://www.aigodlike.com
- https://space.bilibili.com/35723238/channel/collectiondetail?sid=1320931
- https://comfyanonymous.github.io/ComfyUI_examples
- https://blenderneko.github.io/ComfyUI-docs
- https://comfyui-wiki.com/zh


## 使用绘世启动器
>[!IMPORTANT]  
>推荐使用自动安装绘世启动器的方法，可以参考[命令的使用](#命令的使用)中的[安装绘世启动器并自动配置绘世启动器所需的环境](#安装绘世启动器并自动配置绘世启动器所需的环境)命令，该命令可一键配置下载绘世启动器并配置，并且生成`hanamizuki.bat`脚本用于快捷启动绘世启动器，或者可以尝试下面手动配置绘世启动器的方法。

ComfyUI Installer 部署出来的 ComfyUI 可以通过绘世启动器进行启动，使用绘世启动器前需要调整目录结构使绘世启动器能够正确识别到环境。

将`ComfyUI/python`目录移动到`ComfyUI/ComfyUI/python`，`ComfyUI/git`移动到`ComfyUI/ComfyUI/git`。

移动前目录的结构如下。

```
.
├── ComfyUI
│   ├── activate.ps1
│   ├── cache
│   ├── download_models.ps1
│   ├── launch_comfyui_installer.ps1
│   ├── git                           # Git 目录
│   ├── help.txt
│   ├── launch.ps1
│   ├── ComfyUI                       # ComfyUI 路径
│   │   ├── ...
│   │   └── main.py
│   ├── python                        # Python 目录
│   ├── reinstall_pytorch.ps1
│   ├── settings.ps1
│   ├── terminal.ps1
│   ├── update_node.ps1
│   └── update.ps1
└── comfyui_installer.ps1          
```

移动 Python 和 Git 之后的目录结构。

```
.
├── ComfyUI
│   ├── activate.ps1
│   ├── cache
│   ├── download_models.ps1
│   ├── launch_comfyui_installer.ps1
│   ├── help.txt
│   ├── launch.ps1
│   ├── ComfyUI                       # ComfyUI 路径
│   │   ├── git                       # Git 目录
│   │   ├── python                    # Python 目录
│   │   ├── ...
│   │   └── main.py
│   ├── reinstall_pytorch.ps1
│   ├── settings.ps1
│   ├── terminal.ps1
│   ├── update_node.ps1
│   └── update.ps1
└── comfyui_installer.ps1          
```

再下载绘世启动器放到`ComfyUI/ComfyUI`目录中，就可以通过启动器启动 ComfyUI。

|绘世启动器下载|
|---|
|[下载地址 1](https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe)|
|[下载地址 2](https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe)|
|[下载地址 3](https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe)|


## 使用 ComfyUI Installer 管理已有的 ComfyUI
使用 ComfyUI Installer 管理已有的 ComfyUI，需要构建 ComfyUI Installer 所需的目录结构。

将 ComfyUI Installer 下载到本地后，在 ComfyUI Installer 所在目录打开 PowerShell，使用命令运行，将 ComfyUI Installer 的管理脚本安装到本地，比如在`D:/ComfyUI`，则命令如下。

```powershell
./comfyui_installer.ps1 -UseUpdateMode -InstallPath "D:/ComfyUI"
```

运行完成后 ComfyUI Installer 的管理脚本将安装在`D:/ComfyUI`中，目录结构如下。

```
D:/ComfyUI
├── activate.ps1
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_comfyui_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── terminal.ps1
├── update.ps1
├── update_node.ps1
└── update_time.txt
```

接下来需要将 ComfyUI 移动到`D:/ComfyUI`目录中，如果 ComfyUI 的文件夹名称不是`ComfyUI`，比如`ComfyUI-aki-v1.2`，需要将名称修改成`ComfyUI`。

移动进去后此时的目录结构如下。

```
D:/ComfyUI
├── activate.ps1
├── ComfyUI
│   ├── custom_nodes
│   ├── main.py
│   ├── models
│   ...
│   └── nodes.py
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_comfyui_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── terminal.ps1
├── update.ps1
├── update_node.ps1
└── update_time.txt
```

再检查`D:/ComfyUI/ComfyUI`文件夹中是否包含`python`和`git`文件夹，如果未包含，需要运行`launch_comfyui_installer.ps1`重建环境，重建完成后即可运行`launch.ps1`启动 ComfyUI。


## 重装 ComfyUI
将`ComfyUI`文件夹中的`ComfyUI`文件夹删除，然后运行`launch_comfyui_installer.ps1`重新部署 ComfyUI。

>[!NOTE]  
>如果`ComfyUI`文件夹存放了模型文件，请将这些文件备份后再删除`ComfyUI`文件夹。


## 重装 Python 环境
如果 Python 环境出现严重损坏，可以将`ComfyUI/python`和`ComfyUI/ComfyUI/python`文件夹删除，然后运行`launch_comfyui_installer.ps1`重新构建 Python 环境。

>[!IMPORTANT]  
>如果需要使用绘世启动器，在重装 Python 完成后，还需要运行[命令的使用](#命令的使用)中[安装绘世启动器并自动配置绘世启动器所需的环境](#安装绘世启动器并自动配置绘世启动器所需的环境)的命令，保证绘世启动器能够正常识别到 Python 环境。


## 重装 Git
将`ComfyUI/git`和`ComfyUI/ComfyUI/git`文件夹删除，然后运行`launch_comfyui_installer.ps1`重新下载 Git。

>[!IMPORTANT]  
>如果需要使用绘世启动器，在重装 Git 完成后，还需要运行[命令的使用](#命令的使用)中[安装绘世启动器并自动配置绘世启动器所需的环境](#安装绘世启动器并自动配置绘世启动器所需的环境)的命令，保证绘世启动器能够正常识别到 Git 环境。


## 重装 PyTorch
运行`reinstall_pytorch.ps1`脚本，并根据脚本提示的内容进行操作。


## 卸载 ComfyUI
使用 ComfyUI Installer 安装 ComfyUI 后，所有的文件都存放在`ComfyUI`文件夹中，只需要删除`ComfyUI`文件夹即可卸载 ComfyUI。

如果有 ComfyUI 快捷启动方式，可以通过命令进行删除，打开 PowerShell 后，输入以下命令进行删除。
```powershell
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\ComfyUI.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\ComfyUI.lnk" -Force
```


## 移动 ComfyUI 的路径
直接将`ComfyUI`文件夹移动到别的路径即可。

如果启用了自动创建 ComfyUI 快捷启动方式的功能，移动 ComfyUI 后原来的快捷启动方式将失效，需要运行`launch.ps1`更新快捷启动方式。


## 更新 ComfyUI 管理脚本
ComfyUI Installer 的管理脚本在启动时会检查管理脚本的更新，如果有新版本可更新将会提示。

可选择下方 4 种方法中的其中 1 个方法进行更新。


### 1. 直接更新
当检测到有新版的 ComfyUI Installer 时，将询问是否进行更新，输入`y`并回车后将运行 ComfyUI Installer 进行更新。


### 2. 使用 ComfyUI Installer 配置管理器进行更新
运行`settings.ps1`，选择`更新 ComfyUI Installer 管理脚本`功能进行更新，更新完成后需关闭 ComfyUI Installer 管理脚本以应用更新。


### 3. 运行 ComfyUI Installer 进行更新
运行`launch_comfyui_installer.ps1`获取最新的 ComfyUI Installer 后，脚本会自动运行新版 ComfyUI Installer 进行更新。


### 4. 使用命令更新
参考[命令的使用](#命令的使用)的方法进入 ComfyUI Env，并运行`Check-ComfyUI-Installer-Update`命令进行更新。

### 禁用 ComfyUI Installer 更新检查
>[!WARNING]  
>通常不建议禁用 ComfyUI Installer 的更新检查，当 ComfyUI 管理脚本有重要更新（如功能性修复）时将得不到及时提示。

>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

如果要禁用更新检查，可以在脚本同级的目录创建`disable_update.txt`文件，这将禁用 ComfyUI Installer 更新检查。


## 设置 uv 包管理器
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

ComfyUI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。

如需禁用 uv，可在脚本所在目录创建一个`disable_uv.txt`文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

>[!NOTE]  
>1. 当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。
>2. uv 包管理器对网络的稳定性要求更高，在网络不稳定时可能会出现下载软件包出错的问题，可尝试重新运行，或者禁用 uv，这时将切换成 Pip 作为 Python 包管理器，Pip 在网络稳定性差的情况下不容易出错，但这将降低 Python 软件包的安装速度。



## 创建快捷启动方式
>[!NOTE]  
>该设置可通过[管理 ComfyUI Installer 设置](#管理-comfyui-installer-设置)中提到的的`settings.ps1`进行修改。

在脚本同级目录创建`enable_shortcut.txt`文件，当运行`launch.ps1`时将会自动创建快捷启动方式，并添加到 Windows 桌面和 Windows 开始菜单中，下次启动时可以使用快捷方式启动 ComfyUI。

>[!IMPORTANT]  
>如果 ComfyUI 的路径发生移动，需要重新运行`launch.ps1`更新快捷启动方式。


## 管理 ComfyUI Installer 设置
运行`settings.ps1`，根据提示进行设置管理和调整。


## ComfyUI Installer 对 Python / Git 环境的识别
ComfyUI Installer 通常情况下不会去调用系统环境中的 Python / Git，所以在安装过程会安装一个独立的 Python / Git 避免收到系统环境中的 Python / Git 影响。

ComfyUI Installer 可以识别到的 Python 路径为`ComfyUI/python`和`ComfyUI/ComfyUI/python`，当两者同时存在时，优先使用后者。

可以识别到的 Git 路径为`ComfyUI/git`和`ComfyUI/ComfyUI/git`，当两者同时存在时，优先使用后者。

如果这两个路径 Python / Git 都不存在时，此时 ComfyUI 的管理脚本将会调用系统环境中的 Python / Git，这可能会带来不好的结果，所以出现这种情况时就需要运行 ComfyUI Installer 重新安装 Python / Git。


## 使用命令运行 ComfyUI Installer
ComfyUI Installer 支持使用命令参数设置安装 ComfyUI 的参数，支持的参数如下。

|参数|作用|
|---|---|
|`-InstallPath` <ComfyUI 安装路径>|指定安装 ComfyUI 的路径，使用绝对路径进行指定。|
|`-PyTorchMirrorType` <PyTorch 镜像源类型>|指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: `cu11x`, `cu118`, `cu121`, `cu124`, `cu126`, `cu128`|
|`-UseUpdateMode`|使用 ComfyUI Installer 的更新脚本模式，不进行 ComfyUI 的安装。|
|`-DisablePyPIMirror`|禁用 ComfyUI Installer 使用 PyPI 镜像源，使用 PyPI 官方源下载 Python 软件包。|
|`-DisableProxy`|禁用 ComfyUI Installer 自动设置代理服务器。|
|`-UseCustomProxy` <代理服务器地址>|使用自定义的代理服务器地址。|
|`-DisableUV`|禁用 ComfyUI Installer 使用 uv 安装 Python 软件包，使用 Pip 安装 Python 软件包。|
|`-DisableGithubMirror`|禁用 ComfyUI Installer 自动设置 Github 镜像源。|
|`-UseCustomGithubMirror` <Github 镜像站地址>|使用自定义的 Github 镜像站地址。</br>可用的 Github 镜像站地址:</br>`https://ghfast.top/https://github.com`</br>`https://mirror.ghproxy.com/https://github.com`</br>`https://ghproxy.net/https://github.com`</br>`https://gh.api.99988866.xyz/https://github.com`</br>`https://gh-proxy.com/https://github.com`</br>`https://ghps.cc/https://github.com`</br>`https://gh.idayer.com/https://github.com`</br>`https://ghproxy.1888866.xyz/github.com`</br>`https://slink.ltd/https://github.com`</br>`https://github.boki.moe/github.com`</br>`https://github.moeyy.xyz/https://github.com`</br>`https://gh-proxy.net/https://github.com`</br>`https://gh-proxy.ygxz.in/https://github.com`</br>`https://wget.la/https://github.com`</br>`https://kkgithub.com`</br>`https://gitclone.com/github.com`|
|`-BuildMode`|启用 ComfyUI Installer 构建模式，在基础安装流程结束后将调用 ComfyUI Installer 管理脚本执行剩余的安装任务，并且出现错误时不再暂停 ComfyUI Installer 的执行，而是直接退出。<br>当指定调用多个 ComfyUI Installer 脚本时，将按照优先顺序执行 (按从上到下的顺序)：<br><li>`reinstall_pytorch.ps1`：对应`-BuildWithTorch`，`-BuildWithTorchReinstall`参数<br><li>`download_models.ps1`：对应`-BuildWitchModel`参数<br><li>`update.ps1`：对应`-BuildWithUpdate`参数<br><li>`update_node.ps1`：对应`-BuildWithUpdateNode`参数<br><li>`launch.ps1`：对应`-BuildWithLaunch`参数|
|`-BuildWithUpdate`|(需添加`-BuildMode`启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 update.ps1 脚本，更新 ComfyUI 内核。|
|`-BuildWithUpdateNode`|(需添加`-BuildMode`启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 update_node.ps1 脚本，更新 ComfyUI 自定义节点。|
|`-BuildWithLaunch`|(需添加`-BuildMode`启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 launch.ps1 脚本，执行启动 ComfyUI 前的环境检查流程，但跳过启动 ComfyUI。|
|`-BuildWithTorch` <PyTorch 版本编号>|(需添加`-BuildMode`启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 reinstall_pytorch.ps1 脚本，根据 PyTorch 版本编号安 装指定的 PyTorch 版本。<br>PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看。|
|`-BuildWithTorchReinstall`|(需添加`-BuildMode`启用 ComfyUI Installer 构建模式，并且添加 -BuildWithTorch) 在 ComfyUI Installer 构建模式下，执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安 装时使用强制重新安装。|
|`-BuildWitchModel` <模型编号列表>|(需添加`-BuildMode`启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 download_models.ps1 脚本，根据模型编号列表下载指定的模型。<br>模型编号可运行 download_models.ps1 脚本进行查看。|
|`-NoPreDownloadNode`|安装 ComfyUI 时跳过安装 ComfyUI 扩展。|
|`-NoPreDownloadModel`|安装 ComfyUI 时跳过预下载模型。|
|`-PyTorchPackage` <PyTorch 软件包>|(需要同时搭配`-xFormersPackage`一起使用，否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 PyTorch 版本，如`-PyTorchPackage "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"`，在例子中指定的 PyTorch 软件包中指定了 torch 的版本，也就是`2.3.0+cu118`这个版本，`+`号后面的参数将作为指定 PyTorch 镜像源的参数，则这个例子中将会指定 PyTorch 镜像源的类型为`cu118`。若缺少`+`号和后面的参数，则根据 torch 的版本决定要设置的 PyTorch 镜像源类型。|
|`-xFormersPackage` <xFormers 软件包>|(需要同时搭配`-PyTorchPackage`一起使用，否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 xFormers 版本，如`-xFormersPackage "xformers===0.0.26.post1+cu118"`|
|`-DisableUpdate`|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 禁用 ComfyUI Installer 更新检查。|
|`-DisableHuggingFaceMirror`|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 禁用 HuggingFace 镜像源，不使用 HuggingFace 镜像源下载文件。|
|`-UseCustomHuggingFaceMirror` <HuggingFace 镜像源地址>|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址，例如代理服务器地址为 https://hf-mirror.com，则使用`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`设置 HuggingFace 镜像源地址。|
|`-LaunchArg` <ComfyUI 启动参数>|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 设置 ComfyUI 自定义启动参数，如启用 --fast 和 --auto-launch，则使用`-LaunchArg "--fast --auto-launch"`进行启用。|
|`-EnableShortcut`|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 创建 ComfyUI 启动快捷方式。|
|`-DisableCUDAMalloc`|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 禁用 ComfyUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器。|
|`-DisableEnvCheck`|(仅在 ComfyUI Installer 构建模式下生效，并且只作用于 ComfyUI Installer 管理脚本) 禁用 ComfyUI Installer 检查 ComfyUI 运行环境中存在的问题，禁用后可能会导致 ComfyUI 环境中存在的问题无法被发现并修复。|
|`-Help`|显示 ComfyUI Installer 可用的命令行参数。|

例如在`D:/Download`这个路径安装 ComfyUI，则在 ComfyUI Installer 所在路径打开 PowerShell，使用参数运行 ComfyUI Installer。

```powershell
.\comfyui_installer.ps1 -InstallPath "D:/Download"
```


## ComfyUI Installer 构建模式和普通安装模式
ComfyUI Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 ComfyUI Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，模型安装，运行环境检查和修复等并不会执行，这些步骤是在 ComfyUI Installer 管理脚本中进行，如执行`launch.ps1`，`reinstall_pytorch.ps1`脚本等。

而 ComfyUI Installer 构建模式允许在执行基础安装流程后，调用 ComfyUI Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 ComfyUI Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读[使用命令运行 ComfyUI Installer](#使用命令运行-comfyui-installer)中的参数说明。

>[!IMPORTANT]  
>通常安装 ComfyUI 并不需要使用 ComfyUI Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。

使用 Github Action 提供的容器可用于运行 ComfyUI Installer 并启用构建模式，实现自动化制作整合包，Github Action 工作流代码可参考：[build_comfyui.yml · licyk/sd-webui-all-in-one](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/workflows/build_comfyui.yml)


## 运行脚本时出现中文乱码
这可能是 Windows 系统中启用了 UTF 8 编码，可以按照下列方法解决。

1. 按下`Win + R`键，输入`control`后回车启动控制面板。
2. 点击`时钟和区域`->`区域`
3. 在弹出的区域设置窗口中点击顶部的`管理`，再点击`更改系统区域设置`.
4. 在弹出的窗口中将`使用 Unicode UTF-8 提供全球语言支持`取消勾选，然后一直点击确定保存设置，并重启电脑。


## 无法使用 PowerShell 运行
运行 PowerShell 脚本时出现以下错误。

```
.\comfyui_installer.ps1 : 无法加载文件 D:\ComfyUI\comfyui_installer.ps1。
未对文件 D:\ComfyUI\comfyui_installer.ps1进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符: 1
+ .\comfyui_installer.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~
   + CategoryInfo          : SecurityError: (:) []，PSSecurityException
   + FullyQualifiedErrorId : UnauthorizedAccess
```

或者右键运行 PowerShell 脚本时闪一下 PowerShell 的界面后就消失了。

这是因为未解除 Windows 系统对运行 PowerShell 脚本的限制，请使用管理员权限打开 PowerShell，运行下面的命令。

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

或者使用[自动环境配置脚本](#1-使用自动环境配置脚本)解除 Windows 系统对运行 PowerShell 脚本的限制。


## PowerShell 中出现 xFormers 报错
在控制台中出现有关 xFormers 的警告信息，类似下面的内容。

```
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.2.1+cu118 with CUDA 1108 (you have 2.2.2+cu121)
    Python  3.10.11 (you have 3.10.11)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
```

这是因为 xFormers 所适配的 CUDA 版本和 PyTorch 所带的 CUDA 版本不一致，请运行`reinstall_pytorch.ps1`重装 PyTorch。


## ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE
运行 ComfyUI Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将`ComfyUI/cache/pip`文件夹删除，再重新运行 ComfyUI Installer。


## CUDA out of memory
尝试使用分块编 / 解码 VAE 节点，降低出图分辨率。


## DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。


## 以一种访问权限不允许的方式做了一个访问套接字的尝试
启动 ComfyUI 时出现以下的错误。
```
ERROR: [Error 13] error while attempting to bind on address ('127.0.0.1', 28000): 以一种访问权限不允许的方式做了一个访问套接字的尝试。
```

这是因为该端口被其他软件占用，ComfyUI 无法使用。可尝试将占用该端口的软件关闭，或者在`launch.ps1`所在目录创建`launch_args.txt`文件，在该文件中写上启动参数把 ComfyUI 端口修改，如`--port 8888`，保存`launch_args.txt`文件后使用`launch.ps1`重新启动 ComfyUI。

>[!NOTE]  
>设置 ComfyUI 启动参数的方法可参考[设置 ComfyUI 启动参数](#设置-comfyui-启动参数)。


## Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。


## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。


### 1. 使用自动环境激活脚本
运行`terminal.ps1`后将自动打开 PowerShell 并激活 ComfyUI Env。


### 2. 手动输入命令激活
在`ComfyUI`文件夹打开 PowerShell，输入下面的命令激活 ComfyUI Env：

```powershell
.\activate.ps1
```

>[!IMPORTANT]  
>在 PowerShell 中一定要显示`[ComfyUI Env]`才算进入了环境，这样才能使用下面的命令。


## 常用命令

### 清理安装时产生的 Pip 缓存
```powershell
python -m pip cache purge
```


### 安装某个 Python 软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名 
python -m pip install <package_name>
```


### 更新某个软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip install <package_name> -U
```


### 重装某个软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip install <package_name> --force-reinstall
```


### 卸载某个软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip uninstall <package_name>
```

>[!NOTE]  
>推荐使用`python -m pip`的写法，`pip`的写法也可用。ComfyUI Installer 默认将`pip`命令链接到`python -m pip`避免直接调用`pip`。  
>参考：[Deprecate pip, pipX, and pipX.Y · Issue #3164 · pypa/pip](https://github.com/pypa/pip/issues/3164)


### 使用 uv 安装软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
uv pip install <package_name>
```

>[!NOTE]  
>uv 命令的用法可参考：[uv docs](https://docs.astral.sh/uv)


### 更新仓库
```powershell
git pull --recurse-submodules
```


### 运行某个 Python 脚本
```powershell
# 命令中的 <python_script.py> 替换成要执行的 Python 脚本路径
python <python_script.py>
```


### 下载文件
```powershell
# 命令中的 <url> 替换成下载链接，<dir> 替换成下载到的路径，<output_file_name> 替换成保存的文件名
aria2c <url> -c -s 16 -x 16 -k 1M -d <dir> -o <output_file_name>
```


### 更新 uv
```powershell
Update-uv
```


### 更新 Aria2
```powershell
Update-Aria2
```


### 测试可用的 Github 镜像源并应用
```powershell
Test-Github-Mirror
```


### 安装 ComfyUI 自定义节点
```powershell
# <url> 为 ComfyUI 自定义节点的下载链接
Install-ComfyUI-Node <url>
```


### Git 下载命令
```powershell
# <url> 为下载链接, <path> 为下载到的路径
Git-Clone <url> <path>
```


### 安装绘世启动器并自动配置绘世启动器所需的环境
```powershell
Install-Hanamizuki
```

>[!IMPORTANT]  
>运行该命令前请确保 ComfyUI 已经关闭，如果运行该命令出现报错，可根据报错提示内容进行其他操作，再重新运行该命令。


### 列出 ComfyUI 已存在的自定义节点
```powershell
List-Node
```


### 列出 ComfyUI Installer 内置命令
```powershell
List-CMD
```


### 检查 ComfyUI Installer 更新
```powershell
Check-ComfyUI-Installer-Update
```

### 查看并切换 ComfyUI 的版本
```powershell
# 列出当前的所有版本
git -C ComfyUI tag
# 运行该命令后将进入 Git 的交互式界面
# 使用 u 键上翻， d 键下翻，或者使用方向键翻页，使用 q 键退出
# 一般 git tag 命令将列出下面类似的输出
# v0.1.0
# v0.2.0
# v1.1.0
# v1.4.0
# v1.6.0
# v1.7.0
# v1.7.3
# ...
# 这是使用 Git Tag 标记的版本，可以使用 Tag 作为版本号进行切换

# 使用 Tag 切换版本
# 命令中的 <Git Tag> 替换成对应的 Tag
git -C ComfyUI reset --hard --recurse-submodules <Git Tag>

# 使用 git log 查看某个提交信息对应的 Hash 值
git -C ComfyUI log
# 这将得到类似的输出信息
# commit 9aace3e94c2c41a44e3df403329abd0518467bf5 (HEAD -> main, tag: v1.9.0)
# Author: Akegarasu <akiba@anzu.link>
# Date:   Sat Aug 31 22:32:52 2024 +0800
#
#     add vae_batch_size
#
# commit 931392e3c90aab20473175c9196d70fcfe039491
# Author: Akegarasu <akiba@anzu.link>
# Date:   Sat Aug 31 22:31:04 2024 +0800
#
#     tagger
#
# commit 后面对应的字符串为该提交信息对应的 Hash 值

# 可以使用该 Hash 切换版本
# 命令中的 <Git Commit Hash> 替换成对应的 Hash 值
git -C ComfyUI reset --hard --recurse-submodules <Git Commit Hash>
```

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
