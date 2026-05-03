# CLI - SD WebUI All In One 环境变量配置

## SD WebUI All In One 环境变量配置
SD WebUI All In One 支持通过环境变量来调整其行为。

### 基础配置
- `SD_WEBUI_ALL_IN_ONE_LOGGER_NAME`: 日志器名称 (默认: `SD WebUI All In One`)。
- `SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL`: 日志等级 (默认: `20` 即 INFO)。
- `SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR`: 是否启用日志颜色 (`1`|`True` 启用)。
- `SD_WEBUI_ALL_IN_ONE_RETRY_TIMES`: 网络请求重试次数 (默认: `3`)。
- `SD_WEBUI_ALL_IN_ONE_PROXY`: 是否自动读取系统代理配置并应用代理 (`1`|`True` 启用)。
- `SD_WEBUI_ALL_IN_ONE_PATCHER`: 是否启用补丁功能 (`1`|`True` 启用)。
- `SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR`: 是否启用自带的额外 PyPI 镜像源 (`1`|`True` 启用)。
- `SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH`: 是否设置缓存路径 (`1`|`True` 启用)。
- `SD_WEBUI_ALL_IN_ONE_SET_CONFIG`: 是否在启动时通过环境变量进行配置 (`1`|`True` 启用)。
- `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH`：SD WebUI All In One 起始路径。
- `SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY`：是否跳过安装 PyTorch 时设备的兼容性检查。
- `SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR`：是否在运行 WebUI 并发生错误时向上抛出堆栈错误。
- `SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH`：是否在运行 WebUI 前检查运行环境并发生错误时向上抛出堆栈错误。

### 软件根目录配置
可以通过以下环境变量自定义各软件的默认根目录：
- `SD_WEBUI_ROOT`: Stable Diffusion WebUI 根目录。
- `COMFYUI_ROOT`: ComfyUI 根目录。
- `FOOOCUS_ROOT`: Fooocus 根目录。
- `INVOKEAI_ROOT`: InvokeAI 根目录。
- `SD_TRAINER_ROOT`: SD Trainer 根目录。
- `SD_SCRIPTS_ROOT`: SD Scripts 根目录。
- `QWEN_TTS_WEBUI_ROOT`: Qwen TTS WebUI 根目录。
