# Installer

`installer/*.ps1` 是项目的跨平台 PowerShell 安装器。它们既负责首次安装，也负责生成安装目录中的管理脚本，让用户后续可以启动、更新、下载模型、重装 PyTorch、打开终端环境和进行版本管理。

## 安装器清单

| 脚本 | 对应产品 |
| --- | --- |
| `stable_diffusion_webui_installer.ps1` | Stable Diffusion WebUI / Forge / reForge / Forge Classic / AMDGPU / SD.Next |
| `comfyui_installer.ps1` | ComfyUI |
| `fooocus_installer.ps1` | Fooocus |
| `invokeai_installer.ps1` | InvokeAI |
| `qwen_tts_webui_installer.ps1` | Qwen TTS WebUI |
| `sd_trainer_installer.ps1` | SD Trainer / Kohya GUI |
| `sd_trainer_script_installer.ps1` | sd-scripts / ai-toolkit / finetrainers / diffusion-pipe / musubi-tuner |

## 脚本结构

安装器脚本通常包含这些区域：

- 参数区：定义安装路径、内核路径前缀、Python / PyTorch 版本、镜像、代理、构建模式和产品特定选项。
- 路径和环境初始化：规范化安装路径，识别 `core_prefix.txt`，配置 PATH、缓存目录和产品根目录环境变量。
- 基础组件安装：安装或更新 Python、Git、uv / pip 和 `sd_webui_all_in_one` Python 内核。
- 产品安装流程：clone 仓库、切换分支、写入配置、安装依赖、预下载模型或扩展。
- 管理脚本生成：写出 `launch.ps1`、`update.ps1`、`terminal.ps1`、`download_models.ps1`、`version_manager.ps1` 等脚本。
- 模式入口：根据普通安装、更新模式或构建模式决定执行路径。
- 帮助信息：输出参数说明和新文档链接。

## 三种运行模式

| 模式 | 触发方式 | 用途 |
| --- | --- | --- |
| 普通安装模式 | 默认运行安装器 | 首次安装目标 WebUI / 训练工具，并生成管理脚本。 |
| 更新模式 | `-UseUpdateMode` | 只更新安装器和管理脚本，不重新安装目标 WebUI。 |
| 构建模式 | `-BuildMode` | 自动化构建整合包时使用，基础安装后按参数调用管理脚本并减少交互暂停。 |

## 内核路径前缀

安装目录下可能存在根级 `python` / `git`，也可能存在 `<内核路径前缀>/python` / `<内核路径前缀>/git`。安装器通过以下顺序识别内核路径前缀：

1. 命令行参数 `-CorePrefix`。
2. 安装目录中的 `core_prefix.txt`。
3. 产品默认候选目录，例如 `core` 或产品目录名。
4. 兜底使用 `core`。

如果 `-CorePrefix` 是绝对路径，脚本会把它转换为相对于安装目录的路径前缀。维护路径相关逻辑时，文档和脚本都应使用 `<安装目录>/<内核路径前缀>/python` / `<安装目录>/<内核路径前缀>/git` 这种通用表达，不要写死某个产品默认目录。

## 生成的管理脚本

不同产品生成的脚本略有差异，常见脚本包括：

- `launch.ps1`：启动前环境检查、启动参数、内存优化和实际启动。
- `update.ps1`：更新 WebUI / 训练工具仓库。
- `update_extension.ps1` 或 `update_node.ps1`：更新扩展或 ComfyUI 节点。
- `switch_branch.ps1`：切换支持的产品分支。
- `reinstall_pytorch.ps1`：按版本列表重装 PyTorch / xFormers。
- `download_models.ps1`：按内置模型列表下载模型。
- `version_manager.ps1`：打开版本管理 GUI 或对应管理界面。
- `terminal.ps1`：进入带有 Python、Git、镜像和产品环境变量的终端。
- `settings.ps1`：调整代理、镜像、uv、启动参数、内核路径前缀等本地配置。

新增参数或脚本时，要同步安装器帮助文本、`settings.ps1` 菜单、构建模式参数、用户文档和开发维护文档。

## 自动镜像源选择

