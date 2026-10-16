# Mizuoto TTS WebUI Installer 维护与迁移

## 维护与修复

### 恢复被修改 / 删除的脚本
如果不小心把某个脚本修改了导致无法使用，或者是误删除了，可以运行一次 `launch_mizuoto_tts_webui_installer.ps1` 重新生成这些脚本。

```
D:/Downloads
├── BaiduNetworkDownloads
│   └── 新建 文本文档.txt
├── mizuoto-tts-webui                            # 这是 Mizuoto TTS WebUI 文件夹
│   ├── configure_env.bat                     # 配置环境的脚本
│   ├── activate.ps1                          # 进入 Mizuoto TTS WebUI Env 的脚本
│   ├── cache                                 # 缓存文件夹
│   ├── launch_mizuoto_tts_webui_installer.ps1   # 获取最新的 Mizuoto TTS WebUI Installer 并运行的脚本
│   ├── git                                   # Git 目录
│   ├── help.txt                              # 帮助文档
│   ├── launch.ps1                            # 启动 Mizuoto TTS WebUI 的脚本
│   ├── core                                  # Mizuoto TTS WebUI 内核目录
│   │   └── data                              # Mizuoto 的设置、数据库、模型、音色和输出
│   ├── python                                # Python 目录
│   ├── reinstall_pytorch.ps1                 # 重新安装 PyTorch 的脚本
│   ├── settings.ps1                          # 管理 Mizuoto TTS WebUI Installer 设置的脚本
│   ├── snapshot_manager.ps1                  # 打开快照管理 GUI 的脚本
│   ├── terminal.ps1                          # 自动打开 PowerShell 并激活 Mizuoto TTS WebUI Installer 的虚拟环境脚本
│   ├── update.ps1                            # 更新 Mizuoto TTS WebUI 的脚本
│   └── version_manager.ps1                   # 打开版本管理 GUI 的脚本
├── mizuoto_tts_webui_installer.ps1              # Mizuoto TTS WebUI Installer 一般放在 Mizuoto TTS WebUI 文件夹外面，和 Mizuoto TTS WebUI 文件夹同级
└── QQ Files
```

### 使用 Mizuoto TTS WebUI Installer 管理已有的 Mizuoto TTS WebUI
使用 Mizuoto TTS WebUI Installer 管理已有的 Mizuoto TTS WebUI，需要构建 Mizuoto TTS WebUI Installer 所需的目录结构。

将 Mizuoto TTS WebUI Installer 下载到本地后，在 Mizuoto TTS WebUI Installer 所在目录打开 PowerShell，使用命令运行，将 Mizuoto TTS WebUI Installer 的管理脚本安装到本地，比如在`D:/mizuoto-tts-webui`，则命令如下。

```powershell
./mizuoto_tts_webui_installer.ps1 -UseUpdateMode -InstallPath "D:/mizuoto-tts-webui"
```

运行完成后 Mizuoto TTS WebUI Installer 的管理脚本将安装在 `D:/mizuoto-tts-webui` 中，目录结构如下。

```
D:/mizuoto-tts-webui
├── activate.ps1
├── help.txt
├── launch.ps1
├── launch_mizuoto_tts_webui_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── snapshot_manager.ps1
├── terminal.ps1
├── update.ps1
├── version_manager.ps1
└── update_time.txt
```

接下来需要将 Mizuoto TTS WebUI 移动到 `D:/mizuoto-tts-webui` 目录中，如果 Mizuoto TTS WebUI 的文件夹名称不是 `mizuoto-tts-webui`，比如`my-mizuoto-tts-webui`，需要将名称修改成`mizuoto-tts-webui`。

