<div align="center">

# InvokeAI Installer

_✨一键安装 InvokeAI_

</div>

## 目录
- [InvokeAI Installer](#invokeai-installer)
  - [目录](#目录)
  - [简介](#简介)
  - [环境配置](#环境配置)
    - [解除脚本限制](#解除脚本限制)
    - [启用 Windows 长路径支持](#启用-windows-长路径支持)
  - [安装](#安装)
    - [手动下载 InvokeAI Installer 并右键运行](#手动下载-invokeai-installer-并右键运行)
    - [使用 PowerShell 命令](#使用-powershell-命令)
  - [使用](#使用)
    - [启动 InvokeAI](#启动-invokeai)
    - [更新 InvokeAI](#更新-invokeai)
    - [修复 InvokeAI 图库出现无效图片](#修复-invokeai-图库出现无效图片)
    - [进入 InvokeAI 所在的 Python 环境](#进入-invokeai-所在的-python-环境)
    - [获取最新的 InvokeAI Installer 脚本](#获取最新的-invokeai-installer-脚本)
    - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
    - [设置 InvokeAI 中文](#设置-invokeai-中文)
    - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
    - [添加模型](#添加模型)
    - [InvokeAI 的使用方法](#invokeai-的使用方法)
    - [重装 InvokeAI](#重装-invokeai)
    - [显存占用很大](#显存占用很大)
    - [PowerShell 中出现 xFormers 报错](#powershell-中出现-xformers-报错)
    - [InvokeAI 无法正常调用显卡](#invokeai-无法正常调用显卡)
    - [卸载 InvokeAI](#卸载-invokeai)
    - [移动 InvokeAI 的路径](#移动-invokeai-的路径)
    - [InvokeAI 文件夹用途](#invokeai-文件夹用途)
    - [更新 InvokeAI 管理脚本](#更新-invokeai-管理脚本)
    - [配置代理](#配置代理)
    - [命令的使用](#命令的使用)


## 简介
一个在 Windows 系统上部署 [InvokeAI](https://github.com/invoke-ai/InvokeAI) 的 PowerShell 脚本。


## 环境配置
如果是初次使用 PowerShell 脚本，需要解除 Windows 系统对脚本的限制。

Windows 系统默认未启用长路径支持，这可能会导致部分功能出现异常，需要启用 Windows 长路径支持来解决该问题。

### 解除脚本限制
使用管理员权限打开 PowerShell，运行以下命令：
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
输入 `Y` 并回车以确认。

### 启用 Windows 长路径支持
在刚刚的 PowerShell 中运行下面的命令：
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```


## 安装
可以使用以下其中一种方法运行 InvokeAI Installer。

### 手动下载 InvokeAI Installer 并右键运行

||InvokeAI Installer 下载地址|
|---|---|
|↓|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1)|
|↓|[下载地址 2](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1)|
|↓|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|
|↓|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1)|

### 使用 PowerShell 命令
```powershell
irm https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1 | iex
```


在 InvokeAI Installer 成功安装 InvokeAI 后，在 InvokeAI 文件夹中可以看到 InvokeAI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 InvokeAI Installer。


## 使用
在 InvokeAI 文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择使用 PowerShell 运行后即可运行。

### 启动 InvokeAI
运行 launch.ps1 脚本。

### 更新 InvokeAI
运行 update.ps1 脚本。

### 修复 InvokeAI 图库出现无效图片
在 InvokeAI 的图片保存目录删除图片后，会发现 InvokeAI 的图库中图片还存在，并且显示损坏，无法查看，可以运行 fix-db.ps1 进行修复。

### 进入 InvokeAI 所在的 Python 环境
如果需要使用 Python、Pip、InvokeAI 的命令时，请勿将 InvokeAI 的 python 文件夹添加到环境变量，这将会导致不良的后果产生。  
正确的方法是在 InvokeAI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 InvokeAI Env：

```powershell
.\activate.ps1
```

这样就进入 InvokeAI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 获取最新的 InvokeAI Installer 脚本
运行 get_invokeai_installer.ps1 脚本。

### 恢复被修改 / 删除的脚本
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
│   ├── fix-db.ps1                  # 修复 InvokeAI 数据库的脚本
│   ├── get_invokeai_installer.ps1  # 获取最新的 InvokeAI Installer 的脚本
│   ├── help.txt                    # 帮助文档
│   ├── invokeai                    # InvokeAI 生成的图片和模型存放路径
│   ├── launch.ps1                  # 启动 InvokeAI 的脚本
│   ├── python                      # Python 目录
│   └── update.ps1                  # 更新 InvokeAI 的脚本
├── invokeai_installer.ps1          # InvokeAI Installer 放在 InvokeAI 文件夹外面，和 InvokeAI 文件夹同级
└── QQ Files

7 directories, 8 files
```

### 设置 InvokeAI 中文
InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。

### 设置 HuggingFace 镜像
InvokeAI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源||
|---|---|
|https://hf-mirror.com||
|https://huggingface.sukaka.top||

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。

### 添加模型
在 InvokeAI 左侧栏选择模型管理器，在模型管理器中可以添加本地的模型或者下载模型，可以和 SD WebUI / ComfyUI 共享模型。具体可以查看 [Installing Models - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/installation/050_INSTALLING_MODELS/)。

### InvokeAI 的使用方法
推荐下面两个文档：  
- [给所有想学习AI辅助绘画的人的入门课](https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140)
- [InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI)

除了上面的两个文档，也可以通过 Google 等平台搜索教程。

### 重装 InvokeAI
如果 InvokeAI 因为严重损坏导致无法正常使用，可以将 InvokeAI 文件夹中的 python 文件夹删除，然后运行 InvokeAI Installer 重新部署 InvokeAI。

### 显存占用很大
检查 xFomers 是否正确安装，可以运行 InvokeAI Install 查看 xFormers 是否被正确安装。

### PowerShell 中出现 xFormers 报错
在控制台中出现有关 xFormers 的警告信息，类似下面的内容。
```
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.2.1+cu118 with CUDA 1108 (you have 2.2.2+cu121)
    Python  3.10.11 (you have 3.10.11)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
```
这是因为 xFormers 所适配的 CUDA 版本和 PyTorch 所带的 CUDA 版本不一致，请运行 InvokeAI Installer 进行修复。

### InvokeAI 无法正常调用显卡
尝试将显卡驱动更至最新。

### 卸载 InvokeAI
使用 InvokeAI Installer 安装 InvokeAI 后，所有的文件都存放在 InvokeAI 文件夹中，只需要删除 InvokeAI 文件夹即可卸载 InvokeAI。

### 移动 InvokeAI 的路径
直接将 InvokeAI 文件夹移动到别的路径即可。

### InvokeAI 文件夹用途
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

### 更新 InvokeAI 管理脚本
运行 get_invokeai_installer.ps1 获取最新的 InvokeAI Installer，并运行一次 InvokeAI Installer。

### 配置代理
如果出现某些文件无法下载，比如在控制台出现`由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败`之类的报错时，可以尝试配置代理，有以下两种方法。

- 使用系统代理

在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。

- 使用配置文件

在和脚本同级的路径中创建一个`proxy.txt`文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

- 禁用自动设置代理

在和脚本同级的路径中创建一个`disable_proxy.txt`文件，再次启动脚本时将禁用设置代理。

>[!NOTE]  
>配置文件的优先级高于系统代理配置，所以当同时使用了两种方式配置代理，脚本将优先使用配置文件中的代理配置

### 命令的使用
在 InvokeAI 文件夹打开 PowerShell，输入下面的命令激活 InvokeAI Env：

```powershell
.\activate.ps1
```
>[!NOTE]  
>在 PowerShell 中一定要显示`[InvokeAI-Env]`才算进入了环境，这样才能使用下面的命令。

- 清理安装时产生的 Pip 缓存
```powershell
python -m pip cache purge
```

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