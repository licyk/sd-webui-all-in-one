# SD Trainer Installer 高级功能

## 高级功能

### 使用绘世启动器
!!! info
    推荐使用自动安装绘世启动器的方法，可以参考 [命令的使用](commands.md#命令的使用) 中的 [安装绘世启动器并自动配置绘世启动器所需的环境](commands.md#安装绘世启动器并自动配置绘世启动器所需的环境) 命令，该命令可一键配置下载绘世启动器并配置，并且生成 `hanamizuki.bat` 脚本用于快捷启动绘世启动器，或者可以尝试下面手动配置绘世启动器的方法。

SD Trainer Installer 部署出来的 SD-Trainer 可以通过绘世启动器进行启动，使用绘世启动器前需要调整目录结构使绘世启动器能够正确识别到环境。

如果需要手动配置绘世启动器，请将根级 Python / Git 移动到当前内核路径前缀目录下：`<安装目录>/python` 移动到 `<安装目录>/<内核路径前缀>/python`，`<安装目录>/git` 移动到 `<安装目录>/<内核路径前缀>/git`。

!!! note
    实际路径会根据当前内核路径前缀决定：Python 会移动到 `<安装目录>/<内核路径前缀>/python`，Git 会移动到 `<安装目录>/<内核路径前缀>/git`。例如安装目录为 `SD-Trainer` 且内核路径前缀为 `core` 时，实际路径分别为 `SD-Trainer/core/python` 和 `SD-Trainer/core/git`。建议通过自动安装绘世启动器的方法来安装绘世启动器。

移动前目录的结构如下。

```
.
├── SD-Trainer
│   ├── activate.ps1
│   ├── cache
│   ├── download_models.ps1
│   ├── get_comfyui_installer.ps1
│   ├── git                           # Git 目录
│   ├── help.txt
│   ├── launch.ps1
│   ├── lora-scripts                  # SD-Trainer 路径
│   │   ├── ...
│   │   └── gui.py
│   ├── models
│   ├── python                        # Python 目录
│   ├── reinstall_pytorch.ps1
│   ├── switch_branch.ps1
│   ├── settings.ps1
│   ├── terminal.ps1
│   └── update.ps1
└── sd_trainer_installer.ps1          
```

移动 Python 和 Git 之后的目录结构。

```
.
├── SD-Trainer
│   ├── activate.ps1
│   ├── cache
│   ├── download_models.ps1
│   ├── launch_sd_trainer_installer.ps1
│   ├── help.txt
│   ├── launch.ps1
│   ├── lora-scripts                  # SD-Trainer 路径
│   │   ├── git                       # Git 目录
│   │   ├── python                    # Python 目录
│   │   ├── ...
│   │   └── main.py
│   ├── models
│   ├── reinstall_pytorch.ps1
│   ├── switch_branch.ps1
│   ├── settings.ps1
│   ├── terminal.ps1
│   └── update.ps1
└── sd_trainer_installer.ps1          
```

再下载绘世启动器放到 `<安装目录>/<内核路径前缀>` 目录中，就可以通过启动器启动 SD-Trainer。

**绘世启动器下载**

[ModelScope 下载 :material-download:](https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/hanamizuki/hanamizuki.exe){ .md-button .md-button--primary }
[HuggingFace 下载 :material-download:](https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/hanamizuki/hanamizuki.exe){ .md-button }
[GitHub Release 下载 :material-download:](https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe){ .md-button }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe){ .md-button }

