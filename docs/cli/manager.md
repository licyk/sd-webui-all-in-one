# CLI - SD WebUI All In One Manager

## SD WebUI All In One Manager
用于管理 `sd-webui-all-in-one` 自身的组件和补丁。

!!! note
    `check pip` 和 `check uv` 默认启用自动镜像源选择，并支持 `--no-auto-mirror`。自动模式会根据网络检测结果强制覆盖 `--no-pypi-mirror`；需要手动控制 PyPI 镜像时，请同时添加 `--no-auto-mirror`。

### 检查 Aria2
检查 Aria2 是否需要更新。
```bash
sd-webui-all-in-one self-manager check aria2
```
*注：当退出代码非 0 时说明需要更新。*

### 检查并更新 Pip
```bash
sd-webui-all-in-one self-manager check pip [选项]
```

高级选项：

- `--no-auto-mirror`：禁用自动镜像源选择，禁用后才会遵守 `--no-pypi-mirror`。
- `--no-pypi-mirror`：不使用国内 PyPI 镜像源。

### 检查并更新 uv
```bash
sd-webui-all-in-one self-manager check uv [选项]
```

高级选项：

- `--no-auto-mirror`：禁用自动镜像源选择，禁用后才会遵守 `--no-pypi-mirror`。
- `--no-pypi-mirror`：不使用国内 PyPI 镜像源。

### Hotpatcher 配置管理
管理新补丁系统的配置、功能目录和 GUI 管理器。

#### 导出默认配置
```bash
sd-webui-all-in-one self-manager patcher export-config --output <路径> [选项]
```

高级选项：

- `--output <路径>`：输出配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH`；未设置环境变量时为 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。
- `--force`：覆盖已有配置文件。

#### 规范化配置
读取配置文件并补齐缺失的默认字段。

```bash
sd-webui-all-in-one self-manager patcher normalize-config --config <路径> [选项]
```

高级选项：

- `--config <路径>`：配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH`；未设置环境变量时为 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。
- `--write-back`：将规范化后的配置写回文件；不加时输出 JSON 到终端。

#### 应用配置
把配置应用到当前命令进程，主要用于验证配置和调试补丁系统。

```bash
sd-webui-all-in-one self-manager patcher apply-config --config <路径>
```

高级选项：

- `--config <路径>`：配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH`；未设置环境变量时为 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。

#### 显示功能目录
输出 Hotpatcher catalog，包括配置字段元数据、默认值和当前注册补丁状态。

```bash
sd-webui-all-in-one self-manager patcher catalog
```

#### 输出 Hotpatcher PYTHONPATH
输出注入 Hotpatcher 补丁路径后的单行 `PYTHONPATH`，用于需要在外部脚本中设置当前进程环境的启动方式。

```bash
sd-webui-all-in-one self-manager patcher get-pythonpath
```

#### 启动配置管理 GUI
启动 Hotpatcher 配置管理器，并可作为 runtime host 接收 WebUI 进程连接。

```bash
sd-webui-all-in-one self-manager patcher gui [选项]
```

高级选项：

- `--config <路径>`：配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH`；未设置环境变量时为 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。
- `--host <地址>`：Runtime host 监听地址，默认 `127.0.0.1`。
- `--port <端口>`：Runtime host 监听端口，默认 `8765`。
- `--token <令牌>`：Runtime host 连接 token，默认空。

### 获取当前系统代理配置
```bash
sd-webui-all-in-one self-manager get proxy
```

### 获取适合当前系统的 CUDA 内存分配器配置
```bash
sd-webui-all-in-one self-manager get cuda-malloc
```

### 获取适合当前系统的 TCMalloc 配置
```bash
sd-webui-all-in-one self-manager get tcmalloc
sd-webui-all-in-one self-manager get tcmalloc --path
```

### 获取 SD WebUI All In One 使用的环境变量配置
```bash
sd-webui-all-in-one self-manager get env-config
```

### 获取当前设备支持的 PyTorch 类型
默认输出当前设备支持的细分 PyTorch 类型，使用英文逗号分隔。