!!! note
    如果不修改名称，需要根据 [设置内核路径前缀](config.md#_8) 中的说明配置内核路径前缀。在这个例子中内核路径前缀就需要设置为 `my-mizuoto-tts-webui`。

移动进去后此时的目录结构如下。

```
D:/mizuoto-tts-webui
├── activate.ps1
├── mizuoto-tts-webui
│   ├── data
│   ├── mizuoto_tts_webui
│   ├── launch.py
│   ...
│   └── requirements.txt
├── help.txt
├── launch.ps1
├── launch_mizuoto_tts_webui_installer.ps1
├── reinstall_pytorch.ps1
├── settings.ps1
├── snapshot_manager.ps1
├── terminal.ps1
├── update.ps1
├── version_manager.ps1
└── update_time.txt
```

再检查 `<安装目录>/<内核路径前缀>` 文件夹中是否包含 `python` 和 `git` 文件夹，如果未包含，需要运行 `launch_mizuoto_tts_webui_installer.ps1` 重建环境，重建完成后即可运行 `launch.ps1` 启动 Mizuoto TTS WebUI。

!!! note
    使用 Mizuoto TTS WebUI 自带的 `start.bat` / `start.ps1` / `start.sh` 启动脚本时创建的 `venv` 文件夹不会被 Mizuoto TTS WebUI Installer 使用，Mizuoto TTS WebUI Installer 只会识别 [Mizuoto TTS WebUI Installer 对 Python / Git 环境的识别](config.md#mizuoto-tts-webui-installer-python-git) 中列出的 Python / Git 路径。原有的 `data` 文件夹会继续作为 Mizuoto 的数据目录使用。

### 重装 Mizuoto TTS WebUI
将 `mizuoto-tts-webui` 文件夹中的内核目录（默认为 `core`，以实际的内核路径前缀为准）删除，然后运行 `launch_mizuoto_tts_webui_installer.ps1` 重新部署 Mizuoto TTS WebUI。

!!! note
    Mizuoto 的设置、数据库、模型、音色和输出默认保存在内核目录的 `data` 文件夹中，请将这些文件备份后再删除内核目录。

### 重装 Python 环境
如果 Python 环境出现严重损坏，可以删除以下目录，然后运行 `launch_mizuoto_tts_webui_installer.ps1` 重新构建 Python 环境。

```text
<安装目录>/python
<安装目录>/<内核路径前缀>/python
```

默认情况下 `<安装目录>` 为 `mizuoto-tts-webui`；`<内核路径前缀>` 可在 `core_prefix.txt`、`settings.ps1` 或脚本运行日志中查看。

### 重装 Git
如果 Git 环境出现严重损坏，可以删除以下目录，然后运行 `launch_mizuoto_tts_webui_installer.ps1` 重新下载 Git。

```text
<安装目录>/git
<安装目录>/<内核路径前缀>/git
```

### 重装 PyTorch
运行 `reinstall_pytorch.ps1` 脚本，并根据脚本提示的内容进行操作。

!!! warning
    Mizuoto 需要 2.8 及以上版本的 PyTorch，并且不支持 DirectML 版本的 PyTorch。`reinstall_pytorch.ps1` 列出的 PyTorch 版本中可能包含不满足要求的版本，选择时请注意。

### 卸载 Mizuoto TTS WebUI
使用 Mizuoto TTS WebUI Installer 安装 Mizuoto TTS WebUI 后，主要文件都存放在 `mizuoto-tts-webui` 文件夹中。确认模型、音色、输出文件等重要数据（默认位于 `mizuoto-tts-webui/core/data`）已经备份后，删除该文件夹即可卸载 Mizuoto TTS WebUI。

如果创建过快捷启动方式，还需要按系统删除对应快捷方式。Mizuoto TTS WebUI 的快捷方式名称通常为 `Mizuoto-TTS-WebUI`。

Windows 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("Mizuoto-TTS-WebUI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$([System.Environment]::GetFolderPath("Desktop"))\$name.lnk" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\$name.lnk" -Force -ErrorAction SilentlyContinue
}
```

Linux 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("Mizuoto-TTS-WebUI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$HOME/Desktop/$name.desktop" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$HOME/.local/share/applications/$name.desktop" -Force -ErrorAction SilentlyContinue
}
```

macOS 可在 PowerShell 中运行：

```powershell
$shortcutNames = @("Mizuoto-TTS-WebUI")
foreach ($name in $shortcutNames) {
    Remove-Item -Path "$HOME/Desktop/$name.app" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "/Applications/$name.app" -Recurse -Force -ErrorAction SilentlyContinue
}
```

### 移动 Mizuoto TTS WebUI 的路径
直接将 `mizuoto-tts-webui` 文件夹移动到别的路径即可。

如果启用了自动创建 Mizuoto TTS WebUI 快捷启动方式的功能，移动 Mizuoto TTS WebUI 后原来的快捷启动方式将失效，需要运行 `launch.ps1` 更新快捷启动方式。
