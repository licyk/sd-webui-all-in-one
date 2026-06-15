# Python 内核

`sd_webui_all_in_one/` 是项目的 Python 内核，负责 WebUI / 训练工具的安装、启动、更新、模型管理、镜像配置、PyTorch 版本选择、下载、内网穿透和环境检查。CLI、Notebook 和 Installer 生成的管理脚本都会依赖这部分能力。

## 入口与命令

Python 包入口定义在 `pyproject.toml`：

```toml
[project.scripts]
"sd-webui-all-in-one" = "sd_webui_all_in_one.cli_manager.cli:main"
```

`cli_manager/cli.py` 创建根命令，并注册各产品子命令：

- `register_sd_webui`
- `register_comfyui`
- `register_fooocus`
- `register_invokeai`
- `register_qwen_tts_webui`
- `register_sd_trainer`
- `register_sd_scripts`
- `register_manager`

新增 CLI 能力时，应优先放在对应产品的 `cli_manager/*_cli.py` 中，再由注册函数挂到根命令。

## 模块职责

| 模块 | 职责 |
| --- | --- |
| `base_manager/` | 各产品的安装、更新、启动、分支切换、模型和扩展管理基础能力。 |
| `cli_manager/` | CLI 参数解析、子命令注册和对 `base_manager/` 的命令行封装。 |
| `notebook_manager/` | 面向 Colab / Kaggle 的 Manager 类，封装 Notebook 中常用安装、运行、挂载和下载流程。 |
| `downloader/` | 统一下载入口，支持 requests、urllib、Aria2、多线程和压缩包下载解压。 |
| `pytorch_manager/` | GPU 检测、PyTorch 类型推断、版本列表、镜像选择和版本查询。 |
| `model_downloader/` | 模型列表、模型搜索、模型下载和保存路径分类。 |
| `tunnel/` | Cloudflare、Gradio、Ngrok、remote.moe、localhost.run、pinggy.io、Zrok 等内网穿透实现。 |
| `env_check/` | WebUI 运行环境检查和常见依赖问题修复。 |
| `package_analyzer/` | Python 包版本、wheel 文件、requirements 和依赖约束解析。 |
| `file_operations/` | 文件复制、移动、删除、软链接、压缩包解压和打包。 |
| `mirror_manager.py` / `env_manager.py` | PyPI、GitHub、HuggingFace、uv / pip 环境变量和镜像配置。 |

## 产品能力扩展方式

产品能力通常分三层维护：

1. `base_manager/<product>_base.py`：放安装、更新、启动、模型和扩展管理等核心逻辑。
2. `cli_manager/<product>_cli.py`：把核心逻辑包装为 CLI 子命令。
3. `notebook_manager/<product>_manager.py`：把核心逻辑包装为 Notebook 友好的类方法。

如果新增产品或新增产品能力，需要同时检查用户文档中的 [命令行工具](../cli/index.md)、[Jupyter Notebook](../notebook/index.md) 和 [安装器使用](../installer/index.md) 是否要同步。

## 维护约定

- 路径处理优先使用 `pathlib.Path`，只有传给外部命令或环境变量时再转成字符串。
- 日志使用 `sd_webui_all_in_one.logger.get_logger()`，不要随意混用临时 logger。
- 外部命令执行优先走 `sd_webui_all_in_one.cmd.run_cmd()`，方便统一日志、错误和命令预处理。
- 文件下载优先走 `downloader.download_file()` 或 `download_archive_and_unpack()`，避免每个模块自己实现下载。
- 下载后端中 `aria2` 仍是功能最完整的首选；`requests` 使用 aria2-like 的 `split`、`max_connection_per_server`、`min_split_size`、`piece_length` 模型支持 HTTP Range 分片下载、控制文件优先恢复、断点续传和分片级重试；`urllib` 作为无第三方依赖时的单连接兼容 fallback。
- 镜像配置优先使用 `mirror_manager`、`env_manager`、`pytorch_manager` 中的公共函数。
- 能独立测试的解析、版本比较、依赖判断和路径处理逻辑，应优先补到 `tests/`。
