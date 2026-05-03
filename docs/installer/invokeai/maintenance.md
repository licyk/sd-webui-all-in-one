# InvokeAI Installer 维护与迁移

## 维护与修复

### 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 `launch_invokeai_installer.ps1` 重新生成这些脚本。

```
D:/Downloads
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── InvokeAI                            # 这是 InvokeAI 文件夹
│   ├── configure_env.bat               # 配置环境的脚本
│   ├── activate.ps1                    # 进入 InvokeAI Env 的脚本
│   ├── cache                           # 缓存文件夹
│   ├── launch_invokeai_installer.ps1   # 获取最新的 InvokeAI Installer 并运行的脚本
│   ├── help.txt                        # 帮助文档
│   ├── core                            # InvokeAI 生成的图片 / 模型 / 工作流 / 配置文件路径
│   ├── launch.ps1                      # 启动 InvokeAI 的脚本
│   ├── python                          # Python 目录
│   ├── git                             # Git 目录
│   ├── reinstall_pytorch.ps1           # 重装 PyTorch 脚本
│   ├── download_models.ps1             # 模型下载脚本
│   ├── settings.ps1                    # 管理 InvokeAI Installer 设置的脚本
│   ├── terminal.ps1                    # 自动打开 PowerShell 并激活 InvokeAI Installer 的虚拟环境脚本
│   ├── update_node.ps1                 # 更新 InvokeAI 自定义节点的脚本
│   └── update.ps1                      # 更新 InvokeAI 的脚本
├── invokeai_installer.ps1              # InvokeAI Installer 一般放在 InvokeAI 文件夹外面，和 InvokeAI 文件夹同级
└── QQ Files
```

### 使用 InvokeAI Installer 管理已有的 InvokeAI
使用 InvokeAI Installer 管理已有的 InvokeAI，需要构建 InvokeAI Installer 所需的目录结构。

将 InvokeAI Installer 下载到本地后，在 InvokeAI Installer 所在目录打开 PowerShell，使用命令运行，将 InvokeAI Installer 的管理脚本安装到本地，比如在`D:/InvokeAI`，则命令如下。

```powershell
./invokeai_installer.ps1 -UseUpdateMode -InstallPath "D:/InvokeAI"
```

运行完成后 InvokeAI Installer 的管理脚本将安装在 `D:/InvokeAI` 中，目录结构如下。

```
D:/InvokeAI
├── activate.ps1
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_invokeai_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── terminal.ps1
├── update.ps1
├── update_node.ps1
└── update_time.txt
```

接下来需要将 InvokeAI 移动到 `D:/InvokeAI` 目录中，如果 InvokeAI 的文件夹名称不是 `invokeai`，比如 `Invoke`，需要将名称修改成`invokeai`。

!!! note
    如果不修改名称，需要根据 [设置内核路径前缀](config.md#设置内核路径前缀) 中的说明配置内核路径前缀。在这个例子中内核路径前缀就需要设置为 `Invoke`。

移动进去后此时的目录结构如下。

```
D:/InvokeAI
├── activate.ps1
├── invokeai
│   ├── configs
│   ├── databases
│   ├── models
│   ...
│   └── invokeai.yaml
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_invokeai_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── terminal.ps1
├── update.ps1
├── update_node.ps1
└── update_time.txt
```

再运行 `launch_invokeai_installer.ps1` 重建环境，重建完成后即可运行 `launch.ps1` 启动 InvokeAI。

### 重装 InvokeAI
如果 InvokeAI 因为严重损坏导致无法正常使用，可以将 `InvokeAI` 文件夹中的 `python` 文件夹删除，然后运行 `launch_invokeai_installer.ps1` 重新部署 InvokeAI。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以删除以下目录，然后运行 `launch_invokeai_installer.ps1` 重新构建 Python 环境。

```text
<安装目录>/python
<安装目录>/<内核路径前缀>/python
```

默认情况下 `<安装目录>` 为 `InvokeAI`；`<内核路径前缀>` 可在 `core_prefix.txt`、`settings.ps1` 或脚本运行日志中查看。

### 重装 Git
如果 Git 环境出现严重损坏，可以删除以下目录，然后运行 `launch_invokeai_installer.ps1` 重新下载 Git。

```text
<安装目录>/git
<安装目录>/<内核路径前缀>/git
```

### 重置 InvokeAI 数据库
如果 InvokeAI 的数据库出现损坏，可以将 `InvokeAI/invokeai/databases` 文件夹删除。

### 配置 InvokeAI
在`InvokeAI/invokeai` 路径下，可以看到`invokeai.yaml` 配置文件。如果未找到该配置文件，可以运行 `launch.ps1` 启动一次 InvokeAI，此时 InvokeAI 将自动生成该配置文件。

如果需要修改，请参考 `invokeai.example.yaml` 文件内的示例，或者参考 [Configuration - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/configuration) 进行设置。

如果因为修改 `invokeai.yaml` 后导致 InvokeAI 的功能异常，请将该文件删除来重置 InvokeAI 配置。

!!! note
    在大多数情况下并不需要修改该配置文件，因为 InvokeAI 会自动选择最佳的配置。

### 卸载 InvokeAI
使用 InvokeAI Installer 安装 InvokeAI 后，主要文件都存放在 `InvokeAI` 文件夹中。确认模型、训练集、输出文件等重要数据已经备份后，删除该文件夹即可卸载 InvokeAI。

如果创建过快捷启动方式，还需要按系统删除对应快捷方式。InvokeAI 的快捷方式名称通常为 `InvokeAI`。

Windows 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("InvokeAI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\$name.lnk" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\$name.lnk" -Force -ErrorAction SilentlyContinue
}
```

Linux 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("InvokeAI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$HOME/Desktop/$name.desktop" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$HOME/.local/share/applications/$name.desktop" -Force -ErrorAction SilentlyContinue
}
```

macOS 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("InvokeAI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$HOME/Desktop/$name.app" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "/Applications/$name.app" -Recurse -Force -ErrorAction SilentlyContinue
}
```

### 移动 InvokeAI 的路径
直接将 `InvokeAI` 文件夹移动到别的路径即可。

如果启用了自动创建 InvokeAI 快捷启动方式的功能，移动 InvokeAI 后原来的快捷启动方式将失效，需要运行 `launch.ps1` 更新快捷启动方式。

### InvokeAI 文件夹用途
在 `InvokeAI` 文件夹中，存在着 `invokeai` 文件夹，保存着模型和生成出来的图片等，以下为不同文件夹的用途。

```
invokeai
├── cache                 # InvokeAI 的缓存文件夹
├── configs               # 一些模型的配置文件
├── databases             # InvokeAI 的数据库
├── invokeai.example.yaml # InvokeAI 的配置文件示例
├── invokeai.yaml         # InvokeAI 的配置文件
├── models                # 模型文件夹
├── nodes                 # InvokeAI 节点存放路径
├── outputs               # 生成的图片保存位置
└── style_presets         # 提示词预设文件
```
