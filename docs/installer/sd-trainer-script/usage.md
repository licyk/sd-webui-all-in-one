# SD Trainer Script Installer 启动与使用

在 `SD-Trainer-Script` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。如果是 Linux / MacOS 平台，请打开终端并使用`pwsh`命令去运行。

## 管理脚本速查

安装完成后，训练环境初始化、更新、修复环境和调整设置都优先通过这些脚本完成。运行管理脚本时建议在安装目录中执行；如果脚本缺失或被误改，可运行 `launch_sd_trainer_script_installer.ps1` 重新生成。

| 脚本 | 作用 | 何时使用 / 注意事项 |
| --- | --- | --- |
| `configure_env.bat` | Windows 环境配置脚本，会设置 PowerShell 脚本运行策略、启用 Windows 长路径支持，并尝试把 `.ps1` 默认打开方式设为 PowerShell。 | 首次使用 Installer、运行 `.ps1` 闪退、PowerShell 脚本被系统拦截或路径过长导致异常时使用。该脚本会申请管理员权限。 |
| `init.ps1` | 调用 `sd-scripts check-env` 做训练环境检查，并配置 Python / Git / 训练脚本路径、镜像、代理、CUDA 内存分配和 Hotpatcher 环境变量。 | 自己编写训练命令前先调用。它不会替你启动某个固定 WebUI，而是为后续 `python` 训练命令准备运行环境。 |
| `train.ps1` | 用户训练脚本模板，默认先调用 `init.ps1`，再留出位置给用户写入具体训练命令。 | 编写训练任务时使用。请保留文件中初始化部分，训练命令写在模板标记的区域内，并按文档要求保存编码。 |
| `update.ps1` | 调用 `sd-scripts update` 更新当前训练脚本分支，并在调用前处理代理、GitHub 镜像、管理脚本更新和自动快照参数。 | 需要升级 sd-scripts / ai-toolkit / finetrainers / diffusion-pipe / musubi-tuner，或切换分支后同步依赖时使用。 |
| `switch_branch.ps1` | 调用 `sd-scripts switch` 在 sd-scripts、ai-toolkit、finetrainers、diffusion-pipe、musubi-tuner 等受支持分支之间切换。 | 需要更换训练脚本体系时使用。切换后依赖差异较大，通常需要运行 `update.ps1`。 |
| `download_models.ps1` | 调用 `sd-scripts model install-library`，从 Installer 内置模型库中选择并下载训练常用模型。 | 缺少训练基础模型或想快速下载预设模型时使用。固定下载源前，需要先禁用自动镜像源选择，具体见 [模型与资源](resources.md)。 |
| `reinstall_pytorch.ps1` | 调用 `sd-scripts reinstall-pytorch`，按脚本显示的 PyTorch 版本编号重装 PyTorch / xFormers。 | 出现 PyTorch 损坏、xFormers CUDA 不匹配、显卡后端切换、环境升级后训练命令无法运行时使用。该脚本会修改当前 Python 环境中的 PyTorch 相关包。 |
| `version_manager.ps1` | 调用 `sd-scripts gui version-manager` 打开版本管理 GUI。 | 需要通过图形界面查看或调整训练脚本环境版本时使用。 |
| `snapshot_manager.ps1` | 调用 `sd-scripts gui snapshot-manager` 打开快照管理 GUI。 | 需要通过图形界面处理环境快照时使用。自动快照设置可通过 `settings.ps1` 管理。 |
| `settings.ps1` | 打开 Installer 设置管理器，用于调整代理、镜像源、uv、Hotpatcher、自动快照、内核路径前缀和管理脚本更新等本地配置。 | 不想手动创建 `*.txt` 配置文件时优先使用。它会在管理脚本同级目录写入或删除对应配置文件。 |
| `terminal.ps1` | 打开一个已经配置好 PATH、代理、镜像和产品环境变量的 PowerShell 终端，并自动激活当前 Installer 管理的 Python 环境。 | 需要手动运行 `python`、`pip`、`uv`、`git` 或训练相关命令时使用。不要把 Installer 的 `python` 目录手动加入系统环境变量。 |
| `activate.ps1` | 在当前 PowerShell 会话中激活 Installer 管理的 Python / Git 环境。 | 已经打开终端且只想在当前窗口进入环境时使用。一般用户直接运行 `terminal.ps1` 更省事。 |
| `launch_sd_trainer_script_installer.ps1` | 下载最新版 SD Trainer Script Installer 到 `cache` 目录并运行，同时带上当前目录中的代理、镜像、内核路径前缀和快照等本地配置。 | 管理脚本损坏、缺失、需要重新运行 Installer 修复管理脚本，或 Python / Git 环境需要由安装器重新修复时使用。 |

## 基础操作

### 启动训练脚本
编写并运行 `train.ps1` 脚本。

训练脚本中的内容需要自行编写，编写方法请参考 [编写训练脚本](advanced.md#_2) 部分的内容。

### 配置 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 SD Trainer Script Installer 设置](config.md#sd-trainer-script-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 补丁系统默认启用。运行 `init.ps1 -DisableHotpatcher`，或在 `init.ps1` 同级目录创建 `disable_hotpatcher.txt`，即可在初始化训练环境时禁用 Hotpatcher 补丁系统。

默认配置文件固定为 `init.ps1` 同级目录的 `patcher_config.json`。Hotpatcher 默认启用且该文件不存在时，`init.ps1` 会自动导出默认配置。安装器和 `init.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可运行 `init.ps1 -EnableHotpatcherRuntime`，或在同级目录创建 `enable_hotpatcher_runtime.txt`；`-HotpatcherPort 8765` / `hotpatcher_port.txt` 只在 runtime 模式下设置端口。

### 更新 SD-Trainer-Script
运行 `update.ps1` 脚本，如果遇到更新 SD-Trainer-Script 失败的情况可尝试重新运行 `update.ps1` 脚本。

### 切换 SD-Trainer-Script 分支
运行 `switch_branch.ps1` 脚本，根据提示选择分支并切换。

支持切换到的分支如下。

- [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)
- [a-r-r-o-w/finetrainers](https://github.com/a-r-r-o-w/finetrainers)
- [tdrussell/diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)
- [kohya-ss/musubi-tuner](https://github.com/kohya-ss/musubi-tuner)

!!! note
    切换分支后，因为不同分支需要的依赖版本不一致，需要对依赖进行更新，可通过运行 `update.ps1` 进行依赖更新，保证 SD-Trainer-Script 能够正常运行。

## 环境管理

### 进入 SD-Trainer-Script 所在的 Python 环境
如果需要使用 Python、Pip、SD-Trainer-Script 的命令时，请勿将 SD-Trainer-Script 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 SD-Trainer-Script 所在的 Python。

或者是在 SD-Trainer-Script 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 SD-Trainer-Script Env：

```powershell
./activate.ps1
```

这样就进入 SD-Trainer-Script 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 SD-Trainer-Script 的版本
运行 `version_manager.ps1` 脚本。

### 创建和恢复 SD-Trainer-Script 环境快照
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
