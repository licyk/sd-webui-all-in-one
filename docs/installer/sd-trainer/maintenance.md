# SD Trainer Installer 维护与迁移

## 维护与修复

### 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 `launch_sd_trainer_installer.ps1` 重新生成这些脚本。

```
D:/Downloads
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── SD-Trainer                            # 这是 SD-Trainer 文件夹
│   ├── configure_env.bat                 # 配置环境的脚本
│   ├── activate.ps1                      # 进入 SD-Trainer Env 的脚本
│   ├── cache                                 # 缓存文件夹
│   ├── download_models.ps1               # 下载模型的脚本
│   ├── launch_sd_trainer_installer.ps1   # 获取最新的 SD Trainer Installer 并运行的脚本
│   ├── git                               # Git 目录
│   ├── help.txt                          # 帮助文档
│   ├── launch.ps1                        # 启动 SD-Trainer 的脚本
│   ├── core                              # SD-Trainer 内核目录
│   ├── python                                # Python 目录
│   ├── reinstall_pytorch.ps1             # 重新安装 PyTorch 的脚本
│   ├── switch_branch.ps1                 # 切换 SD-Trainer 分支的脚本
│   ├── settings.ps1                      # 管理 SD Trainer Installer 设置的脚本
│   ├── terminal.ps1                      # 自动打开 PowerShell 并激活 SD Trainer Installer 的虚拟环境脚本
│   └── update.ps1                        # 更新 SD-Trainer 的脚本
├── sd_trainer_installer.ps1              # SD Trainer Installer 一般放在 SD-Trainer 文件夹外面，和 SD-Trainer 文件夹同级
└── QQ Files
```

### 使用 SD Trainer Installer 管理已有的 SD-Trainer
使用 SD Trainer Installer 管理已有的 SD-Trainer，需要构建 SD Trainer Installer 所需的目录结构。

将 SD Trainer Installer 下载到本地后，在 SD Trainer Installer 所在目录打开 PowerShell，使用命令运行，将 SD Trainer Installer 的管理脚本安装到本地，比如在`D:/SD-Trainer`，则命令如下。

```powershell
./sd_trainer_installer.ps1 -UseUpdateMode -InstallPath "D:/SD-Trainer"
```

运行完成后 SD Trainer Installer 的管理脚本将安装在 `D:/SD-Trainer` 中，目录结构如下。

```
D:/SD-Trainer
├── activate.ps1
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_sd_trainer_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── switch_branch.ps1
├── terminal.ps1
├── update.ps1
└── update_time.txt
```

接下来需要将 SD-Trainer 移动到 `D:/SD-Trainer` 目录中，如果 SD-Trainer 的文件夹名称不是 `lora-scripts`，比如`lora-scripts-v1.10.0`，需要将名称修改成`lora-scripts`。

!!! note
    如果不修改名称，需要根据 [设置内核路径前缀](config.md#_5) 中的说明配置内核路径前缀。在这个例子中内核路径前缀就需要设置为 `lora-scripts-v1.10.0`。

移动进去后此时的目录结构如下。

```
D:/SD-Trainer
├── activate.ps1
├── lora-scripts
│   ├── assets
│   ├── huggingface
│   ├── mikazuki
│   ...
│   └── gui.py
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_sd_trainer_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── switch_branch.ps1
├── terminal.ps1
├── update.ps1
└── update_time.txt
```

再检查 `<安装目录>/<内核路径前缀>` 文件夹中是否包含 `python` 和 `git` 文件夹，如果未包含，需要运行 `launch_sd_trainer_installer.ps1` 重建环境，重建完成后即可运行 `launch.ps1` 启动 SD-Trainer。

### 重装 SD-Trainer
将 `SD-Trainer` 文件夹中的 `lora-scripts` 文件夹删除，然后运行 `launch_sd_trainer_installer.ps1` 重新部署 SD-Trainer。

!!! note
    如果 `lora-scripts` 文件夹存放了训练集 / 模型文件，请将这些文件备份后再删除 `lora-scripts` 文件夹。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以删除以下目录，然后运行 `launch_sd_trainer_installer.ps1` 重新构建 Python 环境。

```text
<安装目录>/python
<安装目录>/<内核路径前缀>/python
```

默认情况下 `<安装目录>` 为 `SD-Trainer`；`<内核路径前缀>` 可在 `core_prefix.txt`、`settings.ps1` 或脚本运行日志中查看。

### 重装 Git
如果 Git 环境出现严重损坏，可以删除以下目录，然后运行 `launch_sd_trainer_installer.ps1` 重新下载 Git。

```text
<安装目录>/git
<安装目录>/<内核路径前缀>/git
```

### 重装 PyTorch
运行 `reinstall_pytorch.ps1` 脚本，并根据脚本提示的内容进行操作。

### 卸载 SD-Trainer
使用 SD Trainer Installer 安装 SD-Trainer 后，主要文件都存放在 `SD-Trainer` 文件夹中。确认模型、训练集、输出文件等重要数据已经备份后，删除该文件夹即可卸载 SD-Trainer。

如果创建过快捷启动方式，还需要按系统删除对应快捷方式。SD-Trainer 的快捷方式名称会根据安装分支变化，常见名称包括 `SD-Trainer`、`SD-Trainer-Next`、`Kohya-GUI`。

Windows 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("SD-Trainer", "SD-Trainer-Next", "Kohya-GUI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\$name.lnk" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\$name.lnk" -Force -ErrorAction SilentlyContinue
}
```

Linux 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("SD-Trainer", "SD-Trainer-Next", "Kohya-GUI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$HOME/Desktop/$name.desktop" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$HOME/.local/share/applications/$name.desktop" -Force -ErrorAction SilentlyContinue
}
```

macOS 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("SD-Trainer", "SD-Trainer-Next", "Kohya-GUI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$HOME/Desktop/$name.app" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "/Applications/$name.app" -Recurse -Force -ErrorAction SilentlyContinue
}
```

### 移动 SD-Trainer 的路径
直接将 `SD-Trainer` 文件夹移动到别的路径即可。

如果启用了自动创建 SD-Trainer 快捷启动方式的功能，移动 SD-Trainer 后原来的快捷启动方式将失效，需要运行 `launch.ps1` 更新快捷启动方式。
