# InvokeAI Installer 启动与使用

在 `InvokeAI` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，不要左键双击 `.ps1` 脚本；左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。正确方式是右键 PowerShell 脚本，选择 `使用 PowerShell 运行`。如果右键运行后窗口闪退，先运行 `configure_env.bat` 完成环境配置，再重新右键运行 `.ps1` 脚本。如果是 Linux / MacOS 平台，请打开终端并使用 `pwsh` 命令去运行。

## 管理脚本速查

安装完成后，日常启动、更新、修复环境和调整设置都优先通过这些脚本完成。运行管理脚本时建议在安装目录中执行；如果脚本缺失或被误改，可运行 `launch_invokeai_installer.ps1` 重新生成。

| 脚本 | 作用 | 何时使用 / 注意事项 |
| --- | --- | --- |
| `configure_env.bat` | Windows 环境配置脚本，会设置 PowerShell 脚本运行策略、启用 Windows 长路径支持，并尝试把 `.ps1` 默认打开方式设为 PowerShell。 | 首次使用 Installer、运行 `.ps1` 闪退、PowerShell 脚本被系统拦截或路径过长导致异常时使用。该脚本会申请管理员权限。 |
| `launch.ps1` | 先调用 `invokeai check-env` 做启动前环境检查，再调用 `invokeai launch` 启动 InvokeAI；启动参数来自 `launch_args.txt` 和命令行参数。 | 日常启动入口。启动参数写错导致无法启动时，可删除或修改 `launch_args.txt`，也可以通过 `settings.ps1` 调整。 |
| `update.ps1` | 调用 `invokeai update` 更新 InvokeAI，并在调用前处理代理、PyPI 镜像、uv、管理脚本更新和自动快照参数。 | 需要升级 InvokeAI、修复依赖或重新同步环境时使用。更新可能改变当前 InvokeAI 版本。 |
| `update_node.ps1` | 调用 `invokeai custom-node update` 更新 InvokeAI 自定义节点。 | 自定义节点报错、节点缺少新版功能或 InvokeAI 更新后节点不兼容时使用。节点更新后如仍报错，可再运行 `launch.ps1` 做启动检查。 |
| `download_models.ps1` | 调用 `invokeai model install-library`，从 Installer 内置模型库中选择并下载模型。 | 缺少基础模型或想快速下载预设模型时使用。固定下载源前，需要先禁用自动镜像源选择，具体见 [模型与资源](resources.md)。 |
| `reinstall_pytorch.ps1` | 调用 `invokeai reinstall-pytorch`，按脚本显示的 PyTorch 版本编号重装 PyTorch。 | 出现 PyTorch 损坏、显卡后端切换、环境升级后无法启动时使用。该脚本会修改当前 Python 环境中的 PyTorch 相关包。 |
| `version_manager.ps1` | 调用 `invokeai gui version-manager` 打开版本管理 GUI。 | 需要通过图形界面查看或调整 InvokeAI 版本时使用。 |
| `snapshot_manager.ps1` | 调用 `invokeai gui snapshot-manager` 打开快照管理 GUI。 | 需要通过图形界面处理环境快照时使用。自动快照设置可通过 `settings.ps1` 管理。 |
| `settings.ps1` | 打开 Installer 设置管理器，用于调整代理、镜像源、uv、启动参数、Hotpatcher、自动快照、内核路径前缀和管理脚本更新等本地配置。 | 不想手动创建 `*.txt` 配置文件时优先使用。它会在管理脚本同级目录写入或删除对应配置文件。 |
| `terminal.ps1` | 打开一个已经配置好 PATH、代理、镜像和产品环境变量的 PowerShell 终端，并自动激活当前 Installer 管理的 Python 环境。 | 需要运行 `python`、`pip`、`uv`、`git` 或 InvokeAI 相关命令时使用。不要把 Installer 的 `python` 目录手动加入系统环境变量。 |
| `activate.ps1` | 在当前 PowerShell 会话中激活 Installer 管理的 Python / Git 环境。 | 已经打开终端且只想在当前窗口进入环境时使用。一般用户直接运行 `terminal.ps1` 更省事。 |
| `launch_invokeai_installer.ps1` | 下载最新版 InvokeAI Installer 到 `cache` 目录并运行，同时带上当前目录中的代理、镜像、内核路径前缀和快照等本地配置。 | 管理脚本损坏、缺失、需要重新运行 Installer 修复管理脚本，或 Python / Git 环境需要由安装器重新修复时使用。 |

## 基础操作

### 启动 InvokeAI
运行 `launch.ps1` 脚本。

### 更新 InvokeAI
运行 `update.ps1` 脚本，如果遇到更新 InvokeAI 失败的情况可尝试重新运行 `update.ps1` 脚本。

### 更新 InvokeAI 自定义节点
运行 `update_node.ps1` 脚本，如果遇到更新 InvokeAI 自定义节点失败的情况可尝试重新运行 `update_node.ps1` 脚本。

### 设置 InvokeAI 启动参数
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](config.md#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

要设置 InvokeAI 的启动参数，可以在和 `launch.ps1` 脚本同级的目录创建一个 `launch_args.txt` 文件，在文件内写上启动参数，运行 InvokeAI 启动脚本时将自动读取该文件内的启动参数并应用。

### 配置 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](config.md#invokeai-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 补丁系统默认启用。运行 `launch.ps1 -DisableHotpatcher`，或在和 `launch.ps1` 同级的目录创建 `disable_hotpatcher.txt`，即可禁用 Hotpatcher 补丁系统。

默认启用时，`launch.ps1` 会使用同级目录中的 `patcher_config.json` 作为默认配置文件。如果该文件不存在，脚本会自动导出一份默认配置到该路径。安装器和 `launch.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可使用 `launch.ps1 -EnableHotpatcherRuntime` 或创建 `enable_hotpatcher_runtime.txt`；`-HotpatcherPort 8765` / `hotpatcher_port.txt` 只在 runtime 模式下设置端口，有效端口范围为 `1..65535`。

## 环境管理

### 进入 InvokeAI 所在的 Python 环境
如果需要使用 Python、Pip、InvokeAI 的命令时，请勿将 InvokeAI 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 InvokeAI 所在的 Python。

或者是在 InvokeAI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 InvokeAI Env：

```powershell
./activate.ps1
```

这样就进入 InvokeAI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 InvokeAI / 扩展的版本，安装、启用 / 禁用，卸载扩展
运行 `version_manager.ps1` 脚本。

### 创建和恢复 InvokeAI 环境快照
运行 `snapshot_manager.ps1` 脚本。

### 更新到 InvokeAI RC 版
!!! warning
    InvokeAI RC 版属于测试版本，可能存在问题，请谨慎升级。

```powershell
python -m pip install invokeai --pre -U
```

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
