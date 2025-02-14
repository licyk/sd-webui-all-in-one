<div align="center">

# InvokeAI Installer

_✨一键安装 InvokeAI_

</div>

# 目录
- [InvokeAI Installer](#invokeai-installer)
- [目录](#目录)
- [简介](#简介)
- [环境配置](#环境配置)
  - [1. 使用自动环境配置脚本](#1-使用自动环境配置脚本)
  - [2. 手动使用命令配置](#2-手动使用命令配置)
    - [2.1 解除脚本限制](#21-解除脚本限制)
    - [2.2 启用 Windows 长路径支持](#22-启用-windows-长路径支持)
- [安装](#安装)
- [使用](#使用)
  - [启动 InvokeAI](#启动-invokeai)
  - [更新 InvokeAI](#更新-invokeai)
  - [更新 InvokeAI 自定义节点](#更新-invokeai-自定义节点)
  - [进入 InvokeAI 所在的 Python 环境](#进入-invokeai-所在的-python-环境)
  - [获取最新的 InvokeAI Installer 并运行](#获取最新的-invokeai-installer-并运行)
  - [更新 InvokeAI 管理脚本](#更新-invokeai-管理脚本)
    - [1. 直接更新](#1-直接更新)
    - [2. 使用 InvokeAI Installer 配置管理器进行更新](#2-使用-invokeai-installer-配置管理器进行更新)
    - [3. 运行 InvokeAI Installer 进行更新](#3-运行-invokeai-installer-进行更新)
    - [4. 使用命令更新](#4-使用命令更新)
    - [禁用 InvokeAI Installer 更新检查](#禁用-invokeai-installer-更新检查)
  - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
  - [设置 InvokeAI 中文](#设置-invokeai-中文)
  - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
  - [设置 Github 镜像源](#设置-github-镜像源)
  - [设置 Pip 镜像源](#设置-pip-镜像源)
  - [添加模型](#添加模型)
  - [InvokeAI 的使用方法](#invokeai-的使用方法)
  - [启用 InvokeAI 低显存模式](#启用-invokeai-低显存模式)
  - [重装 InvokeAI](#重装-invokeai)
  - [重装 Python 环境](#重装-python-环境)
  - [重装 Git](#重装-git)
  - [重置 InvokeAI 数据库](#重置-invokeai-数据库)
  - [配置 InvokeAI](#配置-invokeai)
  - [下载 InvokeAI 模型配置文件](#下载-invokeai-模型配置文件)
  - [设置 uv 包管理器](#设置-uv-包管理器)
  - [PowerShell 中出现 xFormers 报错](#powershell-中出现-xformers-报错)
  - [重装 PyTorch / xFormers](#重装-pytorch--xformers)
  - [InvokeAI 无法正常调用显卡](#invokeai-无法正常调用显卡)
  - [卸载 InvokeAI](#卸载-invokeai)
  - [移动 InvokeAI 的路径](#移动-invokeai-的路径)
  - [InvokeAI 文件夹用途](#invokeai-文件夹用途)
  - [配置代理](#配置代理)
    - [1. 使用系统代理](#1-使用系统代理)
    - [2. 使用配置文件](#2-使用配置文件)
    - [禁用自动设置代理](#禁用自动设置代理)
  - [创建快捷启动方式](#创建快捷启动方式)
  - [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)
  - [使用命令运行 InvokeAI Installer](#使用命令运行-invokeai-installer)
  - [运行脚本时出现中文乱码](#运行脚本时出现中文乱码)
  - [无法使用 PowerShell 运行](#无法使用-powershell-运行)
  - [ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE](#error-these-packages-do-not-match-the-hashes-from-the-requirements-file)
  - [运行 InvokeAI 时 InvokeAI 出现崩溃](#运行-invokeai-时-invokeai-出现崩溃)
  - [Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.](#microsoft-visual-c-redistributable-is-not-installed-this-may-lead-to-the-dll-load-failure)
  - [NotFoundError: 无法在“Node”上执行“removeChild”: 要删除的节点不是此节点的子节点](#notfounderror-无法在node上执行removechild-要删除的节点不是此节点的子节点)
  - [AttributeError: 'LayerNorm' object has no attribute 'get\_num\_patches'](#attributeerror-layernorm-object-has-no-attribute-get_num_patches)
  - [命令的使用](#命令的使用)
    - [1. 使用自动环境激活脚本](#1-使用自动环境激活脚本)
    - [2. 手动输入命令激活](#2-手动输入命令激活)
  - [常用命令](#常用命令)
    - [启动 InvokeAI](#启动-invokeai-1)
    - [查看 InvokeAI 的版本](#查看-invokeai-的版本)
    - [修复 InvokeAI 数据库](#修复-invokeai-数据库)
    - [从旧版 InvokeAI 导入图片到新版的 InvokeAI](#从旧版-invokeai-导入图片到新版的-invokeai)
    - [清理安装时产生的 Pip 缓存](#清理安装时产生的-pip-缓存)
    - [安装某个 Pip 软件包](#安装某个-pip-软件包)
    - [更新某个软件包](#更新某个软件包)
    - [重装某个软件包](#重装某个软件包)
    - [卸载某个软件包](#卸载某个软件包)
    - [解决 ModuleNotFoundError: No module named 'controlnet\_aux'](#解决-modulenotfounderror-no-module-named-controlnet_aux)
    - [使用 uv 安装软件包](#使用-uv-安装软件包)
    - [更新 uv](#更新-uv)
    - [更新 Aria2](#更新-aria2)
    - [列出 InvokeAI Installer 内置命令](#列出-invokeai-installer-内置命令)
    - [检查 InvokeAI Installer 更新](#检查-invokeai-installer-更新)
    - [安装 InvokeAI 自定义节点](#安装-invokeai-自定义节点)
    - [测试并启用 Github 镜像源](#测试并启用-github-镜像源)
    - [使用 Git 下载项目](#使用-git-下载项目)
    - [查看可用的 InvokeAI 版本并切换](#查看可用的-invokeai-版本并切换)
    - [更新到 InvokeAI RC 版](#更新到-invokeai-rc-版)
    - [查看 Git / Python 命令实际调用的路径](#查看-git--python-命令实际调用的路径)

***

# 简介
一个在 Windows 系统上部署 [InvokeAI](https://github.com/invoke-ai/InvokeAI) 的 PowerShell 脚本，并提供不同的管理工具。

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
>关于 Windows 长路径支持的说明：[最大路径长度限制 - Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)

***

# 安装
将 InvokeAI Installer 下载至本地，右键`invokeai_installer.ps1`脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 InvokeAI Installer 将安装 InvokeAI 至本地。

|InvokeAI Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1)|

在 InvokeAI Installer 成功安装 InvokeAI 后，在`InvokeAI`文件夹中可以看到 InvokeAI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 InvokeAI Installer。

>[!NOTE]  
>1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](#环境配置)中的方法进行解除。
>2. InvokeAI Installer 支持使用在命令行中通过参数配置 InvokeAI 的安装参数，具体说明可阅读[使用命令运行 InvokeAI Installer](#使用命令运行-invokeai-installer)。

>[!IMPORTANT]  
>从 InvokeAI 5.1.0 开始，InvokeAI 要求的 PyTorch 版本更改为 2.4.1，而 InvokeAI Installer 使用的 [PyTorch 镜像源](https://mirror.sjtu.edu.cn/docs/pytorch-wheels) 并没有提供 PyTorch 2.4.1 的镜像，则 InvokeAI Installer 在安装 PyTorch 2.4.1 时将会切换至 PyTorch 官方源进行安装。  
>但在不使用代理的情况下从 PyTorch 官方源安装 PyTorch 时失败的概率较高（通常是下载 PyTorch 安装包失败导致安装失败），所以 InvokeAI Installer 默认安装 InvokeAI 5.0.2 以保证在安装 PyTorch 时能够使用 PyTorch 镜像源进行安装。  
>如果需要安装更高的 InvokeAI 版本，在 InvokeAI Installer 安装 InvokeAI 成功后进入`InvokeAI`文件夹运行`update.ps1`进行更新（需要使用代理）。

***

# 使用
在`InvokeAI`文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。


## 启动 InvokeAI
运行`launch.ps1`脚本。


## 更新 InvokeAI
运行`update.ps1`脚本，如果遇到更新 InvokeAI 失败的情况可尝试重新运行`update.ps1`脚本。


## 更新 InvokeAI 自定义节点
运行`update_node.ps1`脚本，如果遇到更新 InvokeAI 自定义节点失败的情况可尝试重新运行`update_node.ps1`脚本。


## 进入 InvokeAI 所在的 Python 环境
如果需要使用 Python、Pip、InvokeAI 的命令时，请勿将 InvokeAI 的`python`文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是在 InvokeAI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 InvokeAI Env：

```powershell
.\activate.ps1
```

这样就进入 InvokeAI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

或者运行`terminal.ps1`脚本，这将打开 PowerShell 并自动执行`activate.ps1`，此时就进入了 InvokeAI 所在的 Python。


## 获取最新的 InvokeAI Installer 并运行
运行`launch_invokeai_installer.ps1`脚本，如果下载成功将会把 InvokeAI Installer 下载到`cache`目录中并运行。


## 更新 InvokeAI 管理脚本
InvokeAI Installer 的管理脚本在启动时会检查管理脚本的更新，如果有新版本可更新将会提示。

可选择下方 4 种方法中的其中 1 个方法进行更新。


### 1. 直接更新
当检测到有新版的 InvokeAI Installer 时，将询问是否进行更新，输入`y`并回车后将运行 InvokeAI Installer 进行更新。


### 2. 使用 InvokeAI Installer 配置管理器进行更新
运行`settings.ps1`，选择`更新 InvokeAI Installer 管理脚本`功能进行更新，更新完成后需关闭 InvokeAI Installer 管理脚本以应用更新。


### 3. 运行 InvokeAI Installer 进行更新
运行`launch_invokeai_installer.ps1`获取最新的 InvokeAI Installer 后，脚本会自动运行新版 InvokeAI Installer 进行更新。


### 4. 使用命令更新
参考[命令的使用](#命令的使用)的方法进入 InvokeAI Env，并运行`Check-InvokeAI-Installer-Update`命令进行更新。


### 禁用 InvokeAI Installer 更新检查
>[!WARNING]  
>通常不建议禁用 InvokeAI Installer 的更新检查，当 InvokeAI 管理脚本有重要更新（如功能性修复）时将得不到及时提示。

>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

如果要禁用更新检查，可以在脚本同级的目录创建`disable_update.txt`文件，这将禁用 InvokeAI Installer 更新检查。


## 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次`launch_invokeai_installer.ps1`重新生成这些脚本。

```
$ tree -L 2
.
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── InvokeAI                            # 这是 InvokeAI 文件夹
│   ├── activate.ps1                    # 进入 InvokeAI Env 的脚本
│   ├── cache                           # 缓存文件夹
│   ├── download_config.ps1             # 下载模型配置文件脚本
│   ├── launch_invokeai_installer.ps1   # 获取最新的 InvokeAI Installer 并运行的脚本
│   ├── help.txt                        # 帮助文档
│   ├── invokeai                        # InvokeAI 生成的图片 / 模型 / 工作流 / 配置文件路径
│   ├── launch.ps1                      # 启动 InvokeAI 的脚本
│   ├── python                          # Python 目录
│   ├── git                             # Git 目录
│   ├── models                          # download_models.ps1 下载模型脚本下载模型的路径
│   ├── reinstall_pytorch.ps1           # 重装 PyTorch 脚本
│   ├── download_models.ps1             # 模型下载脚本
│   ├── settings.ps1                    # 管理 InvokeAI Installer 设置的脚本
│   ├── terminal.ps1                    # 自动打开 PowerShell 并激活 InvokeAI Installer 的虚拟环境脚本
│   ├── update_node.ps1                 # 更新 InvokeAI 自定义节点的脚本
│   └── update.ps1                      # 更新 InvokeAI 的脚本
├── invokeai_installer.ps1              # InvokeAI Installer 一般放在 InvokeAI 文件夹外面，和 InvokeAI 文件夹同级
└── QQ Files

7 directories, 8 files
```


## 设置 InvokeAI 中文
InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。


## 设置 HuggingFace 镜像
>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

InvokeAI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源|
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。


## 设置 Github 镜像源
>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

InvokeAI Installer 为了加速访问 Github 的速度，如加快下载和更新 InvokeAI 自定义节点的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建`gh_mirror.txt`文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

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
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

InvokeAI Installer 默认启用了 Pip 镜像源加速下载 Python 软件包，如果需要禁用 Pip 镜像源，可以在脚本同级目录创建`disable_pip_mirror.txt`文件，再次运行脚本时将 Pip 源切换至官方源。


## 添加模型
如果没有下载模型，可以使用`download_models.ps1`脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。在 InvokeAI 左侧栏选择模型管理器，在模型管理器中可以添加本地的模型或者下载模型，可以和 SD WebUI / ComfyUI 共享模型。具体可以查看 [Installing Models - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/installation/050_INSTALLING_MODELS/)。


## InvokeAI 的使用方法
推荐下面的教程：  
- [InvokeAI - SD Note](https://sdnote.netlify.app/guide/invokeai)
- [给所有想学习AI辅助绘画的人的入门课（基于 InvokeAI 3.7.0）](https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140)
- [InvokeAI 官方入门教程（基于 InvokeAI 5.x）](https://www.youtube.com/playlist?list=PLvWK1Kc8iXGrQy8r9TYg6QdUuJ5MMx-ZO)
- [一个使用 InvokeAI 5.0 的新统一画布完成常见任务的简述（升级到 InvokeAI 5.0 后必看）](https://www.youtube.com/watch?v=Tl-69JvwJ2s)
- [如何使用 InvokeAI 5.0 的新统一画布和工作流系统](https://www.youtube.com/watch?v=y80W3PjR0Gc)
- [InvokeAI 官方视频教程](https://www.youtube.com/@invokeai)
- [InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI)
- [Solutions : Invoke Support Portal](https://support.invoke.ai/support/solutions)
- [Reddit 社区](https://www.reddit.com/r/invokeai)

除了上面的教程，也可以通过 Google 等平台搜索教程。


## 启用 InvokeAI 低显存模式
当显存较小，并且经常出现显存不足的问题，可尝试启用 InvokeAI 的低显存模式。

>[!IMPORTANT]  
>InvokeAI 低显存模式在 InvokeAI 5.6.0 的版本中被加入，如果当前 InvokeAI 的版本低于 5.6.0，需要运行`update.ps1`对 InvokeAI 进行更新。

在运行`launch.ps1`启动一次 InvokeAI 后，在`InvokeAI/invokeai`路径将产生一个`invokeai.yaml`文件，这就是 InvokeAI 的配置文件。

打开`invokeai.yaml`文件后，在该文件添加以下内容启用 InvokeAI 的低显存模式。

```yaml
enable_partial_loading: true
```

保存该文件并重新启动 InvokeAI 即可应用该设置。

>[!NOTE]  
>关于 InvokeAI 低显存模式详细说明可阅读：[Low-VRAM mode - Invoke](https://invoke-ai.github.io/InvokeAI/features/low-vram)。


## 重装 InvokeAI
如果 InvokeAI 因为严重损坏导致无法正常使用，可以将`InvokeAI`文件夹中的`python`文件夹删除，然后运行`launch_invokeai_installer.ps1`重新部署 InvokeAI。


## 重装 Python 环境
如果 Python 环境出现严重损坏，可以将`InvokeAI/python`文件夹删除，然后运行`launch_invokeai_installer.ps1`重新构建 Python 环境。


## 重装 Git
将`InvokeAI/git`文件夹删除，然后运行`launch_invokeai_installer.ps1`重新下载 Git。


## 重置 InvokeAI 数据库
如果 InvokeAI 的数据库出现损坏，可以将`InvokeAI/invokeai/databases`文件夹删除。


## 配置 InvokeAI
在`InvokeAI/invokeai`路径下，可以看到`invokeai.yaml`配置文件。如果未找到该配置文件，可以运行`launch.ps1`启动一次 InvokeAI，此时 InvokeAI 将自动生成该配置文件。

如果需要修改，请参考`invokeai.example.yaml`文件内的示例，或者参考 [Configuration - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/configuration) 进行设置。

如果因为修改`invokeai.yaml`后导致 InvokeAI 的功能异常，请将该文件删除来重置 InvokeAI 配置。

>[!NOTE]  
>在大多数情况下并不需要修改该配置文件，因为 InvokeAI 会自动选择最佳的配置。


## 下载 InvokeAI 模型配置文件
运行`download_config.ps1`脚本。


## 设置 uv 包管理器
>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

InvokeAI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个`disable_uv.txt`文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

>[!NOTE]  
>1. 当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。
>2. uv 包管理器对网络的稳定性要求更高，在网络不稳定时可能会出现下载软件包出错的问题，可尝试重新运行，或者禁用 uv，这时将切换成 Pip 作为 Python 包管理器，Pip 在网络稳定性差的情况下不容易出错，但这将降低 Python 软件包的安装速度。


## PowerShell 中出现 xFormers 报错
在控制台中出现有关 xFormers 的警告信息，类似下面的内容。

```
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.2.1+cu118 with CUDA 1108 (you have 2.2.2+cu121)
    Python  3.10.11 (you have 3.10.11)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
```

这是因为 xFormers 所适配的 CUDA 版本和 PyTorch 所带的 CUDA 版本不一致，请运行`reinstall_pytorch.ps1`脚本进行修复。


## 重装 PyTorch / xFormers
运行`reinstall_pytorch.ps1`脚本。


## InvokeAI 无法正常调用显卡
尝试将显卡驱动更至最新或者运行`reinstall_pytorch.ps1`脚本重装 PyTorch。

>[!NOTE]  
>Nvidia 显卡驱动下载：https://www.nvidia.cn/geforce/drivers


## 卸载 InvokeAI
使用 InvokeAI Installer 安装 InvokeAI 后，所有的文件都存放在`InvokeAI`文件夹中，只需要删除`InvokeAI`文件夹即可卸载 InvokeAI。

如果有 InvokeAI 快捷启动方式，可以通过命令进行删除，打开 PowerShell 后，输入以下命令进行删除。
```powershell
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\InvokeAI.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\InvokeAI.lnk" -Force
```


## 移动 InvokeAI 的路径
直接将`InvokeAI`文件夹移动到别的路径即可。

如果启用了自动创建 InvokeAI 快捷启动方式的功能，移动 InvokeAI 后原来的快捷启动方式将失效，需要运行`launch.ps1`更新快捷启动方式。


## InvokeAI 文件夹用途
在`InvokeAI`文件夹中，存在着`invokeai`文件夹，保存着模型和生成出来的图片等，以下为不同文件夹的用途。

```
$ tree -L 1 invokeai
invokeai
├── cache                 # InvokeAI 的缓存文件夹
├── configs               # 一些模型的配置文件
├── databases             # InvokeAI 的数据库
├── invokeai.example.yaml # InvokeAI 的配置文件示例
├── invokeai.yaml         # InvokeAI 的配置文件
├── models                # 模型文件夹
├── nodes                 # InvokeAI 节点存放路径
├── outputs               # 生成的图片保存位置
└── style_presets         # 提示词预设文件

7 directories, 2 files
```


## 配置代理
如果出现某些文件无法下载，比如在控制台出现`由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败`之类的报错时，可以尝试配置代理，有以下两种方法。


### 1. 使用系统代理
在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。


### 2. 使用配置文件
>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

在和脚本同级的路径中创建一个`proxy.txt`文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

>[!NOTE]  
>**配置文件**的优先级高于**系统代理**配置，所以当同时使用了两种方式配置代理，脚本将优先使用**配置文件**中的代理配置。


### 禁用自动设置代理
>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

在和脚本同级的路径中创建一个`disable_proxy.txt`文件，再次启动脚本时将禁用设置代理。


## 创建快捷启动方式
>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。

在脚本同级目录创建`enable_shortcut.txt`文件，当运行`launch.ps1`时将会自动创建快捷启动方式，并添加到 Windows 桌面和 Windows 开始菜单中，下次启动时可以使用快捷方式启动 InvokeAI。

>[!IMPORTANT]  
>如果 InvokeAI 的路径发生移动，需要重新运行`launch.ps1`更新快捷启动方式。


## 管理 InvokeAI Installer 设置
运行`settings.ps1`，根据提示进行设置管理和调整。


## 使用命令运行 InvokeAI Installer
InvokeAI Installer 支持使用命令参数设置安装 InvokeAI 的参数，支持的参数如下。

|参数|作用|
|---|---|
|`-InstallPath` <InvokeAI 安装路径>|指定安装 InvokeAI 的路径，使用绝对路径进行指定。|
|`-UseUpdateMode`|使用 InvokeAI Installer 的更新脚本模式，不进行 InvokeAI 的安装。|
|`-DisablePipMirror`|禁用 InvokeAI Installer 使用 Pip 镜像源, 使用 Pip 官方源下载 Python 软件包。|
|`-DisableProxy`|禁用 InvokeAI Installer 自动设置代理服务器。|
|`·UseCustomProxy` <代理服务器地址>|使用自定义的代理服务器地址。|
|`-DisableUV`|禁用 InvokeAI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包。|
|`-Help`|显示 InvokeAI Installer 可用的命令行参数。|

例如在`D:/Download`这个路径安装 InvokeAI，则在 InvokeAI Installer 所在路径打开 PowerShell，使用参数运行 InvokeAI Installer。

```powershell
.\invokeai_installer.ps1 -InstallPath "D:/Download"
```


## 运行脚本时出现中文乱码
这可能是 Windows 系统中启用了 UTF 8 编码，可以按照下列方法解决。

1. 按下`Win + R`键，输入`control`后回车启动控制面板。
2. 点击`时钟和区域`->`区域`
3. 在弹出的区域设置窗口中点击顶部的`管理`，再点击`更改系统区域设置`.
4. 在弹出的窗口中将`使用 Unicode UTF-8 提供全球语言支持`取消勾选，然后一直点击确定保存设置，并重启电脑。


## 无法使用 PowerShell 运行
运行 PowerShell 脚本时出现以下错误。

```
.\invokeai_installer.ps1 : 无法加载文件 D:\InvokeAI\invokeai_installer.ps1。
未对文件 D:\InvokeAI\invokeai_installer.ps1进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符: 1
+ .\invokeai_installer.ps1
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


## ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE
运行 InvokeAI Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将`InvokeAI/cache/pip`文件夹删除，再重新运行 InvokeAI Installer。


## 运行 InvokeAI 时 InvokeAI 出现崩溃
尝试增加 Windows 系统虚拟内存。


## Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。



## NotFoundError: 无法在“Node”上执行“removeChild”: 要删除的节点不是此节点的子节点
尝试重置 UI 或者更换浏览器。


## AttributeError: 'LayerNorm' object has no attribute 'get_num_patches'
InvokeAI 5.6.0 和之后的版本暂时无法使用带有 Norm 块的 LyCORIS 模型，可尝试移除 LyCORIS 模型中的 Norm 块解决，下面是移除该 Norm 块的 Python 代码。

```python
import os
from safetensors.torch import load_file, save_file

# 这里修改为 LyCORIS 模型的路径
lora_path = "D:/Downloads/BaiduNetdiskDownload/ill-xl-01-rurudo_3-000034.safetensors"
# 移除 Norm 块后的 LyCORIS 模型将保存在 D:/Downloads/BaiduNetdiskDownload/ill-xl-01-rurudo_3-000034_without_norm_block.safetensors

save_path = os.path.join(
    os.path.dirname(lora_path),
    os.path.splitext(os.path.basename(lora_path))[0] + "_without_norm_block.safetensors"
)
norm_block_list = []
model_weights = load_file(lora_path)

for block, _ in model_weights.items():
    if "norm" in block:
        norm_block_list.append(block)

for block in norm_block_list:
    del model_weights[block]

save_file(model_weights, save_path)
```

将该 Python 代码保存到一个文件中，比如`remove_norm.py`，并放到`InvokeAI`文件夹中，然后运行`terminal.ps1`打开终端，运行该脚本。

```powershell
python remove_norm.py
```

得到移除 Norm 块的 LyCORIS 模型后即可导入到 InvokeAI 中使用。


## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。


### 1. 使用自动环境激活脚本
运行`terminal.ps1`后将自动打开 PowerShell 并激活 InvokeAI Env。


### 2. 手动输入命令激活
在`InvokeAI`文件夹打开 PowerShell，输入下面的命令激活 InvokeAI Env：

```powershell
.\activate.ps1
```

>[!IMPORTANT]  
>在 PowerShell 中一定要显示`[InvokeAI-Env]`才算进入了环境，这样才能使用下面的命令。


## 常用命令

### 启动 InvokeAI
```powershell
invokeai-web
```


### 查看 InvokeAI 的版本
```powershell
invokeai-web --version
```


### 修复 InvokeAI 数据库
```powershell
invokeai-db-maintenance --operation all
```

>[!WARNING]  
>该命令因为会造成数据丢失，已被 InvokeAI 官方移除，详情可阅读：[build: remove broken scripts · invoke-ai/InvokeAI@576f1cb](https://github.com/invoke-ai/InvokeAI/commit/576f1cbb757ac107c0532681cd643f98d6e0d2e8)


### 从旧版 InvokeAI 导入图片到新版的 InvokeAI
```powershell
invokeai-import-images
```

>[!WARNING]  
>该命令因为会造成数据丢失，已被 InvokeAI 官方移除，详情可阅读：[build: remove broken scripts · invoke-ai/InvokeAI@576f1cb](https://github.com/invoke-ai/InvokeAI/commit/576f1cbb757ac107c0532681cd643f98d6e0d2e8)


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


### 解决 ModuleNotFoundError: No module named 'controlnet_aux'
```powershell
python -m pip cache remove controlnet_aux
python -m pip uninstall controlnet_aux -y
python -m pip install controlnet_aux
```

>[!NOTE]  
>1. 推荐使用`python -m pip`的写法，`pip`的写法也可用。InvokeAI Installer 默认将`pip`命令链接到`python -m pip`避免直接调用`pip`。  
>参考：[Deprecate pip, pipX, and pipX.Y · Issue #3164 · pypa/pip](https://github.com/pypa/pip/issues/3164)
>2. 该问题的参考：[ModuleNotFoundError: No module named 'controlnet_aux' - FAQ - Invoke](https://invoke-ai.github.io/InvokeAI/faq/?h=controlnet_aux#modulenotfounderror-no-module-named-controlnet_aux)


### 使用 uv 安装软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
uv pip install <package_name>
```
>[!NOTE]  
>uv 命令的用法可参考：[uv docs](https://docs.astral.sh/uv)


### 更新 uv
```powershell
Update-uv
```


### 更新 Aria2
```powershell
Update-Aria2
```


### 列出 InvokeAI Installer 内置命令
```powershell
List-CMD
```


### 检查 InvokeAI Installer 更新
```powershell
Check-InvokeAI-Installer-Update
```


### 安装 InvokeAI 自定义节点
```powershell
Install-InvokeAI-Node <InvokeAI 自定义节点的下载地址>
```


### 测试并启用 Github 镜像源
```powershell
Test-Github-Mirror
# 可用于加速从 Github 下载项目
```


### 使用 Git 下载项目
```powershell
Git-Clone <Repo Url> <Path>
# <Repo Url> 为 Github 仓库的链接，<Path> 为下载到本地的路径，可不填
```


### 查看可用的 InvokeAI 版本并切换
```powershell
# 查询 PyPI 上 InvokeAI 可用的版本
python -m pip index versions invokeai
# 运行后将会输出所有可用的版本和已安装的版本
# WARNING: pip index is currently an experimental command. It may be removed/changed in a future release without prior warning.
# WARNING: Skipping page https://mirror.baidu.com/pypi/simple/invokeai/ because the GET request got Content-Type: application/octet-stream. The only supported Content-Types are application/vnd.pypi.simple.v1+json, application/vnd.pypi.simple.v1+html, and text/html
# invokeai (5.0.0)
# Available versions: 5.0.0, 4.2.9, 4.2.8, 4.2.7.post1, 4.2.7, 4.2.6.post1, 4.2.6, 4.2.5, 4.2.4, 4.2.3, 4.2.2.post1, 4.2.2, 4.2.1, 4.2.0, 4.1.0, 4.0.4, 4.0.3, 4.0.2, 4.0.1, 4.0.0, 3.7.0, 3.6.3, 3.6.2, 3.6.1, 3.6.0, 3.5.1, 3.5.0, 3.4.0.post2, 3.4.0.post1, 3.4.0, 3.3.0.post3, 3.3.0.post2, 3.3.0.post1, 3.3.0, 3.2.0, 3.1.1, 3.1.0, 3.0.2.post1, 3.0.2, 3.0.1.post3, 3.0.1.post2, 3.0.1.post1, 3.0.1, 3.0.0, 2.3.5.post2, 2.3.5.post1, 2.3.5, 2.3.4.post1, 2.3.4, 2.3.3, 2.3.2.post1, 2.3.2, 2.3.1.post2, 2.3.1.post1, 2.3.1, 2.3.0, 2.2.5, 2.2.4.7, 2.2.4.6, 2.2.4.5
#   INSTALLED: 4.2.9
#   LATEST:    5.0.0

# 切换到指定的版本
# 命令中的 <Version> 替换成要切换的版本
python -m pip install invokeai==<Version>
```


### 更新到 InvokeAI RC 版
>[!WARNING]  
>InvokeAI RC 版属于测试版本，可能存在问题，请谨慎升级。

```powershell
python -m pip install invokeai --pre -U
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
