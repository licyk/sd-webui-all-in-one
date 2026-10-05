# RVC Next WebUI Installer 配置与镜像

## 配置管理

### 自动镜像源选择
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

RVC Next WebUI Installer 生成的管理脚本默认启用 CLI 自动镜像源选择。启用时，管理脚本不会向 Python CLI 传递手动镜像参数，Python CLI 会通过 `network_gfw_test()` 自动决定是否使用 PyPI、Github 和 HuggingFace 镜像源。

!!! warning
    自动镜像源选择会强制覆盖 `disable_pypi_mirror.txt`、`disable_gh_mirror.txt`、`gh_mirror.txt`、`disable_hf_mirror.txt` 和 `hf_mirror.txt` 对 Python CLI 的手动镜像设置。需要手动调整这些设置时，请先在同级目录创建 `disable_auto_mirror.txt`，或运行管理脚本时传入 `-DisableAutoMirror`。

### 常见配置文件
下表列出 RVC Next WebUI Installer 生成的管理脚本实际会读取的常见本地配置。多数配置可通过 `settings.ps1` 创建、修改或删除；多数 `disable_*.txt` / `enable_*.txt` 是空文件开关，文件存在就表示对应设置生效。

| 配置文件 | 作用 | 备注 |
| --- | --- | --- |
| `disable_auto_mirror.txt` | 禁用 CLI 自动镜像源选择。 | 需要手动固定 PyPI / GitHub / Hugging Face 设置时使用。 |
| `proxy.txt` / `disable_proxy.txt` | 手动指定代理，或禁用管理脚本自动设置代理。 | `proxy.txt` 中填写代理地址，例如 `http://127.0.0.1:10809`。 |
| `disable_uv.txt` | 禁用 uv，改用 Pip 管理 Python 包。 | 排查 uv 安装问题时使用。 |
| `hf_mirror.txt` / `disable_hf_mirror.txt` | 自定义或禁用 Hugging Face 镜像源。 | `hf_mirror.txt` 中填写镜像地址。对 RVC Next 的影响见 [设置 HuggingFace 镜像](#huggingface)。 |
| `gh_mirror.txt` / `disable_gh_mirror.txt` | 自定义或禁用 GitHub 镜像源。 | `gh_mirror.txt` 中填写镜像地址。 |
| `disable_update.txt` | 禁用 RVC Next WebUI Installer 管理脚本自动检查更新。 | 通常不建议禁用。 |
| `launch_args.txt` | 保存 RVC Next WebUI 启动参数。 | `launch.ps1` 启动时读取；默认不包含任何启动参数。 |
| `patcher_config.json` | Hotpatcher 补丁系统配置。 | Hotpatcher 默认启用时会自动生成；`settings.ps1` 的补丁系统 GUI 会使用该文件。 |
| `disable_hotpatcher.txt` | 禁用 Hotpatcher 补丁系统。 | 空文件开关。 |
| `enable_hotpatcher_runtime.txt` / `hotpatcher_port.txt` | 启用 Hotpatcher runtime host 连接，并指定通信端口。 | 一般用户通常不需要；端口范围为 `1` 到 `65535`。 |
| `enable_shortcut.txt` | 允许管理脚本创建或刷新快捷启动方式。 | 移动安装目录后可重新运行 `launch.ps1` 刷新快捷方式。 |
| `disable_pypi_mirror.txt` | 禁用 PyPI 镜像，改用 PyPI 官方源。 | 排查 Python 包下载或镜像兼容问题时使用。 |
| `disable_set_pytorch_cuda_memory_alloc.txt` | 禁用管理脚本自动设置 PyTorch CUDA 内存分配优化。 | 遇到显存分配相关兼容问题时再考虑。 |
| `disable_check_env.txt` | 禁用启动前环境检查。 | 只建议临时排查时使用，可能跳过问题检测。 |
| `core_prefix.txt` | 指定 Installer 管理的 RVC Next WebUI 内核目录名、相对路径或绝对路径。 | 用于管理外部已有安装，或内核目录名不是默认值的情况。 |
| `disable_snapshot.txt` | 禁用安装结果快照和管理脚本操作前自动快照。 | 空文件开关。 |

这些配置文件不一定都会出现；只有启用过对应设置、安装器复制了设置，或管理脚本自动生成默认配置时才会出现。

### 设置 HuggingFace 镜像
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

RVC Next WebUI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建 `hf_mirror.txt` 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源 |
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建 `disable_hf_mirror.txt` 文件，再次启动脚本时将禁用 HuggingFace 镜像源。

RVC Next 不读取 `HF_ENDPOINT` 环境变量，因此启用 HuggingFace 镜像源时，启动 RVC Next WebUI 前会额外设置以下环境变量，让 RVC Next 通过镜像源下载模型资源：

```text
RVC_NEXT_DOWNLOADS__SOURCE=custom
RVC_NEXT_DOWNLOADS__ENDPOINT=<HuggingFace 镜像源地址>
```

如果已经手动设置了 `RVC_NEXT_DOWNLOADS__SOURCE` 或 `RVC_NEXT_DOWNLOADS__ENDPOINT` 中的任意一个环境变量，则不会覆盖这两个环境变量。

!!! warning
    这两个环境变量会覆盖 RVC Next 自身的下载源设置，因此在环境变量生效期间，RVC Next WebUI 设置界面中的下载源设置会被固定，无法在界面中修改。

    如果希望在 RVC Next WebUI 的设置界面中自行选择下载源，请先禁用 RVC Next WebUI Installer 的 HuggingFace 镜像源：通过 `settings.ps1` 将“Hugging Face 下载镜像源”设置为禁用，或在脚本同级目录创建 `disable_hf_mirror.txt` 文件，也可以在运行 `launch.ps1` 时添加 `-DisableHuggingFaceMirror` 参数。启用了 [自动镜像源选择](#_2) 时，手动的 HuggingFace 镜像设置会被自动覆盖，需要同时禁用自动镜像源选择。

### 设置 Github 镜像源
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

RVC Next WebUI Installer 为了加速访问 Github 的速度，加快下载和更新 RVC Next WebUI 的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建 `gh_mirror.txt` 文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

|可用的 Github 镜像源 |
|---|
|https://ghfast.top/https://github.com|
|https://mirror.ghproxy.com/https://github.com|
|https://gh.api.99988866.xyz/https://github.com|
|https://gitclone.com/github.com|
|https://gh-proxy.com/https://github.com|
|https://ghps.cc/https://github.com|
|https://gh.idayer.com/https://github.com|
|https://ghproxy.1888866.xyz/github.com|
|https://slink.ltd/https://github.com|
|https://github.boki.moe/github.com|
|https://github.moeyy.xyz/https://github.com|
|https://gh-proxy.net/https://github.com|
|https://gh-proxy.ygxz.in/https://github.com|
|https://wget.la/https://github.com|
|https://kkgithub.com|
|https://ghproxy.net/https://github.com|

如果需要禁用设置 Github 镜像源，在和脚本同级的目录中创建 `disable_gh_mirror.txt` 文件，再次启动脚本时将禁用 Github 镜像源。

### 设置 PyPI 镜像源
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

RVC Next WebUI Installer 默认启用了 PyPI镜像源加速下载 Python 软件包，如果需要禁用 PyPI镜像源，可以在脚本同级目录创建 `disable_pypi_mirror.txt` 文件，再次运行脚本时将 PyPI 源切换至官方源。

### 配置代理
如果出现某些文件无法下载，比如在控制台出现 `由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败` 之类的报错时，可以尝试配置代理，有以下两种方法。

#### 1. 使用系统代理
在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。

#### 2. 使用配置文件
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

在和脚本同级的路径中创建一个 `proxy.txt` 文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

!!! note
    **配置文件**的优先级高于**系统代理**配置，所以当同时使用了两种方式配置代理，脚本将优先使用**配置文件**中的代理配置。

!!! note
    RVC Next WebUI 自带的代理设置会被禁用（启动时总是附加 `--disable-proxy`），代理统一由 RVC Next WebUI Installer 设置，因此在 `launch_args.txt` 中填写 `--proxy` 不会生效。

#### 禁用自动设置代理
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

在和脚本同级的路径中创建一个 `disable_proxy.txt` 文件，再次启动脚本时将禁用设置代理。

## 其他配置
### 设置 uv 包管理器
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

RVC Next WebUI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个 `disable_uv.txt` 文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

!!! note
    当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。

### 设置 Hotpatcher 补丁系统
!!! info
    该设置中的补丁系统开关和端口可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 默认启用。需要禁用时，可在 `launch.ps1` 同级目录创建 `disable_hotpatcher.txt` 文件，或运行 `launch.ps1` 时添加 `-DisableHotpatcher` 参数。

默认启用时，`launch.ps1` 会使用同级目录下的 `patcher_config.json` 作为默认配置文件。如果默认配置不存在，脚本会自动导出默认配置到该路径。安装器和 `launch.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可创建 `enable_hotpatcher_runtime.txt` 或运行 `launch.ps1 -EnableHotpatcherRuntime`；`hotpatcher_port.txt` / `-HotpatcherPort <端口>` 只在 runtime 模式下设置端口，文件内容填写 `1` 到 `65535` 范围内的端口号。

### 设置快照功能
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

快照功能默认启用。RVC Next WebUI Installer 会在安装完成后保存一次安装结果快照；启动、更新、重装 PyTorch 等可能改变环境的管理脚本会在执行前创建操作前快照。

如需禁用自动快照，可以在安装目录中创建 `disable_snapshot.txt`，或运行安装器和管理脚本时添加 `-DisableSnapshot` 参数。首次运行安装器时，也可以把 `disable_snapshot.txt` 放在安装器脚本同级目录，安装器会将该配置复制到安装目录。禁用后会跳过安装结果快照和管理脚本执行前的自动快照。

需要手动创建或恢复快照时，运行 `snapshot_manager.ps1` 打开快照管理 GUI。需要从快照重建安装目录时，重新运行 RVC Next WebUI Installer，并同时传入 `-RestoreFromSnapshot` 和 `-SnapshotPath <快照文件>`；该模式会按快照中的 Python 版本和环境信息恢复，不能和 `-UseUpdateMode` 同时使用。

### 设置内核路径前缀
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改，也可以通过 `core_prefix.txt` 或 `-CorePrefix` 参数指定。

RVC Next WebUI Installer 通过“内核路径前缀”找到要启动和管理的 RVC Next WebUI 内核。运行管理脚本时，脚本会先检查 `-CorePrefix` 参数或脚本同级目录中的 `core_prefix.txt`；如果没有手动指定，就会在安装目录中按预设名称自动查找，当前预设包括：`core`, `rvc-next-webui*`。如果没有找到匹配目录，则使用 `core` 作为内核路径前缀。

如果内核就在安装器脚本同级目录下，可以直接把目录名写入 `core_prefix.txt`。例如内核目录名为 `my-rvc-next-webui`，则 `core_prefix.txt` 内容写为 `my-rvc-next-webui`，之后 `launch.ps1`、`update.ps1`、`terminal.ps1` 等管理脚本都会使用该目录。

内核路径前缀也可以填写相对路径或绝对路径。填写绝对路径时，脚本会在运行时转换为相对于安装器脚本目录的内核路径前缀；这适合把 RVC Next WebUI Installer 指向外部已有的 RVC Next WebUI 安装目录。为了减少路径转义问题，推荐优先使用绝对路径。

例如 RVC Next WebUI Installer 位于 `D:/Downloads/rvc-next-webui`，已有 RVC Next WebUI 位于 `D:/Tools/AI/rvc-next-webui`，可以将 `D:/Tools/AI/rvc-next-webui` 写入 `core_prefix.txt`；脚本会自动换算为相对于 `D:/Downloads/rvc-next-webui` 的路径，并继续管理该内核。

### 启动前环境检查
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

运行 `launch.ps1` 时，会先检查 RVC Next WebUI 的运行环境，再启动 RVC Next WebUI。RVC Next WebUI 自带的环境检查会被跳过（启动时总是附加 `--skip-check`），环境检查统一由 RVC Next WebUI Installer 负责。检查包含以下任务：

| 任务名称 | 作用 |
| --- | --- |
| `python-dependencies` | 检查 RVC Next WebUI 的 `requirements.txt` 以及 `rvc-next` 软件包自身声明的依赖，缺失时自动安装。如果 PyTorch 未安装或版本低于 2.7.1，将不会自动安装，而是报错并提示使用 PyTorch 重装工具（`reinstall_pytorch.ps1`）重新安装 PyTorch。 |
| `torch-libomp` | 检测并修复 PyTorch 的 libomp 问题。 |
| `torch-version` | 检查当前安装的 PyTorch 类型是否适合当前设备，例如有可用显卡却安装了 CPU 版本的 PyTorch 时给出警告。 |

如需禁用启动前环境检查，可在脚本同级目录创建 `disable_check_env.txt` 文件，或运行 `launch.ps1` 时添加 `-DisableEnvCheck` 参数。禁用后可能会导致运行环境中存在的问题无法被发现并修复，只建议临时排查问题时使用。

如果只需要执行或跳过某个检查任务，可以在 [RVC Next WebUI Env](usage.md#rvc-next-webui-python) 中使用 `--include-check` / `--exclude-check` 手动运行环境检查，这两个参数都可以重复传入：

```powershell
# 只检查 Python 依赖
python -m sd_webui_all_in_one rvc-next-webui check-env --rvc-next-webui-path "$Env:RVC_NEXT_WEBUI_PATH" --include-check python-dependencies

# 跳过 PyTorch 类型检查
python -m sd_webui_all_in_one rvc-next-webui check-env --rvc-next-webui-path "$Env:RVC_NEXT_WEBUI_PATH" --exclude-check torch-version
```

### 管理 RVC Next WebUI Installer 设置
运行 `settings.ps1`，根据提示进行设置管理和调整。

设置菜单包含以下选项：

| 编号 | 菜单项 | 对应配置 |
| --- | --- | --- |
| `0` | 自动选择下载镜像源 | `disable_auto_mirror.txt` |
| `1` | 网络代理设置 | `proxy.txt` / `disable_proxy.txt` |
| `2` | Python 包管理器 | `disable_uv.txt` |
| `3` | Hugging Face 下载镜像源 | `hf_mirror.txt` / `disable_hf_mirror.txt` |
| `4` | GitHub 下载镜像源 | `gh_mirror.txt` / `disable_gh_mirror.txt` |
| `5` | 自动检查 Installer 更新 | `disable_update.txt` |
| `6` | 应用启动参数 | `launch_args.txt` |
| `7` | Hotpatcher 补丁系统 | `disable_hotpatcher.txt` |
| `8` | Hotpatcher 运行时服务 | `enable_hotpatcher_runtime.txt` |
| `9` | Hotpatcher 运行时端口 | `hotpatcher_port.txt` |
| `10` | 创建启动快捷方式 | `enable_shortcut.txt` |
| `11` | PyPI 软件包镜像 | `disable_pypi_mirror.txt` |
| `12` | PyTorch CUDA 内存分配优化 | `disable_set_pytorch_cuda_memory_alloc.txt` |
| `13` | 启动前环境检测 | `disable_check_env.txt` |
| `14` | Installer 内核路径前缀 | `core_prefix.txt` |
| `15` | 自动快照 | `disable_snapshot.txt` |
| `16` | 打开 Hotpatcher 补丁系统 GUI | 使用同级目录的 `patcher_config.json` |
| `17` | 立即检查 Installer 更新 | - |
| `18` | 打开在线文档 | - |
| `19` | 退出设置 | - |

### RVC Next WebUI Installer 对 Python / Git 环境的识别
RVC Next WebUI Installer 通常不会主动调用系统环境中的 Python / Git。运行安装器和管理脚本时，会先把安装器管理的 Python / Git 路径加入 `PATH`，避免被系统环境干扰。

Python 会优先识别以下路径：

```text
<安装目录>/<内核路径前缀>/python
<安装目录>/python
```

Git 会优先识别以下路径：

```text
<安装目录>/<内核路径前缀>/git
<安装目录>/git
```

其中 `<安装目录>` 通常是 `rvc-next-webui`，`<内核路径前缀>` 是当前通过自动识别、`core_prefix.txt` 或 `-CorePrefix` 得到的目录。内核路径前缀下的 Python / Git 会排在根级 Python / Git 前面，因此当两处都存在时，优先使用 `<安装目录>/<内核路径前缀>/python` 和 `<安装目录>/<内核路径前缀>/git`。

如果这些路径下的 Python / Git 都不存在，管理脚本可能会退回到系统环境中的 Python / Git，这可能带来运行环境问题。出现这种情况时，建议重新运行 `launch_rvc_next_webui_installer.ps1` 修复 Python / Git 环境。
