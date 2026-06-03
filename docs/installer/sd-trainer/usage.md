# SD Trainer Installer 启动与使用

在 `SD-Trainer` 文件夹中可以看到不同的 PowerShell 脚本，右键 PowerShell 脚本。如果是 Windows 平台，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。如果是 Linux / MacOS 平台，请打开终端并使用`pwsh`命令去运行。

## 基础操作

### 启动 SD-Trainer
运行 `launch.ps1` 脚本。

### 更新 SD-Trainer
运行 `update.ps1` 脚本，如果遇到更新 SD-Trainer 失败的情况可尝试重新运行 `update.ps1` 脚本。

### 设置 SD-Trainer 启动参数
!!! info
    该设置可通过 [管理 SD Trainer Installer 设置](config.md#sd-trainer-installer_1) 中提到的 `settings.ps1` 进行修改。

要设置 SD-Trainer 的启动参数，可以在和 `launch.ps1` 脚本同级的目录创建一个`launch_args.txt` 文件，在文件内写上启动参数，运行 SD-Trainer 启动脚本时将自动读取该文件内的启动参数并应用。

!!! note
    SD-Trainer 可用的启动参数可阅读：[Akegarasu/lora-scripts ### 程序参数](https://github.com/Akegarasu/lora-scripts/blob/main/README-zh.md#%E7%A8%8B%E5%BA%8F%E5%8F%82%E6%95%B0)

    SD Trainer Next 可用的启动参数可参考：[wochenlong/lora-scripts-next](https://github.com/wochenlong/lora-scripts-next)
    
    Kohya GUI 可用的启动参数可阅读：[bmaltais/kohya_ss - Starting GUI Service](https://github.com/bmaltais/kohya_ss?tab=readme-ov-file#starting-gui-service)
    
    如果修改启动参数导致无法正常启动，可将启动参数设置为默认启动参数。
    
    SD-Trainer 默认使用的启动参数：
    
    ```
    --skip-prepare-onnxruntime
    ```

    SD Trainer Next 默认使用的启动参数：

    ```
    --skip-prepare-onnxruntime
    ```
    
    Kohya GUI 默认使用的启动参数：
    
    ```
    --inbrowser --language zh-CN --noverify
    ```

### 配置 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 SD Trainer Installer 设置](config.md#sd-trainer-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 补丁系统默认启用。运行 `launch.ps1 -DisableHotpatcher`，或在 `launch.ps1` 同级目录创建 `disable_hotpatcher.txt`，即可在启动 SD-Trainer 时禁用 Hotpatcher 补丁系统。

默认配置文件固定为 `launch.ps1` 同级目录的 `patcher_config.json`。Hotpatcher 默认启用且未指定 `-HotpatcherConfig` 时，如果该文件不存在，`launch.ps1` 会自动导出默认配置；如果指定了 `-HotpatcherConfig`，脚本只使用指定路径，不会自动创建配置文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可运行 `launch.ps1 -EnableHotpatcherRuntime`，或在同级目录创建 `enable_hotpatcher_runtime.txt`；`-HotpatcherPort 8765` / `hotpatcher_port.txt` 只在 runtime 模式下设置端口。

### 切换 SD-Trainer 分支
运行 `switch_branch.ps1` 脚本，根据提示选择分支并切换。

支持切换到的分支如下。

- [Akegarasu/SD-Trainer](https://github.com/Akegarasu/lora-scripts)
- [wochenlong/SD Trainer Next](https://github.com/wochenlong/lora-scripts-next)
- [bmaltais/Kohya GUI](https://github.com/bmaltais/kohya_ss)

!!! note
    切换分支后需要删去原有的启动参数，因为两个不同的分支的启动参数互不兼容，可将 `launch_args.txt` 删除或者通过 [管理 SD Trainer Installer 设置](config.md#sd-trainer-installer_1) 中提到的 `settings.ps1` 进行删除。

## 环境管理

### 进入 SD-Trainer 所在的 Python 环境
如果需要使用 Python、Pip、SD-Trainer 的命令时，请勿将 SD-Trainer 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 SD-Trainer 所在的 Python。

或者是在 SD-Trainer 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 SD-Trainer Env：

```powershell
./activate.ps1
```

这样就进入 SD-Trainer 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 SD-Trainer 的版本
运行 `version_manager.ps1` 脚本。

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
