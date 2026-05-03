# SD Trainer Script Installer 维护与迁移

## 维护与修复

### 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 `launch_sd_trainer_script_installer.ps1` 重新生成这些脚本。

```
D:/Downloads
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── SD-Trainer-Script                           # 这是 SD-Trainer-Script 文件夹
│   ├── configure_env.bat                       # 配置环境的脚本
│   ├── activate.ps1                            # 进入 SD-Trainer-Script Env 的脚本
│   ├── cache                                   # 缓存文件夹
│   ├── download_models.ps1                     # 下载模型的脚本
│   ├── launch_sd_trainer_script_installer.ps1  # 获取最新的 SD Trainer Script Installer 并运行的脚本
│   ├── git                                     # Git 目录
│   ├── help.txt                                # 帮助文档
│   ├── init.ps1                                # 初始化训练环境的脚本
│   ├── core                                    # SD-Trainer-Script 内核目录
│   ├── python                                  # Python 目录
│   ├── reinstall_pytorch.ps1                   # 重新安装 PyTorch 的脚本
│   ├── switch_branch.ps1                       # 切换 SD-Trainer-Script 分支的脚本
│   ├── settings.ps1                            # 管理 SD Trainer Script Installer 设置的脚本
│   ├── terminal.ps1                            # 自动打开 PowerShell 并激活 SD Trainer Script Installer 的虚拟环境脚本
│   └── update.ps1                              # 更新 SD-Trainer-Script 的脚本
├── sd_trainer_script_installer.ps1             # SD Trainer Script Installer 一般放在 SD-Trainer-Script 文件夹外面，和 SD-Trainer-Script 文件夹同级
└── QQ Files
```

### 重装 SD-Trainer-Script
将 `SD-Trainer-Script` 文件夹中的 `sd-scripts` 文件夹删除，然后运行 `launch_sd_trainer_script_installer.ps1` 重新部署 SD-Trainer-Script。

!!! note
    如果 `sd-scripts` 文件夹存放了训练集 / 模型文件，请将这些文件备份后再删除 `sd-scripts` 文件夹。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以将 `SD-Trainer-Script/python` 文件夹删除，然后运行 `launch_sd_trainer_script_installer.ps1` 重新构建 Python 环境。

### 重装 Git
将 `SD-Trainer-Script/git` 文件夹删除，然后运行 `launch_sd_trainer_script_installer.ps1` 重新下载 Git。

### 重装 PyTorch
运行 `reinstall_pytorch.ps1` 脚本，并根据脚本提示的内容进行操作。

### 卸载 SD-Trainer-Script
使用 SD Trainer Script Installer 安装 SD-Trainer-Script 后，所有的文件都存放在 `SD-Trainer-Script` 文件夹中，只需要删除 `SD-Trainer-Script` 文件夹即可卸载 SD-Trainer-Script。

如果有 SD-Trainer-Script 快捷启动方式，可以通过命令进行删除，打开 PowerShell 后，输入以下命令进行删除。
```powershell
Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\SD-Trainer-Script.lnk" -Force
Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\SD-Trainer-Script.lnk" -Force
```

### 移动 SD-Trainer-Script 的路径
直接将 `SD-Trainer-Script` 文件夹移动到别的路径即可。
