# InvokeAI Installer 配置与镜像

## 配置管理

### 自动镜像源选择
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

InvokeAI Installer 生成的管理脚本默认启用 CLI 自动镜像源选择。启用时，管理脚本不会向 Python CLI 传递手动镜像参数，Python CLI 会通过 `network_gfw_test()` 自动决定是否使用 PyPI、Github、HuggingFace 镜像源和 ModelScope 模型下载源。

!!! warning
    自动镜像源选择会强制覆盖 `disable_pypi_mirror.txt`、`disable_gh_mirror.txt`、`gh_mirror.txt`、`disable_hf_mirror.txt`、`hf_mirror.txt` 和 `disable_model_mirror.txt` 对 Python CLI 的手动镜像设置。需要手动调整这些设置时，请先在同级目录创建 `disable_auto_mirror.txt`，或运行管理脚本时传入 `-DisableAutoMirror`。

### 设置 InvokeAI 中文
InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。

### 设置 HuggingFace 镜像
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

InvokeAI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建 `hf_mirror.txt` 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源 |
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建 `disable_hf_mirror.txt` 文件，再次启动脚本时将禁用 HuggingFace 镜像源。

### 设置 Github 镜像源
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

InvokeAI Installer 为了加速访问 Github 的速度，如加快下载和更新 InvokeAI 自定义节点的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建 `gh_mirror.txt` 文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

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
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

InvokeAI Installer 默认启用了 PyPI镜像源加速下载 Python 软件包，如果需要禁用 PyPI镜像源，可以在脚本同级目录创建 `disable_pypi_mirror.txt` 文件，再次运行脚本时将 PyPI 源切换至官方源。

### 配置代理
如果出现某些文件无法下载，比如在控制台出现 `由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败` 之类的报错时，可以尝试配置代理，有以下两种方法。

#### 1. 使用系统代理
在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。

#### 2. 使用配置文件
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

在和脚本同级的路径中创建一个 `proxy.txt` 文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

!!! note
    **配置文件**的优先级高于**系统代理**配置，所以当同时使用了两种方式配置代理，脚本将优先使用**配置文件**中的代理配置。

#### 禁用自动设置代理
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

在和脚本同级的路径中创建一个 `disable_proxy.txt` 文件，再次启动脚本时将禁用设置代理。

## 其他配置
### 设置 uv 包管理器
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

InvokeAI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个 `disable_uv.txt` 文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

!!! note
    当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。

### 设置内核路径前缀
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改，也可以通过 `core_prefix.txt` 或 `-CorePrefix` 参数指定。

InvokeAI Installer 通过“内核路径前缀”找到要启动和管理的 InvokeAI 内核。运行管理脚本时，脚本会先检查 `-CorePrefix` 参数或脚本同级目录中的 `core_prefix.txt`；如果没有手动指定，就会在安装目录中按预设名称自动查找，当前预设包括：`invokeai*`。如果没有找到匹配目录，则使用 `core` 作为内核路径前缀。

如果内核就在安装器脚本同级目录下，可以直接把目录名写入 `core_prefix.txt`。例如内核目录名为 `InvokeAI-aki-v1`，则 `core_prefix.txt` 内容写为 `InvokeAI-aki-v1`，之后 `launch.ps1`、`update.ps1`、`terminal.ps1` 等管理脚本都会使用该目录。

内核路径前缀也可以填写相对路径或绝对路径。填写绝对路径时，脚本会在运行时转换为相对于安装器脚本目录的内核路径前缀；这适合把 InvokeAI Installer 指向外部已有安装目录或已经解压的整合包目录。为了减少路径转义问题，推荐优先使用绝对路径。

例如 InvokeAI Installer 位于 `D:/Downloads/InvokeAI`，已有 InvokeAI 位于 `D:/Tools/AI/InvokeAI-aki-v1.1`，可以将 `D:/Tools/AI/InvokeAI-aki-v1.1` 写入 `core_prefix.txt`；脚本会自动换算为相对于 `D:/Downloads/InvokeAI` 的路径，并继续管理该内核。

### 设置 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改，也可以通过 `disable_hotpatcher.txt`、`enable_hotpatcher_runtime.txt`、`hotpatcher_port.txt` 或 `launch.ps1` 参数指定。

Hotpatcher 补丁系统默认启用。在和 `launch.ps1` 同级的目录创建 `disable_hotpatcher.txt` 后，再次运行 `launch.ps1` 时将禁用 Hotpatcher 补丁系统。也可以使用 `launch.ps1 -DisableHotpatcher` 临时禁用。

默认配置文件固定为 `patcher_config.json`，路径位于 `launch.ps1` 同级目录。Hotpatcher 默认启用且该文件不存在时，脚本会自动导出默认配置。安装器和 `launch.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可使用 `-EnableHotpatcherRuntime` 或创建 `enable_hotpatcher_runtime.txt`；`hotpatcher_port.txt` / `-HotpatcherPort <端口>` 只在 runtime 模式下设置端口，端口必须在 `1..65535` 范围内。

### 设置快照功能
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

快照功能默认启用。InvokeAI Installer 会在安装完成后保存一次安装结果快照；启动、更新、切换分支、重装 PyTorch 等可能改变环境的管理脚本会在执行前创建操作前快照。

如需禁用自动快照，可以在安装目录中创建 `disable_snapshot.txt`，或运行安装器和管理脚本时添加 `-DisableSnapshot` 参数。首次运行安装器时，也可以把 `disable_snapshot.txt` 放在安装器脚本同级目录，安装器会将该配置复制到安装目录。禁用后会跳过安装结果快照和管理脚本执行前的自动快照。

需要手动创建或恢复快照时，运行 `snapshot_manager.ps1` 打开快照管理 GUI。需要从快照重建安装目录时，重新运行 InvokeAI Installer，并同时传入 `-RestoreFromSnapshot` 和 `-SnapshotPath <快照文件>`；该模式会按快照中的 Python 版本和环境信息恢复，不能和 `-UseUpdateMode` 同时使用。

### 管理 InvokeAI Installer 设置
运行 `settings.ps1`，根据提示进行设置管理和调整。

其中“补丁系统”菜单项会切换 `disable_hotpatcher.txt`，“补丁系统 Runtime”菜单项会切换 `enable_hotpatcher_runtime.txt`，“补丁系统端口”菜单项会写入或删除 `hotpatcher_port.txt`，“自动快照”菜单项会切换 `disable_snapshot.txt`，“补丁系统 GUI”菜单项会打开 Hotpatcher 配置管理 GUI 并使用同级目录的 `patcher_config.json`。

### InvokeAI Installer 对 Python / Git 环境的识别
InvokeAI Installer 通常不会主动调用系统环境中的 Python / Git。运行安装器和管理脚本时，会先把安装器管理的 Python / Git 路径加入 `PATH`，避免被系统环境干扰。

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

其中 `<安装目录>` 通常是 `InvokeAI`，`<内核路径前缀>` 是当前通过自动识别、`core_prefix.txt` 或 `-CorePrefix` 得到的目录。内核路径前缀下的 Python / Git 会排在根级 Python / Git 前面，因此当两处都存在时，优先使用 `<安装目录>/<内核路径前缀>/python` 和 `<安装目录>/<内核路径前缀>/git`。

如果这些路径下的 Python / Git 都不存在，管理脚本可能会退回到系统环境中的 Python / Git，这可能带来运行环境问题。出现这种情况时，建议重新运行 `launch_invokeai_installer.ps1` 修复 Python / Git 环境。
