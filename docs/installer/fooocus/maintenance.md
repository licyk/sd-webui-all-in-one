# Fooocus Installer 维护与迁移

## 维护与修复

### 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 `launch_fooocus_installer.ps1` 重新生成这些脚本。

```
D:/Downloads
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── Fooocus                           # 这是 Fooocus 文件夹
│   ├── configure_env.bat             # 配置环境的脚本
│   ├── activate.ps1                  # 进入 Fooocus Env 的脚本
│   ├── cache                         # 缓存文件夹
│   ├── download_models.ps1           # 下载模型的脚本
│   ├── launch_fooocus_installer.ps1  # 获取最新的 Fooocus Installer 并运行的脚本
│   ├── git                           # Git 目录
│   ├── help.txt                      # 帮助文档
│   ├── launch.ps1                    # 启动 Fooocus 的脚本
│   ├── core                          # Fooocus 内核目录
│   ├── python                        # Python 目录
│   ├── reinstall_pytorch.ps1         # 重新安装 PyTorch 的脚本
│   ├── switch_branch.ps1             # 切换 Fooocus 分支的脚本
│   ├── settings.ps1                  # 管理 Fooocus Installer 设置的脚本
│   ├── terminal.ps1                  # 自动打开 PowerShell 并激活 Fooocus Installer 的虚拟环境脚本
│   └── update.ps1                    # 更新 Fooocus 的脚本
├── fooocus_installer.ps1             # Fooocus Installer 一般放在 Fooocus 文件夹外面，和 Fooocus 文件夹同级
└── QQ Files
```

### 重装 Fooocus
将 `Fooocus` 文件夹中的 `Fooocus` 文件夹删除，然后运行 `launch_fooocus_installer.ps1` 重新部署 Fooocus。

!!! note
    如果 `Fooocus` 文件夹存放了模型文件，请将这些文件备份后再删除 `Fooocus` 文件夹。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以将 `Fooocus/python` 和`Fooocus/Fooocus/python` 文件夹删除，然后运行 `launch_fooocus_installer.ps1` 重新构建 Python 环境。

### 重装 Git
将 `Fooocus/git` 和`Fooocus/Fooocus/git` 文件夹删除，然后运行 `launch_fooocus_installer.ps1` 重新下载 Git。

### 重装 PyTorch
运行 `reinstall_pytorch.ps1` 脚本，并根据脚本提示的内容进行操作。

### 卸载 Fooocus
使用 Fooocus Installer 安装 Fooocus 后，所有的文件都存放在 `Fooocus` 文件夹中，只需要删除 `Fooocus` 文件夹即可卸载 Fooocus。

如果有 Fooocus 快捷启动方式，可以通过命令进行删除，打开 PowerShell 后，输入以下命令进行删除。
```powershell
# 安装的是 lllyasviel/Fooocus 分支时
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\Fooocus.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\Fooocus.lnk" -Force

# 安装的是 MoonRide303/Fooocus-MRE 分支时
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\Fooocus-MRE.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\Fooocus-MRE.lnk" -Force

# 安装的是 runew0lf/RuinedFooocus 分支时
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\RuinedFooocus.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\RuinedFooocus.lnk" -Force
```

### 移动 Fooocus 的路径
直接将 `Fooocus` 文件夹移动到别的路径即可。

如果启用了自动创建 Fooocus 快捷启动方式的功能，移动 Fooocus 后原来的快捷启动方式将失效，需要运行 `launch.ps1` 更新快捷启动方式。

## 管理已有安装
### 使用 Fooocus Installer 管理已有的 Fooocus
使用 Fooocus Installer 管理已有的 Fooocus，需要构建 Fooocus Installer 所需的目录结构。

将 Fooocus Installer 下载到本地后，在 Fooocus Installer 所在目录打开 PowerShell，使用命令运行，将 Fooocus Installer 的管理脚本安装到本地，比如在`D:/Fooocus`，则命令如下。

```powershell
./fooocus_installer.ps1 -UseUpdateMode -InstallPath "D:/Fooocus"
```

运行完成后 Fooocus Installer 的管理脚本将安装在 `D:/Fooocus` 中，目录结构如下。

```
D:/Fooocus
├── activate.ps1
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_fooocus_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── switch_branch.ps1
├── terminal.ps1
├── update.ps1
└── update_time.txt
```

接下来需要将 Fooocus 移动到 `D:/Fooocus` 目录中，如果 Fooocus 的文件夹名称不是 `Fooocus`，比如`Fooocus_win64`，需要将名称修改成`Fooocus`。

!!! note
    如果不修改名称，需要根据 [设置内核路径前缀](config.md#设置内核路径前缀) 中的说明配置内核路径前缀。在这个例子中内核路径前缀就需要设置为 `Fooocus_win64`。

移动进去后此时的目录结构如下。

```
D:/Fooocus
├── activate.ps1
├── Fooocus
│   ├── ldm_patched
│   ├── launch.py
│   ├── models
│   ...
│   └── entry_with_update.py
├── download_models.ps1
├── help.txt
├── launch.ps1
├── launch_fooocus_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── switch_branch.ps1
├── terminal.ps1
├── update.ps1
└── update_time.txt
```

再检查 `D:/Fooocus/Fooocus` 文件夹中是否包含 `python` 和`git` 文件夹，如果未包含，需要运行 `launch_fooocus_installer.ps1` 重建环境，重建完成后即可运行 `launch.ps1` 启动 Fooocus。
