# RVC Next WebUI Installer 启动与使用

在 `rvc-next-webui` 文件夹中可以看到不同的 PowerShell 脚本。如果是 Windows 平台，不要左键双击 `.ps1` 脚本；左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。正确方式是右键 PowerShell 脚本，选择 `使用 PowerShell 运行`。如果右键运行后窗口闪退，先运行 `configure_env.bat` 完成环境配置，再重新右键运行 `.ps1` 脚本。如果是 Linux / MacOS 平台，请打开终端并使用 `pwsh` 命令去运行。

## 管理脚本速查

安装完成后，日常启动、更新、修复环境和调整设置都优先通过这些脚本完成。运行管理脚本时建议在安装目录中执行；如果脚本缺失或被误改，可运行 `launch_rvc_next_webui_installer.ps1` 重新生成。

| 脚本 | 作用 | 何时使用 / 注意事项 |
| --- | --- | --- |
| `configure_env.bat` | Windows 环境配置脚本，会设置 PowerShell 脚本运行策略、启用 Windows 长路径支持，并尝试把 `.ps1` 默认打开方式设为 PowerShell。 | 首次使用 Installer、运行 `.ps1` 闪退、PowerShell 脚本被系统拦截或路径过长导致异常时使用。该脚本会申请管理员权限。 |
| `launch.ps1` | 先调用 `rvc-next-webui check-env` 做启动前环境检查，再调用 `rvc-next-webui launch` 启动 RVC Next WebUI；启动参数来自 `launch_args.txt` 和命令行参数。 | 日常启动入口。启动参数写错导致无法启动时，可删除或修改 `launch_args.txt`，也可以通过 `settings.ps1` 调整。 |
| `update.ps1` | 调用 `rvc-next-webui update` 更新 RVC Next WebUI，并在调用前处理代理、GitHub 镜像、管理脚本更新和自动快照参数。 | 需要升级 RVC Next WebUI 或重新同步仓库时使用。更新可能改变当前 WebUI 版本。 |
| `reinstall_pytorch.ps1` | 调用 `rvc-next-webui reinstall-pytorch`，按脚本显示的 PyTorch 版本编号重装 PyTorch。 | 出现 PyTorch 损坏、显卡后端切换、环境升级后无法启动时使用。该脚本会修改当前 Python 环境中的 PyTorch 相关包；RVC Next 需要 2.7.1 及以上版本且非 DirectML 的 PyTorch，选择版本时请注意。 |
| `version_manager.ps1` | 调用 `rvc-next-webui gui version-manager` 打开版本管理 GUI。 | 需要通过图形界面查看或调整 RVC Next WebUI 版本时使用。 |
| `snapshot_manager.ps1` | 调用 `rvc-next-webui gui snapshot-manager` 打开快照管理 GUI。 | 需要通过图形界面处理环境快照时使用。自动快照设置可通过 `settings.ps1` 管理。 |
| `settings.ps1` | 打开 Installer 设置管理器，用于调整代理、镜像源、uv、启动参数、Hotpatcher、自动快照、内核路径前缀和管理脚本更新等本地配置。 | 不想手动创建 `*.txt` 配置文件时优先使用。它会在管理脚本同级目录写入或删除对应配置文件。 |
| `terminal.ps1` | 打开一个已经配置好 PATH、代理、镜像和产品环境变量的 PowerShell 终端，并自动激活当前 Installer 管理的 Python 环境。 | 需要运行 `python`、`pip`、`uv`、`git` 或 RVC Next WebUI 相关命令时使用。不要把 Installer 的 `python` 目录手动加入系统环境变量。 |
| `activate.ps1` | 在当前 PowerShell 会话中激活 Installer 管理的 Python / Git 环境。 | 已经打开终端且只想在当前窗口进入环境时使用。一般用户直接运行 `terminal.ps1` 更省事。 |
| `launch_rvc_next_webui_installer.ps1` | 下载最新版 RVC Next WebUI Installer 到 `cache` 目录并运行，同时带上当前目录中的代理、镜像、内核路径前缀和快照等本地配置。 | 管理脚本损坏、缺失、需要重新运行 Installer 修复管理脚本，或 Python / Git 环境需要由安装器重新修复时使用。 |

## 基础操作

### 启动 RVC Next WebUI
运行 `launch.ps1` 脚本。启动完成后，控制台中会显示 RVC Next WebUI 的访问地址，默认地址为 `http://127.0.0.1:7868`，并会自动在浏览器中打开。

### 更新 RVC Next WebUI
运行 `update.ps1` 脚本，如果遇到更新 RVC Next WebUI 失败的情况可尝试重新运行 `update.ps1` 脚本。

