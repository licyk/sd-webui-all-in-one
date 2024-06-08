<div align="center">

# SD-Trainer Installer

_✨一键安装 SD-Trainer_

</div>

## 目录
- [SD-Trainer Installer](#sd-trainer-installer)
  - [目录](#目录)
  - [简介](#简介)
  - [环境配置](#环境配置)
    - [解除脚本限制](#解除脚本限制)
    - [启用 Windows 长路径支持](#启用-windows-长路径支持)
  - [安装](#安装)
    - [手动下载 SD-Trainer Installer 并右键运行](#手动下载-sd-trainer-installer-并右键运行)
    - [使用 PowerShell 命令](#使用-powershell-命令)
  - [使用](#使用)
    - [启动 SD-Trainer](#启动-sd-trainer)
    - [更新 SD-Trainer](#更新-sd-trainer)
    - [设置 SD-Trainer 启动参数](#设置-sd-trainer-启动参数)
    - [进入 SD-Trainer 所在的 Python 环境](#进入-sd-trainer-所在的-python-环境)
    - [获取最新的 SD-Trainer Installer 脚本](#获取最新的-sd-trainer-installer-脚本)
    - [恢复被修改 / 删除的脚本](#恢复被修改--删除的脚本)
    - [设置 HuggingFace 镜像](#设置-huggingface-镜像)
    - [设置 Github 镜像源](#设置-github-镜像源)
    - [配置代理](#配置代理)
    - [添加模型](#添加模型)
    - [模型训练的方法](#模型训练的方法)
    - [重装 SD-Trainer](#重装-sd-trainer)
    - [重装 Python 环境](#重装-python-环境)
    - [重装 Git](#重装-git)
    - [重装 PyTorch](#重装-pytorch)
    - [PowerShell 中出现 xFormers 报错](#powershell-中出现-xformers-报错)
    - [SD-Trainer 无法正常调用显卡](#sd-trainer-无法正常调用显卡)
    - [卸载 SD-Trainer](#卸载-sd-trainer)
    - [移动 SD-Trainer 的路径](#移动-sd-trainer-的路径)
    - [更新 SD-Trainer 管理脚本](#更新-sd-trainer-管理脚本)
    - [无法使用 PowerShell 运行](#无法使用-powershell-运行)
    - [RuntimeError: Error(s) in loading state\_dict for UNet2DConditionModel](#runtimeerror-errors-in-loading-state_dict-for-unet2dconditionmodel)
    - [UnicodeDecodeError: 'utf-8' codec can't decode byte xxxx in position xxx: invalid continuation byte](#unicodedecodeerror-utf-8-codec-cant-decode-byte-xxxx-in-position-xxx-invalid-continuation-byte)
    - [RuntimeError: NaN detected in latents: X:\\xxx\\xxx\\xx.png](#runtimeerror-nan-detected-in-latents-xxxxxxxxxpng)
    - [CUDA out of memory](#cuda-out-of-memory)
    - [DefaultCPUAllocator: not enough memory](#defaultcpuallocator-not-enough-memory)
    - [Loss?](#loss)
    - [训练素材中图片的分辨率不一致，而且有些图片的分辨率很大，需要裁剪?](#训练素材中图片的分辨率不一致而且有些图片的分辨率很大需要裁剪)
    - [命令的使用](#命令的使用)


## 简介
一个在 Windows 系统上部署 [SD-Trainer](https://github.com/Akegarasu/lora-scripts) 的 PowerShell 脚本。


## 环境配置
如果是初次使用 PowerShell 脚本，需要解除 Windows 系统对脚本的限制。

Windows 系统默认未启用长路径支持，这可能会导致部分功能出现异常，需要启用 Windows 长路径支持来解决该问题。

### 解除脚本限制
使用管理员权限打开 PowerShell，运行以下命令：
```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser

```
输入 `Y` 并回车以确认。

>[!NOTE]  
>关于 PowerShell 执行策略的说明：[关于执行策略 - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)

### 启用 Windows 长路径支持
在刚刚的 PowerShell 中运行下面的命令：
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

>[!NOTE]  
>关于 Windows 长路径支持的说明：[最大路径长度限制 - Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)


## 安装
可以使用以下其中一种方法运行 SD-Trainer Installer。

### 手动下载 SD-Trainer Installer 并右键运行

||SD-Trainer Installer 下载地址|
|---|---|
|↓|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1)|
|↓|[下载地址 2](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1)|
|↓|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1)|
|↓|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1)|

### 使用 PowerShell 命令
```powershell
irm https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1 | iex
```


在 SD-Trainer Installer 成功安装 SD-Trainer 后，在 SD-Trainer 文件夹中可以看到 SD-Trainer 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 SD-Trainer Installer。


## 使用
在 SD-Trainer 文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本，选择使用 PowerShell 运行后即可运行。在 lora-scripts 文件夹中也有 PowerShell 脚本，但不建议使用该文件夹中的脚本进行运行。

### 启动 SD-Trainer
运行 launch.ps1 脚本。

### 更新 SD-Trainer
运行 update.ps1 脚本。

### 设置 SD-Trainer 启动参数
要设置 SD-Trainer 的启动参数，可以在和 launch.ps1 脚本同级的目录创建一个 launch_args.txt 文件，在文件内写上启动参数，运行 SD-Trainer 启动脚本时将自动读取该文件内的启动参数并应用。

>[!NOTE]  
>SD-Trainer 可用的启动参数可阅读：[Akegarasu/lora-scripts - 程序参数](https://github.com/Akegarasu/lora-scripts/blob/main/README-zh.md#%E7%A8%8B%E5%BA%8F%E5%8F%82%E6%95%B0)

### 进入 SD-Trainer 所在的 Python 环境
如果需要使用 Python、Pip、SD-Trainer 的命令时，请勿将 SD-Trainer 的 python 文件夹添加到环境变量，这将会导致不良的后果产生。  
正确的方法是在 SD-Trainer 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 SD-Trainer Env：

```powershell
.\activate.ps1
```

这样就进入 SD-Trainer 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 获取最新的 SD-Trainer Installer 脚本
运行 get_sd_trainer_installer.ps1 脚本。

### 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 SD-Trainer Installer 重新生成这些脚本。

>[!NOTE]  
>SD-Trainer Installer 必须放在 SD-Trainer 文件夹外运行，不知道放哪的可以参考下面的目录结构。

```
$ tree -L 2
.
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── SD-Trainer                        # 这是 SD-Trainer 文件夹
│   ├── activate.ps1                  # 进入 SD-Trainer Env 的脚本
│   ├── cache                         # 缓存文件夹
│   ├── download_models.ps1           # 下载模型的脚本
│   ├── get_sd_trainer_installer.ps1  # 获取最新的 SD-Trainer Installer 的脚本
│   ├── git                           # Git 目录
│   ├── help.txt                      # 帮助文档
│   ├── launch.ps1                    # 启动 SD-Trainer 的脚本
│   ├── lora-scripts                  # SD-Trainer 路径
│   ├── models                        # download_models.ps1 脚本下载模型的路径
│   ├── python                        # Python 目录
│   ├── reinstall_pytorch.ps1         # 重新安装 PyTorch 的脚本
│   └── update.ps1                    # 更新 SD-Trainer 的脚本
├── sd_trainer_installer.ps1          # SD-Trainer Installer 放在 SD-Trainer 文件夹外面，和 SD-Trainer 文件夹同级
└── QQ Files

8 directories, 9 files
```

### 设置 HuggingFace 镜像
SD-Trainer Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建`hf_mirror.txt`文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源|
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建`disable_hf_mirror.txt`文件，再次启动脚本时将禁用 HuggingFace 镜像源。

### 设置 Github 镜像源
SD-Trainer Installer 为了加速访问 Github 的速度，加快下载和更新 SD-Trainer 的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建`gh_mirror.txt`文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

|可用的 Github 镜像源|
|---|
|https://mirror.ghproxy.com/https://github.com|
|https://ghproxy.net/https://github.com|
|https://gitclone.com/github.com|
|https://gh-proxy.com/https://github.com|
|https://ghps.cc/https://github.com|
|https://gh.idayer.com/https://github.com|

如果需要禁用设置 Github 镜像源，在和脚本同级的目录中创建`disable_gh_mirror.txt`文件，再次启动脚本时将禁用 Github 镜像源。

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

### 添加模型
在 SD-Trainer 中可以选择本地已下载的模型，如果有下载某些用于训练的模型（非融合模型），可以使用 download_models.ps1 脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。

### 模型训练的方法
推荐的哔哩哔哩 UP 主：
- 青龙圣者：https://space.bilibili.com/219296
- 秋葉aaaki：https://space.bilibili.com/12566101
- 琥珀青葉：https://space.bilibili.com/507303431

一些训练模型的教程：
- https://rentry.org/59xed3
- https://civitai.com/articles/2056
- https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
- https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
- https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
- https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
- https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
- https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora

除了上面的教程，也可以通过哔哩哔哩、Google 等平台搜索教程。

### 重装 SD-Trainer
将 SD-Trainer 文件夹中的 lora-scripts 文件夹删除，然后运行 SD-Trainer Installer 重新部署 SD-Trainer。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以将 SD-Trainer 文件夹中的 python 文件夹删除，然后运行 SD-Trainer Installer 重新构建 Python 环境。

### 重装 Git
将 SD-Trainer 文件夹中的 git 文件夹删除，然后运行 SD-Trainer Installer 重新下载 Git。

### 重装 PyTorch
运行 reinstall_pytorch.ps1 脚本，并根据脚本提示的内容进行操作。

### PowerShell 中出现 xFormers 报错
在控制台中出现有关 xFormers 的警告信息，类似下面的内容。
```
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.2.1+cu118 with CUDA 1108 (you have 2.2.2+cu121)
    Python  3.10.11 (you have 3.10.11)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
```
这是因为 xFormers 所适配的 CUDA 版本和 PyTorch 所带的 CUDA 版本不一致，请运行 reinstall_pytorch.ps1 重装 PyTorch。

### SD-Trainer 无法正常调用显卡
尝试将显卡驱动更至最新，确保显卡驱动支持的 CUDA 版本大于或等于 PyTorch 中所带的 CUDA 版本，或者使用 reinstall_pytorch.ps1 重装 PyTorch。

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

### 卸载 SD-Trainer
使用 SD-Trainer Installer 安装 SD-Trainer 后，所有的文件都存放在 SD-Trainer 文件夹中，只需要删除 SD-Trainer 文件夹即可卸载 SD-Trainer。

### 移动 SD-Trainer 的路径
直接将 SD-Trainer 文件夹移动到别的路径即可。

### 更新 SD-Trainer 管理脚本
运行 get_sd_trainer_installer.ps1 获取最新的 SD-Trainer Installer，并运行一次 SD-Trainer Installer。

### 无法使用 PowerShell 运行
运行 PowerShell 脚本时出现以下错误。
```
.\sd_trainer_installer.ps1 : 无法加载文件 D:\SD-Trainer\sd_trainer_installer.ps1。
未对文件 D:\SD-Trainer\sd_trainer_installer.ps1进行数字签名。无法在当前系统上运行该脚本。
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
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### RuntimeError: Error(s) in loading state_dict for UNet2DConditionModel
检查训练参数是否正确，确认是否选择对应大模型版本的训练参数。

### UnicodeDecodeError: 'utf-8' codec can't decode byte xxxx in position xxx: invalid continuation byte
检查训练参数中是否存在中文，如模型文件名是否包含中文等。

### RuntimeError: NaN detected in latents: X:\xxx\xxx\xx.png
检查图片是否有问题，如果是训练 SDXL 的 LoRA，请外挂一个 [sdxl_fp16_fix](http://modelscope.cn/api/v1/models/licyks/sd-vae/repo?Revision=master&FilePath=sdxl_1.0%2Fsdxl_fp16_fix_vae.safetensors) 的 VAE 或者使用 BF16 精度进行训练。

### CUDA out of memory
确认显卡的显存大小是否满足训练要求（显存最低要求 > 6G），如果满足，重新调整训练参数。

### DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。

### Loss?
没必要看。想要看练出来的模型效果如何，直接用模型进行跑图测试，Loss 并不能准确的代表训练出来的模型的好坏。

### 训练素材中图片的分辨率不一致，而且有些图片的分辨率很大，需要裁剪?
SD-Trainer 默认开启 arb 桶，自动处理不同分辨率的图片，无需手动进行图片裁剪。

### 命令的使用
在 SD-Trainer 文件夹打开 PowerShell，输入下面的命令激活 SD-Trainer Env：

```powershell
.\activate.ps1
```
>[!NOTE]  
>在 PowerShell 中一定要显示`[SD-Trainer Env]`才算进入了环境，这样才能使用下面的命令。

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

>推荐使用`python -m pip`的写法，因为`pip`的写法可能会带来一些问题。  
>参考：[Deprecate pip, pipX, and pipX.Y · Issue #3164 · pypa/pip](https://github.com/pypa/pip/issues/3164)

- 更新仓库
```powershell
git pull --recurse-submodules
```

- 运行某个 Python 脚本
```powershell
python <python_script.py>
```

- 下载文件
```powershell
aria2c <url> -c -x <thread_count> -d <dir> -o <output_file_name>
```