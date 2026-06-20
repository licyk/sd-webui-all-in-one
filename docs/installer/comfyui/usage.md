# ComfyUI Installer 启动与使用

在 `ComfyUI` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，不要左键双击 `.ps1` 脚本；左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。正确方式是右键 PowerShell 脚本，选择 `使用 PowerShell 运行`。如果右键运行后窗口闪退，先运行 `configure_env.bat` 完成环境配置，再重新右键运行 `.ps1` 脚本。如果是 Linux / MacOS 平台，请打开终端并使用 `pwsh` 命令去运行。

## 管理脚本速查

安装完成后，日常启动、更新、修复环境和调整设置都优先通过这些脚本完成。运行管理脚本时建议在安装目录中执行；如果脚本缺失或被误改，可运行 `launch_comfyui_installer.ps1` 重新生成。

| 脚本 | 作用 | 何时使用 / 注意事项 |
| --- | --- | --- |
| `configure_env.bat` | Windows 环境配置脚本，会设置 PowerShell 脚本运行策略、启用 Windows 长路径支持，并尝试把 `.ps1` 默认打开方式设为 PowerShell。 | 首次使用 Installer、运行 `.ps1` 闪退、PowerShell 脚本被系统拦截或路径过长导致异常时使用。该脚本会申请管理员权限。 |
| `launch.ps1` | 先调用 `comfyui check-env` 做启动前环境检查，再调用 `comfyui launch` 启动 ComfyUI；启动参数来自 `launch_args.txt` 和命令行参数。 | 日常启动入口。启动参数写错导致无法启动时，可删除或修改 `launch_args.txt`，也可以通过 `settings.ps1` 调整。 |
| `update.ps1` | 调用 `comfyui update` 更新 ComfyUI，并在调用前处理代理、GitHub 镜像、管理脚本更新和自动快照参数。 | 需要升级 ComfyUI、修复依赖或重新同步仓库时使用。更新可能改变当前 ComfyUI 版本。 |
| `update_node.ps1` | 调用 `comfyui custom-node update` 更新 ComfyUI 自定义节点。 | 自定义节点报错、节点缺少新版功能或 ComfyUI 更新后节点不兼容时使用。节点更新后如仍报错，可再运行 `launch.ps1` 做启动检查。 |
| `download_models.ps1` | 调用 `comfyui model install-library`，从 Installer 内置模型库中选择并下载模型。 | 缺少基础模型或想快速下载预设模型时使用。固定下载源前，需要先禁用自动镜像源选择，具体见 [模型与资源](resources.md)。 |
| `reinstall_pytorch.ps1` | 调用 `comfyui reinstall-pytorch`，按脚本显示的 PyTorch 版本编号重装 PyTorch / xFormers。 | 出现 PyTorch 损坏、xFormers CUDA 不匹配、显卡后端切换、环境升级后无法启动时使用。该脚本会修改当前 Python 环境中的 PyTorch 相关包。 |
| `version_manager.ps1` | 调用 `comfyui gui version-manager` 打开版本管理 GUI。 | 需要通过图形界面查看或调整 ComfyUI / 自定义节点版本时使用。 |
| `snapshot_manager.ps1` | 调用 `comfyui gui snapshot-manager` 打开快照管理 GUI。 | 需要通过图形界面处理环境快照时使用。自动快照设置可通过 `settings.ps1` 管理。 |
| `settings.ps1` | 打开 Installer 设置管理器，用于调整代理、镜像源、uv、启动参数、Hotpatcher、自动快照、内核路径前缀和管理脚本更新等本地配置。 | 不想手动创建 `*.txt` 配置文件时优先使用。它会在管理脚本同级目录写入或删除对应配置文件。 |
| `terminal.ps1` | 打开一个已经配置好 PATH、代理、镜像和产品环境变量的 PowerShell 终端，并自动激活当前 Installer 管理的 Python 环境。 | 需要运行 `python`、`pip`、`uv`、`git` 或 ComfyUI 相关命令时使用。不要把 Installer 的 `python` 目录手动加入系统环境变量。 |
| `activate.ps1` | 在当前 PowerShell 会话中激活 Installer 管理的 Python / Git 环境。 | 已经打开终端且只想在当前窗口进入环境时使用。一般用户直接运行 `terminal.ps1` 更省事。 |
| `launch_comfyui_installer.ps1` | 下载最新版 ComfyUI Installer 到 `cache` 目录并运行，同时带上当前目录中的代理、镜像、内核路径前缀和快照等本地配置。 | 管理脚本损坏、缺失、需要重新运行 Installer 修复管理脚本，或 Python / Git 环境需要由安装器重新修复时使用。 |
| `hanamizuki.bat` | 启动绘世启动器的快捷脚本，依赖内核目录中的 `hanamizuki.exe`。 | 仅在安装或配置绘世启动器后使用。没有安装绘世启动器时运行该脚本会提示缺少 `hanamizuki.exe`。 |

## 基础操作

### 启动 ComfyUI
运行 `launch.ps1` 脚本。

### 更新 ComfyUI
运行 `update.ps1` 脚本，如果遇到更新 ComfyUI 失败的情况可尝试重新运行 `update.ps1` 脚本。

### 更新 ComfyUI 自定义节点
运行 `update_node.ps1` 脚本，如果遇到更新 ComfyUI 自定义节点失败的情况可尝试重新运行 `update_node.ps1` 脚本。

### 设置 ComfyUI 启动参数
!!! info
    该设置可通过 [管理 ComfyUI Installer 设置](config.md#comfyui-installer_1) 中提到的 `settings.ps1` 进行修改。

要设置 ComfyUI 的启动参数，可以在和 `launch.ps1` 脚本同级的目录创建一个`launch_args.txt` 文件，在文件内写上启动参数，运行 ComfyUI 启动脚本时将自动读取该文件内的启动参数并应用。

!!! note
    如果修改启动参数导致无法正常启动，可将启动参数设置为默认启动参数。
    
    ComfyUI 默认使用的启动参数：
    
    ```
    --auto-launch --preview-method auto --disable-cuda-malloc --enable-manager
    ```

### 配置 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 ComfyUI Installer 设置](config.md#comfyui-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 补丁系统默认启用。运行 `launch.ps1 -DisableHotpatcher`，或在脚本同级目录创建 `disable_hotpatcher.txt`，即可禁用 Hotpatcher。

默认配置路径固定为 `launch.ps1` 同级目录下的 `patcher_config.json`。Hotpatcher 默认启用且该文件不存在时，`launch.ps1` 会自动导出默认配置。安装器和 `launch.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可使用 `-EnableHotpatcherRuntime` 或创建 `enable_hotpatcher_runtime.txt`；`-HotpatcherPort <端口>` / `hotpatcher_port.txt` 只在 runtime 模式下设置端口，范围为 `1..65535`。

## 环境管理

### 进入 ComfyUI 所在的 Python 环境
如果需要使用 Python、Pip、ComfyUI 的命令时，请勿将 ComfyUI 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 ComfyUI 所在的 Python。

或者是在 ComfyUI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 ComfyUI Env：

```powershell
./activate.ps1
```

这样就进入 ComfyUI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 ComfyUI / 扩展的版本，安装、启用 / 禁用，卸载扩展
运行 `version_manager.ps1` 脚本。

### 创建和恢复 ComfyUI 环境快照
运行 `snapshot_manager.ps1` 脚本。

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
