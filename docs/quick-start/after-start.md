# 启动后的下一步

WebUI 或训练工具启动后，可以继续处理模型、扩展、更新、终端环境和实际使用教程。本页只做入口汇总。

## 学习实际使用

本项目文档主要覆盖安装、启动和管理。WebUI 界面使用、绘图流程、模型使用、提示词、工作流和绘世启动器操作，可以继续阅读 [SD Note](https://licyk.github.io/SDNote/)。

## 下载模型和资源

- SD WebUI：阅读 [SD WebUI 模型与资源](../installer/sd-webui/resources.md)。
- ComfyUI：阅读 [ComfyUI 模型与资源](../installer/comfyui/resources.md)。
- Fooocus：阅读 [Fooocus 模型与资源](../installer/fooocus/resources.md)。
- InvokeAI：阅读 [InvokeAI 模型与资源](../installer/invokeai/resources.md)。
- SD Trainer：阅读 [SD Trainer 模型与资源](../installer/sd-trainer/resources.md)。
- SD Trainer Script：阅读 [SD Trainer Script 模型与资源](../installer/sd-trainer-script/resources.md)。

## 常用管理脚本

安装器和整合包通常会生成这些脚本：

- `launch.ps1`：启动 WebUI 或工具。
- `update.ps1`：更新程序或管理脚本。
- `terminal.ps1`：打开已配置好的终端环境。
- `download_models.ps1`：下载模型。
- `version_manager.ps1`：管理安装器生成的版本相关任务。

每个产品的脚本说明见对应产品的“启动与使用”“维护与迁移”“常用命令”页面。

## 常见配置文件

安装器生成的管理脚本会读取同级目录中的配置文件。大部分配置都可以通过 `settings.ps1` 创建、修改或删除；直接看到这些文件时，可以把它们理解为“本地设置的保存结果”。多数 `disable_*.txt` / `enable_*.txt` 是空文件开关，文件存在就表示对应设置生效；带具体内容的 `.txt` 文件会读取文件内容。

| 配置文件 | 作用 | 备注 |
| --- | --- | --- |
| `launch_args.txt` | 保存 WebUI / 工具启动参数，`launch.ps1` 启动时会读取。 | 启动参数写错可能导致无法启动；可通过 `settings.ps1` 修改或删除。SD Trainer Script 的训练命令主要写在 `train.ps1`。 |
| `proxy.txt` | 保存代理地址，例如 `http://127.0.0.1:10809`。 | 优先级高于系统代理。 |
| `disable_proxy.txt` | 禁用管理脚本自动设置代理。 | 空文件开关。 |
| `disable_auto_mirror.txt` | 禁用 CLI 自动镜像源选择，让手动 PyPI / GitHub / Hugging Face / 模型下载源设置生效。 | 若保持自动镜像源选择，手动镜像文件可能会被 Python CLI 自动判断覆盖。 |
| `hf_mirror.txt` / `disable_hf_mirror.txt` | 自定义或禁用 Hugging Face 镜像源。 | `hf_mirror.txt` 内填写镜像地址。 |
| `gh_mirror.txt` / `disable_gh_mirror.txt` | 自定义或禁用 GitHub 镜像源。 | `gh_mirror.txt` 内填写镜像地址。 |
| `disable_pypi_mirror.txt` | 禁用 PyPI 镜像，改用 PyPI 官方源。 | 空文件开关。 |
| `disable_uv.txt` | 禁用 uv，改用 Pip 管理 Python 包。 | 排查 uv 安装问题时使用。 |
| `disable_model_mirror.txt` | 将模型下载源从 ModelScope 切换为 Hugging Face。 | 主要用于有 `download_models.ps1` 的产品；固定下载源前通常需要先禁用自动镜像源选择。 |
| `core_prefix.txt` | 指定安装器要管理的内核目录名、相对路径或绝对路径。 | 用于管理外部已有安装、整合包目录，或内核目录名不是默认值的情况。 |
| `patcher_config.json` | Hotpatcher 补丁系统配置。 | Hotpatcher 默认启用时会自动生成；需要细调补丁时再修改。 |
| `disable_hotpatcher.txt` | 禁用 Hotpatcher 补丁系统。 | 空文件开关；SD Trainer Script 由 `init.ps1` 读取。 |
| `enable_hotpatcher_runtime.txt` | 启用 Hotpatcher runtime host 连接。 | 一般用户通常不需要。 |
| `hotpatcher_port.txt` | 指定 Hotpatcher runtime 通信端口。 | 只在 runtime 模式下生效，端口范围 `1` 到 `65535`。 |
| `disable_snapshot.txt` | 禁用安装结果快照和管理脚本操作前自动快照。 | 空文件开关。 |
| `disable_update.txt` | 禁用 Installer 管理脚本自动检查更新。 | 空文件开关。 |
| `disable_check_env.txt` | 禁用启动前环境检查。 | 只建议临时排查时使用，可能跳过问题检测。 |
| `enable_shortcut.txt` | 允许管理脚本创建或刷新快捷启动方式。 | 空文件开关，不是所有产品都会需要。 |
| `disable_set_pytorch_cuda_memory_alloc.txt` | 禁用管理脚本自动设置 PyTorch CUDA 内存分配优化。 | 遇到显存分配相关兼容问题时再考虑。 |

这些文件不一定都会出现；只有启用过对应设置、安装器复制了设置，或管理脚本自动生成默认配置时才会出现。需要查看完整说明时，进入 [安装器使用](../installer/index.md) 后选择对应产品的“配置与镜像”页面。

## 遇到问题

- Notebook 问题：阅读 [Notebook 故障排查](../notebook/troubleshooting.md)。
- 下载器或 Launcher 问题：阅读 [下载器与启动器故障排查](../tools/troubleshooting.md)。
- 整合包和绘世启动器问题：阅读 [常见问题](../portable/qa.md)。
- Installer 问题：进入 [安装器使用](../installer/index.md)，选择对应产品的故障排查页面。
