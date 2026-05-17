# 下载器与启动器故障排查

本页整理 AI 整合包下载器、Windows GUI Launcher 和 Bash TUI / CLI Launcher 的常见问题。安装器自身报错时，也需要结合对应产品的 [安装器故障排查](../installer/index.md) 一起阅读。

## 下载器无法刷新列表

AI 整合包下载器会从远程 `portable_list.json` 同步资源列表。如果刷新失败：

- 检查网络是否可以访问 GitHub、Gitee 或资源镜像。
- 检查 Windows 系统代理是否正确；下载器启动时会读取系统代理。
- 点击“刷新同步”重新获取列表。
- 关闭下载器后重新打开，确认是否能重新下载资源配置。

## 下载失败

下载器使用 Aria2 执行下载任务。如果任务失败：

- 切换下载源，例如从 `ModelScope` 切换到 `HuggingFace`。
- 检查保存路径是否可写。
- 确认磁盘剩余空间足够。
- 检查安全软件是否拦截 `aria2c.exe`。
- 重新添加任务，Aria2 会尝试利用已有临时文件继续下载。

## 解压失败

下载器会调用 `7za.exe` 解压整合包。如果解压失败：

- 确认压缩包已经完整下载。
- 确认目标路径可写，并且磁盘空间充足。
- 关闭正在占用目标目录的程序。
- 取消“解压成功后删除压缩包”，保留压缩包后手动使用 7-Zip 或 Bandizip 解压。

## 保存路径无效或磁盘空间不足

底部磁盘空间信息会显示当前路径的可用空间和总容量。如果路径无效或空间不足：

- 点击“更改保存路径”选择真实存在的目录。
- 避免把整合包下载到权限受限目录。
- 清理目标磁盘，或选择容量更大的磁盘。

## GUI 无法启动

Windows GUI Launcher 需要 Windows PowerShell 5.1 或 PowerShell 7+，并依赖 WPF / .NET 桌面环境。

可尝试：

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\installer_launcher_gui.ps1
```

如果仍然失败：

- 确认当前系统为 Windows。
- 确认 PowerShell 可以正常启动。
- 使用 `install.bat` 重新安装 GUI。
- 查看 `%LOCALAPPDATA%\installer-launcher\logs\` 下的日志。

## GUI 检测为未安装或安装不完整

GUI 根据安装路径和管理脚本判断安装状态：

- `未安装`：安装路径不存在。
- `安装不完整`：安装目录存在，但缺少管理脚本。
- `已安装`：安装目录存在，并找到管理脚本。

遇到 `安装不完整` 时，建议在“高级选项”确认安装路径后，切回“一键启动”的安装模式重新运行安装器修复。

## GUI 代理或更新检查失败

GUI 的代理模式包括：

- `auto`：读取 Windows 系统代理。
- `manual`：使用手动代理地址。
- `off`：清理当前启动器进程中的代理变量。

自动更新只更新启动器自身。更新失败不会阻止继续使用当前版本。需要排查时，在“设置”页面点击“查看日志”。

## TUI 无法显示图形界面

TUI 使用 `dialog` 提供终端图形界面。如果没有 `dialog`，会退回文本交互。

可检查：

```bash
dialog --version
```

缺少 `dialog` 时，根据系统包管理器安装它，或继续使用文本交互和 CLI 命令。

## TUI 提示 Bash 版本过低

macOS 自带 Bash 版本通常低于 5。先安装 Homebrew Bash：

```bash
brew install bash
```

然后使用 `/opt/homebrew/bin/bash` 重新运行启动器。

## TUI 缺少 PowerShell、curl、wget 或 git

TUI / CLI 至少需要：

- `pwsh` 或 `powershell`：执行上游安装器和管理脚本。
- `curl` 或 `wget`：下载安装器脚本。
- `git`：用于安装或更新启动器自身；没有 `git` 时会尝试源码压缩包。

安装依赖后重新运行：

```bash
installer-launcher tui
```

## 查看日志

Bash TUI / CLI：

```bash
./installer_launcher.sh show-log 200
```

Windows GUI：

```text
%LOCALAPPDATA%\installer-launcher\logs\
```

日志会记录安装器下载源、配置加载、PowerShell 脚本执行、管理脚本运行、项目卸载和启动器更新等信息。日志中会对 token、password、key 等敏感字段做脱敏处理。
