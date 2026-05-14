# 环境变量总览

本文档集中说明 `sd_webui_all_in_one_hotpatcher` 及其扩展会读取的环境变量。README 和专题文档只保留接入示例；完整变量语义以这里为准。

核心框架变量统一使用 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_` 前缀。`HF_ENDPOINT` 是 HF Endpoint 镜像扩展读取的外部变量，不属于 bootstrap 前缀。

## 入口规则

如果包含 `sitecustomize.py` 的目录在 `PYTHONPATH` 中，Python 启动时会自动导入它。当前实现只要发现任意 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` 变量，就会调用 `sd_webui_all_in_one_hotpatcher.bootstrap.configure_from_env()`。这只负责进入 bootstrap；具体能力仍需要对应开关或配置启用。

也可以在代码中显式调用：

```python
from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

state = configure_from_env()
```

取值规则：

- import hook、runtime、services 和 stack shadow 的主开关按字符串 `"1"` 判断。
- logs/errors 相关布尔变量接受 `1`、`true`、`yes`、`on`，不区分大小写；其他值视为关闭。
- list 类变量使用英文逗号分隔，空白会被忽略。
- 未设置环境变量时，通常使用运行时配置对象中的同名配置；没有配置时才使用代码默认值。
- `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_BOOTSTRAPPED` 是内部防重复标记，通常不应手动设置。

## 快速示例

最小 bootstrap + import hook：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK=1 \
PYTHONPATH=sd_webui_all_in_one/patcher python your_app.py
```

连接 runtime 宿主并从文件加载配置：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME=1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST=127.0.0.1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT=8765 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=file \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE=/path/to/hotpatcher-config.json \
PYTHONPATH=sd_webui_all_in_one/patcher python your_app.py
```

启用日志采集和普通异常上报：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME=1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST=127.0.0.1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT=8765 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS=1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERRORS=1 \
PYTHONPATH=sd_webui_all_in_one/patcher python your_app.py
```

启用 HF Endpoint 镜像扩展时指定镜像：

```bash
HF_ENDPOINT=https://hf-mirror.example
```

## 自动启动

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `PYTHONPATH` | 让 Python 能导入 `sitecustomize.py` 和 hotpatcher 包。 | 包含 `sitecustomize.py` 所在目录时自动启动逻辑才会生效。 | 无 | 路径列表 | Python 启动流程；不是 hotpatcher 自定义变量。 |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG` | bootstrap 或 runtime 连接失败时打印 traceback，便于调试。 | 值为 `"1"` 时生效。 | 未设置 | `"1"` 或未设置 | `sitecustomize.py`、`runtime.client.RuntimeClient.connect_from_env()`；可配合 `sitecustomize` 或显式调用使用。 |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_BOOTSTRAPPED` | 标记当前进程已执行过自动 bootstrap，避免重复执行。 | `sitecustomize.py` 或 `configure_from_env()` 会写入 `"1"`。 | 未设置 | 内部使用 | `sitecustomize.py`、`bootstrap.py`；通常不要手动设置。 |

## 核心启动

这些变量由 `sd_webui_all_in_one_hotpatcher.bootstrap.configure_from_env()` 读取。通过 `sitecustomize.py` 自动启动或手动调用 `configure_from_env()` 都可以生效。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK` | 安装 import hook。 | 值为 `"1"`。 | 未设置，默认不安装。 | `"1"` 或未设置 | `bootstrap.configure_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME` | 允许 bootstrap 创建 runtime client，并允许 `auto` 配置源尝试远程配置。 | 值为 `"1"`，并提供 `HOST` / `PORT` 才能连接。 | 未设置，默认不连接。 | `"1"` 或未设置 | `bootstrap.configure_from_env()`、`runtime.config.load_config()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES` | 在已有 runtime client 时打开 services 控制通道。 | 值为 `"1"` 且 runtime 已连接。 | 未设置，默认不打开控制通道。 | `"1"` 或未设置 | `bootstrap.configure_from_env()` |

## Stack Shadow