安装器封装 Python CLI 时默认启用自动镜像源选择，由 Python CLI 的 `network_gfw_test()` 决定是否使用 PyPI、Github、HuggingFace 镜像源以及 ModelScope 模型下载源。PowerShell 侧只负责传递 `-DisableAutoMirror` / `disable_auto_mirror.txt` 到 Python CLI 的 `--no-auto-mirror`，不要在安装器 bootstrap 阶段重新实现网络探测逻辑。

维护镜像相关参数时，需要同步以下位置：

- 主安装器参数和帮助文本：`-DisableAutoMirror`、`-DisablePyPIMirror`、`-DisableGithubMirror`、`-DisableHuggingFaceMirror`、`-DisableModelMirror` 和自定义镜像参数。
- 生成的管理脚本参数：安装、启动、更新、扩展更新、分支切换、模型下载、重装 PyTorch、版本管理等会封装 Python CLI 的脚本都要能接收 `-DisableAutoMirror`。
- CLI 参数拼接：默认自动模式下不向 Python CLI 传递手动镜像参数；禁用自动镜像后先追加 `--no-auto-mirror`，再继续传递手动镜像参数。
- 配置复制与设置菜单：`Copy-InstallerConfig` 要复制 `disable_auto_mirror.txt`，`settings.ps1` 要能创建 / 删除该文件，并提示自动模式会强制覆盖其它手动镜像设置。
- 构建模式和产品文档：构建模式要把 `-DisableAutoMirror` 转发给后续管理脚本，用户文档要说明 `-DisableAutoMirror` / `disable_auto_mirror.txt` 是手动镜像设置生效的前置开关。

## Hotpatcher 启动封装

已有 `launch` 子命令的产品安装器需要在 `launch.ps1` 中封装 Hotpatcher 启动参数，并把补丁配置固定到管理脚本同级目录：

- PowerShell 参数：`-DisableHotpatcher`、`-EnableHotpatcherRuntime`、`-HotpatcherPort`。
- 配置文件：`disable_hotpatcher.txt`、`enable_hotpatcher_runtime.txt`、`hotpatcher_port.txt`、`patcher_config.json`。
- 默认配置路径：`Join-NormalizedPath $PSScriptRoot "patcher_config.json"`，不要依赖当前工作目录推断。
- 参数优先级：命令行参数高于同级配置文件。

维护这类参数时，需要同步 `launch.ps1` 的 Python CLI 参数拼接、`settings.ps1` 的本地配置菜单和 Hotpatcher GUI 入口、`Copy-InstallerConfig` 的配置复制、`BuildWithLaunch` 的构建模式转发和产品文档。安装器不再提供自定义 Hotpatcher 配置路径参数，只复制并使用同级 `patcher_config.json`。没有 `launch` 子命令或不生成 `launch.ps1` 的安装器不应只在 PowerShell 层硬加 Hotpatcher 参数，应先补齐 Python CLI 的启动能力。

SD Trainer Script 是特殊启动方式：训练命令由用户脚本在 `init.ps1` 初始化后执行，不走 Python `launch` 函数。它通过 `sd-webui-all-in-one self-manager patcher get-pythonpath` 获取补丁路径优先的 `PYTHONPATH`，再由 `init.ps1` 默认只设置 Hotpatcher `PYTHONPATH` 和从同级 `patcher_config.json` 读取的配置内容；启用 runtime 时才设置连接用的 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME/HOST/PORT/SERVICES` 环境变量；`-DisableHotpatcher`、`-EnableHotpatcherRuntime`、`-HotpatcherPort` 和同级配置文件仍保持与其它安装器一致的语义。

## 版本与更新

每个安装器脚本内部维护自己的版本号和更新检查间隔，并记录所需的 `sd_webui_all_in_one` 内核最低版本。更新模式会下载或复制新版安装器，再刷新管理脚本。修改安装器行为时，应确认：

- 版本号是否需要递增。
- 更新模式是否能写出新管理脚本。
- 构建模式是否能在 CI / 整合包构建中无交互运行。
- 帮助信息中的文档链接是否仍指向 `https://licyk.github.io/sd-webui-all-in-one/installer/.../`。
