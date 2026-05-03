# Fooocus Installer 更新

## 更新管理

### 获取最新的 Fooocus Installer 并运行
运行 `launch_fooocus_installer.ps1` 脚本，如果下载成功将会把 Fooocus Installer 下载到 `cache` 目录中并运行。

### 更新 Fooocus 管理脚本
Fooocus Installer 的管理脚本在启动时会检查管理脚本的更新，如果有新版本可更新将会提示。

可选择下方 3 种方法中的其中 1 个方法进行更新。

#### 1. 直接更新
当检测到有新版的 Fooocus Installer 时将自动应用更新。

#### 2. 使用 Fooocus Installer 配置管理器进行更新
运行 `settings.ps1`，选择 `更新 Fooocus Installer 管理脚本` 功能进行更新，更新完成后需关闭 Fooocus Installer 管理脚本以应用更新。

#### 3. 运行 Fooocus Installer 进行更新
运行 `launch_fooocus_installer.ps1` 获取最新的 Fooocus Installer 后，脚本会自动运行新版 Fooocus Installer 进行更新。

#### 禁用 Fooocus Installer 更新检查
!!! warning
    通常不建议禁用 Fooocus Installer 的更新检查，当 Fooocus 管理脚本有重要更新（如功能性修复）时将得不到及时提示。

!!! info
    该设置可通过 [管理 Fooocus Installer 设置](config.md#管理-fooocus-installer-设置) 中提到的 `settings.ps1` 进行修改。

如果要禁用更新，可以在脚本同级的目录创建 `disable_update.txt` 文件，这将禁用 Fooocus Installer 更新检查。