这些变量由 `sd_webui_all_in_one_hotpatcher.stack_shadow.configure_stack_shadower_from_env()` 读取。该函数在 bootstrap 起始阶段执行，因此适合通过 `sitecustomize.py` 提前安装。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW` | 启用栈隐藏 finder，重写目标模块 code object 的 `co_filename`。 | 值为 `"1"`。 | 未设置，默认不安装。 | `"1"` 或未设置 | `stack_shadow.configure_stack_shadower_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_PREFIXES` | 指定需要隐藏 traceback 路径的模块前缀。 | `SHADOW=1` 时读取。 | `sd_webui_all_in_one_hotpatcher` | 逗号分隔模块前缀 | `stack_shadow.configure_stack_shadower_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_TEMPLATE` | 指定伪装后的 filename 模板。 | `SHADOW=1` 时读取。 | `<hidden {name}>` | 字符串模板，支持 `{name}`、`{fullname}`、`{module}` | `stack_shadow.configure_stack_shadower_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_SOURCE_LOADERS` | 是否同时处理普通源码 loader。设为 `0` 后只处理 zip 模块。 | `SHADOW=1` 时读取。 | `1` | `0` 表示关闭 source loader 支持，其他值表示开启。 | `stack_shadow.configure_stack_shadower_from_env()` |

## Runtime 连接

这些变量由 `sd_webui_all_in_one_hotpatcher.runtime.client.RuntimeClient.connect_from_env()` 读取。bootstrap 只有在 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME=1` 时才会尝试连接。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST` | runtime TCP 宿主地址。 | runtime 连接时必须提供。 | 未设置 | 主机名或 IP | `RuntimeClient.connect_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT` | runtime TCP 宿主端口。 | runtime 连接时必须提供。 | 未设置 | 整数端口 | `RuntimeClient.connect_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN` | hello 握手中的 token。 | runtime 连接时读取，可为空。 | 空字符串 | 字符串 | `RuntimeClient.connect_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT` | 建连和请求默认超时时间。 | runtime 连接时读取。 | `5` | 秒数，可转换为 `float` | `RuntimeClient.connect_from_env()` |

## 配置来源

这些变量由 `sd_webui_all_in_one_hotpatcher.runtime.config.load_config()` 读取。bootstrap 每次都会尝试加载配置；没有任何可用来源时返回空配置。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE` | 指定配置来源。 | 调用 `load_config()` 时读取。 | `auto` | `env`、`file`、`remote`、`auto` | `runtime.config.load_config()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON` | 直接提供配置 JSON。 | `CONFIG_SOURCE=env` 时读取；`auto` 模式下优先读取。 | 未设置 | JSON object 字符串 | `runtime.config.load_config()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE` | 指定配置文件路径。 | `CONFIG_SOURCE=file` 时读取；`auto` 模式下在 `CONFIG_JSON` 之后读取。 | 未设置 | UTF-8 JSON object 文件路径，支持 `~` | `runtime.config.load_config()` |

`CONFIG_SOURCE=remote` 会通过 runtime client 发送 `config.get` 请求。`auto` 模式下只有在 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME=1` 且 `HOST` / `PORT` 都存在时才会尝试远程配置。

## Services

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES` | 打开 runtime services 控制通道。 | 值为 `"1"` 且 bootstrap 已连接 runtime client。 | 未设置，默认不打开。 | `"1"` 或未设置 | `bootstrap.configure_from_env()` |

配置中的 `"services": {"apply_on_bootstrap": true}` 会让 bootstrap 在加载配置后自动调用 `services.apply_config()`。这个行为不是环境变量控制的。

## 日志采集

