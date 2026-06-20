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
│   ├── train.ps1                               # 编写并运行训练命令的模板脚本
│   ├── patcher_config.json                     # Hotpatcher 默认配置文件
│   ├── disable_hotpatcher.txt                  # 可选, 禁用 Hotpatcher 补丁系统
│   ├── enable_hotpatcher_runtime.txt           # 可选, 启用 Hotpatcher runtime host 连接
│   ├── hotpatcher_port.txt                     # 可选, runtime 模式通信端口
│   ├── core                                    # SD-Trainer-Script 内核目录
│   ├── python                                  # Python 目录
│   ├── reinstall_pytorch.ps1                   # 重新安装 PyTorch 的脚本
│   ├── snapshot_manager.ps1                    # 打开快照管理 GUI 的脚本
│   ├── switch_branch.ps1                       # 切换 SD-Trainer-Script 分支的脚本
│   ├── settings.ps1                            # 管理 SD Trainer Script Installer 设置的脚本
│   ├── terminal.ps1                            # 自动打开 PowerShell 并激活 SD Trainer Script Installer 的虚拟环境脚本
│   ├── update.ps1                              # 更新 SD-Trainer-Script 的脚本
│   └── version_manager.ps1                     # 打开版本管理 GUI 的脚本
├── sd_trainer_script_installer.ps1             # SD Trainer Script Installer 一般放在 SD-Trainer-Script 文件夹外面，和 SD-Trainer-Script 文件夹同级
└── QQ Files
```

### 重装 SD-Trainer-Script
将 `SD-Trainer-Script` 文件夹中的 `sd-scripts` 文件夹删除，然后运行 `launch_sd_trainer_script_installer.ps1` 重新部署 SD-Trainer-Script。

!!! note
    如果 `sd-scripts` 文件夹存放了训练集 / 模型文件，请将这些文件备份后再删除 `sd-scripts` 文件夹。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以删除以下目录，然后运行 `launch_sd_trainer_script_installer.ps1` 重新构建 Python 环境。

```text
<安装目录>/python
<安装目录>/<内核路径前缀>/python
```

默认情况下 `<安装目录>` 为 `SD-Trainer-Script`；`<内核路径前缀>` 可在 `core_prefix.txt`、`settings.ps1` 或脚本运行日志中查看。

### 重装 Git
如果 Git 环境出现严重损坏，可以删除以下目录，然后运行 `launch_sd_trainer_script_installer.ps1` 重新下载 Git。

```text
<安装目录>/git
<安装目录>/<内核路径前缀>/git
```

### 重装 PyTorch
运行 `reinstall_pytorch.ps1` 脚本，并根据脚本提示的内容进行操作。

### 卸载 SD-Trainer-Script
使用 SD Trainer Script Installer 安装 SD-Trainer-Script 后，主要文件都存放在 `SD-Trainer-Script` 文件夹中。确认模型、训练集、输出文件等重要数据已经备份后，删除该文件夹即可卸载 SD-Trainer-Script。

### 移动 SD-Trainer-Script 的路径
直接将 `SD-Trainer-Script` 文件夹移动到别的路径即可。