```bash
sd-webui-all-in-one self-manager get pytorch-device-type
```

只输出当前设备对应的 PyTorch 大类：

```bash
sd-webui-all-in-one self-manager get pytorch-device-type --category
```

### 导出 WebUI 环境信息

各 WebUI 管理命令都可以将主机、硬件、PyTorch 状态和现有 WebUI 快照组合为独立 JSON 报告：

```bash
sd-webui-all-in-one <webui> export-environment --output <文件路径> [选项]
```

其中 `<webui>` 可以是 `sd-webui`、`comfyui`、`fooocus`、`invokeai`、`sd-trainer`、`sd-scripts`、`qwen-tts-webui` 或 `rvc-next-webui`。高级选项：

- 对应的 `--*-path <路径>`：指定 WebUI 根目录；未传时使用该产品的默认目录。
- `--no-packages`：不在嵌套快照中记录当前 Python 包列表。
- `--force`：覆盖已有输出文件；默认拒绝覆盖。

报告保留现有快照中的原始绝对路径和来源 URL，分享前应自行确认内容。

### API 服务
启动基于 Python 标准库的轻量 HTTP JSON API 服务。服务只提供 `/api/v2`，并统一使用真实 Python callable 的运行时签名进行方法发现、参数校验和调用。

```bash
sd-webui-all-in-one self-manager api serve [选项]
```

高级选项：

- `--host <地址>`：监听地址，默认 `127.0.0.1`。
- `--port <端口>`：监听端口，默认 `8765`。
- `--token <令牌>`：Bearer token；为空时不启用鉴权。

鉴权启用时，请求需要携带：

```text
Authorization: Bearer <令牌>
```

统一响应格式：

```json
{"ok":true,"result":{}}
```

错误响应格式：

```json
{"ok":false,"error":{"code":"error_code","message":"error message"}}
```

基础端点：

- `GET /health`：健康检查，不需要鉴权。
- `GET /api/v2/status`：服务运行状态，包括进程 ID、启动时间、运行秒数、按状态统计的任务数量和线程池占用（`workers.max`、`workers.busy`）。读取任务管理器，因此任务管理器卡死时该请求也会超时。
- `GET /api/v2/methods`：获取已注册方法、方法元数据、任务状态列表和错误码列表。
- `GET /api/v2/methods/<method>`：获取单个方法的元数据和结构化参数说明。
- `POST /api/v2/call`：调用已注册 API 方法。
- `POST /api/v2/tasks`：创建后台任务。
- `GET /api/v2/tasks`：获取后台任务列表。
- `GET /api/v2/tasks/<task_id>`：获取后台任务状态、进度、结果和错误。
- `GET /api/v2/tasks/<task_id>/logs`：获取后台任务日志。
- `POST /api/v2/tasks/<task_id>/cancel`：请求取消后台任务。

`HEAD /health` 和 `OPTIONS` 可用于外部 GUI 进行连通性和能力探测。

方法命名规范：

- 使用点号分隔的小写命名空间，例如 `comfyui.extension.list`、`invokeai.snapshot.create`、`sd_webui.version.switch_branch`。
- 每段只能使用小写字母、数字和下划线，并且必须以小写字母开头。

方法元数据由 `GET /api/v2/methods` 的 `metadata` 字段返回，每个方法可包含：

- `name`：方法名。
- `kind`：当前统一为 `job`。
- `description`：方法说明。
- `target`：实际调用的 Python callable 完整名称。
- `params_schema`：参数 JSON schema。

方法元数据同时返回 `parameters` 数组。每个参数包含：

- `name`：参数名。
- `type`：JSON Schema 类型；可空等联合类型以数组表示。
- `required`：是否必填。
- `has_default`：schema 是否明确声明了默认值。
- `default`：默认值，仅在 `has_default=true` 时返回；默认值为 `null` 时也会保留。
- `schema`：参数的完整 JSON Schema，包含枚举、格式和约束等信息。

`has_default=false` 只表示 API 规范没有声明默认值，不会把“可选参数”自动视为具有默认值。

任务状态固定为：

```text
pending,running,succeeded,failed,canceled
```

