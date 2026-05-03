# Qwen TTS WebUI Installer 高级功能

## 高级功能

### 创建快捷启动方式
!!! info
    该设置可通过 [管理 Qwen TTS WebUI Installer 设置](config.md#管理-qwen-tts-webui-installer-设置) 中提到的的 `settings.ps1` 进行修改。

在脚本同级目录创建 `enable_shortcut.txt` 文件，当运行 `launch.ps1` 时将会自动创建快捷启动方式，并添加到 Windows 桌面和 Windows 开始菜单中，下次启动时可以使用快捷方式启动 Qwen TTS WebUI。

!!! warning
    如果 Qwen TTS WebUI 的路径发生移动，需要重新运行 `launch.ps1` 更新快捷启动方式。

### 使用命令运行 Qwen TTS WebUI Installer
Qwen TTS WebUI Installer 支持使用命令参数设置安装 Qwen TTS WebUI 的参数，支持的参数如下。

|参数 | 作用|
|---|---|
|`-Help`|获取 Qwen TTS WebUI Installer 的帮助信息。|
|`-CorePrefix` <内核路径前缀>|设置内核的路径前缀，默认路径前缀为 `core`。|
|`-InstallPath` <安装 Qwen TTS WebUI 的绝对路径>|指定 Qwen TTS WebUI Installer 安装 Qwen TTS WebUI 的路径，使用绝对路径表示。<br>例如：`./qwen_tts_webui_installer.ps1 -InstallPath "D:\Download"`，这将指定安装到 D:\Download 路径。|
|`-PyTorchMirrorType` <PyTorch 镜像源类型>|指定安装 PyTorch 时使用的镜像源类型。可指定的类型包括：`cu113`, `cu117`, `cu118`, `cu121`, `cu124`, `cu126`, `cu128`, `cu129`, `cu130`, `rocm5.4.2`, `rocm5.6`, `rocm5.7`, `rocm6.0`, `rocm6.1`, `rocm6.2`, `rocm6.2.4`, `rocm6.3`, `rocm6.4`, `rocm7.1`, `rocm_rdna3`, `rocm_rdna3.5`, `rocm_rdna4`, `rocm_win`, `xpu`, `ipex_legacy_arc`, `cpu`, `directml`, `all`|
|`-InstallPythonVersion` <Python 版本>|指定要安装的 Python 版本。可选值：`3.10`, `3.11`, `3.12`, `3.13`, `3.14`|
|`-UseUpdateMode`|指定 Qwen TTS WebUI Installer 使用更新模式，只对 Qwen TTS WebUI Installer 的管理脚本进行更新。|
|`-DisablePyPIMirror`|禁用 Qwen TTS WebUI Installer 使用 PyPI镜像源，使用 PyPI 官方源下载 Python 软件包。|
|`-DisableProxy`|禁用 Qwen TTS WebUI Installer 自动设置代理服务器。|
|`-UseCustomProxy` <代理服务器地址>|使用自定义的代理服务器地址。例如：`-UseCustomProxy "http://127.0.0.1:10809"`|
|`-DisableUV`|禁用 Qwen TTS WebUI Installer 使用 uv 安装 Python 软件包，改用 Pip 安装。|
|`-DisableGithubMirror`|禁用 Qwen TTS WebUI Installer 自动设置 Github 镜像源。|
|`-UseCustomGithubMirror` <Github 镜像站地址>|使用自定义的 Github 镜像站地址。例如：`https://ghfast.top/https://github.com` 等。|
|`-BuildMode`|启用构建模式，在基础安装结束后将调用管理脚本执行剩余任务。出现错误时不再暂停而是直接退出。<br>多个脚本将按以下优先级执行：<br><li>`reinstall_pytorch.ps1`：对应`-BuildWithTorch`/`-BuildWithTorchReinstall`<br><li>`update.ps1`：对应`-BuildWithUpdate`<br><li>`launch.ps1`：对应`-BuildWithLaunch`|
|`-BuildWithTorch` <PyTorch 版本编号>|(需添加 `-BuildMode`) 调用 `reinstall_pytorch.ps1` 脚本，根据版本编号安装指定的 PyTorch 版本。编号可运行该脚本查看。|
|`-BuildWithTorchReinstall`|(需添加 `-BuildMode`及`-BuildWithTorch`) 执行 PyTorch 指定版本安装时使用强制重新安装模式。|
|`-BuildWithUpdate`|(需添加 `-BuildMode`) 安装流程结束后调用 `update.ps1` 脚本，更新 Qwen TTS WebUI 内核。|
|`-BuildWithLaunch`|(需添加 `-BuildMode`) 安装流程结束后调用 `launch.ps1` 脚本，执行启动前的环境检查，但跳过启动 Qwen TTS WebUI。|
|`-PyTorchPackage` <PyTorch 软件包>|(需搭配 `-xFormersPackage`) 指定安装的 PyTorch 版本。如：`-PyTorchPackage "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"`|
|`-xFormersPackage` <xFormers 软件包>|(需搭配 `-PyTorchPackage`) 指定安装的 xFormers 版本。如：`-xFormersPackage "xformers===0.0.26.post1+cu118"`|
|`-NoCleanCache`|安装结束后保留下载的 Python 软件包缓存。|
|`-NoPause`|脚本执行完成后不暂停, 直接退出。|
|`-DisableUpdate`|(仅在构建模式生效且只作用于管理脚本) 禁用 Qwen TTS WebUI Installer 更新检查。|
|`-DisableHuggingFaceMirror`|(仅在构建模式生效且只作用于管理脚本) 禁用 HuggingFace 镜像源。|
|`-UseCustomHuggingFaceMirror` <HuggingFace 镜像源地址>|(仅在构建模式生效且只作用于管理脚本) 使用自定义 HuggingFace 镜像源。例如：`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`|
|`-LaunchArg` <Qwen TTS WebUI 启动参数>|(仅在构建模式生效且只作用于管理脚本) 设置 Qwen TTS WebUI 自定义启动参数。如：`-LaunchArg "--fast --auto-launch"`|
|`-EnableShortcut`|(仅在构建模式生效且只作用于管理脚本) 创建 Qwen TTS WebUI 启动快捷方式。|
|`-DisableCUDAMalloc`|(仅在构建模式生效且只作用于管理脚本) 禁用通过 `PYTORCH_CUDA_ALLOC_CONF` / `PYTORCH_ALLOC_CONF` 环境变量设置 CUDA 内存分配器。|
|`-DisableEnvCheck`|(仅在构建模式生效且只作用于管理脚本) 禁用检查 Qwen TTS WebUI 运行环境问题。|

例如在 `D:/Download` 这个路径安装 Qwen TTS WebUI，则在 Qwen TTS WebUI Installer 所在路径打开 PowerShell，使用参数运行 Qwen TTS WebUI Installer。

```powershell
./qwen_tts_webui_installer.ps1 -InstallPath "D:/Download"
```

### Qwen TTS WebUI Installer 构建模式和普通安装模式
Qwen TTS WebUI Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 Qwen TTS WebUI Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，模型安装，运行环境检查和修复等并不会执行，这些步骤是在 Qwen TTS WebUI Installer 管理脚本中进行，如执行 `launch.ps1`,`reinstall_pytorch.ps1` 脚本等。

而 Qwen TTS WebUI Installer 构建模式允许在执行基础安装流程后，调用 Qwen TTS WebUI Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 Qwen TTS WebUI Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读 [使用命令运行 Qwen TTS WebUI Installer](advanced.md#使用命令运行-qwen-tts-webui-installer) 中的参数说明。

!!! info
    通常安装 Qwen TTS WebUI 并不需要使用 Qwen TTS WebUI Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。

使用 Github Action 提供的容器可用于运行 Qwen TTS WebUI Installer 并启用构建模式，实现自动化制作整合包，Github Action 工作流代码可参考：[build_qwen_tts_webui.yml · licyk/sd-webui-all-in-one](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/workflows/build_qwen_tts_webui.yml)
