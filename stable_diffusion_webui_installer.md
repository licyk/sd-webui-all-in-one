<div align="center">

# SD WebUI Installer

_✨一键安装 Stable Diffusion WebUI_

</div>

# 目录
- [SD WebUI Installer](#sd-webui-installer)
- [目录](#目录)
- [简介](#简介)
- [环境配置](#环境配置)
  - [使用自动环境配置脚本](#使用自动环境配置脚本)
  - [手动使用命令配置](#手动使用命令配置)
    - [解除脚本限制](#解除脚本限制)
    - [启用 Windows 长路径支持](#启用-windows-长路径支持)
- [安装](#安装)
- [使用](#使用)
  - [启动 Stable Diffusion WebUI](#启动-stable-diffusion-webui)
  - [更新 Stable Diffusion WebUI](#更新-stable-diffusion-webui)
  - [更新 Stable Diffusion WebUI 扩展](#更新-stable-diffusion-webui-扩展)
  - [设置 Stable Diffusion WebUI 启动参数](#设置-stable-diffusion-webui-启动参数)
  - [切换 Stable Diffusion WebUI 分支](#切换-stable-diffusion-webui-分支)
  - [进入 Stable Diffusion WebUI 所在的 Python 环境](#进入-stable-diffusion-webui-所在的-python-环境)
  - [获取最新的 SD WebUI Installer 脚本](#获取最新的-sd-webui-installer-脚本)
  - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
  - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
  - [设置 Github 镜像源](#设置-github-镜像源)
  - [设置 Pip 镜像源](#设置-pip-镜像源)
  - [配置代理](#配置代理)
    - [使用系统代理](#使用系统代理)
    - [使用配置文件](#使用配置文件)
    - [禁用自动设置代理](#禁用自动设置代理)
  - [下载模型](#下载模型)
  - [Stable Diffusion WebUI 使用方法](#stable-diffusion-webui-使用方法)
  - [使用绘世启动器](#使用绘世启动器)
  - [重装 Stable Diffusion WebUI](#重装-stable-diffusion-webui)
  - [重装 Python 环境](#重装-python-环境)
  - [重装 Git](#重装-git)
  - [重装 PyTorch](#重装-pytorch)
  - [卸载 Stable Diffusion WebUI](#卸载-stable-diffusion-webui)
  - [移动 Stable Diffusion WebUI 的路径](#移动-stable-diffusion-webui-的路径)
  - [更新 Stable Diffusion WebUI 管理脚本](#更新-stable-diffusion-webui-管理脚本)
    - [直接更新](#直接更新)
    - [使用 SD WebUI Installer 配置管理器进行更新](#使用-sd-webui-installer-配置管理器进行更新)
    - [手动运行 SD WebUI Installer 进行更新](#手动运行-sd-webui-installer-进行更新)
    - [使用命令更新](#使用命令更新)
  - [设置 uv 包管理器](#设置-uv-包管理器)
  - [创建快捷启动方式](#创建快捷启动方式)
  - [管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)
  - [SD WebUI Installer 对 Python / Git 环境的识别](#sd-webui-installer-对-python--git-环境的识别)
  - [运行脚本时出现中文乱码](#运行脚本时出现中文乱码)
  - [无法使用 PowerShell 运行](#无法使用-powershell-运行)
  - [PowerShell 中出现 xFormers 报错](#powershell-中出现-xformers-报错)
  - [ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE](#error-these-packages-do-not-match-the-hashes-from-the-requirements-file)
  - [CUDA out of memory](#cuda-out-of-memory)
  - [DefaultCPUAllocator: not enough memory](#defaultcpuallocator-not-enough-memory)
  - [以一种访问权限不允许的方式做了一个访问套接字的尝试](#以一种访问权限不允许的方式做了一个访问套接字的尝试)
  - [Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.](#microsoft-visual-c-redistributable-is-not-installed-this-may-lead-to-the-dll-load-failure)
  - [命令的使用](#命令的使用)
    - [使用自动环境激活脚本](#使用自动环境激活脚本)
    - [手动输入命令激活](#手动输入命令激活)
  - [常用命令](#常用命令)
    - [清理安装时产生的 Pip 缓存](#清理安装时产生的-pip-缓存)
    - [安装某个 Pip 软件包](#安装某个-pip-软件包)
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
    - [安装 Stable Diffusion WebUI 扩展](#安装-stable-diffusion-webui-扩展)
    - [Git 下载命令](#git-下载命令)
    - [安装绘世启动器并自动配置绘世启动器所需的环境](#安装绘世启动器并自动配置绘世启动器所需的环境)
    - [列出 Stable Diffusion WebUI 已存在的扩展](#列出-stable-diffusion-webui-已存在的扩展)
    - [列出 SD WebUI Installer 内置命令](#列出-sd-webui-installer-内置命令)
    - [检查 SD WebUI Installer 更新](#检查-sd-webui-installer-更新)
    - [查看并切换 Stable Diffusion WebUI 的版本](#查看并切换-stable-diffusion-webui-的版本)

***

# 简介
一个在 Windows 系统上部署 Stable Diffusion WebUI 的 PowerShell 脚本，并提供不同的管理工具。

支持部署的 Stable Diffusion WebUI 分支如下。

- [AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
- [Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)
- [lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)
- [vladmandic/SD.Next](https://github.com/vladmandic/automatic)

***

# 环境配置
如果是初次使用 PowerShell 脚本，需要解除 Windows 系统对脚本的限制。

Windows 系统默认未启用长路径支持，这可能会导致部分功能出现异常，需要启用 Windows 长路径支持来解决该问题。

下面提供 2 种方法进行环境配置。

## 使用自动环境配置脚本
下载环境自动配置脚本，双击运行`configure_env.bat`后将会弹出管理员权限申请提示，选择`是`授权管理员权限给环境配置脚本，这时将自动配置运行环境。

|环境配置脚本下载|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/raw/main/configure_env.bat)|
|[下载地址 2](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/configure_env.bat)|
|[下载地址 3](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/configure_env.bat)|
|[下载地址 4](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)|
|[下载地址 5](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)|

>[!NOTE]  
>[使用自动环境配置脚本](#使用自动环境配置脚本)的方法和[手动使用命令配置](#手动使用命令配置)的方法效果一致。


## 手动使用命令配置

### 解除脚本限制
使用管理员权限打开 PowerShell，运行以下命令：

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

>[!NOTE]  
>关于 PowerShell 执行策略的说明：[关于执行策略 ### PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)


### 启用 Windows 长路径支持
在刚刚的 PowerShell 中运行下面的命令：

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

>[!NOTE]  
>关于 Windows 长路径支持的说明：[最大路径长度限制 ### Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)

***

# 安装
SD WebUI Installer 默认情况下安装的是 [AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 分支，如果需要指定安装的分支，需要在 SD WebUI Installer 所在路径创建配置文件，以下为不同配置文件对应的 Stable Diffusion WebUI 分支。

|配置文件名|对应安装的分支|
|---|---|
|`install_sd_webui.txt`|[AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)|
|`install_sd_webui_forge.txt`|[lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)|
|`install_sd_webui_reforge.txt`|[Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)|
|`install_sd_webui_amdgpu.txt`|[lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)|
|`install_sd_next.txt`|[vladmandic/SD.Next](https://github.com/vladmandic/automatic)|

创建配置文件后，将 SD WebUI Installer 下载至本地，和配置文件放在一起。

右键`stable_diffusion_webui_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 SD WebUI Installer 将安装 Stable Diffusion WebUI 至本地。

|SD WebUI Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/raw/main/stable_diffusion_webui_installer.ps1)|
|[下载地址 2](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/stable_diffusion_webui_installer.ps1)|
|[下载地址 3](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/stable_diffusion_webui_installer.ps1)|
|[下载地址 4](https://github.com/licyk/sd-webui-all-in-one/releases/download/stable_diffusion_webui_installer/stable_diffusion_webui_installer.ps1)|
|[下载地址 5](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/stable_diffusion_webui_installer/stable_diffusion_webui_installer.ps1)|

在 SD WebUI Installer 成功安装 Stable Diffusion WebUI 后，在`stable-diffusion-webui`文件夹中可以看到 Stable Diffusion WebUI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 SD WebUI Installer。

>[!NOTE]  
>如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](#环境配置)中的方法进行解除。

***

# 使用
在`stable-diffusion-webui`文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。在`stable-diffusion-webui`文件夹中也有 PowerShell 脚本，但不建议使用该文件夹中的脚本进行运行。


## 启动 Stable Diffusion WebUI
运行`launch.ps1`脚本。


## 更新 Stable Diffusion WebUI
运行`update.ps1`脚本，如果遇到更新 Stable Diffusion WebUI 失败的情况可尝试重新运行`update.ps1`脚本。


## 更新 Stable Diffusion WebUI 扩展
运行`update_extension.ps1`脚本，如果遇到更新 Stable Diffusion WebUI 扩展失败的情况可尝试重新运行`update_extension.ps1`脚本。


## 设置 Stable Diffusion WebUI 启动参数
要设置 Stable Diffusion WebUI 的启动参数，可以在和`launch.ps1`脚本同级的目录创建一个`launch_args.txt`文件，在文件内写上启动参数，运行 Stable Diffusion WebUI 启动脚本时将自动读取该文件内的启动参数并应用。

>[!NOTE]  
>该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 切换 Stable Diffusion WebUI 分支
运行`switch_branch.ps1`脚本，根据提示选择分支并切换。

支持切换到的分支如下。

- [AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
- [Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)
- [lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)
- [vladmandic/SD.Next](https://github.com/vladmandic/automatic)


## 进入 Stable Diffusion WebUI 所在的 Python 环境
如果需要使用 Python、Pip、Stable Diffusion WebUI 的命令时，请勿将 Stable Diffusion WebUI 的`python`文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是在 Stable Diffusion WebUI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 Stable Diffusion WebUI Env：

```powershell
.\activate.ps1
```

这样就进入 Stable Diffusion WebUI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

或者运行`terminal.ps1`脚本，这将打开 PowerShell 并自动执行`activate.ps1`，此时就进入了 Stable Diffusion WebUI 所在的 Python。


## 获取最新的 SD WebUI Installer 脚本
运行`get_stable_diffusion_webui_installer.ps1`脚本，运行成功后将会把 SD WebUI Installer 保存在`stable-diffusion-webui`文件夹的上一级目录中。


## 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次`stable_diffusion_webui_installer.ps1`重新生成这些脚本。

>[!NOTE]  
>SD WebUI Installer 必须放在`stable-diffusion-webui`文件夹外运行，不知道放哪的可以参考下面的目录结构。

```
$ tree -L 2
.
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── stable-diffusion-webui                        # 这是 Stable Diffusion WebUI 文件夹
│   ├── activate.ps1                              # 进入 Stable Diffusion WebUI Env 的脚本
│   ├── cache                                     # 缓存文件夹
│   ├── download_models.ps1                       # 下载模型的脚本
│   ├── get_stable_diffusion_webui_installer.ps1  # 获取最新的 SD WebUI Installer 的脚本
│   ├── git                                       # Git 目录
│   ├── help.txt                                  # 帮助文档
│   ├── launch.ps1                                # 启动 Stable Diffusion WebUI 的脚本
│   ├── stable-diffusion-webui                    # Stable Diffusion WebUI 路径
│   ├── models                                    # download_models.ps1 下载模型脚本
│   ├── python                                    # Python 目录
│   ├── reinstall_pytorch.ps1                     # 重新安装 PyTorch 的脚本
│   ├── switch_branch.ps1                         # 切换 Stable Diffusion WebUI 分支的脚本
│   ├── settings.ps1                              # 管理 SD WebUI Installer 设置的脚本
│   ├── terminal.ps1                              # 自动打开 PowerShell 并激活 SD WebUI Installer 的虚拟环境脚本
│   ├── update_extension.ps1                      # 更新 Stable Diffusion WebUI 扩展
│   └── update.ps1                                # 更新 Stable Diffusion WebUI 的脚本
├── stable_diffusion_webui_installer.ps1          # SD WebUI Installer 放在 Stable Diffusion WebUI 文件夹外面，和 Stable Diffusion WebUI 文件夹同级
└── QQ Files

8 directories, 9 files
```

>[!WARNING]  
>`stable-diffusion-webui`文件夹的名称切勿修改，修改后将导致 SD WebUI Installer 更新管理脚本时出现异常。


## 设置 HuggingFace 镜像
SD WebUI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`hf_mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源|
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_hf_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。

>[!NOTE]  
>该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 设置 Github 镜像源
SD WebUI Installer 为了加速访问 Github 的速度，加快下载和更新 Stable Diffusion WebUI 的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建`gh_mirror.txt`文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

|可用的 Github 镜像源|
|---|
|https://ghp.ci/https://github.com|
|https://mirror.ghproxy.com/https://github.com|
|https://ghproxy.net/https://github.com|
|https://gitclone.com/github.com|
|https://gh-proxy.com/https://github.com|
|https://ghps.cc/https://github.com|
|https://gh.idayer.com/https://github.com|

如果需要禁用设置 Github 镜像源，在和脚本同级的目录中创建`disable_gh_mirror.txt`文件，再次启动脚本时将禁用 Github 镜像源。

>[!NOTE]  
>该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 设置 Pip 镜像源
SD WebUI Installer 默认启用了 Pip 镜像源加速下载 Python 软件包，如果需要禁用 Pip 镜像源，可以在脚本同级目录创建`disable_pip_mirror.txt`文件，再次运行脚本时将 Pip 源切换至官方源。

>[!NOTE]  
>该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 配置代理
如果出现某些文件无法下载，比如在控制台出现`由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败`之类的报错时，可以尝试配置代理，有以下两种方法。

### 使用系统代理

在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。

### 使用配置文件

在和脚本同级的路径中创建一个`proxy.txt`文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

### 禁用自动设置代理

在和脚本同级的路径中创建一个`disable_proxy.txt`文件，再次启动脚本时将禁用设置代理。

>[!NOTE]  
>1. 配置文件的优先级高于系统代理配置，所以当同时使用了两种方式配置代理，脚本将优先使用配置文件中的代理配置。
>2. 该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 下载模型
可以使用`download_models.ps1`脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。


## Stable Diffusion WebUI 使用方法
推荐的哔哩哔哩 UP 主：
- 秋葉aaaki：https://space.bilibili.com/12566101

Stable Diffusion WebUI 的使用教程：
- https://sdnote.netlify.app/guide/sd_webui
- https://sdnote.netlify.app/help/sd_webui


## 使用绘世启动器
SD WebUI Installer 部署出来的 Stable Diffusion WebUI 可以通过绘世启动器进行启动，使用绘世启动器前需要调整目录结构使绘世启动器能够正确识别到环境。

将`stable-diffusion-webui/python`目录移动到`stable-diffusion-webui/stable-diffusion-webui/python`，`stable-diffusion-webui/git`移动到`stable-diffusion-webui/stable-diffusion-webui/git`。

移动前目录的结构如下。

```
.
├── stable-diffusion-webui
│   ├── activate.ps1
│   ├── cache
│   ├── download_models.ps1
│   ├── get_stable_diffusion_webui_installer.ps1
│   ├── git                           # Git 目录
│   ├── help.txt
│   ├── launch.ps1
│   ├── stable-diffusion-webui        # Stable Diffusion WebUI 路径
│   │   ├── ...
│   │   └── main.py
│   ├── models
│   ├── python                        # Python 目录
│   ├── reinstall_pytorch.ps1
│   ├── switch_branch.ps1
│   ├── settings.ps1
│   ├── terminal.ps1
│   ├── update_extension.ps1
│   └── update.ps1
└── stable_diffusion_webui_installer.ps1          
```

移动 Python 和 Git 之后的目录结构。

```
.
├── stable-diffusion-webui
│   ├── activate.ps1
│   ├── cache
│   ├── download_models.ps1
│   ├── get_stable_diffusion_webui_installer.ps1
│   ├── help.txt
│   ├── launch.ps1
│   ├── stable-diffusion-webui        # Stable Diffusion WebUI 路径
│   │   ├── git                       # Git 目录
│   │   ├── python                    # Python 目录
│   │   ├── ...
│   │   └── main.py
│   ├── models
│   ├── reinstall_pytorch.ps1
│   ├── switch_branch.ps1
│   ├── settings.ps1
│   ├── terminal.ps1
│   ├── update_extension.ps1
│   └── update.ps1
└── stable_diffusion_webui_installer.ps1          
```

再下载绘世启动器放到`stable-diffusion-webui/stable-diffusion-webui`目录中，就可以通过启动器启动 Stable Diffusion WebUI。

|绘世启动器下载|
|---|
|[下载地址 1](https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe)|
|[下载地址 2](https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe)|
|[下载地址 3](https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe)|

如果使用自动的方法，可以参考[命令的使用](#命令的使用)中的[安装绘世启动器并自动配置绘世启动器所需的环境](#安装绘世启动器并自动配置绘世启动器所需的环境)命令，该命令可一键配置下载绘世启动器并配置。


## 重装 Stable Diffusion WebUI
将`stable-diffusion-webui`文件夹中的`stable-diffusion-webui`文件夹删除，然后运行`stable_diffusion_webui_installer.ps1`重新部署 Stable Diffusion WebUI。

>[!NOTE]  
>如果`stable-diffusion-webui`文件夹存放了训练集 / 模型文件，请将这些文件备份后再删除`stable-diffusion-webui`文件夹。


## 重装 Python 环境
如果 Python 环境出现严重损坏，可以将`stable-diffusion-webui/python`和`stable-diffusion-webui/stable-diffusion-webui/python`文件夹删除，然后运行`stable_diffusion_webui_installer.ps1`重新构建 Python 环境。


## 重装 Git
将`stable-diffusion-webui/git`和`stable-diffusion-webui/stable-diffusion-webui/git`文件夹删除，然后运行`stable_diffusion_webui_installer.ps1`重新下载 Git。


## 重装 PyTorch
运行`reinstall_pytorch.ps1`脚本，并根据脚本提示的内容进行操作。


## 卸载 Stable Diffusion WebUI
使用 SD WebUI Installer 安装 Stable Diffusion WebUI 后，所有的文件都存放在`stable-diffusion-webui`文件夹中，只需要删除`stable-diffusion-webui`文件夹即可卸载 Stable Diffusion WebUI。

如果有 Stable Diffusion WebUI 快捷启动方式，可以通过命令进行删除，打开 PowerShell 后，输入以下命令进行删除。
```powershell
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\SD-WebUI.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\SD-WebUI.lnk" -Force
```


## 移动 Stable Diffusion WebUI 的路径
直接将`stable-diffusion-webui`文件夹移动到别的路径即可。

如果启用了自动创建 Stable Diffusion WebUI 快捷启动方式的功能，移动 Stable Diffusion WebUI 后原来的快捷启动方式将失效，需要运行`launch.ps1`更新快捷启动方式。


## 更新 Stable Diffusion WebUI 管理脚本
SD WebUI Installer 的管理脚本在启动时会检查管理脚本的更新，如果有新版本可更新将会提示。

可选择下方 4 种方法中的其中 1 个方法进行更新。


### 直接更新
当检测到有新版的 SD WebUI Installer 时，将询问是否进行更新，输入`y`并回车后将运行 SD WebUI Installer 进行更新。

如果遇到更新终止警告，这是因为 SD WebUI Installer 的管理脚本所在文件夹的名称不是`stable-diffusion-webui`，请按照提示修改文件夹名称为`stable-diffusion-webui`后再次进行更新。


### 使用 SD WebUI Installer 配置管理器进行更新
运行`settings.ps1`，选择`更新 SD WebUI Installer 管理脚本`功能进行更新，更新完成后需关闭 SD WebUI Installer 管理脚本以应用更新。


### 手动运行 SD WebUI Installer 进行更新
运行`get_stable_diffusion_webui_installer.ps1`获取最新的 SD WebUI Installer 后，返回上一个目录并运行`stable_diffusion_webui_installer.ps1`。SD WebUI Installer 在安装过程无报错并完整的运行所有安装流程后，Stable Diffusion WebUI 的管理脚本将会得到更新。


### 使用命令更新
参考[命令的使用](#命令的使用)的方法进入 Stable Diffusion WebUI Env，并运行`Check-stable-diffusion-webui-Installer-Update`命令进行更新。


如果要禁用更新，可以在脚本同级的目录创建`disable_update.txt`文件，这将禁用 SD WebUI Installer 更新检查。

>[!WARNING]  
>通常不建议禁用 SD WebUI Installer 的更新检查，当 Stable Diffusion WebUI 管理脚本有重要更新（如功能性修复）时将得不到及时提示。

>[!NOTE]  
>该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 设置 uv 包管理器
SD WebUI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个`disable_uv.txt`文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

>[!NOTE]  
>1. uv 包管理器对网络的稳定性要求更高，在网络不稳定时可能会出现下载软件包出错的问题，可尝试重新运行，或者禁用 uv，这时将切换成 Pip 作为 Python 包管理器，Pip 在网络稳定性差的情况下不容易出错，但这将降低 Python 软件包的安装速度。
>2. 当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。
>3. 该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 创建快捷启动方式
在脚本同级目录创建`enable_shortcut.txt`文件，当运行`launch.ps1`时将会自动创建快捷启动方式，并添加到 Windows 桌面和 Windows 开始菜单中，下次启动时可以使用快捷方式启动 Stable Diffusion WebUI。

>[!NOTE]  
>1. 如果 Stable Diffusion WebUI 的路径发生移动，需要重新运行`launch.ps1`更新快捷启动方式。
>2. 该设置可通过[管理 SD WebUI Installer 设置](#管理-sd-webui-installer-设置)中提到的的`settings.ps1`进行修改。


## 管理 SD WebUI Installer 设置
运行`settings.ps1`，根据提示进行设置管理和调整。


## SD WebUI Installer 对 Python / Git 环境的识别
SD WebUI Installer 通常情况下不会去调用系统环境中的 Python / Git，所以在安装过程会安装一个独立的 Python / Git 避免收到系统环境中的 Python / Git 影响。

SD WebUI Installer 可以识别到的 Python 路径为`stable-diffusion-webui/python`和`stable-diffusion-webui/stable-diffusion-webui/python`，当两者同时存在时，优先使用后者。

可以识别到的 Git 路径为`stable-diffusion-webui/git`和`stable-diffusion-webui/stable-diffusion-webui/git`，当两者同时存在时，优先使用后者。

如果这两个路径 Python / Git 都不存在时，此时 Stable Diffusion WebUI 的管理脚本将会调用系统环境中的 Python / Git，这可能会带来不好的结果，所以出现这种情况时就需要运行 SD WebUI Installer 重新安装 Python / Git。


## 运行脚本时出现中文乱码
这可能是 Windows 系统中启用了 UTF 8 编码，可以按照下列方法解决。

1. 按下`Win + R`键，输入`control`后回车启动控制面板。
2. 点击`时钟和区域`->`区域`
3. 在弹出的区域设置窗口中点击顶部的`管理`，再点击`更改系统区域设置`.
4. 在弹出的窗口中将`使用 Unicode UTF-8 提供全球语言支持`取消勾选，然后一直点击确定保存设置，并重启电脑。


## 无法使用 PowerShell 运行
运行 PowerShell 脚本时出现以下错误。

```
.\stable_diffusion_webui_installer.ps1 : 无法加载文件 D:\stable-diffusion-webui\stable_diffusion_webui_installer.ps1。
未对文件 D:\stable-diffusion-webui\stable_diffusion_webui_installer.ps1进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符: 1
+ .\stable_diffusion_webui_installer.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~
   + CategoryInfo          : SecurityError: (:) []，PSSecurityException
   + FullyQualifiedErrorId : UnauthorizedAccess
```

或者右键运行 PowerShell 脚本时闪一下 PowerShell 的界面后就消失了。

这是因为未解除 Windows 系统对运行 PowerShell 脚本的限制，请使用管理员权限打开 PowerShell，运行下面的命令。

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

或者使用[自动环境配置脚本](#使用自动环境配置脚本)解除 Windows 系统对运行 PowerShell 脚本的限制。


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
运行 SD WebUI Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将`stable-diffusion-webui/cache/pip`文件夹删除，再重新运行 SD WebUI Installer。


## CUDA out of memory
确认显卡的显存大小是否满足训练要求（显存最低要求 > 6G），如果满足，重新调整训练参数。


## DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。


## 以一种访问权限不允许的方式做了一个访问套接字的尝试
启动 Stable Diffusion WebUI 时出现以下的错误。
```
ERROR: [Error 13] error while attempting to bind on address ('127.0.0.1', 28000): 以一种访问权限不允许的方式做了一个访问套接字的尝试。
```

这是因为该端口被其他软件占用，Stable Diffusion WebUI 无法使用。可尝试将占用该端口的软件关闭，或者在`launch.ps1`所在目录创建`launch_args.txt`文件，在该文件中写上启动参数把 Stable Diffusion WebUI 端口修改，如`--port 8888`，保存`launch_args.txt`文件后使用`launch.ps1`重新启动 Stable Diffusion WebUI。

>[!NOTE]  
>设置 Stable Diffusion WebUI 启动参数的方法可参考[设置 Stable Diffusion WebUI 启动参数](#设置-stable-diffusion-webui-启动参数)。


## Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。


## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。


### 使用自动环境激活脚本
运行`terminal.ps1`后将自动打开 PowerShell 并激活 Stable Diffusion WebUI Env。


### 手动输入命令激活
在`stable-diffusion-webui`文件夹打开 PowerShell，输入下面的命令激活 Stable Diffusion WebUI Env：

```powershell
.\activate.ps1
```
>[!NOTE]  
>在 PowerShell 中一定要显示`[SD WebUI Env]`才算进入了环境，这样才能使用下面的命令。


## 常用命令

### 清理安装时产生的 Pip 缓存
```powershell
python -m pip cache purge
```


### 安装某个 Pip 软件包
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

>推荐使用`python -m pip`的写法，`pip`的写法也可用。SD WebUI Installer 默认将`pip`命令链接到`python -m pip`避免直接调用`pip`。  
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
aria2c <url> -c -s 16 -x 16 -d <dir> -o <output_file_name>
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


### 安装 Stable Diffusion WebUI 扩展
```powershell
# <url> 为 Stable Diffusion WebUI 扩展的下载链接
Install-stable-diffusion-webui-Extension <url>
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


### 列出 Stable Diffusion WebUI 已存在的扩展
```powershell
List-Extension
```


### 列出 SD WebUI Installer 内置命令
```powershell
List-CMD
```


### 检查 SD WebUI Installer 更新
```powershell
Check-stable-diffusion-webui-Installer-Update
```

### 查看并切换 Stable Diffusion WebUI 的版本
```powershell
# 列出当前的所有版本
git -C stable-diffusion-webui tag
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
git -C stable-diffusion-webui reset --hard --recurse-submodules <Git Tag>

# 使用 git log 查看某个提交信息对应的 Hash 值
git -C stable-diffusion-webui log
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
git -C stable-diffusion-webui reset --hard --recurse-submodules <Git Commit Hash>
```
