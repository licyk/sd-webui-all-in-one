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
- 下载后端中 `aria2` 仍是功能最完整的首选；`requests` 使用 aria2-like 的 `split`、`max_connection_per_server`、`min_split_size`、`piece_length` 模型支持 HTTP Range 分片下载、控制文件优先恢复、断点续传和分片级重试。探测确认远端不支持 Range 时，全新任务自动降级为单流；已有断点默认由 `always_resume=True` 保护并报错保留，只有显式关闭该选项且达到 `max_resume_failure_tries` 策略时才会丢弃进度重头下载。`urllib` 作为无第三方依赖时的单连接兼容 fallback。
- `requests` 对规范化后的最终目标使用“等待后复用”的进程内互斥，并通过系统锁覆盖跨进程任务。POSIX 下载期间会在同目录创建 `.文件名.download.lock` advisory lock，退出临界区时持锁删除，并由等待者校验文件 inode 后重试，避免删除锁文件造成并发绕过；Windows 使用命名互斥量，不创建磁盘锁文件。POSIX 锁依赖本地文件系统正确实现 `flock`，不保证不支持文件锁语义的网络文件系统。
- Range 数据提交遵循“数据先于状态”：每次进度回调前刷新 Python 文件缓冲，保存 state 前对临时数据文件执行 `fsync`，state 使用临时文件写入、`fsync`、原子替换并尽力同步父目录。这里选择在状态提交点执行 `fsync`，而不是每个网络 chunk 都同步磁盘，以兼顾崩溃一致性和吞吐。
- 统一入口的已有文件默认策略是 `resume`，还可显式选择 `reuse`、`verify`、`overwrite` 或 `rename`。`requests` 将顺序正式文件复制为临时断点后再原子替换，覆盖下载失败不会破坏原文件；aria2 后端把相同策略映射到 `continue`、`allow-overwrite` 和 `auto-file-renaming` 单任务选项。
- 下载文件名当前只允许单个文件名，不允许相对子目录；统一入口和两个主要后端都会拒绝绝对路径、`..`、驱动器/UNC 路径、NUL 和 Windows 保留名称，同时保留合法 Unicode 与空格文件名。
- `requests` 的 `max_tries` 是“每个 URI、每条请求链或 segment”的预算；镜像分别计数，一个坏镜像不会消耗好镜像的额度。永久 4xx、配置错误和 state 错误立即返回，统一入口不再叠加固定三轮外层重试。429/503 支持 `Retry-After` 秒数和 HTTP-date；503 的 `retry_wait>0` 显式覆盖响应等待值，`retry_wait=0` 且没有 `Retry-After` 时立即重试，其他临时错误使用带抖动的指数退避。
- Digest 会从 HEAD、Range probe 和实际 GET 汇总，支持 SHA-512、SHA-256、SHA-1 并选最强算法；同算法冲突会隔离镜像并报完整性错误。当前只解释传统 `Digest`，不把表示选定表示语义的 `Repr-Digest` 混用；若未来支持，需单独建模内容编码与表示选择。
- 同步 `download_file()` 仍可直接使用，同时可传线程安全的 `cancel_event` 和结构化 `progress_callback`。进度事件不依赖 tqdm，包含最终目标、总量、完成量、瞬时/平均速度、活动连接和当前 URI。取消与连接/读取超时使用不同错误类型；Range 取消会先提交可恢复 state。当前不提供 pause 状态，避免把暂停与取消混为一谈。
- 镜像配置优先使用 `mirror_manager`、`env_manager`、`pytorch_manager` 中的公共函数。
- 能独立测试的解析、版本比较、依赖判断和路径处理逻辑，应优先补到 `tests/`。
