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
    - [InvokeAI 无法正常调用显卡](#invokeai-无法正常调用显卡)


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
InvokeAI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，可以使用文本编辑器打开脚本查看该设置，以 launch.ps1 脚本为例。
```powershell
function Print-Msg ($msg){
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")][InvokeAI-Installer]:: $msg"
}
$env:PIP_INDEX_URL = "https://mirror.baidu.com/pypi/simple"
$env:PIP_EXTRA_INDEX_URL = "https://mirrors.bfsu.edu.cn/pypi/web/simple"
$env:PIP_FIND_LINKS = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$env:HF_ENDPOINT = "https://hf-mirror.com" # 这里就是 Huggingface 镜像源, 可以自己修改这个镜像源。如果不使用这个镜像源时可以将这行注释掉
$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$env:PIP_TIMEOUT=30
$env:PIP_RETRIES=5
$env:CACHE_HOME = "$PSScriptRoot/invokeai/cache"
$env:HF_HOME = "$PSScriptRoot/invokeai/cache/huggingface"
$env:MATPLOTLIBRC = "$PSScriptRoot/invokeai/cache"
$env:MODELSCOPE_CACHE = "$PSScriptRoot/invokeai/cache/modelscope/hub"
$env:MS_CACHE_HOME = "$PSScriptRoot/invokeai/cache/modelscope/hub"
$env:SYCL_CACHE_DIR = "$PSScriptRoot/invokeai/cache/libsycl_cache"
$env:TORCH_HOME = "$PSScriptRoot/invokeai/cache/torch"
$env:U2NET_HOME = "$PSScriptRoot/invokeai/cache/u2net"
$env:XDG_CACHE_HOME = "$PSScriptRoot/invokeai/cache"
$env:PIP_CACHE_DIR = "$PSScriptRoot/invokeai/cache/pip"
$env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/invokeai/cache/pycache"
$env:INVOKEAI_ROOT="$PSScriptRoot/InvokeAI/invokeai"
Print-Msg "启动 InvokeAI 中"
Print-Msg "使用浏览器打开 http://127.0.0.1:9090 地址"
Print-Msg "提示: 打开浏览器后，InvokeAI 还处在启动状态，可能会浏览器会显示连接失败，可以在弹出的 PowerShell 中查看 InvokeAI 的启动过程, 等待 InvokeAI 启动完成后刷新浏览器网页即可"
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:9090"
./python/Scripts/invokeai-web.exe --root "$PSScriptRoot/invokeai"
pause
```

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

### InvokeAI 无法正常调用显卡
尝试将显卡驱动更至最新。