默认方法直接注册真实 Python callable，并按能力分为以下命名空间：

- `<webui>.version.*`：各 WebUI 的版本、更新检查和仓库操作。
- `<webui>.environment.collect`：返回各 WebUI 的结构化环境信息报告，不在服务端写文件。
- `<webui>.snapshot.*`：各 WebUI 的快照操作。
- `<webui>.extension.*`：SD WebUI、ComfyUI 和 InvokeAI 的扩展操作。
- `<webui>.launch.*`：各 WebUI 的启动准备和参数发现。
- `<webui>.model.*`：各 WebUI 的文件模型、InvokeAI 注册模型和内置模型库操作。
- `<webui>.pytorch.*`：各 WebUI 的 PyTorch 目录、选择解析和重装操作。
- `package.*`、`pytorch.*`、`system.*`：与具体 WebUI 无关的公共能力。
- `hotpatcher.*`：Hotpatcher 配置和 runtime 操作。

其中 `<webui>` 是 `sd_webui`、`comfyui`、`fooocus`、`invokeai`、`sd_trainer`、`sd_scripts`、`qwen_tts_webui` 或 `rvc_next_webui`。只注册对应实现实际支持的能力；例如扩展 Registry 方法只存在于 `comfyui.extension.*`。

方法名已经确定具体 WebUI，因此不再传递 `webui_type`。参数结构完全跟随真实函数签名：普通参数直接平铺，真实函数本身使用 dataclass 等结构化对象时则由 schema 展示其子字段。

环境信息调用示例：

```json
{
  "method": "comfyui.environment.collect",
  "params": {
    "comfyui_path": "/path/to/ComfyUI",
    "include_packages": true
  }
}
```

```json
{
  "method": "comfyui.version.branches",
  "params": {
    "path": "/path/to/ComfyUI",
    "fetch": true
  }
}
```

方法的 `target`、参数类型、默认值和 schema 均在启动时从实际 callable 签名生成。服务器会在创建任务前拒绝缺失参数、未知参数及类型错误。完整方法集合以 `GET /api/v2/methods` 的运行时结果为准。

启动服务后可直接用 `curl` 查询和调用：

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/api/v2/methods
curl http://127.0.0.1:8765/api/v2/methods/comfyui.version.branches
curl -X POST http://127.0.0.1:8765/api/v2/call \
  -H 'Content-Type: application/json' \
  -d '{"method":"comfyui.version.branches","params":{"path":"/path/to/ComfyUI","fetch":true}}'
```

启用 `--token` 后，在每条受保护的请求中增加 `-H 'Authorization: Bearer <令牌>'`。

外部 Python GUI 可以使用内置客户端：

```python
from sd_webui_all_in_one.api_server import ApiClient