这些变量由 `sd_webui_all_in_one_hotpatcher.runtime.logs.configure_log_capture_from_env()` 读取。bootstrap 只有在 runtime client 已连接时才会尝试安装日志采集。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS` | 启用进程级日志采集。 | 布尔真值，或配置中的 `logs` 为真。 | 未设置时跟随配置；无配置则关闭。 | `1`、`true`、`yes`、`on` | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGING` | 是否采集 Python `logging` 记录。 | 日志采集启用后读取。 | `true` | 布尔值 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_STREAMS` | 需要 tee 的标准流。 | 日志采集启用后读取。 | `stdout,stderr` | 逗号分隔；`0`、`false`、`none`、`off` 表示不采集标准流。 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS` | 子进程输出采集模式。 | 日志采集启用后读取。 | `safe` | `0`、`safe`、`force` | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_POLICY` | 日志 payload 裁剪策略。 | 日志采集启用后读取。 | `bounded` | `bounded`、`raw` | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_MAX_CHARS` | `bounded` 模式下单个字符串最大长度。 | 日志采集启用后读取。 | `8192` | 整数；小于等于 `0` 时相当于不裁剪。 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_QUEUE_SIZE` | 后台发送队列大小。 | 日志采集启用后读取。 | `1000` | 整数 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGER_INCLUDE` | 限定允许采集的 logger 前缀。 | 日志采集启用后读取。 | 空，表示不限制 include。 | 逗号分隔 logger 前缀 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGER_EXCLUDE` | 排除采集的 logger 前缀，避免递归采集 runtime 自身日志。 | 日志采集启用后读取。 | `sd_webui_all_in_one_hotpatcher` | 逗号分隔 logger 前缀 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_POLICY` | stdout/stderr、logging、subprocess hook 被覆盖时的处理策略。 | 日志采集启用后读取。 | `cooperative` | `cooperative`、`warn`、`reapply` | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_CHECK_INTERVAL` | `warn` / `reapply` 模式下检查 hook 状态的间隔秒数。 | 日志采集启用后读取。 | `1` | 整数秒 | `runtime.logs.configure_log_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_FD_CAPTURE` | 实验性 fd 级标准流采集兜底。 | 日志采集启用后读取。 | `0` | `0`、`false`、`none`、`off`、`fallback`、`force` | `runtime.logs.configure_log_capture_from_env()` |

## 错误捕获

这些变量由 `sd_webui_all_in_one_hotpatcher.runtime.errors.configure_error_capture_from_env()` 读取。bootstrap 只有在 runtime client 已连接时才会尝试安装错误捕获。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERRORS` | 启用普通 Python 异常上报。 | 布尔真值，或配置中的 `runtime.errors.enabled` / `errors.enabled` 为真。 | 未设置时跟随配置；无配置则关闭。 | `1`、`true`、`yes`、`on` | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_SYS_EXCEPTHOOK` | 捕获未处理的主线程异常。 | 错误捕获启用后读取。 | `true` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_THREADING_EXCEPTHOOK` | 捕获 `threading.excepthook` 异常。 | 错误捕获启用后读取。 | `true` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_UNRAISABLEHOOK` | 捕获 `sys.unraisablehook` 异常。 | 错误捕获启用后读取。 | `true` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_ASYNCIO` | 捕获 asyncio event loop 异常。 | 错误捕获启用后读取。 | `true` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_INCLUDE_LOCALS` | 在异常 frame 中附带脱敏后的 locals 摘要。 | 错误捕获启用后读取。 | `false` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_EXCEPTIONS` | 启用实验性 caught exception trace 捕获。 | 错误捕获启用后读取；该能力有明显性能成本。 | `false` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_THREADING` | caught exception trace 是否覆盖新线程。 | caught exception 捕获启用后读取。 | `true` | 布尔值 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_MODULE_PREFIXES` | caught exception trace 只捕获这些模块前缀。 | caught exception 捕获启用后读取。 | 空，表示不按 include 限制。 | 逗号分隔模块前缀 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_EXCLUDE_PREFIXES` | caught exception trace 排除这些模块前缀。 | caught exception 捕获启用后读取。 | `sd_webui_all_in_one_hotpatcher,sd_webui_all_in_one_hotpatcher_ext` | 逗号分隔模块前缀；空字符串表示不排除。 | `runtime.errors.configure_error_capture_from_env()` |
| `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_MAX_EVENTS_PER_SECOND` | caught exception trace 每秒最多上报事件数。 | caught exception 捕获启用后读取。 | `20` | 整数；小于等于 `0` 表示不发送 caught exception 事件。 | `runtime.errors.configure_error_capture_from_env()` |

## 扩展变量

扩展变量由具体扩展自己读取，不会因为存在该变量而触发 `sitecustomize.py` 的 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` 自动 bootstrap。

| 变量 | 用途 | 启用条件 | 默认值 | 取值格式 | 读取位置 / 入口 |
| --- | --- | --- | --- | --- | --- |
| `HF_ENDPOINT` | HF Endpoint 镜像源，用于把 `https://huggingface.co/...` 下载 URL 改写到镜像地址。 | 已调用 `sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror.apply_mirror()` 或相关低层 patch；下载函数调用时实时读取。 | 未设置，默认不改写 URL。 | 完整 URL，例如 `https://hf-mirror.example`。空值、非完整 URL 或目标 URL host 不是 `huggingface.co` 时不改写。 | `sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror.rewrite_huggingface_url()` |

