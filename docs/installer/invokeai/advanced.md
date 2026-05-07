# InvokeAI Installer 高级功能

## 高级功能

### 创建快捷启动方式
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](config.md#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

在脚本同级目录创建 `enable_shortcut.txt` 文件，当运行 `launch.ps1` 时将会自动创建快捷启动方式，下次启动时可以使用快捷方式启动 InvokeAI。

快捷方式会根据当前系统写入以下位置：

- Windows：桌面 `.lnk` 文件，以及 `%APPDATA%\Microsoft\Windows\Start Menu\Programs` 中的开始菜单快捷方式。
- Linux：桌面 `.desktop` 文件，以及 `~/.local/share/applications/` 中的应用入口。
- macOS：桌面 `.app` 应用，以及 `/Applications/` 中的应用入口。

!!! warning
    如果 InvokeAI 的路径发生移动，需要重新运行 `launch.ps1` 更新快捷启动方式。

### 使用命令运行 InvokeAI Installer
InvokeAI Installer 支持使用命令参数设置安装 InvokeAI 的参数，支持的参数如下。

**参数清单**

- `-Help`：获取 InvokeAI Installer 的帮助信息。
- `-CorePrefix` `<内核路径前缀>`：设置内核路径前缀。可填写内核目录名、相对路径或绝对路径；绝对路径会在运行时转换为相对于安装器脚本目录的内核路径前缀。未指定时会按预设目录自动识别，未找到时使用 `core`。
- `-InstallPath` `<安装 InvokeAI 的绝对路径>`：指定 InvokeAI Installer 安装 InvokeAI 的路径，使用绝对路径表示。
    例如：`./invokeai_installer.ps1 -InstallPath "D:\Download"`，这将指定安装到 D:\Download 路径。
- `-PyTorchMirrorType` `<PyTorch 镜像源类型>`：指定安装 PyTorch 时使用的镜像源类型。可指定的类型包括：`cuda`, `rocm`, `xpu`, `mps`, `cpu`
- `-InstallPythonVersion` `<Python 版本>`：指定要安装的 Python 版本。可选值：`3.10`, `3.11`, `3.12`, `3.13`, `3.14`
- `-UseUpdateMode`：指定 InvokeAI Installer 使用更新模式，只对 InvokeAI Installer 的管理脚本进行更新。
- `-DisablePyPIMirror`：禁用 InvokeAI Installer 使用 PyPI镜像源，使用 PyPI 官方源下载 Python 软件包。
- `-DisableProxy`：禁用 InvokeAI Installer 自动设置代理服务器。
- `-UseCustomProxy` `<代理服务器地址>`：使用自定义的代理服务器地址。例如：`-UseCustomProxy "http://127.0.0.1:10809"`
- `-DisableUV`：禁用 InvokeAI Installer 使用 uv 安装 Python 软件包，改用 Pip 安装。
- `-DisableGithubMirror`：禁用 InvokeAI Installer 自动设置 Github 镜像源。
- `-UseCustomGithubMirror` `<Github 镜像站地址>`：使用自定义的 Github 镜像站地址。
    可用的参考地址:
    `https://ghfast.top/https://github.com`
    `https://mirror.ghproxy.com/https://github.com`
    `https://ghproxy.net/https://github.com`
    `https://gh-proxy.com/https://github.com`
    `https://kkgithub.com`等。
- `-BuildMode`：启用构建模式，在基础安装结束后将调用管理脚本执行剩余任务。出现错误时不再暂停而是直接退出。
    多个脚本将按以下优先级执行：
    - `reinstall_pytorch.ps1`：对应`-BuildWithTorch` 参数
    - `download_models.ps1`：对应`-BuildWithModel` 参数
    - `update.ps1`：对应`-BuildWithUpdate` 参数
    - `update_node.ps1`：对应`-BuildWithUpdateNode` 参数
    - `launch.ps1`：对应`-BuildWithLaunch` 参数
- `-BuildWithTorch` `<PyTorch 类型>`：(需添加 `-BuildMode`) 调用 `reinstall_pytorch.ps1` 脚本，根据 PyTorch 类型安装指定的 PyTorch 版本。类型可运行该脚本查看。
- `-BuildWithModel` `<模型编号列表>`：(需添加 `-BuildMode`) 调用 `download_models.ps1` 脚本，根据编号列表下载模型。编号可运行该脚本查看。
- `-BuildWithUpdate`：(需添加 `-BuildMode`) 安装流程结束后调用 `update.ps1` 脚本，更新 InvokeAI 内核。
- `-BuildWithUpdateNode`：(需添加 `-BuildMode`) 安装流程结束后调用 `update_node.ps1` 脚本，更新 InvokeAI 扩展。
- `-BuildWithLaunch`：(需添加 `-BuildMode`) 安装流程结束后调用 `launch.ps1` 脚本，执行启动前的环境检查，但跳过启动 InvokeAI。
- `-NoPreDownloadModel`：安装 InvokeAI 时跳过预下载模型。
- `-NoCleanCache`：安装结束后保留下载的 Python 软件包缓存。
- `-DisableModelMirror`：不使用 ModelScope 下载模型, 使用 HuggingFace 下载模型。
- `-NoPause`：脚本执行完成后不暂停, 直接退出。
- `-DisableUpdate`：(仅在构建模式生效且只作用于管理脚本) 禁用 InvokeAI Installer 更新检查。
- `-DisableHuggingFaceMirror`：(仅在构建模式生效且只作用于管理脚本) 禁用 HuggingFace 镜像源。
- `-UseCustomHuggingFaceMirror` `<HuggingFace 镜像源地址>`：(仅在构建模式生效且只作用于管理脚本) 使用自定义 HuggingFace 镜像源。例如：`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`
- `-LaunchArg` `<InvokeAI 启动参数>`：(仅在构建模式生效且只作用于管理脚本) 设置 InvokeAI 自定义启动参数。如启用 `--fast`，则使用`-LaunchArg "--fast"`进行启用。
- `-Hotpatcher`：(仅在构建模式生效且只作用于管理脚本) 启用 InvokeAI Hotpatcher 补丁系统。
- `-HotpatcherConfig` `<配置文件路径>`：(仅在构建模式生效且只作用于管理脚本) 设置 InvokeAI Hotpatcher 配置文件路径。指定该参数时不会自动创建配置文件。
- `-HotpatcherPort` `<端口>`：(仅在构建模式生效且只作用于管理脚本) 设置 InvokeAI Hotpatcher runtime 通信端口，有效范围为 `1..65535`。
- `-EnableShortcut`：(仅在构建模式生效且只作用于管理脚本) 创建 InvokeAI 启动快捷方式。
- `-DisableCUDAMalloc`：(仅在构建模式生效且只作用于管理脚本) 禁用通过 `PYTORCH_CUDA_ALLOC_CONF` / `PYTORCH_ALLOC_CONF` 环境变量设置 CUDA 内存分配器。
- `-DisableEnvCheck`：(仅在构建模式生效且只作用于管理脚本) 禁用检查 InvokeAI 运行环境问题。

!!! note
    Hotpatcher 参数会随 `-BuildMode -BuildWithLaunch` 转发到 `launch.ps1`。`launch.ps1` 在构建模式下只执行环境检查，不会把 Hotpatcher 参数传给 `check-env`；实际启动 InvokeAI 时才会追加 `--hotpatcher`、`--hotpatcher-config` 和有效的 `--hotpatcher-port`。

例如在 `D:/Download` 这个路径安装 InvokeAI，则在 InvokeAI Installer 所在路径打开 PowerShell，使用参数运行 InvokeAI Installer。

```powershell
./invokeai_installer.ps1 -InstallPath "D:/Download"
```

### InvokeAI Installer 构建模式和普通安装模式
InvokeAI Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 InvokeAI Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，模型安装，运行环境检查和修复等并不会执行，这些步骤是在 InvokeAI Installer 管理脚本中进行，如执行 `launch.ps1`,`reinstall_pytorch.ps1` 脚本等。

而 InvokeAI Installer 构建模式允许在执行基础安装流程后，调用 InvokeAI Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 InvokeAI Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读 [使用命令运行 InvokeAI Installer](advanced.md#invokeai-installer_1) 中的参数说明。

!!! info
    通常安装 InvokeAI 并不需要使用 InvokeAI Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。

使用 Github Action 提供的容器可用于运行 InvokeAI Installer 并启用构建模式，实现自动化制作整合包，Github Action 工作流代码可参考：[build_invokeai.yml · licyk/sd-webui-all-in-one](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/workflows/build_invokeai.yml)