### 设置 RVC Next WebUI 启动参数
!!! info
    该设置可通过 [管理 RVC Next WebUI Installer 设置](config.md#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

要设置 RVC Next WebUI 的启动参数，可以在和 `launch.ps1` 脚本同级的目录创建一个`launch_args.txt` 文件，在文件内写上启动参数，运行 RVC Next WebUI 启动脚本时将自动读取该文件内的启动参数并应用。

RVC Next WebUI Installer 默认生成的 `launch_args.txt` 不包含任何启动参数。常用的启动参数如下：

| 参数 | 说明 |
| --- | --- |
| `--port <端口>` | 监听端口，默认为 `7868`，端口被占用时会尝试下一个端口。 |
| `--strict-port` | 端口被占用时直接退出，不尝试下一个端口。 |
| `--host <地址>` | 监听地址，默认为 `127.0.0.1`。监听非本机地址时需要同时设置 `--access-token`。 |
| `--access-token <令牌>` | 访问令牌。 |
| `--no-browser` | 启动后不自动打开浏览器。 |
| `--api-prefix <路径>` | 将 API 和 WebUI 挂载到指定路径下，如 `/voice`。 |
| `--data-dir <路径>` | RVC Next 数据目录，默认为内核目录中的 `data` 文件夹。 |
| `--config-dir <路径>` | 保存 `settings.toml` 的目录，默认为数据目录。 |
| `--debug` | 启用 Debug 日志。 |

例如需要在局域网中访问 RVC Next WebUI，并且不自动打开浏览器，`launch_args.txt` 可写为：

```
--host 0.0.0.0 --access-token <自定义的访问令牌> --no-browser
```

!!! note
    RVC Next WebUI 支持的全部启动参数可阅读：[启动参数 · licyk/rvc-next-webui](https://github.com/licyk/rvc-next-webui?tab=readme-ov-file#%E5%90%AF%E5%8A%A8%E5%8F%82%E6%95%B0)。
    
    如果修改启动参数导致无法正常启动，可将 `launch_args.txt` 清空，恢复为默认的空启动参数。

!!! warning
    RVC Next WebUI Installer 启动 RVC Next WebUI 时总是会附加 `--skip-check --disable-proxy` 启动参数，运行环境检查和代理设置由 RVC Next WebUI Installer 负责，因此不需要在 `launch_args.txt` 中填写这两个参数。
    
    也因为这个原因，RVC Next WebUI 自带的 `--torch-backend`、`--reinstall-torch`、`--index-url`、`--proxy` 参数在 RVC Next WebUI Installer 中不会生效：
    
    - 重装或切换 PyTorch 请使用 `reinstall_pytorch.ps1`。
    - PyPI 镜像源请参考 [设置 PyPI 镜像源](config.md#pypi)。
    - 代理请参考 [配置代理](config.md#_4)。

### RVC Next WebUI 的数据目录
RVC Next 的所有数据（设置文件 `settings.toml`、数据库、模型、实验和输出）默认保存在内核目录的 `data` 文件夹中，即 `rvc-next-webui/core/data`（`core` 为默认的内核路径前缀，以实际内核目录为准）。备份、迁移或重装 RVC Next WebUI 时，请优先备份该文件夹。

如需将数据保存到其他位置，可在启动参数中使用 `--data-dir` 指定数据目录。

RVC Next WebUI Installer 不会预下载模型，RVC Next 运行所需的模型资源由 RVC Next 在使用时自行下载。下载这些资源使用的 HuggingFace 镜像源设置可参考 [设置 HuggingFace 镜像](config.md#huggingface)。

### 配置 Hotpatcher 补丁系统
!!! info
    该设置中的补丁系统开关和端口可通过 [管理 RVC Next WebUI Installer 设置](config.md#rvc-next-webui-installer_1) 中提到的 `settings.ps1` 进行修改。

Hotpatcher 补丁系统默认启用。运行 `launch.ps1` 时添加 `-DisableHotpatcher` 可禁用 Hotpatcher 补丁系统：

```powershell
./launch.ps1 -DisableHotpatcher
```

也可以在 `launch.ps1` 同级目录创建 `disable_hotpatcher.txt` 文件禁用。

默认配置路径固定为 `launch.ps1` 同级目录下的 `patcher_config.json`。Hotpatcher 默认启用且该文件不存在时，`launch.ps1` 会自动导出默认配置。安装器和 `launch.ps1` 不提供自定义配置路径参数；需要调整配置时，请直接修改该文件。

Hotpatcher 默认只做本地补丁注入。需要 runtime host 连接时，可使用 `-EnableHotpatcherRuntime`，或在 `launch.ps1` 同级目录创建 `enable_hotpatcher_runtime.txt`；`-HotpatcherPort <端口>` / `hotpatcher_port.txt` 只在 runtime 模式下设置端口。

## 环境管理

### 进入 RVC Next WebUI 所在的 Python 环境
如果需要使用 Python、Pip、RVC Next WebUI 的命令时，请勿将 RVC Next WebUI 的 `python` 文件夹添加到环境变量，这将会导致不良的后果产生。

正确的方法是运行 `terminal.ps1` 脚本，这将打开 PowerShell 并自动执行 `activate.ps1`，此时就进入了 RVC Next WebUI 所在的 Python。

或者是在 RVC Next WebUI 目录中打开 PowerShell，在 PowerShell 中运行下面的命令进入 RVC Next WebUI Env：

```powershell
./activate.ps1
```

这样就进入 RVC Next WebUI 所在的 Python 环境，可以在这个环境中使用该环境的 Python 等命令。

### 管理 RVC Next WebUI 的版本
运行 `version_manager.ps1` 脚本。

### 创建和恢复 RVC Next WebUI 环境快照
运行 `snapshot_manager.ps1` 脚本。

### 查看 Git / Python 命令实际调用的路径
```powershell
# 查看 Git 命令调用的路径
(Get-Command git).Source

# 查看 Python 命令调用的路径
(Get-Command python).Source

# 查看其他命令的实际调用路径也是同样的方法
# (Get-Command <command>).Source
```
