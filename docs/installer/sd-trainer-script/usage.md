# SD Trainer Script Installer 启动与使用

在 `SD-Trainer-Script` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。如果是 Linux / MacOS 平台，请打开终端并使用`pwsh`命令去运行。

## 基础操作

### 启动训练脚本
编写并运行 `train.ps1` 脚本。

训练脚本中的内容需要自行编写，编写方法请参考 [编写训练脚本](advanced.md#_2) 部分的内容。

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

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
