# RVC Next WebUI Installer 高级功能

## 高级功能

### 创建快捷启动方式
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](config.md#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

在脚本同级目录创建 `enable_shortcut.txt` 文件，当运行 `launch.ps1` 时将会自动创建快捷启动方式，下次启动时可以使用快捷方式启动 RVC Next WebUI。

快捷方式会根据当前系统写入以下位置：

- Windows：桌面 `.lnk` 文件，以及 `%APPDATA%\Microsoft\Windows\Start Menu\Programs` 中的开始菜单快捷方式。
- Linux：桌面 `.desktop` 文件，以及 `~/.local/share/applications/` 中的应用入口。
- macOS：桌面 `.app` 应用，以及 `/Applications/` 中的应用入口。

!!! warning
    如果 RVC Next WebUI 的路径发生移动，需要重新运行 `launch.ps1` 更新快捷启动方式。

### 使用 Hanafubuki 启动器
可在安装 RVC Next WebUI 时添加 `-InstallHanafubuki`，或进入 RVC Next WebUI Env 后运行 `Install-Hanafubuki`。安装器会按 Hugging Face、ModelScope 的顺序读取版本清单，并下载当前平台和架构对应的安装包。

Hanafubuki 的安装位置如下：

- Windows：`<安装目录>/hanafubuki-launcher.exe`
- Linux：`<安装目录>/hanafubuki-launcher`
- macOS：`<安装目录>/Hanafubuki Launcher.app`

为了让 Hanafubuki 能够正确识别到环境，安装器会将根级 Python / Git 移入当前内核路径前缀目录，即从 `<安装目录>/python`、`<安装目录>/git` 移动到 `<安装目录>/<内核路径前缀>/python`、`<安装目录>/<内核路径前缀>/git`。如果目标目录已存在，安装器不会覆盖已有环境。

### 使用命令运行 RVC Next WebUI Installer
RVC Next WebUI Installer 支持使用命令参数设置安装 RVC Next WebUI 的参数，支持的参数如下。

**参数清单**

- `-Help`：获取 RVC Next WebUI Installer 的帮助信息。
- `-CorePrefix` `<内核路径前缀>`：设置内核路径前缀。可填写内核目录名、相对路径或绝对路径；绝对路径会在运行时转换为相对于安装器脚本目录的内核路径前缀。未指定时会按预设目录自动识别，未找到时使用 `core`。
- `-InstallPath` `<安装 RVC Next WebUI 的绝对路径>`：指定 RVC Next WebUI Installer 安装 RVC Next WebUI 的路径，使用绝对路径表示。
    例如：`./rvc_next_webui_installer.ps1 -InstallPath "D:\Download"`，这将指定安装到 D:\Download 路径。
- `-PyTorchMirrorType` `<PyTorch 镜像源类型>`：指定安装 PyTorch 时使用的镜像源类型。可指定的类型包括：`cu113`, `cu117`, `cu118`, `cu121`, `cu124`, `cu126`, `cu128`, `cu129`, `cu130`, `rocm5.4.2`, `rocm5.6`, `rocm5.7`, `rocm6.0`, `rocm6.1`, `rocm6.2`, `rocm6.2.4`, `rocm6.3`, `rocm6.4`, `rocm7.1`, `rocm7.2`, `rocm7`, `rocm10`, `xpu`, `ipex_legacy_arc`, `cpu`, `directml`, `all`
    RVC Next 不支持 DirectML，指定 `directml` 时安装会直接报错并终止；如果所选类型对应的 PyTorch 版本低于 2.7.1（如较旧的 CUDA / ROCm 类型），安装同样会报错并终止。
- `-InstallPythonVersion` `<Python 版本>`：指定要安装的 Python 版本。可选值：`3.10`, `3.11`, `3.12`, `3.13`, `3.14`
- `-RestoreFromSnapshot`：启用快照重建模式，根据快照文件重新准备 Python 版本并恢复环境。
- `-SnapshotPath` `<快照文件>`：指定用于快照重建的环境快照 JSON 文件路径。启用快照重建模式时需要和 `-RestoreFromSnapshot` 同时使用。
- `-DisableSnapshot`：禁用自动快照，包括安装结束后的结果快照以及管理脚本执行前的自动快照。
- `-UseUpdateMode`：指定 RVC Next WebUI Installer 使用更新模式，只对 RVC Next WebUI Installer 的管理脚本进行更新。
- `-DisablePyPIMirror`：禁用 RVC Next WebUI Installer 使用 PyPI镜像源，使用 PyPI 官方源下载 Python 软件包。
- `-DisableAutoMirror`：禁用 CLI 自动镜像源选择。默认自动镜像启用时，Python CLI 会强制覆盖 PyPI / Github / HuggingFace 等手动镜像设置；需要手动控制这些镜像参数时，请添加该参数。
- `-DisableProxy`：禁用 RVC Next WebUI Installer 自动设置代理服务器。
- `-UseCustomProxy` `<代理服务器地址>`：使用自定义的代理服务器地址。例如：`-UseCustomProxy "http://127.0.0.1:10809"`
- `-DisableUV`：禁用 RVC Next WebUI Installer 使用 uv 安装 Python 软件包，改用 Pip 安装。
- `-DisableGithubMirror`：禁用 RVC Next WebUI Installer 自动设置 Github 镜像源。
- `-UseCustomGithubMirror` `<Github 镜像站地址>`：使用自定义的 Github 镜像站地址。例如：`https://ghfast.top/https://github.com` 等。
- `-BuildMode`：启用构建模式，在基础安装结束后将调用管理脚本执行剩余任务。出现错误时不再暂停而是直接退出。
    多个脚本将按以下优先级执行：
    - `reinstall_pytorch.ps1`：对应`-BuildWithTorch`/`-BuildWithTorchReinstall`
    - `update.ps1`：对应`-BuildWithUpdate`
    - `launch.ps1`：对应`-BuildWithLaunch`
- `-BuildWithTorch` `<PyTorch 版本编号>`：(需添加 `-BuildMode`) 调用 `reinstall_pytorch.ps1` 脚本，根据版本编号安装指定的 PyTorch 版本。编号可运行该脚本查看，请选择 2.7.1 及以上版本且非 DirectML 的 PyTorch。
- `-BuildWithTorchReinstall`：(需添加 `-BuildMode`及`-BuildWithTorch`) 执行 PyTorch 指定版本安装时使用强制重新安装模式。
- `-BuildWithUpdate`：(需添加 `-BuildMode`) 安装流程结束后调用 `update.ps1` 脚本，更新 RVC Next WebUI 内核。
- `-BuildWithLaunch`：(需添加 `-BuildMode`) 安装流程结束后调用 `launch.ps1` 脚本，执行启动前的环境检查，但跳过启动 RVC Next WebUI。
- `-PyTorchPackage` `<PyTorch 软件包>`：指定安装的 PyTorch 版本，RVC Next 需要 2.7.1 及以上版本的 PyTorch，低于该版本时安装会直接报错并终止。如：`-PyTorchPackage "torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128"`
- `-NoCleanCache`：安装结束后保留下载的 Python 软件包缓存。
- `-InstallHanafubuki`：安装当前平台和架构对应的 Hanafubuki 启动器，并将根级 Python / Git 移入当前内核路径前缀目录。
- `-NoPause`：脚本执行完成后不暂停, 直接退出。
- `-DisableUpdate`：(仅在构建模式生效且只作用于管理脚本) 禁用 RVC Next WebUI Installer 更新检查。
- `-DisableHuggingFaceMirror`：(仅在构建模式生效且只作用于管理脚本) 禁用 HuggingFace 镜像源。
- `-UseCustomHuggingFaceMirror` `<HuggingFace 镜像源地址>`：(仅在构建模式生效且只作用于管理脚本) 使用自定义 HuggingFace 镜像源。例如：`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`
- `-LaunchArg` `<RVC Next WebUI 启动参数>`：(仅在构建模式生效且只作用于管理脚本) 设置 RVC Next WebUI 自定义启动参数。如：`-LaunchArg "--port 7870 --no-browser"`
- `-DisableHotpatcher`：(仅在构建模式生效且只作用于管理脚本) 禁用 RVC Next WebUI Hotpatcher 补丁系统。
- `-EnableHotpatcherRuntime`：启用 Hotpatcher runtime host 连接。
- `-HotpatcherPort` `<端口>`：(仅在构建模式生效且只作用于管理脚本) 指定 Hotpatcher runtime 模式通信端口。有效范围为 `1` 到 `65535`，优先级高于 `hotpatcher_port.txt`。
- `-EnableShortcut`：(仅在构建模式生效且只作用于管理脚本) 创建 RVC Next WebUI 启动快捷方式。
- `-DisableCUDAMalloc`：(仅在构建模式生效且只作用于管理脚本) 禁用通过 `PYTORCH_CUDA_ALLOC_CONF` / `PYTORCH_ALLOC_CONF` 环境变量设置 CUDA 内存分配器。
- `-DisableEnvCheck`：(仅在构建模式生效且只作用于管理脚本) 禁用检查 RVC Next WebUI 运行环境问题。

例如在 `D:/Download` 这个路径安装 RVC Next WebUI，则在 RVC Next WebUI Installer 所在路径打开 PowerShell，使用参数运行 RVC Next WebUI Installer。

```powershell
./rvc_next_webui_installer.ps1 -InstallPath "D:/Download"
```

### RVC Next WebUI Installer 构建模式和普通安装模式
RVC Next WebUI Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 RVC Next WebUI Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，运行环境检查和修复等并不会执行，这些步骤是在 RVC Next WebUI Installer 管理脚本中进行，如执行 `launch.ps1`,`reinstall_pytorch.ps1` 脚本等。

而 RVC Next WebUI Installer 构建模式允许在执行基础安装流程后，调用 RVC Next WebUI Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 RVC Next WebUI Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读 [使用命令运行 RVC Next WebUI Installer](advanced.md#rvc-next-webui-installer_1) 中的参数说明。

!!! info
    通常安装 RVC Next WebUI 并不需要使用 RVC Next WebUI Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。