client = ApiClient("http://127.0.0.1:8765", token="")
print(client.health())
print(client.methods())
```

### 整合包资源管理
生成 AI 整合包下载器使用的远程资源列表。

#### 生成整合包资源列表
```bash
sd-webui-all-in-one self-manager portable list [选项]
```

高级选项：

- `--output <路径>`：输出 JSON 文件路径，默认输出到当前启动路径下的 `portable_list.json`。
- `--hf-repo-id <仓库>`：HuggingFace 仓库 ID。
- `--hf-repo-type <类型>`：HuggingFace 仓库类型，可选 `model`、`dataset`、`space`，默认 `model`。
- `--ms-repo-id <仓库>`：ModelScope 仓库 ID。
- `--ms-repo-type <类型>`：ModelScope 仓库类型，可选 `model`、`dataset`、`space`，默认 `model`。
- `--revision <版本>`：仓库分支、标签或提交哈希。
- `--hf-token <令牌>`：HuggingFace Token；未传时读取 `HF_TOKEN`。
- `--ms-token <令牌>`：ModelScope Token；未传时读取 `MODELSCOPE_API_TOKEN`。

至少需要配置 HuggingFace 或 ModelScope 中的一个下载源。整合包文件名必须使用
`<software>_<accelerator>-<signature>-<platform>-<版本或 nightly>.<扩展名>` 格式，其中
`accelerator` 可选 `cuda`、`rocm`、`xpu`、`mps`，`platform` 可选 `windows`、`linux`、
`macos`。输出资源按下载源、平台和软件分组：

```json
{
  "update_time": "2026-06-16T00:00:00Z",
  "resources": {
    "modelscope": {
      "windows": {
        "sd_webui_cuda": {
          "display_name": "Stable Diffusion WebUI (NVIDIA)",
          "description": "Stable Diffusion WebUI 的 NVIDIA 显卡整合包。",
          "stable": [
            {
              "filename": "sd_webui_cuda-licyk-windows-v1.0.0.7z",
              "path": "portable/sd_webui_cuda-licyk-windows-v1.0.0.7z",
              "url": "https://...",
              "signature": "licyk",
              "platform": "windows",
              "channel": "stable",
              "version": "1.0.0",
              "build_date": null,
              "extension": "7z"
            }
          ],
          "nightly": []
        }
      }
    }
  }
}
```

#### 上传整合包目录
```bash
sd-webui-all-in-one self-manager portable upload <upload_path> [选项]
```

位置参数：

- `<upload_path>`：要上传的本地目录；目录内相对路径会原样作为仓库内路径。

高级选项：

- `--hf-repo-id <仓库>`：HuggingFace 目标仓库 ID。
- `--hf-repo-type <类型>`：HuggingFace 仓库类型，可选 `model`、`dataset`、`space`，默认 `model`。
- `--ms-repo-id <仓库>`：ModelScope 目标仓库 ID。
- `--ms-repo-type <类型>`：ModelScope 仓库类型，可选 `model`、`dataset`、`space`，默认 `model`。
- `--revision <版本>`：上传目标分支、标签或提交哈希。
- `--path-in-repo <路径>`：仓库中的上传路径前缀，默认上传到仓库根目录。
- `--public`：仓库不存在并需要创建时设为公开仓库；默认创建私有仓库。
- `--threads <数量>`：单个目标仓库内部的上传线程数，默认 `1`。
- `--target-workers <数量>`：多个目标仓库之间的并发数，默认按已配置目标数量并发。
- `--hf-token <令牌>`：HuggingFace Token；未传时读取 `HF_TOKEN`。
- `--ms-token <令牌>`：ModelScope Token；未传时读取 `MODELSCOPE_API_TOKEN`。

至少需要配置 HuggingFace 或 ModelScope 中的一个目标。命令内部复用 `RepoManager` 的上传能力，会跳过远端已存在且 hash 相同的文件。

### Python 资源管理
下载 [python-build-standalone](https://github.com/astral-sh/python-build-standalone) 构建的 Python，重新打包后上传到 HuggingFace / ModelScope 仓库，并查询已上传的资源。安装器使用的 Python 即来自这些仓库。

资源在仓库中的路径为 `<path-in-repo>/<系统>/<架构>/<文件名>`，例如 `python/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip`。

仓库通用选项（`sync` 和 `list` 共用）：

- `--hf-repo-id <仓库>`：HuggingFace 仓库 ID，默认 `licyk/sd-webui-all-in-one`；传入空字符串或使用 `--no-hf` 时不使用。
- `--hf-repo-type <类型>`：HuggingFace 仓库类型，可选 `model`、`dataset`、`space`，默认 `model`。
- `--ms-repo-id <仓库>`：ModelScope 仓库 ID，默认 `licyks/sd-webui-all-in-one`；传入空字符串或使用 `--no-ms` 时不使用。
- `--ms-repo-type <类型>`：ModelScope 仓库类型，默认 `model`。
- `--revision <分支>`：仓库分支，默认使用仓库默认分支。
- `--path-in-repo <路径>`：仓库中的 Python 资源目录，默认 `python`。
- `--hf-token <令牌>`：HuggingFace Token；未传时读取 `HF_TOKEN`。
- `--ms-token <令牌>`：ModelScope Token；未传时读取 `MODELSCOPE_API_TOKEN`。

#### 下载、打包并上传
```bash
sd-webui-all-in-one self-manager python-standalone sync [选项]
```

命令会先读取目标仓库中已有的文件，只为缺失的部分创建任务：两个仓库都已有的文件跳过，只缺少其中一个仓库的文件只上传到缺失的仓库，本地输出目录中已打包过的文件直接上传。执行前会打印任务计划表，多线程执行时每个任务的日志带有不同颜色的标签。

Release 与构建选项：

- `--release-tag <标签>`：python-build-standalone 的 Release 标签，默认 `latest`；可用 `releases` 命令查看可选标签。
- `--source-repo <仓库>`：python-build-standalone 发布仓库，默认 `astral-sh/python-build-standalone`。
- `--github-api-url <地址>`：GitHub API 地址，默认 `https://api.github.com`。
- `--github-token <令牌>`：GitHub Token；未传时读取 `GITHUB_TOKEN`，用于避免 API 速率限制。
- `--versions <版本>`：逗号分隔的 Python 主次版本号，默认 `3.10,3.11,3.12,3.13,3.14`；每个版本取该 Release 中补丁版本最高的构建。
- `--platforms <平台>`：逗号分隔的平台，默认全部内置平台：`windows/amd64`、`windows/aarch64`、`linux/amd64`、`linux/aarch64`、`macos/amd64`、`macos/aarch64`。
- `--platform-map <系统/架构=三元组>`：添加或覆盖平台到构建目标三元组的映射，可重复使用，例如 `--platform-map linux/musl=x86_64-unknown-linux-musl`。
- `--variant <变体>`：构建变体，默认 `install_only`，也可使用 `install_only_stripped`、`freethreaded-install_only` 等。
- `--archive-format <格式>`：重新打包的格式，默认 `.zip`，可选 `.7z`、`.tar.gz`、`.tar.xz`、`.tar.zst` 等。压缩包根目录为 `python/`。

