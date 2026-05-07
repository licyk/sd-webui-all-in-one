# ComfyUI Installer 启动与使用

在 `ComfyUI` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。如果是 Linux / MacOS 平台，请打开终端并使用`pwsh`命令去运行。

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
    --auto-launch --preview-method auto --disable-cuda-malloc
    ```

### 启用 Hotpatcher 补丁系统
!!! info
    该设置可通过 [管理 ComfyUI Installer 设置](config.md#comfyui-installer_1) 中提到的 `settings.ps1` 进行修改。

运行 `launch.ps1` 时可通过 `-Hotpatcher` 启用 Hotpatcher，也可以在脚本同级目录创建 `enable_hotpatcher.txt` 后启用。启用后，`launch.ps1` 会向 ComfyUI 启动命令追加 `--hotpatcher` 和 `--hotpatcher-config <路径>`。

默认配置路径固定为 `launch.ps1` 同级目录下的 `patcher_config.json`。未指定 `-HotpatcherConfig` 且该文件不存在时，`launch.ps1` 会自动导出默认配置；如果指定了 `-HotpatcherConfig`，脚本会直接使用指定路径，不会自动创建配置文件。

Hotpatcher runtime 通信端口可通过 `-HotpatcherPort <端口>` 或 `hotpatcher_port.txt` 设置，端口范围为 `1..65535`，且命令行参数优先于配置文件。

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

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