### 创建快捷启动方式
!!! info
    该设置可通过 [管理 SD Trainer Installer 设置](config.md#管理-sd-trainer-installer-设置) 中提到的 `settings.ps1` 进行修改。

在脚本同级目录创建 `enable_shortcut.txt` 文件，当运行 `launch.ps1` 时将会自动创建快捷启动方式，下次启动时可以使用快捷方式启动 SD-Trainer。

快捷方式会根据当前系统写入以下位置：

- Windows：桌面 `.lnk` 文件，以及 `%APPDATA%\Microsoft\Windows\Start Menu\Programs` 中的开始菜单快捷方式。
- Linux：桌面 `.desktop` 文件，以及 `~/.local/share/applications/` 中的应用入口。
- macOS：桌面 `.app` 应用，以及 `/Applications/` 中的应用入口。

!!! warning
    如果 SD-Trainer 的路径发生移动，需要重新运行 `launch.ps1` 更新快捷启动方式。

### 使用命令运行 SD Trainer Installer
SD Trainer Installer 支持使用命令参数设置安装 SD-Trainer 的参数，支持的参数如下。

**参数清单**

- `-Help`：获取 SD Trainer Installer 的帮助信息。
- `-CorePrefix` `<内核路径前缀>`：设置内核路径前缀。可填写内核目录名、相对路径或绝对路径；绝对路径会在运行时转换为相对于安装器脚本目录的内核路径前缀。未指定时会按预设目录自动识别，未找到时使用 `core`。
- `-InstallPath` `<安装 SD Trainer 的绝对路径>`：指定 SD Trainer Installer 安装 SD Trainer 的路径，使用绝对路径表示。
    例如：`./sd_trainer_installer.ps1 -InstallPath "D:\Download"`，这将指定安装到 D:\Download 路径。
- `-PyTorchMirrorType` `<PyTorch 镜像源类型>`：指定安装 PyTorch 时使用的镜像源类型。可指定的类型包括：`cu113`, `cu117`, `cu118`, `cu121`, `cu124`, `cu126`, `cu128`, `cu129`, `cu130`, `rocm5.4.2`, `rocm5.6`, `rocm5.7`, `rocm6.0`, `rocm6.1`, `rocm6.2`, `rocm6.2.4`, `rocm6.3`, `rocm6.4`, `rocm7.1`, `rocm_rdna3`, `rocm_rdna3.5`, `rocm_rdna4`, `rocm_win`, `xpu`, `ipex_legacy_arc`, `cpu`, `directml`, `all`
- `-InstallPythonVersion` `<Python 版本>`：指定要安装的 Python 版本。可选值：`3.10`, `3.11`, `3.12`, `3.13`, `3.14`
- `-UseUpdateMode`：指定 SD Trainer Installer 使用更新模式，只对 SD Trainer Installer 的管理脚本进行更新。
- `-DisablePyPIMirror`：禁用 SD Trainer Installer 使用 PyPI镜像源，使用 PyPI 官方源下载 Python 软件包。
- `-DisableProxy`：禁用 SD Trainer Installer 自动设置代理服务器。
- `-UseCustomProxy` `<代理服务器地址>`：使用自定义的代理服务器地址。例如：`-UseCustomProxy "http://127.0.0.1:10809"`
- `-DisableUV`：禁用 SD Trainer Installer 使用 uv 安装 Python 软件包，改用 Pip 安装。
- `-DisableGithubMirror`：禁用 SD Trainer Installer 自动设置 Github 镜像源。
- `-UseCustomGithubMirror` `<Github 镜像站地址>`：使用自定义的 Github 镜像站地址。
- `-InstallBranch` `<安装的 SD Trainer 分支>`：指定安装的 SD Trainer 分支。未指定时默认安装 Akegarasu/SD-Trainer。
    支持的分支如下：
    - `sd_trainer_main`: Akegarasu - SD-Trainer 分支
    - `kohya_gui_main`: bmaltais - Kohya GUI 分支
- `-BuildMode`：启用构建模式，在基础安装结束后将调用管理脚本执行剩余任务。出现错误时不再暂停而是直接退出。
    多个脚本将按以下优先级执行：
    - `reinstall_pytorch.ps1`：对应`-BuildWithTorch`/`-BuildWithTorchReinstall`
    - `download_models.ps1`：对应`-BuildWithModel`
    - `switch_branch.ps1`：对应`-BuildWithBranch`
    - `update.ps1`：对应`-BuildWithUpdate`
    - `launch.ps1`：对应`-BuildWithLaunch`
- `-BuildWithTorch` `<PyTorch 版本编号>`：(需添加 `-BuildMode`) 调用 `reinstall_pytorch.ps1` 脚本，根据版本编号安装指定的 PyTorch 版本。编号可运行该脚本查看。
- `-BuildWithTorchReinstall`：(需添加 `-BuildMode`及`-BuildWithTorch`) 执行 PyTorch 指定版本安装时使用强制重新安装模式。
- `-BuildWithModel` `<模型编号列表>`：(需添加 `-BuildMode`) 调用 `download_models.ps1` 脚本，根据编号列表下载模型。编号可运行该脚本查看。
- `-BuildWithBranch` `<SD Trainer 分支编号>`：(需添加 `-BuildMode`) 调用 `switch_branch.ps1` 脚本，根据分支编号切换分支。编号可运行该脚本查看。
- `-BuildWithUpdate`：(需添加 `-BuildMode`) 安装流程结束后调用 `update.ps1` 脚本，更新 SD Trainer 内核。
- `-BuildWithLaunch`：(需添加 `-BuildMode`) 安装流程结束后调用 `launch.ps1` 脚本，执行启动前的环境检查，但跳过启动 SD Trainer。
- `-NoPreDownloadModel`：安装 SD Trainer 时跳过预下载模型。
- `-PyTorchPackage` `<PyTorch 软件包>`：(需搭配 `-xFormersPackage`) 指定安装的 PyTorch 版本。如：`-PyTorchPackage "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"`
- `-xFormersPackage` `<xFormers 软件包>`：(需搭配 `-PyTorchPackage`) 指定安装的 xFormers 版本。如：`-xFormersPackage "xformers===0.0.26.post1+cu118"`
- `-InstallHanamizuki`：安装绘世启动器，并生成 `hanamizuki.bat` 用于启动。
- `-NoCleanCache`：安装结束后保留下载的 Python 软件包缓存。
- `-DisableModelMirror`：不使用 ModelScope 下载模型, 使用 HuggingFace 下载模型。
- `-NoPause`：脚本执行完成后不暂停, 直接退出。
- `-DisableUpdate`：(仅在构建模式生效且只作用于管理脚本) 禁用 SD Trainer Installer 更新检查。
- `-DisableHuggingFaceMirror`：(仅在构建模式生效且只作用于管理脚本) 禁用 HuggingFace 镜像源。
- `-UseCustomHuggingFaceMirror` `<HuggingFace 镜像源地址>`：(仅在构建模式生效且只作用于管理脚本) 使用自定义 HuggingFace 镜像源。例如：`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`
- `-LaunchArg` `<SD Trainer 启动参数>`：(仅在构建模式生效且只作用于管理脚本) 设置 SD Trainer 自定义启动参数。如：`-LaunchArg "--fast --auto-launch"`
- `-EnableShortcut`：(仅在构建模式生效且只作用于管理脚本) 创建 SD Trainer 启动快捷方式。

例如在 `D:/Download` 这个路径安装 [bmaltais/Kohya GUI](https://github.com/bmaltais/kohya_ss)，则在 SD Trainer Installer 所在路径打开 PowerShell，使用参数运行 SD Trainer Installer。

```powershell
./sd_trainer_installer.ps1 -InstallPath "D:/Download" -InstallBranch "kohya_gui_main"
```

### SD Trainer Installer 构建模式和普通安装模式
SD Trainer Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 SD Trainer Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，模型安装，运行环境检查和修复等并不会执行，这些步骤是在 SD Trainer Installer 管理脚本中进行，如执行 `launch.ps1`,`reinstall_pytorch.ps1` 脚本等。

而 SD Trainer Installer 构建模式允许在执行基础安装流程后，调用 SD Trainer Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 SD Trainer Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读 [使用命令运行 SD Trainer Installer](advanced.md#使用命令运行-sd-trainer-installer) 中的参数说明。

!!! info
    通常安装 SD-Trainer 并不需要使用 SD Trainer Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。

使用 Github Action 提供的容器可用于运行 SD Trainer Installer 并启用构建模式，实现自动化制作整合包，Github Action 工作流代码可参考：[build_sd_trainer.yml · licyk/sd-webui-all-in-one](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/workflows/build_sd_trainer.yml)
