# Fooocus Installer 启动与使用

在 `Fooocus` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。如果是 Linux / MacOS 平台，请打开终端并使用`pwsh`命令去运行。

## 基础操作

### 启动 Fooocus
运行 `launch.ps1` 脚本。

### 更新 Fooocus
运行 `update.ps1` 脚本，如果遇到更新 Fooocus 失败的情况可尝试重新运行 `update.ps1` 脚本。

### 设置 Fooocus 启动参数
!!! info
    该设置可通过 [管理 Fooocus Installer 设置](config.md#fooocus-installer_1) 中提到的 `settings.ps1` 进行修改。

要设置 Fooocus 的启动参数，可以在和 `launch.ps1` 脚本同级的目录创建一个`launch_args.txt` 文件，在文件内写上启动参数，运行 Fooocus 启动脚本时将自动读取该文件内的启动参数并应用。

!!! note
    Fooocus 支持的启动参数可阅读：[All CMD Flags · lllyasviel/Fooocus](https://github.com/lllyasviel/Fooocus?tab=readme-ov-file#all-cmd-flags)。
    
    如果修改启动参数导致无法正常启动，可将启动参数设置为默认启动参数。
    
    Fooocus 默认使用的启动参数：
    
    ```
    --language zh --preset fooocus_installer --disable-offload-from-vram --disable-analytics --always-download-new-model
    ```

### 配置 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 Fooocus Installer 设置](config.md#fooocus-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 补丁系统默认启用。运行 `launch.ps1 -DisableHotpatcher`，或在 `launch.ps1` 同级目录创建 `disable_hotpatcher.txt`，即可在启动 Fooocus 时禁用 Hotpatcher 补丁系统。

默认配置文件固定为 `launch.ps1` 同级目录的 `patcher_config.json`。Hotpatcher 默认启用且该文件不存在时，`launch.ps1` 会自动导出默认配置。安装器和 `launch.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可运行 `launch.ps1 -EnableHotpatcherRuntime`，或在同级目录创建 `enable_hotpatcher_runtime.txt`；`-HotpatcherPort 8765` / `hotpatcher_port.txt` 只在 runtime 模式下设置端口。

### 切换 Fooocus 分支
运行 `switch_branch.ps1` 脚本，根据提示选择分支并切换。

支持切换到的分支如下。

- [lllyasviel/Fooocus](https://github.com/lllyasviel/Fooocus)
- [MoonRide303/Fooocus-MRE](https://github.com/MoonRide303/Fooocus-MRE)
- [runew0lf/RuinedFooocus](https://github.com/runew0lf/RuinedFooocus)

## 环境管理

### 进入 Fooocus 所在的 Python 环境
如果需要使用 Python、Pip、Fooocus 的命令时，请勿将 Fooocus 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 Fooocus 所在的 Python。

或者是在 Fooocus 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 Fooocus Env：

```powershell
./activate.ps1
```

这样就进入 Fooocus 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 Fooocus 的版本
运行 `version_manager.ps1` 脚本。

### 创建和恢复 Fooocus 环境快照
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