任务选项：

- `--no-upload`：只下载和打包，不读取仓库状态也不上传。
- `--public`：仓库不存在需要创建时设为公开仓库。
- `--force`：忽略仓库状态，强制重新下载、打包并上传全部任务。
- `--dry-run`：只打印任务计划表，不执行任务。
- `--workers <数量>`：同时执行的任务数，默认 `4`。
- `--upload-threads <数量>`：单个仓库的上传线程数，默认 `1`。同一仓库的上传会依次进行，避免并发提交冲突。
- `--download-tool <工具>`：下载工具，可选 `aria2`、`requests`、`urllib`，默认 `requests`。
- `--download-split <数量>`：单个文件下载分片数，默认 `5`。
- `--no-verify-hash`：不校验下载文件的 SHA256。
- `--output-dir <路径>`：打包结果保存目录，默认 `./python_dist`；目录结构与仓库中的路径相同，之后运行时已打包过的文件可直接上传。
- `--temp-output`：打包结果只保存在临时目录中，每个任务上传完成后立即删除，不写入 `--output-dir`；需要至少一个上传目标，不能与 `--output-dir`、`--no-upload` 同时使用。适合磁盘空间有限的环境，报告中仍会记录文件大小和 SHA256。
- `--work-dir <路径>`：临时工作目录，默认使用系统临时目录。
- `--keep-temp`：保留临时工作目录中的文件；与 `--temp-output` 同时使用时打包结果也会保留在临时工作目录中。
- `--progress` / `--no-progress`：是否显示进度条；默认只在单任务并发且在终端中运行时显示。
- `--no-color`：不为任务日志标签着色。

报告选项：

- `--report-markdown <路径>`：任务完成后输出 Markdown 报告，`-` 表示标准输出。
- `--report-json <路径>`：任务完成后输出 JSON 报告，`-` 表示标准输出。

报告中每个资源包含类型、名称、版本、平台、变体、大小、SHA256、执行结果和各仓库的下载链接。有任务失败时退出码为 `1`，任务被中断时为 `130`。

