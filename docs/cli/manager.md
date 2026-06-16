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

- `--output <路径>`：输出配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。
- `--force`：覆盖已有配置文件。

#### 规范化配置
读取配置文件并补齐缺失的默认字段。

```bash
sd-webui-all-in-one self-manager patcher normalize-config --config <路径> [选项]
```

高级选项：

- `--config <路径>`：配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。
- `--write-back`：将规范化后的配置写回文件；不加时输出 JSON 到终端。

#### 应用配置
把配置应用到当前命令进程，主要用于验证配置和调试补丁系统。

```bash
sd-webui-all-in-one self-manager patcher apply-config --config <路径>
```

高级选项：

- `--config <路径>`：配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。

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

- `--config <路径>`：配置文件路径，默认是 `SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH/patcher_config.json`。
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

至少需要配置 HuggingFace 或 ModelScope 中的一个下载源。输出结构为新版 `resources/update_time` 格式：

```json
{
  "update_time": "2026-06-16T00:00:00Z",
  "resources": {
    "modelscope": {
      "sd_webui": {
        "display_name": "Stable Diffusion WebUI",
        "description": "上手简单，操作方便，适合入门使用。",
        "stable": [
          {
            "filename": "sd_webui-licyk-v1.0.0.7z",
            "path": "portable/sd_webui-licyk-v1.0.0.7z",
            "url": "https://...",
            "signature": "licyk",
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
- `--public`：仓库不存在并需要创建时设为公开仓库；默认创建私有仓库。
- `--threads <数量>`：单个目标仓库内部的上传线程数，默认 `1`。
- `--target-workers <数量>`：多个目标仓库之间的并发数，默认按已配置目标数量并发。
- `--hf-token <令牌>`：HuggingFace Token；未传时读取 `HF_TOKEN`。
- `--ms-token <令牌>`：ModelScope Token；未传时读取 `MODELSCOPE_API_TOKEN`。

至少需要配置 HuggingFace 或 ModelScope 中的一个目标。命令内部复用 `RepoManager` 的上传能力，会跳过远端已存在且 hash 相同的文件。

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
- `--split <数量>`：aria2 风格的单文件最大分割数，默认 `5`。
- `--max-connection-per-server <数量>`：aria2 风格的单服务器最大连接数，默认 `1`；单 URL 默认不会并发多连接。
- `--min-split-size <字节>`：aria2 风格的最小切分大小，默认 `20971520`。
- `--piece-length <字节>`：aria2 风格的 piece 大小，默认 `1048576`。
- `--allow-piece-length-change`：控制文件中的 piece 大小变化时，转换已完成 bitfield 并丢弃 in-flight 进度。
- `--continue`：没有匹配控制文件时，从已有文件继续下载；匹配的控制文件会自动恢复。
- `--max-tries <次数>`：单个分片最大尝试次数，默认 `5`。
- `--retry-wait <秒>`：HTTP 503 重试前等待秒数，默认 `0`。
- `--conditional-get`：已有本地文件时发送 `If-Modified-Since`，远端返回 `304` 时复用本地文件。
- `--no-remote-time`：禁用按远端 `Last-Modified` 设置本地文件时间；默认启用。

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
