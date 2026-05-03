# SD WebUI Installer 启动与使用

在`stable-diffusion-webui`文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，右键 PowerShell 脚本，选择`使用 PowerShell 运行`后即可运行。如果是 Linux / MacOS 平台，请打开终端并使用`pwsh`命令去运行。

## 基础操作

### 启动 Stable Diffusion WebUI
运行`launch.ps1`脚本。

### 更新 Stable Diffusion WebUI
运行`update.ps1`脚本，如果遇到更新 Stable Diffusion WebUI 失败的情况可尝试重新运行`update.ps1`脚本。

### 更新 Stable Diffusion WebUI 扩展
运行`update_extension.ps1`脚本，如果遇到更新 Stable Diffusion WebUI 扩展失败的情况可尝试重新运行`update_extension.ps1`脚本。

### 设置 Stable Diffusion WebUI 启动参数
!!! info
    该设置可通过 [管理 SD WebUI Installer 设置](config.md#管理-sd-webui-installer-设置) 中提到的的 `settings.ps1` 进行修改。

要设置 Stable Diffusion WebUI 的启动参数，可以在和 `launch.ps1` 脚本同级的目录创建一个 `launch_args.txt` 文件，在文件内写上启动参数，运行 Stable Diffusion WebUI 启动脚本时将自动读取该文件内的启动参数并应用。

!!! note
    Stable Diffusion WebUI 支持的启动参数可阅读：[Command Line Arguments and Settings · AUTOMATIC1111/stable-diffusion-webui Wiki](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Command-Line-Arguments-and-Settings)。
    
    Stable Diffusion WebUI Forge Classic 支持的启动参数可阅读：[Commandline - Haoming02/sd-webui-forge-classic: The "classic" version of the Forge WebUI](https://github.com/Haoming02/sd-webui-forge-classic?tab=readme-ov-file#commandline)。
    
    SD.Next 支持的启动参数可阅读：[CLI Arguments - SD.Next Documentation](https://vladmandic.github.io/sdnext-docs/CLI-Arguments)。
    
    如果修改启动参数导致无法正常启动，可将启动参数设置为默认启动参数。
    
    Stable Diffusion WebUI 默认使用的启动参数：
    
    ```
    --theme dark --autolaunch --xformers --api --skip-load-model-at-start --skip-python-version-check --skip-version-check --no-download-sd-model
    ```
    
    Stable Diffusion WebUI Forge 默认使用的启动参数：
    
    ```
    --theme dark --autolaunch --xformers --api --skip-python-version-check --skip-version-check --no-download-sd-model
    ```
    
    Stable Diffusion WebUI reForge 默认使用的启动参数：
    
    ```
    --theme dark --autolaunch --xformers --api --skip-python-version-check --skip-version-check --no-download-sd-model
    ```
    
    Stable Diffusion WebUI Forge Classic 默认使用的启动参数：
    
    ```
    --theme dark --autolaunch --xformers --api --skip-python-version-check --skip-version-check
    ```
    
    Stable Diffusion WebUI AMDGPU 默认使用的启动参数：
    
    ```
    --theme dark --autolaunch --api --skip-torch-cuda-test --backend directml --skip-python-version-check --skip-version-check --no-download-sd-model
    ```
    
    SD.Next 默认使用的启动参数：
    
    ```
    --autolaunch --use-cuda --use-xformers
    ```

### 切换 Stable Diffusion WebUI 分支
运行`switch_branch.ps1`脚本，根据提示选择分支并切换。

支持切换到的分支如下。

- [AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
- [Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)
- [Haoming02/Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic)
- [lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)
- [vladmandic/SD.Next](https://github.com/vladmandic/sdnext)

## 环境管理

### 进入 Stable Diffusion WebUI 所在的 Python 环境
如果需要使用 Python、Pip、Stable Diffusion WebUI 的命令时，请勿将 Stable Diffusion WebUI 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 Stable Diffusion WebUI 所在的 Python。

或者是在 Stable Diffusion WebUI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 Stable Diffusion WebUI Env：

```powershell
./activate.ps1
```

这样就进入 Stable Diffusion WebUI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 Stable Diffusion WebUI / 扩展的版本，安装、启用 / 禁用，卸载扩展
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