```json
{
  "type": "python-standalone",
  "generated_at": "2026-09-29T00:00:00Z",
  "source_repo": "astral-sh/python-build-standalone",
  "release_tag": "20260924",
  "targets": ["HuggingFace:licyk/sd-webui-all-in-one", "ModelScope:licyks/sd-webui-all-in-one"],
  "summary": {"total": 29, "success": 29, "failed": 0, "skipped": 0, "cancelled": 0},
  "resources": [
    {
      "type": "python-standalone",
      "name": "cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip",
      "implementation": "cpython",
      "version": "3.12.14",
      "minor": "3.12",
      "build_date": "20260924",
      "platform": "linux",
      "arch": "amd64",
      "triple": "x86_64-unknown-linux-gnu",
      "variant": "install_only",
      "archive_format": ".zip",
      "path": "python/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip",
      "size": 145392215,
      "sha256": "...",
      "urls": {
        "huggingface": "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/amd64/...",
        "modelscope": "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/amd64/..."
      },
      "action": "build",
      "status": "success",
      "uploaded_to": ["huggingface", "modelscope"],
      "error": null,
      "duration": 17.1
    }
  ]
}
```

#### 查询已上传的资源
```bash
sd-webui-all-in-one self-manager python-standalone list [选项]
```

默认只显示最新的构建：每个平台、Python 主次版本、变体和压缩包格式的组合只保留构建日期最新的一个。

- `--all`：显示全部构建。
- `--versions <版本>`：逗号分隔的主次版本号（如 `3.12`）或完整版本号（如 `3.12.14`）。
- `--platforms <平台>`：逗号分隔的平台（如 `linux/amd64`）或系统（如 `linux`）。
- `--variants <变体>`：逗号分隔的构建变体。
- `--archive-formats <格式>`：逗号分隔的压缩包格式，如 `.zip,.tar.gz`。
- `--build-date <日期>`：只显示该构建日期（即 Release 标签）的资源。
- `--platform-map <系统/架构=三元组>`：用于解析自定义平台的文件名。
- `--format <格式>`：输出格式，可选 `table`、`markdown`、`json`，默认 `table`。
- `--output <路径>`：输出到文件，默认输出到标准输出。

JSON 输出包含 `generated_at`、`sources`、`latest_only` 和 `resources`，`resources` 中每项的字段与同步报告相同（不含执行结果字段）。下载链接直接按仓库地址拼接，HuggingFace 地址可通过 `HF_ENDPOINT` 环境变量修改。

#### 查看 python-build-standalone Release
```bash
sd-webui-all-in-one self-manager python-standalone releases [选项]
```

- `--limit <数量>`：显示数量，默认 `10`。
- `--format <格式>`：输出格式，可选 `table`、`json`，默认 `table`。
- `--output <路径>`：输出到文件，默认输出到标准输出。
- `--source-repo`、`--github-api-url`、`--github-token`：与 `sync` 相同。

!!! info
    仓库中的 GitHub Actions 工作流 `Sync Python Standalone` 只能手动触发，会使用 `--temp-output` 执行 `sync` 并把 Markdown 报告和最新资源列表写入运行摘要，JSON 报告作为构件上传。

### HuggingFace / ModelScope 仓库管理
调用 Python 内核中的 `RepoManager` 管理 HuggingFace / ModelScope 仓库文件。

通用选项：

- `<api>`：仓库 API 类型，可选 `huggingface`、`modelscope`。
- `--repo-type <类型>`：仓库类型，可选 `model`、`dataset`、`space`，默认 `model`。
- `--revision <版本>`：仓库分支、标签或提交哈希。
- `--hf-token <令牌>`：HuggingFace Token；未传时读取 `HF_TOKEN`。
- `--ms-token <令牌>`：ModelScope Token；未传时读取 `MODELSCOPE_API_TOKEN`。

ModelScope 对 `space` 的支持受 `RepoManager` 当前实现限制；不支持的仓库类型会按现有逻辑报错。

#### 获取仓库文件列表
```bash
sd-webui-all-in-one self-manager repo list <api> <repo_id> [选项]
```

高级选项：

- `--format <格式>`：输出格式，可选 `json`、`text`，默认 `json`。`text` 模式每行输出一个仓库文件路径。

#### 获取仓库文件元数据
```bash
sd-webui-all-in-one self-manager repo metadata <api> <repo_id> [选项]
```

