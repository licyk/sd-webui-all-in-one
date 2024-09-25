<div align="center">

# InvokeAI Installer

_✨一键安装 InvokeAI_

</div>

# 目录
- [InvokeAI Installer](#invokeai-installer)
- [目录](#目录)
- [简介](#简介)
- [环境配置](#环境配置)
  - [使用自动环境配置脚本](#使用自动环境配置脚本)
  - [手动使用命令配置](#手动使用命令配置)
    - [解除脚本限制](#解除脚本限制)
    - [启用 Windows 长路径支持](#启用-windows-长路径支持)
- [安装](#安装)
- [使用](#使用)
  - [启动 InvokeAI](#启动-invokeai)
  - [更新 InvokeAI](#更新-invokeai)
  - [修复 InvokeAI 图库出现无效图片](#修复-invokeai-图库出现无效图片)
  - [进入 InvokeAI 所在的 Python 环境](#进入-invokeai-所在的-python-环境)
  - [获取最新的 InvokeAI Installer 脚本](#获取最新的-invokeai-installer-脚本)
  - [更新 InvokeAI 管理脚本](#更新-invokeai-管理脚本)
    - [使用 InvokeAI Installer 配置管理器进行更新](#使用-invokeai-installer-配置管理器进行更新)
    - [手动运行 InvokeAI Installer 进行更新](#手动运行-invokeai-installer-进行更新)
    - [使用命令更新](#使用命令更新)
  - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
  - [设置 InvokeAI 中文](#设置-invokeai-中文)
  - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
  - [添加模型](#添加模型)
  - [InvokeAI 的使用方法](#invokeai-的使用方法)
  - [重装 InvokeAI](#重装-invokeai)
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
  - [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)
  - [运行脚本时出现中文乱码](#运行脚本时出现中文乱码)
  - [无法使用 PowerShell 运行](#无法使用-powershell-运行)
  - [ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE](#error-these-packages-do-not-match-the-hashes-from-the-requirements-file)
  - [运行 InvokeAI 时 InvokeAI 出现崩溃](#运行-invokeai-时-invokeai-出现崩溃)
  - [Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.](#microsoft-visual-c-redistributable-is-not-installed-this-may-lead-to-the-dll-load-failure)
  - [命令的使用](#命令的使用)
    - [使用自动环境激活脚本](#使用自动环境激活脚本)
    - [手动输入命令激活](#手动输入命令激活)
    - [常用命令](#常用命令)

***

# 简介
一个在 Windows 系统上部署 [InvokeAI](https://github.com/invoke-ai/InvokeAI) 的 PowerShell 脚本，并提供不同的管理工具。

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
>关于 PowerShell 执行策略的说明：[关于执行策略 - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)


### 启用 Windows 长路径支持
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
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1)|
|[下载地址 2](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1)|
|[下载地址 3](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1)|
|[下载地址 4](https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|
|[下载地址 5](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|

在 InvokeAI Installer 成功安装 InvokeAI 后，在 InvokeAI 文件夹中可以看到 InvokeAI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 InvokeAI Installer。

>[!NOTE]  
>如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照[环境配置](#环境配置)中的方法进行解除。

***

# 使用
在 InvokeAI 文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。


## 启动 InvokeAI
运行 launch.ps1 脚本。


## 更新 InvokeAI
运行 update.ps1 脚本，如果遇到更新 InvokeAI 失败的情况可尝试重新运行`update.ps1`脚本。


## 修复 InvokeAI 图库出现无效图片
在 InvokeAI 的图片保存目录删除图片后，会发现 InvokeAI 的图库中图片还存在，并且显示损坏，无法查看，可以运行`fix_db.ps1`进行修复。


## 进入 InvokeAI 所在的 Python 环境
如果需要使用 Python、Pip、InvokeAI 的命令时，请勿将 InvokeAI 的 python 文件夹添加到环境变量，这将会导致不良的后果产生。  
正确的方法是在 InvokeAI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 InvokeAI Env：

```powershell
.\activate.ps1
```

这样就进入 InvokeAI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

或者运行`terminal.ps1`脚本，这将打开 PowerShell 并自动执行`activate.ps1`，此时就进入了 InvokeAI 所在的 Python。


## 获取最新的 InvokeAI Installer 脚本
运行`get_invokeai_installer.ps1`脚本，运行成功后将会把 InvokeAI Installer 保存在 InvokeAI 文件夹的上一级目录中。


## 更新 InvokeAI 管理脚本
InvokeAI Installer 的管理脚本在启动时会检查管理脚本的更新，如果有新版本可更新将会提示。

可选择下方 3 种方法中的其中 1 个方法进行更新。


### 使用 InvokeAI Installer 配置管理器进行更新
运行`settings.ps1`，选择`更新 InvokeAI Installer 管理脚本`功能进行更新，更新完成后需关闭 InvokeAI Installer 管理脚本以应用更新。


### 手动运行 InvokeAI Installer 进行更新
运行`get_invokeai_installer.ps1`获取最新的 InvokeAI Installer 后，返回上一个目录并运行`invokeai_installer.ps1`。InvokeAI Installer 在安装过程无报错并完整的运行所有安装流程后，InvokeAI 的管理脚本将会得到更新。


### 使用命令更新
参考[命令的使用](#命令的使用)的方法进入 InvokeAI Env，并运行`Check-InvokeAI-Installer-Update`命令进行更新。


如果要禁用更新，可以在脚本同级的目录创建`disable_update.txt`文件，这将禁用 InvokeAI Installer 更新检查。

>[!WARNING]  
>通常不建议禁用 InvokeAI Installer 的更新检查，当 InvokeAI 管理脚本有重要更新（如功能性修复）时将得不到及时提示。

>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。


## 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 InvokeAI Installer 重新生成这些脚本。

>[!NOTE]  
>InvokeAI Installer 必须放在 InvokeAI 文件夹外运行，不知道放哪的可以参考下面的目录结构。

```
$ tree -L 2
.
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── InvokeAI                        # 这是 InvokeAI 文件夹
│   ├── activate.ps1                # 进入 InvokeAI Env 的脚本
│   ├── cache                       # 缓存文件夹
│   ├── download_config.ps1         # 下载模型配置文件脚本
│   ├── fix_db.ps1                  # 修复 InvokeAI 数据库的脚本
│   ├── get_invokeai_installer.ps1  # 获取最新的 InvokeAI Installer 的脚本
│   ├── help.txt                    # 帮助文档
│   ├── invokeai                    # InvokeAI 生成的图片 / 模型 / 工作流 / 配置文件路径
│   ├── launch.ps1                  # 启动 InvokeAI 的脚本
│   ├── python                      # Python 目录
│   ├── reinstall_pytorch.ps1       # 重装 PyTorch 脚本
│   ├── settings.ps1                # 管理 InvokeAI Installer 设置的脚本
│   ├── terminal.ps1                # 自动打开 PowerShell 并激活 InvokeAI Installer 的虚拟环境脚本
│   └── update.ps1                  # 更新 InvokeAI 的脚本
├── invokeai_installer.ps1          # InvokeAI Installer 放在 InvokeAI 文件夹外面，和 InvokeAI 文件夹同级
└── QQ Files

7 directories, 8 files
```

>[!WARNING]  
>`InvokeAI`文件夹的名称切勿修改，修改后将导致 InvokeAI Installer 更新管理脚本时出现异常。


## 设置 InvokeAI 中文
InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。


## 设置 HuggingFace 镜像
InvokeAI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源|
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。

>[!NOTE]  
>该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。


## 添加模型
在 InvokeAI 左侧栏选择模型管理器，在模型管理器中可以添加本地的模型或者下载模型，可以和 SD WebUI / ComfyUI 共享模型。具体可以查看 [Installing Models - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/installation/050_INSTALLING_MODELS/)。


## InvokeAI 的使用方法
推荐下面的教程：  
- [给所有想学习AI辅助绘画的人的入门课（基于 InvokeAI 3.7.0）](https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140)
- [InvokeAI 官方入门教程（基于 InvokeAI 5.x）](https://www.youtube.com/playlist?list=PLvWK1Kc8iXGrQy8r9TYg6QdUuJ5MMx-ZO)
- [InvokeAI 官方视频教程](https://www.youtube.com/@invokeai)
- [InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI)
- [Reddit 社区](https://www.reddit.com/r/invokeai)

除了上面的教程，也可以通过 Google 等平台搜索教程。


## 重装 InvokeAI
如果 InvokeAI 因为严重损坏导致无法正常使用，可以将 InvokeAI 文件夹中的 python 文件夹删除，然后运行 InvokeAI Installer 重新部署 InvokeAI。


## 重置 InvokeAI 数据库
如果 InvokeAI 的数据库出现损坏，可以将`InvokeAI/invokeai/databases`文件夹删除。


## 配置 InvokeAI
在`InvokeAI/invokeai`路径下，可以看到`invokeai.yaml`配置文件，如果需要修改，请参考`invokeai.example.yaml`文件内的示例，或者参考 [Configuration - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/features/CONFIGURATION) 进行设置。

如果因为修改`invokeai.yaml`后导致 InvokeAI 的功能异常，请将该文件删除来重置 InvokeAI 配置。

>[!NOTE]  
>在大多数情况下并不需要修改该配置文件，因为 InvokeAI 会自动选择最佳的配置。


## 下载 InvokeAI 模型配置文件
运行`download_config.ps1`脚本。


## 设置 uv 包管理器
InvokeAI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个`disable_uv.txt`文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

>[!NOTE]  
>1. uv 包管理器对网络的稳定性要求更高，在网络不稳定时可能会出现下载软件包出错的问题，可尝试重新运行，或者禁用 uv，这时将切换成 Pip 作为 Python 包管理器，Pip 在网络稳定性差的情况下不容易出错，但这将降低 Python 软件包的安装速度。
>2. 该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。


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


## 卸载 InvokeAI
使用 InvokeAI Installer 安装 InvokeAI 后，所有的文件都存放在 InvokeAI 文件夹中，只需要删除 InvokeAI 文件夹即可卸载 InvokeAI。


## 移动 InvokeAI 的路径
直接将 InvokeAI 文件夹移动到别的路径即可。


## InvokeAI 文件夹用途
在 InvokeAI 文件夹中，存在着 invokeai 文件夹，保存着模型和生成出来的图片等，以下为不同文件夹的用途。

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
└── outputs               # 生成的图片保存位置

7 directories, 2 files
```


## 配置代理
如果出现某些文件无法下载，比如在控制台出现`由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败`之类的报错时，可以尝试配置代理，有以下两种方法。

- 使用系统代理

在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。

- 使用配置文件

在和脚本同级的路径中创建一个`proxy.txt`文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

- 禁用自动设置代理

在和脚本同级的路径中创建一个`disable_proxy.txt`文件，再次启动脚本时将禁用设置代理。

>[!NOTE]  
>1. 配置文件的优先级高于系统代理配置，所以当同时使用了两种方式配置代理，脚本将优先使用配置文件中的代理配置。
>2. 该设置可通过[管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置)中提到的的`settings.ps1`进行修改。


## 管理 InvokeAI Installer 设置
运行`settings.ps1`，根据提示进行设置管理和调整。


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

或者使用[自动环境配置脚本](#使用自动环境配置脚本)解除 Windows 系统对运行 PowerShell 脚本的限制。


## ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE
运行 InvokeAI Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将 InvokeAI/cache/pip 文件夹删除，再重新运行 InvokeAI Installer。


## 运行 InvokeAI 时 InvokeAI 出现崩溃
尝试增加 Windows 系统虚拟内存。


## Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。


## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。


### 使用自动环境激活脚本
运行`terminal.ps1`后将自动打开 PowerShell 并激活 InvokeAI Env。


### 手动输入命令激活
在 InvokeAI 文件夹打开 PowerShell，输入下面的命令激活 InvokeAI Env：

```powershell
.\activate.ps1
```

>[!NOTE]  
>在 PowerShell 中一定要显示`[InvokeAI-Env]`才算进入了环境，这样才能使用下面的命令。


### 常用命令

- 启动 InvokeAI
```powershell
invokeai-web
```


- 查看 InvokeAI 的版本
```powershell
invokeai-web --version
```


- 修复 InvokeAI 数据库
```powershell
invokeai-db-maintenance --operation all
```


- 从旧版 InvokeAI 导入图片到新版的 InvokeAI
```powershell
invokeai-import-images
```


- 清理安装时产生的 Pip 缓存
```powershell
python -m pip cache purge
```


- 安装某个 Pip 软件包
```powershell
python -m pip install <package_name>
```


- 更新某个软件包
```powershell
python -m pip install <package_name> -U
```


- 重装某个软件包
```powershell
python -m pip install <package_name> --force-reinstall
```


- 卸载某个软件包
```powershell
python -m pip uninstall <package_name>
```


- 解决 ModuleNotFoundError: No module named 'controlnet_aux'
```powershell
python -m pip cache remove controlnet_aux
python -m pip uninstall controlnet_aux -y
python -m pip install controlnet_aux
```

>推荐使用`python -m pip`的写法，因为`pip`的写法可能会带来一些问题。  
>参考：[Deprecate pip, pipX, and pipX.Y · Issue #3164 · pypa/pip](https://github.com/pypa/pip/issues/3164)


- 使用 uv 安装软件包
```
uv pip install <package_name>
```
>[!NOTE]  
>uv 命令的用法可参考：[uv docs](https://docs.astral.sh/uv)


- 更新 uv
```powershell
Update-uv
```


- 列出 InvokeAI Installer 内置命令
```powershell
List-CMD
```


- 检查 InvokeAI Installer 更新
```powershell
Check-InvokeAI-Installer-Update
```
