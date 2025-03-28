<div align="center">

# SD-Trainer-Script Installer

_✨快速部署训练环境_

</div>

# 目录
- [SD-Trainer-Script Installer](#sd-trainer-script-installer)
- [目录](#目录)
- [简介](#简介)
- [环境配置](#环境配置)
  - [1. 使用自动环境配置脚本](#1-使用自动环境配置脚本)
  - [2. 手动使用命令配置](#2-手动使用命令配置)
    - [2.1 解除脚本限制](#21-解除脚本限制)
    - [2.2 启用 Windows 长路径支持](#22-启用-windows-长路径支持)
- [安装](#安装)
- [使用](#使用)
  - [启动训练脚本](#启动训练脚本)
  - [更新 SD-Trainer-Script](#更新-sd-trainer-script)
  - [切换 SD-Trainer-Script 分支](#切换-sd-trainer-script-分支)
  - [进入 SD-Trainer-Script 所在的 Python 环境](#进入-sd-trainer-script-所在的-python-环境)
  - [获取最新的 SD-Trainer-Script Installer 并运行](#获取最新的-sd-trainer-script-installer-并运行)
  - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
  - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
  - [设置 Github 镜像源](#设置-github-镜像源)
  - [设置 Pip 镜像源](#设置-pip-镜像源)
  - [配置代理](#配置代理)
    - [1. 使用系统代理](#1-使用系统代理)
    - [2. 使用配置文件](#2-使用配置文件)
    - [禁用自动设置代理](#禁用自动设置代理)
  - [添加模型](#添加模型)
  - [模型训练的方法](#模型训练的方法)
  - [重装 SD-Trainer-Script](#重装-sd-trainer-script)
  - [重装 Python 环境](#重装-python-环境)
  - [重装 Git](#重装-git)
  - [重装 PyTorch](#重装-pytorch)
  - [卸载 SD-Trainer-Script](#卸载-sd-trainer-script)
  - [移动 SD-Trainer-Script 的路径](#移动-sd-trainer-script-的路径)
  - [更新 SD-Trainer-Script 管理脚本](#更新-sd-trainer-script-管理脚本)
    - [1. 直接更新](#1-直接更新)
    - [2. 使用 SD-Trainer-Script Installer 配置管理器进行更新](#2-使用-sd-trainer-script-installer-配置管理器进行更新)
    - [3. 运行 SD-Trainer-Script Installer 进行更新](#3-运行-sd-trainer-script-installer-进行更新)
    - [4. 使用命令更新](#4-使用命令更新)
    - [禁用 SD-Trainer-Script Installer 更新检查](#禁用-sd-trainer-script-installer-更新检查)
  - [设置 uv 包管理器](#设置-uv-包管理器)
  - [管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-script-installer-设置)
  - [SD-Trainer-Script Installer 对 Python / Git 环境的识别](#sd-trainer-script-installer-对-python--git-环境的识别)
  - [使用命令运行 SD-Trainer-Script Installer](#使用命令运行-sd-trainer-script-installer)
  - [SD-Trainer-Script Installer 构建模式和普通安装模式](#sd-trainer-script-installer-构建模式和普通安装模式)
  - [运行脚本时出现中文乱码](#运行脚本时出现中文乱码)
  - [无法使用 PowerShell 运行](#无法使用-powershell-运行)
  - [SD-Trainer-Script 提示'Torch is not able to use GPU'](#sd-trainer-script-提示torch-is-not-able-to-use-gpu)
  - [PowerShell 中出现 xFormers 报错](#powershell-中出现-xformers-报错)
  - [ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE](#error-these-packages-do-not-match-the-hashes-from-the-requirements-file)
  - [RuntimeError: Error(s) in loading state\_dict for UNet2DConditionModel](#runtimeerror-errors-in-loading-state_dict-for-unet2dconditionmodel)
  - [UnicodeDecodeError: 'utf-8' codec can't decode byte xxxx in position xxx: invalid continuation byte](#unicodedecodeerror-utf-8-codec-cant-decode-byte-xxxx-in-position-xxx-invalid-continuation-byte)
  - [RuntimeError: NaN detected in latents: X:\\xxx\\xxx\\xx.png](#runtimeerror-nan-detected-in-latents-xxxxxxxxxpng)
  - [CUDA out of memory](#cuda-out-of-memory)
  - [DefaultCPUAllocator: not enough memory](#defaultcpuallocator-not-enough-memory)
  - [Loss?](#loss)
  - [训练素材中图片的分辨率不一致，而且有些图片的分辨率很大，需要裁剪?](#训练素材中图片的分辨率不一致而且有些图片的分辨率很大需要裁剪)
  - [AssertError: caption file is empty: xxx\\xxxxxx\\xx\\2\_xxx\\xxxxxxx.txt](#asserterror-caption-file-is-empty-xxxxxxxxxxx2_xxxxxxxxxxtxt)
  - [NotImplemenredError: Cannot cppy out of meta tensor; no data! Please use torch.nn.Module.to\_empty() instead of torch.nn.Module.to() when moving module from mera to a different device.](#notimplemenrederror-cannot-cppy-out-of-meta-tensor-no-data-please-use-torchnnmoduleto_empty-instead-of-torchnnmoduleto-when-moving-module-from-mera-to-a-different-device)
  - [Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.](#microsoft-visual-c-redistributable-is-not-installed-this-may-lead-to-the-dll-load-failure)
  - [命令的使用](#命令的使用)
    - [1. 使用自动环境激活脚本](#1-使用自动环境激活脚本)
    - [2. 手动输入命令激活](#2-手动输入命令激活)
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
    - [列出 SD-Trainer-Script Installer 内置命令](#列出-sd-trainer-script-installer-内置命令)
    - [检查 SD-Trainer-Script Installer 更新](#检查-sd-trainer-script-installer-更新)
    - [查看并切换 SD-Trainer-Script 的版本](#查看并切换-sd-trainer-script-的版本)
    - [将 LoRA 模型融进 Stable Diffusion 模型中](#将-lora-模型融进-stable-diffusion-模型中)
    - [查看 Git / Python 命令实际调用的路径](#查看-git--python-命令实际调用的路径)
  - [编写训练脚本](#编写训练脚本)
    - [如何编写](#如何编写)
    - [kohya-ss/sd-scripts 训练命令参考](#kohya-sssd-scripts-训练命令参考)
    - [使用 TensorBoard 查看训练情况](#使用-tensorboard-查看训练情况)

***

# 简介
一个在 Windows 系统上部署 SD-Trainer-Script 的 PowerShell 脚本，并提供不同的管理工具。

支持部署的 SD-Trainer-Script 分支如下。

- [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [~~bghira/SimpleTuner~~](https://github.com/bghira/SimpleTuner)
- [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)
- [a-r-r-o-w/finetrainers](https://github.com/a-r-r-o-w/finetrainers)
- [tdrussell/diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)
- [kohya-ss/musubi-tuner](https://github.com/kohya-ss/musubi-tuner)

>[!WARNING]  
>此部署工具部署的训练工具需要一定的编写训练命令基础，如果需要使用简单的模型训练工具，请使用 [SD-Trainer Installer](./sd_trainer_installer.md) 部署训练工具并使用。

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
SD-Trainer-Script Installer 默认情况下安装的是 [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts) 分支，如果需要指定安装的分支，需要在 SD-Trainer-Script Installer 所在路径创建配置文件，以下为不同配置文件对应的 SD-Trainer-Script 分支。

|配置文件名|对应安装的分支|
|---|---|
|`install_sd_scripts.txt`|[kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)|
|~~`Install_simple_tuner.txt`~~|[~~bghira/SimpleTuner~~](https://github.com/bghira/SimpleTuner)|
|`install_ai_toolkit.txt`|[ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)|
|`install_finetrainers.txt`|[a-r-r-o-w/finetrainers](https://github.com/a-r-r-o-w/finetrainers)|
|`install_diffusion_pipe.txt`|[tdrussell/diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)|
|`install_musubi_tuner.txt`|[kohya-ss/musubi-tuner](https://github.com/kohya-ss/musubi-tuner)|

创建配置文件后，将 SD-Trainer-Script Installer 下载至本地，和配置文件放在一起，如下所示。

```
$ tree -L 1
.
├── 119966207_p0_master1200.jpg
├── 437A9AE81C043B83110F55316EC7789E.png
├── BaiduNetdiskDownload
├── BaiduNetdiskWorkspace
├── install_simple_tuner.txt  # 这是配置文件
├── QQDownloads
├── sd_trainer_installer.ps1  # 这是 SD-Trainer-Script Installer
├── z-noob_artist.csv
└── 得意黑_横屏.prtextstyle

4 directories, 6 files
```

右键`sd_trainer_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 SD-Trainer-Script Installer 将安装 SD-Trainer-Script 至本地。

>[!NOTE]  
>SD-Trainer-Script Installer 在安装时还可以通过其他配置文件指定其他参数, 可阅读以下的说明：
>- [设置 Github 镜像源](#设置-github-镜像源)
>- [设置 Pip 镜像源](#设置-pip-镜像源)
>- [设置 uv 包管理器](#设置-uv-包管理器)
>- [配置代理](#配置代理)
>
>通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

|SD-Trainer-Script Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1)|

在 SD-Trainer-Script Installer 成功安装 SD-Trainer-Script 后，在`SD-Trainer-Script`文件夹中可以看到 SD-Trainer-Script 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 SD-Trainer-Script Installer。

>[!NOTE]  
>1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](#环境配置)中的方法进行解除。
>2. SD-Trainer-Script Installer 支持使用在命令行中通过参数配置 SD-Trainer-Script 的安装参数，具体说明可阅读[使用命令运行 SD-Trainer-Script Installer](#使用命令运行-sd-trainer-script-installer)。

***

# 使用
在`SD-Trainer-Script`文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。在`sd-scripts`文件夹中也有 PowerShell 脚本，但不建议使用该文件夹中的脚本进行运行。


## 启动训练脚本
编写并运行`train.ps1`脚本。

训练脚本中的内容需要自行编写，编写方法请参考[编写训练脚本](#编写训练脚本)部分的内容。


## 更新 SD-Trainer-Script
运行`update.ps1`脚本，如果遇到更新 SD-Trainer-Script 失败的情况可尝试重新运行`update.ps1`脚本。


## 切换 SD-Trainer-Script 分支
运行`switch_branch.ps1`脚本，根据提示选择分支并切换。

支持切换到的分支如下。

- [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [~~bghira/SimpleTuner~~](https://github.com/bghira/SimpleTuner)
- [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)
- [a-r-r-o-w/finetrainers](https://github.com/a-r-r-o-w/finetrainers)
- [tdrussell/diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)
- [kohya-ss/musubi-tuner](https://github.com/kohya-ss/musubi-tuner)

>[!NOTE]  
>切换分支后，因为不同分支需要的依赖版本不一致，需要对依赖进行更新，可通过运行`update.ps1`进行依赖更新，保证 SD-Trainer-Script 能够正常运行。


## 进入 SD-Trainer-Script 所在的 Python 环境
如果需要使用 Python、Pip、SD-Trainer-Script 的命令时，请勿将 SD-Trainer-Script 的`python`文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行`terminal.ps1`脚本，这将打开 PowerShell 并自动执行`activate.ps1`，此时就进入了 SD-Trainer-Script 所在的 Python。

或者是在 SD-Trainer-Script 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 SD-Trainer-Script Env：

```powershell
.\activate.ps1
```

这样就进入 SD-Trainer-Script 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。


## 获取最新的 SD-Trainer-Script Installer 并运行
运行`launch_sd_trainer_installer.ps1`脚本，如果下载成功将会把 SD-Trainer-Script Installer 下载到`cache`目录中并运行。


## 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次`launch_sd_trainer_installer.ps1`重新生成这些脚本。

```
$ tree -L 2
.
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── SD-Trainer-Script                            # 这是 SD-Trainer-Script 文件夹
│   ├── activate.ps1                      # 进入 SD-Trainer-Script Env 的脚本
│   ├── cache                             # 缓存文件夹
│   ├── download_models.ps1               # 下载模型的脚本
│   ├── launch_sd_trainer_installer.ps1   # 获取最新的 SD-Trainer-Script Installer 并运行的脚本
│   ├── git                               # Git 目录
│   ├── help.txt                          # 帮助文档
│   ├── init.ps1                          # 初始化训练环境的脚本
│   ├── sd-scripts                        # SD-Trainer-Script 路径
│   ├── models                            # download_models.ps1 下载模型脚本下载模型的路径
│   ├── python                            # Python 目录
│   ├── reinstall_pytorch.ps1             # 重新安装 PyTorch 的脚本
│   ├── switch_branch.ps1                 # 切换 SD-Trainer-Script 分支的脚本
│   ├── settings.ps1                      # 管理 SD-Trainer-Script Installer 设置的脚本
│   ├── terminal.ps1                      # 自动打开 PowerShell 并激活 SD-Trainer-Script Installer 的虚拟环境脚本
│   └── update.ps1                        # 更新 SD-Trainer-Script 的脚本
├── sd_trainer_installer.ps1              # SD-Trainer-Script Installer 一般放在 SD-Trainer-Script 文件夹外面，和 SD-Trainer-Script 文件夹同级
└── QQ Files

8 directories, 9 files
```


## 设置 HuggingFace 镜像
>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

SD-Trainer-Script Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`hf_mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源|
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_hf_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。


## 设置 Github 镜像源
>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

SD-Trainer-Script Installer 为了加速访问 Github 的速度，加快下载和更新 SD-Trainer-Script 的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建`gh_mirror.txt`文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

|可用的 Github 镜像源|
|---|
|https://ghfast.top/https://github.com|
|https://mirror.ghproxy.com/https://github.com|
|https://ghproxy.net/https://github.com|
|https://gh.api.99988866.xyz/https://github.com|
|https://gitclone.com/github.com|
|https://gh-proxy.com/https://github.com|
|https://ghps.cc/https://github.com|
|https://gh.idayer.com/https://github.com|

如果需要禁用设置 Github 镜像源，在和脚本同级的目录中创建`disable_gh_mirror.txt`文件，再次启动脚本时将禁用 Github 镜像源。


## 设置 Pip 镜像源
>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

SD-Trainer-Script Installer 默认启用了 Pip 镜像源加速下载 Python 软件包，如果需要禁用 Pip 镜像源，可以在脚本同级目录创建`disable_pip_mirror.txt`文件，再次运行脚本时将 Pip 源切换至官方源。


## 配置代理
如果出现某些文件无法下载，比如在控制台出现`由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败`之类的报错时，可以尝试配置代理，有以下两种方法。

### 1. 使用系统代理
在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。


### 2. 使用配置文件
>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

在和脚本同级的路径中创建一个`proxy.txt`文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

>[!NOTE]  
>**配置文件**的优先级高于**系统代理**配置，所以当同时使用了两种方式配置代理，脚本将优先使用**配置文件**中的代理配置。


### 禁用自动设置代理
>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

在和脚本同级的路径中创建一个`disable_proxy.txt`文件，再次启动脚本时将禁用设置代理。


## 添加模型
在 SD-Trainer-Script 中可以选择本地已下载的模型，如果没有下载某些用于训练的模型（非融合模型），可以使用`download_models.ps1`脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。


## 模型训练的方法
推荐的哔哩哔哩 UP 主：
- 青龙圣者：https://space.bilibili.com/219296
- 秋葉aaaki：https://space.bilibili.com/12566101
- 琥珀青葉：https://space.bilibili.com/507303431
观看这些 UP 主的视频可获得一些训练模型的教程。

其他的一些训练模型的教程：
- https://rentry.org/59xed3
- https://civitai.com/articles/2056
- https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
- https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
- https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
- https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
- https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
- https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora

除了上面的教程，也可以通过哔哩哔哩、Google 等平台搜索教程。


## 重装 SD-Trainer-Script
将`SD-Trainer-Script`文件夹中的`sd-scripts`文件夹删除，然后运行`launch_sd_trainer_installer.ps1`重新部署 SD-Trainer-Script。

>[!NOTE]  
>如果`sd-scripts`文件夹存放了训练集 / 模型文件，请将这些文件备份后再删除`sd-scripts`文件夹。


## 重装 Python 环境
如果 Python 环境出现严重损坏，可以将`SD-Trainer-Script/python`和`SD-Trainer-Script/sd-scripts/python`文件夹删除，然后运行`launch_sd_trainer_installer.ps1`重新构建 Python 环境。


## 重装 Git
将`SD-Trainer-Script/git`和`SD-Trainer-Script/sd-scripts/git`文件夹删除，然后运行`launch_sd_trainer_installer.ps1`重新下载 Git。


## 重装 PyTorch
运行`reinstall_pytorch.ps1`脚本，并根据脚本提示的内容进行操作。


## 卸载 SD-Trainer-Script
使用 SD-Trainer-Script Installer 安装 SD-Trainer-Script 后，所有的文件都存放在`SD-Trainer-Script`文件夹中，只需要删除`SD-Trainer-Script`文件夹即可卸载 SD-Trainer-Script。

如果有 SD-Trainer-Script 快捷启动方式，可以通过命令进行删除，打开 PowerShell 后，输入以下命令进行删除。
```powershell
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\SD-Trainer-Script.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\SD-Trainer-Script.lnk" -Force
```


## 移动 SD-Trainer-Script 的路径
直接将`SD-Trainer-Script`文件夹移动到别的路径即可。


## 更新 SD-Trainer-Script 管理脚本
SD-Trainer-Script Installer 的管理脚本在启动时会检查管理脚本的更新，如果有新版本可更新将会提示。

可选择下方 4 种方法中的其中 1 个方法进行更新。


### 1. 直接更新
当检测到有新版的 SD-Trainer-Script Installer 时，将询问是否进行更新，输入`y`并回车后将运行 SD-Trainer-Script Installer 进行更新。


### 2. 使用 SD-Trainer-Script Installer 配置管理器进行更新
运行`settings.ps1`，选择`更新 SD-Trainer-Script Installer 管理脚本`功能进行更新，更新完成后需关闭 SD-Trainer-Script Installer 管理脚本以应用更新。


### 3. 运行 SD-Trainer-Script Installer 进行更新
运行`launch_sd_trainer_installer.ps1`获取最新的 SD-Trainer-Script Installer 后，脚本会自动运行新版 SD-Trainer-Script Installer 进行更新。


### 4. 使用命令更新
参考[命令的使用](#命令的使用)的方法进入 SD-Trainer-Script Env，并运行`Check-SD-Trainer-Script-Installer-Update`命令进行更新。


### 禁用 SD-Trainer-Script Installer 更新检查
>[!WARNING]  
>通常不建议禁用 SD-Trainer-Script Installer 的更新检查，当 SD-Trainer-Script 管理脚本有重要更新（如功能性修复）时将得不到及时提示。

>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

如果要禁用更新，可以在脚本同级的目录创建`disable_update.txt`文件，这将禁用 SD-Trainer-Script Installer 更新检查。


## 设置 uv 包管理器
>[!NOTE]  
>该设置可通过[管理 SD-Trainer-Script Installer 设置](#管理-sd-trainer-installer-设置)中提到的的`settings.ps1`进行修改。

SD-Trainer-Script Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个`disable_uv.txt`文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

>[!NOTE]  
>1. 当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。
>2. uv 包管理器对网络的稳定性要求更高，在网络不稳定时可能会出现下载软件包出错的问题，可尝试重新运行，或者禁用 uv，这时将切换成 Pip 作为 Python 包管理器，Pip 在网络稳定性差的情况下不容易出错，但这将降低 Python 软件包的安装速度。


## 管理 SD-Trainer-Script Installer 设置
运行`settings.ps1`，根据提示进行设置管理和调整。


## SD-Trainer-Script Installer 对 Python / Git 环境的识别
SD-Trainer-Script Installer 通常情况下不会去调用系统环境中的 Python / Git，所以在安装过程会安装一个独立的 Python / Git 避免收到系统环境中的 Python / Git 影响。

SD-Trainer-Script Installer 可以识别到的 Python 路径为`SD-Trainer-Script/python`和`SD-Trainer-Script/sd-scripts/python`，当两者同时存在时，优先使用后者。

可以识别到的 Git 路径为`SD-Trainer-Script/git`和`SD-Trainer-Script/sd-scripts/git`，当两者同时存在时，优先使用后者。

如果这两个路径 Python / Git 都不存在时，此时 SD-Trainer-Script 的管理脚本将会调用系统环境中的 Python / Git，这可能会带来不好的结果，所以出现这种情况时就需要运行 SD-Trainer-Script Installer 重新安装 Python / Git。


## 使用命令运行 SD-Trainer-Script Installer
SD-Trainer-Script Installer 支持使用命令参数设置安装 SD-Trainer-Script 的参数，支持的参数如下。

|参数|作用|
|---|---|
|`-InstallPath` <SD-Trainer-Script 安装路径>|指定安装 SD-Trainer-Script 的路径，使用绝对路径进行指定。|
|`-InstallBranch` <SD-Trainer-Script 分支名>|指定 SD-Trainer-Script Installer 安装的 SD-Trainer-Script 的分支，SD-Trainer-Script 分支名对应的分支如下：</br>`sd_scripts`：[kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)</br>~~`Simple_tuner`：[bghira/SimpleTuner](https://github.com/bghira/SimpleTuner)~~</br>`ai_toolkit`：[ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)</br>`finetrainers`：[a-r-r-o-w/finetrainers](https://github.com/a-r-r-o-w/finetrainers)</br>`diffusion_pipe`：[tdrussell/diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)</br>`musubi_tuner`：[kohya-ss/musubi-tuner](https://github.com/kohya-ss/musubi-tuner)|
|`-UseUpdateMode`|使用 SD-Trainer-Script Installer 的更新脚本模式，不进行 SD-Trainer-Script 的安装。|
|`-DisablePipMirror`|禁用 SD-Trainer-Script Installer 使用 Pip 镜像源，使用 Pip 官方源下载 Python 软件包。|
|`-DisableProxy`|禁用 SD-Trainer-Script Installer 自动设置代理服务器。|
|`-UseCustomProxy` <代理服务器地址>|使用自定义的代理服务器地址。|
|`-DisableUV`|禁用 SD-Trainer-Script Installer 使用 uv 安装 Python 软件包，使用 Pip 安装 Python 软件包。|
|`-DisableGithubMirror`|禁用 SD-Trainer-Script Installer 自动设置 Github 镜像源。|
|`-UseCustomGithubMirror` <Github 镜像站地址>|使用自定义的 Github 镜像站地址。</br>可用的 Github 镜像站地址:</br>`https://ghfast.top/https://github.com`</br>`https://mirror.ghproxy.com/https://github.com`</br>`https://ghproxy.net/https://github.com`</br>`https://gh.api.99988866.xyz/https://github.com`</br>`https://gitclone.com/github.com`</br>`https://gh-proxy.com/https://github.com`</br>`https://ghps.cc/https://github.com`</br>`https://gh.idayer.com/https://github.com`|
|`-BuildMode`|启用 SD-Trainer-Script Installer 构建模式，在基础安装流程结束后将调用 SD-Trainer-Script Installer 管理脚本执行剩余的安装任务，并且出现错误时不再暂停 SD-Trainer-Script Installer 的执行，而是直接退出。<br>当指定调用多个 SD-Trainer-Script Installer 脚本时，将按照优先顺序执行 (按从上到下的顺序)：<br><li>`reinstall_pytorch.ps1`：对应`-BuildWithTorch`，`-BuildWithTorchReinstall`参数<br><li>`switch_branch.ps1`：对应`-BuildWitchBranch`参数<br><li>`download_models.ps1`：对应`-BuildWitchModel`参数<br><li>`update.ps1`：对应`-BuildWithUpdate`参数<br><li>`init.ps1`：对应`-BuildWithLaunch`参数|
|`-BuildWithUpdate`|(需添加`-BuildMode`启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 update.ps1 脚本，更新 SD-Trainer-Script 内核。|
|`-BuildWithLaunch`|(需添加`-BuildMode`启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 init.ps1 脚本，执行启 动 SD-Trainer-Script 前的环境检查流程，但跳过启动 SD-Trainer-Script。|
|`-BuildWithTorch` <PyTorch 版本编号>|(需添加`-BuildMode`启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 reinstall_pytorch.ps1 脚本，根据 PyTorch 版本编号安装指定的 PyTorch 版本。<br>PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看。|
|`-BuildWithTorchReinstall`|(需添加`-BuildMode`启用 SD-Trainer-Script Installer 构建模式，并且添加 -BuildWithTorch) 在 SD-Trainer-Script Installer 构建模式下，执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装。|
|`-BuildWitchModel` <模型编号列表>|(需添加`-BuildMode`启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 download_models.ps1 脚本，根据模型编号列表下载指定的模型。<br>模型编号可运行 download_models.ps1 脚本进行查看。|
|`-BuildWitchBranch` <SD-Trainer-Script 分支编号>|(需添加`-BuildMode`启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 switch_branch.ps1 脚本，根据 SD-Trainer-Script 分支编号切换到对应的 SD-Trainer-Script 分支。<br>SD-Trainer-Script 分支编号可运行 switch_branch.ps1 脚本进行查看。|
|`-DisableUpdate`|(仅在 SD-Trainer-Script Installer 构建模式下生效，并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 SD-Trainer-Script Installer 更新检查。|
|-DisableHuggingFaceMirror|(仅在 SD-Trainer-Script Installer 构建模式下生效，并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 HuggingFace 镜像源，不使用 HuggingFace 镜像源下载文件。|
|`-UseCustomHuggingFaceMirror` <HuggingFace 镜像源地址>|(仅在 SD-Trainer-Script Installer 构建模式下生效，并且只作用于 SD-Trainer-Script Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址，例如代理服务器地址为 https://hf-mirror.com，则使用`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`设置 HuggingFace 镜像源地址。|
|`-DisableCUDAMalloc`|(仅在 SD-Trainer-Script Installer 构建模式下生效，并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 SD-Trainer-Script Installer 通过`PYTORCH_CUDA_ALLOC_CONF`环境 变量设置 CUDA 内存分配器。|
|`-DisableEnvCheck`|(仅在 SD-Trainer-Script Installer 构建模式下生效，并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 SD-Trainer-Script Installer 检查 SD-Trainer-Script 运行环境中 存在的问题，禁用后可能会导致 SD-Trainer-Script 环境中存在的问题无法被发现并修复。|
|`-Help`|显示 SD-Trainer-Script Installer 可用的命令行参数。|

例如在`D:/Download`这个路径安装 [bmaltais/Kohya GUI](https://github.com/bmaltais/kohya_ss)，则在 SD-Trainer-Script Installer 所在路径打开 PowerShell，使用参数运行 SD-Trainer-Script Installer。

```powershell
.\sd_trainer_installer.ps1 -InstallPath "D:/Download" -InstallBranch "kohya_gui"
```


## SD-Trainer-Script Installer 构建模式和普通安装模式
SD-Trainer-Script Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 SD-Trainer-Script Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，模型安装，运行环境检查和修复等并不会执行，这些步骤是在 SD-Trainer-Script Installer 管理脚本中进行，如执行`init.ps1`，`reinstall_pytorch.ps1`脚本等。

而 SD-Trainer-Script Installer 构建模式允许在执行基础安装流程后，调用 SD-Trainer-Script Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 SD-Trainer-Script Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读[使用命令运行 SD-Trainer-Script Installer](#使用命令运行-sd-trainer-script-installer)中的参数说明。

>[!IMPORTANT]  
>通常安装 SD-Trainer-Script 并不需要使用 SD-Trainer-Script Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。

使用 Github Action 提供的容器可用于运行 SD-Trainer-Script Installer 并启用构建模式，实现自动化制作整合包，Github Action 工作流代码可参考：[build_sd_scripts.yml · licyk/sd-webui-all-in-one](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/workflows/build_sd_scripts.yml)


## 运行脚本时出现中文乱码
这可能是 Windows 系统中启用了 UTF 8 编码，可以按照下列方法解决。

1. 按下`Win + R`键，输入`control`后回车启动控制面板。
2. 点击`时钟和区域`->`区域`
3. 在弹出的区域设置窗口中点击顶部的`管理`，再点击`更改系统区域设置`.
4. 在弹出的窗口中将`使用 Unicode UTF-8 提供全球语言支持`取消勾选，然后一直点击确定保存设置，并重启电脑。


## 无法使用 PowerShell 运行
运行 PowerShell 脚本时出现以下错误。

```
.\sd_trainer_installer.ps1 : 无法加载文件 D:\SD-Trainer-Script\sd_trainer_installer.ps1。
未对文件 D:\SD-Trainer-Script\sd_trainer_installer.ps1进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符: 1
+ .\sd_trainer_installer.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~
   + CategoryInfo          : SecurityError: (:) []，PSSecurityException
   + FullyQualifiedErrorId : UnauthorizedAccess
```

或者右键运行 PowerShell 脚本时闪一下 PowerShell 的界面后就消失了。

这是因为未解除 Windows 系统对运行 PowerShell 脚本的限制，请使用管理员权限打开 PowerShell，运行下面的命令。

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

或者使用[自动环境配置脚本](#1-使用自动环境配置脚本))解除 Windows 系统对运行 PowerShell 脚本的限制。


## SD-Trainer-Script 提示'Torch is not able to use GPU'
尝试将显卡驱动更至最新，确保显卡驱动支持的 CUDA 版本大于或等于 PyTorch 中所带的 CUDA 版本，或者使用`reinstall_pytorch.ps1`重装 PyTorch。

>[!NOTE]  
>Nvidia 显卡驱动下载：https://www.nvidia.cn/geforce/drivers

如果要查询驱动最高支持的 CUDA 版本，可以打开 PowerShell，运行下方的命令。

```powershell
nvidia-smi
```

可以看到 PowerShell 中显示的以下信息。

```
Fri Jun  7 19:07:00 2024
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 552.44                 Driver Version: 552.44         CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                     TCC/WDDM  | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 4060 ...  WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   51C    P0             16W /   95W |       0MiB /   8188MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

`CUDA Version`后面显示的数字即为显卡驱动支持最高的 CUDA 版本。


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
运行 SD-Trainer-Script Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将`SD-Trainer-Script/cache/pip`文件夹删除，再重新运行 SD-Trainer-Script Installer。


## RuntimeError: Error(s) in loading state_dict for UNet2DConditionModel
检查训练参数是否正确，确认是否选择对应大模型版本的训练参数。


## UnicodeDecodeError: 'utf-8' codec can't decode byte xxxx in position xxx: invalid continuation byte
检查训练参数中是否存在中文，如模型文件名是否包含中文等。


## RuntimeError: NaN detected in latents: X:\xxx\xxx\xx.png
检查图片是否有问题，如果是训练 SDXL 的 LoRA，请外挂一个 [sdxl_fp16_fix](https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors) 的 VAE 或者使用 BF16 精度进行训练。


## CUDA out of memory
确认显卡的显存大小是否满足训练要求（显存最低要求 > 6G），如果满足，重新调整训练参数。


## DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。


## Loss?
当 Loss 不为 nan 或者大于 1 时没必要看。想要看练出来的模型效果如何，直接用模型进行跑图测试，Loss 并不能准确的代表训练出来的模型的好坏。


## 训练素材中图片的分辨率不一致，而且有些图片的分辨率很大，需要裁剪?
请使用 SD-Trainer-Script 的 arb 桶，这将自动处理不同分辨率的图片，无需手动进行图片裁剪。


## AssertError: caption file is empty: xxx\xxxxxx\xx\2_xxx\xxxxxxx.txt
这是因为图片的打标文件的内容为空，请检查报错指出的文件里的内容是否为空，如果为空，需要重新打标。


## NotImplemenredError: Cannot cppy out of meta tensor; no data! Please use torch.nn.Module.to_empty() instead of torch.nn.Module.to() when moving module from mera to a different device.
训练使用的模型可能有问题，尝试更换模型。


## Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。


## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。


### 1. 使用自动环境激活脚本
运行`terminal.ps1`后将自动打开 PowerShell 并激活 SD-Trainer-Script Env。


### 2. 手动输入命令激活
在`SD-Trainer-Script`文件夹打开 PowerShell，输入下面的命令激活 SD-Trainer-Script Env：

```powershell
.\activate.ps1
```

>[!IMPORTANT]  
>在 PowerShell 中一定要显示`[SD-Trainer-Script Env]`才算进入了环境，这样才能使用下面的命令。


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

>[!NOTE]  
>推荐使用`python -m pip`的写法，`pip`的写法也可用。SD-Trainer-Script Installer 默认将`pip`命令链接到`python -m pip`避免直接调用`pip`。  
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


### 列出 SD-Trainer-Script Installer 内置命令
```powershell
List-CMD
```


### 检查 SD-Trainer-Script Installer 更新
```powershell
Check-SD-Trainer-Script-Installer-Update
```


### 查看并切换 SD-Trainer-Script 的版本
```powershell
# 列出当前的所有版本
git -C sd-scripts tag
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
git -C sd-scripts reset --hard --recurse-submodules <Git Tag>

# 使用 git log 查看某个提交信息对应的 Hash 值
git -C sd-scripts log
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
git -C sd-scripts reset --hard --recurse-submodules <Git Commit Hash>
```


### 将 LoRA 模型融进 Stable Diffusion 模型中
```powershell
# 先下载融合 LoRA 的工具
git clone https://github.com/KohakuBlueleaf/LyCORIS

# 接下来就能进行模型融合了，比如我要融合的 LoRA 模型为 artist_all_in_one_2-000036.safetensors，Stable Diffusion 模型为 animagine-xl-3.1.safetensors，先把这 2 个模型放到当前的文件夹，接下来就可以进行模型融合
python LyCORIS/tools/merge.py animagine-xl-3.1.safetensors artist_all_in_one_2-000036.safetensors licyk_style_v0.1.safetensors --is_sdxl --dtype fp16

# 解释上面命令的意思：
# animagine-xl-3.1.safetensors 为 Stable Diffusion 模型
# artist_all_in_one_2-000036.safetensors 为 LoRA 模型
# licyk_style_v0.1.safetensors 为融合后要保存的模型名称
# --is_sdxl 参数指定了模型类型为 SDXL，如果模型类型为 SD 2.x 则改为 --is_v2，如果模型类型为 SD 1.x 则不需要加参数
# --dtype fp16 指定保存的模型精度为 fp16，常用的模型精度为 fp16、bf16
# 融合完成后在当前文件夹中就可以看到融合好的 Stable Diffusion 模型
# 注意，融合模型需要大于或等于 64G 的内存，如果内存低于这个大小可能会大量使用虚拟内存进行补足，增大硬盘的读写消耗
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


## 编写训练脚本
进行模型训练需要编写代码来调用训练器进行训练，下面将介绍如何进行编写。


### 如何编写
SD-Trainer-Script Installer 在安装时将会生成一个`train.ps1`脚本，可用于编写训练命令。该脚本的内容如下

```powershell
#################################################
# 初始化基础环境变量, 以正确识别到运行环境
& "$PSScriptRoot/init.ps1"
Set-Location $PSScriptRoot
# 此处的代码不要修改或者删除, 否则可能会出现意外情况
# 
# SD-Trainer-Script 环境初始化后提供以下变量便于使用
# 
# ${ROOT_PATH}               当前目录
# ${SD_SCRIPTS_PATH}         训练脚本所在目录
# ${DATASET_PATH}            数据集目录
# ${MODEL_PATH}              模型下载器下载的模型路径
# ${GIT_EXEC}                Git 路径
# ${PYTHON_EXEC}             Python 解释器路径
# 
# 下方可编写训练代码
# 编写训练命令可参考: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
# 编写结束后, 该文件必须使用 UTF-8 with BOM 编码保存
#################################################





#################################################
Write-Host "训练结束, 退出训练脚本"
Read-Host | Out-Null # 训练结束后保持控制台不被关闭
```

该脚本在执行时将会运行`init.ps1`用于初始化环境（在`& "$PSScriptRoot/init.ps1"`部分），使训练所需的环境能够被正确识别，这是必须的步骤。在执行完`init.ps1`后将设置一些路径变量可供使用，并且将会显示出来，可以在部分路径变量指出的路径放置训练所需的文件方便使用。

`Set-Location $PSScriptRoot`将切换目录到`train.ps1`所在路径。

必要的步骤执行后，下方的训练命令就可以执行了，这里尝试编写一个训练模型命令。以下的训练命令基于 [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)，不同的训练器所使用的训练参数各不同，需阅读项目的文档进行了解。

```powershell
#################################################
# 初始化基础环境变量, 以正确识别到运行环境
& "$PSScriptRoot/init.ps1"
Set-Location $PSScriptRoot
# 此处的代码不要修改或者删除, 否则可能会出现意外情况
# 
# SD-Trainer-Script 环境初始化后提供以下变量便于使用
# 
# ${ROOT_PATH}               当前目录
# ${SD_SCRIPTS_PATH}         训练脚本所在目录
# ${DATASET_PATH}            数据集目录
# ${MODEL_PATH}              模型下载器下载的模型路径
# ${OUTPUT_PATH}             保存训练模型的路径
# ${GIT_EXEC}                Git 路径
# ${PYTHON_EXEC}             Python 解释器路径
# 
# 下方可编写训练代码
# 编写训练命令可参考: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
# 编写结束后, 该文件必须使用 UTF-8 with BOM 编码保存
#################################################


python "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=12 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --full_fp16


#################################################
Write-Host "训练结束, 退出训练脚本"
Read-Host | Out-Null # 训练结束后保持控制台不被关闭
```

这是一段在 SDXL 模型上训练 LoRA 的训练命令，每一行参数使用 ` 符号进行换行，而最后一行参数则不需要该符号进行换行。

在最后一行`Read-Host | Out-Null`是为了在训练结束后保持控制台不被关闭。

训练命令编写完成后，将该文件保存下来，再运行`train.ps1`即可开始训练。

除了编辑`train.ps1`进行训练，也可以自行创建 PowerShell 脚本并按照要求进行编写。

>[!WARNING]  
>`train.ps1`文件或者其他 PowerShell 脚本需要将保存编码设置为`UTF-8 BOM`，否则将出现乱码或者运行异常的问题。


### kohya-ss/sd-scripts 训练命令参考
下面是 [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts) 不同的训练参数例子，可用于参考。

```powershell
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数在 animagine-xl-3.1.safetensors 测试, 大概在 30 ~ 40 Epoch 有比较好的效果 (在 36 Epoch 出好效果的概率比较高)
#
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
#
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset，可以调整训练网络的大小
# 该值默认为 full，而使用 attn-mlp 可以得到更小的 LoRA 但几乎不影响 LoRA 效果
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="attn-mlp" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset，可以调整训练网络的大小
# 该值默认为 full，而使用 attn-mlp 可以得到更小的 LoRA 但几乎不影响 LoRA 效果
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 当 weight_decay 设置为 0.05 时, 大概在 38 Epoch 有比较好的效果
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="attn-mlp" `
    --optimizer_args `
        weight_decay=0.1 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# (自己在用的)
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# (自己在用的)
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好 (最好还是 full 吧, 其他的预设效果不是很好)
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
# 测试的时候发现 --debiased_estimation_loss 对于训练效果的有些改善
# 这里有个对比: https://licyk.netlify.app/2025/02/10/debiased_estimation_loss_in_stable_diffusion_model_training
# 启用后能提高拟合速度和颜色表现吧, 画风的学习能学得更好
# 但, 肢体崩坏率可能会有点提高, 不过有另一套参数去优化了一下这个问题, 貌似会好一点
# debiased estimation loss 有个相关的论文可以看看: https://arxiv.org/abs/2310.08442
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好 (最好还是 full 吧, 其他的预设效果不是很好)
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
# 测试的时候发现 --debiased_estimation_loss 对于训练效果的有些改善
# 这里有个对比: https://licyk.netlify.app/2025/02/10/debiased_estimation_loss_in_stable_diffusion_model_training
# 启用后能提高拟合速度和颜色表现吧, 画风的学习能学得更好
# 把学习率调度器 constant_with_warmup 换成了cosine, 稍微缓解了一下拟合速度过快导致肢体崩坏率增大的问题
# 如果学的效果不够好, 拟合度不够高, 可以适当增加 --max_train_epochs 的值或者提高训练集的重复次数
# debiased estimation loss 有个相关的论文可以看看: https://arxiv.org/abs/2310.08442
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine" `
    --lr_warmup_steps=0 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 人物 LoRA, 使用多卡进行训练
# 适合极少图或者单图训练集进行人物 LoRA 训练
# 训练集使用打标器进行打标后, 要保留的人物的哪些特征, 就把对应的 Tag 删去, 触发词可加可不加
# 
# 该参数使用 scale_weight_norms 降低过拟合程度, 进行训练时, 可在控制台输出看到 Average key norm 这个值
# 通常测试 LoRA 时就测试 Average key norm 值在 0.5 ~ 0.9 之间的保存的 LoRA 模型
# max_train_epochs 设置为 200, save_every_n_epochs 设置为 1 以为了更好的挑选最好的结果
# 
# 可使用该方法训练一个人物 LoRA 模型用于生成人物的图片, 并将这些图片重新制作成训练集
# 再使用不带 scale_weight_norms 的训练参数进行训练, 通过这种方式, 可以在图片极少的情况下得到比较好的 LoRA 模型
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=200 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --scale_weight_norms=1 `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用 rtx 4060 8g laptop 进行训练, 通过 fp8 降低显存占用
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
python "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=3 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0002 `
    --unet_lr=0.0002 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="AdamW8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --fp8_base


# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 参数加上了 noise_offset, 可以提高暗处和亮处的表现, 一般使用设置成 0.05 ~ 0.1
# 但 noise_offset 可能会导致画面泛白, 光影效果变差
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --noise_offset=0.1 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 人物 LoRA, 使用多卡进行训练
# 参数中使用了 --scale_weight_norms, 用于提高泛化性, 但可能会造成拟合度降低
# 如果当训练人物 LoRA 的图片较多时, 可考虑删去该参数
# 当训练人物 LoRA 的图片较少, 为了避免过拟合, 就可以考虑使用 --scale_weight_norms 降低过拟合概率
#
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/robin" `
    --output_name="robin_1" `
    --output_dir="${OUTPUT_PATH}/robin_1" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --scale_weight_norms=1 `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 人物 LoRA, 使用多卡进行训练
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/murasame_(senren)_3" `
    --output_name="murasame_(senren)_10" `
    --output_dir="${OUTPUT_PATH}/murasame_(senren)_10" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00004 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --scale_weight_norms=1 `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 XL 画风 LoRA, 使用单卡进行训练 (Kaggle 的单 Tesla P100 性能不如双 Tesla T4, 建议使用双卡训练)
python "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/rafa" `
    --output_name="rafa_1" `
    --output_dir="${OUTPUT_PATH}/rafa" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00007 `
    --unet_lr=0.00007 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 SD1.5 画风 LoRA, 使用双卡进行训练
# 使用 NovelAI 1 模型进行训练
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animefull-final-pruned.safetensors" `
    --vae="${MODEL_PATH}/vae-ft-mse-840000-ema-pruned.safetensors" `
    --train_data_dir="${DATASET_PATH}/sunfish" `
    --output_name="nai1-sunfish_5" `
    --output_dir="${OUTPUT_PATH}/nai1-sunfish_5" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="768,768" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=1024 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=12 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00024 `
    --unet_lr=0.00024 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16


# 使用 lokr 算法训练 SD1.5 多画风(多概念) LoRA, 使用双卡进行训练
# 使用 NovelAI 1 模型进行训练
# 
# 在 SD1.5 中训练 Text Encoder 可以帮助模型更好的区分不同的画风(概念)
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animefull-final-pruned.safetensors" `
    --vae="${MODEL_PATH}/vae-ft-mse-840000-ema-pruned.safetensors" `
    --train_data_dir="${DATASET_PATH}/sunfish" `
    --output_name="nai1-sunfish_5" `
    --output_dir="${OUTPUT_PATH}/nai1-sunfish_5" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="768,768" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=1024 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=12 `
    --gradient_checkpointing `
    --learning_rate=0.00028 `
    --unet_lr=0.00028 `
    --text_encoder_lr=0.000015 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16
```


### 使用 TensorBoard 查看训练情况
这里可以编写一个`tensorboard.ps1`脚本用于运行 TensorBoard。


```powershell
# 初始化基础环境变量, 以正确识别到运行环境
& "$PSScriptRoot/init.ps1"

# TensorBoard 日志路径
$LOG_DIR = "${OUTPUT_PATH}/logs"


python -m tensorboard.main `
    --host=127.0.0.1 `
    --port=8899 `
    --logdir="${LOG_DIR}"


# 运行这个脚本后将会在 http://127.0.0.1:8899 打开 TensorBoard 的网页界面
```

保存后右键运行即可启动。