高级选项：

- `--format <格式>`：输出格式，可选 `json`、`text`，默认 `json`。
- `--include-dirs`：包含目录条目。
- `--include-raw`：包含第三方库原始返回。

#### 获取仓库文件下载地址
```bash
sd-webui-all-in-one self-manager repo url <api> <repo_id> <file_path> [选项]
```

位置参数：

- `<file_path>`：仓库中的文件路径。

#### 检查或创建仓库
```bash
sd-webui-all-in-one self-manager repo check <api> <repo_id> [选项]
```

高级选项：

- `--public`：仓库不存在并需要创建时设为公开仓库；默认创建私有仓库。

#### 上传本地目录到仓库
```bash
sd-webui-all-in-one self-manager repo upload <api> <repo_id> <upload_path> [选项]
```

位置参数：

- `<upload_path>`：要上传的本地目录。

高级选项：

- `--path-in-repo <路径>`：仓库中的上传路径前缀，默认上传到仓库根目录。
- `--public`：仓库不存在并需要创建时设为公开仓库；默认创建私有仓库。
- `--threads <数量>`：上传线程数，默认 `1`。

#### 从仓库下载文件
```bash
sd-webui-all-in-one self-manager repo download <api> <repo_id> <local_dir> [选项]
```

位置参数：

- `<local_dir>`：本地下载目录。

高级选项：

- `--folder <路径>`：只下载指定路径前缀或单个文件。
- `--threads <数量>`：下载线程数，默认 `8`。

#### 镜像仓库文件
```bash
sd-webui-all-in-one self-manager repo mirror <src_api> <dst_api> <src_repo_id> <dst_repo_id> [选项]
```

高级选项：

- `--src-repo-type <类型>`：源仓库类型，默认 `model`。
- `--dst-repo-type <类型>`：目标仓库类型，默认 `model`。
- `--public`：目标仓库不存在并需要创建时设为公开仓库；默认创建私有仓库。
- `--threads <数量>`：镜像线程数，默认 `1`。
- `--retry-times <次数>`：单个文件镜像失败后的重试次数。
- `--fast-download`：使用内置 downloader 先获取源文件下载地址再下载。
- `--download-tool <工具>`：启用 `--fast-download` 时使用的下载工具，可选 `aria2`、`requests`、`urllib`，默认 `requests`。
- `--download-split <数量>`：启用 `--fast-download` 时传给下载器的分片数，默认 `5`。
- `--no-download-progress`：禁用 `--fast-download` 的下载进度条。

### 下载文件
调用 Python 内核中的 `downloader.download_file()` 下载任意文件。
```bash
sd-webui-all-in-one self-manager download-file <下载链接> [选项]
```

高级选项：

- `--path <路径>`：文件下载路径，默认当前目录。
- `--save-name <文件名>`：文件保存名称，默认从 URL 中提取。
- `--downloader <工具>`：下载工具，可选 `aria2`、`requests`、`urllib`，默认 `requests`。
- `--no-progress`：禁用下载进度条。
- `--split <数量>`：aria2 风格的单文件最大分割数，默认 `32`。
- `--max-connection-per-server <数量>`：aria2 风格的单服务器最大连接数，默认 `16`。
- `--min-split-size <字节>`：aria2 风格的最小切分大小，默认 `20971520`。
- `--piece-length <字节>`：aria2 风格的 piece 大小，默认 `1048576`。
- `--allow-piece-length-change`：控制文件中的 piece 大小变化时，转换已完成 bitfield 并丢弃 in-flight 进度。
- `--continue`：没有匹配控制文件时，从已有文件继续下载；匹配的控制文件会自动恢复。
- `--max-tries <次数>`：单个分片最大尝试次数，默认 `5`。
- `--retry-wait <秒>`：HTTP 503 重试前等待秒数，默认 `0`。
- `--conditional-get`：已有本地文件时发送 `If-Modified-Since`，远端返回 `304` 时复用本地文件。
- `--no-remote-time`：禁用按远端 `Last-Modified` 设置本地文件时间；默认启用。
- `--no-always-resume`：允许在续传失败达到阈值后丢弃已有进度并从头下载；默认不允许，以免静默覆盖断点。
- `--max-resume-failure-tries <次数>`：允许重头下载前的续传失败阈值，默认 `0`，表示所有 URI 都无法续传后重头下载；仅在 `--no-always-resume` 时生效。
- `--existing-file <策略>`：已有正式文件的处理方式，可选 `reuse`（不联网直接复用）、`verify`（按远端大小或哈希校验）、`resume`（作为顺序断点继续，默认）、`overwrite`（原子覆盖）和 `rename`（生成新名称）。默认从旧的“文件存在即成功”改为 `resume`，因此残缺文件会继续下载，而不会直接误报成功。
- `--hash <十六进制值>`：校验下载结果，可传完整哈希或前缀；显式值优先于服务端 Digest。
- `--hash-algorithm <算法>`：`--hash` 使用的算法，可选 `sha1`、`sha256`、`sha512`，默认 `sha256`。
- `--connect-timeout <秒>` / `--read-timeout <秒>`：分别控制建立连接和单次读取停滞，默认均为 `60`。
- `--lowest-speed-limit <B/s>` / `--lowest-speed-time <秒>`：在给定窗口内持续低于最低速度时重新调度连接；任一值为 `0` 时禁用，默认禁用。

`requests` 和 `aria2` 后端共享上述 `32/16/20 MiB/1 MiB` 任务默认值。`aria2.conf` 也使用相同的连接和分段默认值；通过统一下载入口发起任务时，RPC 的单任务选项会显式覆盖配置文件中的同名值。较高连接数可提升大文件吞吐，但服务端可能据此限流或返回 `429`；小于 `min-split-size` 的文件不会使用全部分段。

### 压缩包解压和压缩
调用 Python 内核中的压缩包工具解压或创建压缩包。

#### 解压压缩包
```bash
sd-webui-all-in-one self-manager archive extract <压缩包路径> --output <输出路径>
```

位置参数：

- `<压缩包路径>`：要解压的压缩包。

高级选项：

- `--output <输出路径>`：解压目标目录。
- `--no-progress`：禁用解压进度条。

#### 创建压缩包
```bash
sd-webui-all-in-one self-manager archive compress <源路径...> --output <压缩包路径>
```

位置参数：

- `<源路径...>`：要压缩的一个或多个文件 / 目录。

高级选项：

- `--output <压缩包路径>`：压缩包保存路径，文件扩展名决定实际使用的压缩格式。
- `--no-progress`：禁用压缩进度条。

支持解压的格式：`.zip`、`.7z`、`.rar`、`.tar`、`.tar.lzma`、`.tar.bz2`、`.tar.gz`、`.tar.xz`、`.tar.zst`、`.tgz`、`.tbz2`、`.txz`、`.tlz`。

支持创建的格式：`.zip`、`.7z`、`.tar`、`.tar.lzma`、`.tar.bz2`、`.tar.gz`、`.tar.xz`、`.tar.zst`、`.tgz`、`.tbz2`、`.txz`、`.tlz`。

### 启动内网穿透
启动内网穿透服务，将本地端口映射到公网。
```bash
sd-webui-all-in-one self-manager start-tunnel <端口> [选项]
```

位置参数：

- `<端口>`：要进行端口映射的本地端口号。

高级选项：

- `--workspace <路径>`：工作区路径，默认为当前目录。
- `--ngrok`：启用 Ngrok 内网穿透。
- `--ngrok-token <令牌>`：Ngrok 账号令牌。
- `--cloudflare`：启用 CloudFlare 内网穿透。
- `--remote-moe`：启用 remote.moe 内网穿透。
- `--localhost-run`：启用 localhost.run 内网穿透。
- `--gradio`：启用 Gradio 内网穿透。
- `--pinggy-io`：启用 pinggy.io 内网穿透。
- `--zrok`：启用 Zrok 内网穿透。
- `--zrok-token <令牌>`：Zrok 账号令牌。

*注：启动后会显示本地和公网地址，按 Ctrl + C 停止服务。*
