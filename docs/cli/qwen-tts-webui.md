# CLI - Qwen TTS WebUI

## Qwen TTS WebUI
Qwen TTS WebUI 是一款基于 Qwen 模型的文本转语音软件。

!!! note
    本页中包含镜像源设置的子命令默认启用自动镜像源选择，并支持 `--no-auto-mirror`。自动模式会根据网络检测结果强制覆盖 PyPI、Github、HuggingFace 和模型下载源参数；需要手动调整 `--no-*mirror`、`--custom-*`、`--model-resource` 或 `--source` 时，请同时添加 `--no-auto-mirror`。

### 安装 Qwen TTS WebUI
```bash
sd-webui-all-in-one qwen-tts-webui install [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录，默认为配置文件中的路径。
  - `--pytorch-mirror-type <类型>`: 设置使用的 PyTorch 镜像源类型。
  - `--custom-pytorch-package <包名>`: 自定义 PyTorch 软件包版本声明。
  - `--custom-xformers-package <包名>`: 自定义 xFormers 软件包版本声明。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--model-resource`: 默认配置资源来源，用于选择生成的 `config.json` 预设 (默认: `modelscope`)。

### 更新 Qwen TTS WebUI
```bash
sd-webui-all-in-one qwen-tts-webui update [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 生成环境快照
```bash
sd-webui-all-in-one qwen-tts-webui snapshot [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--output <路径>`: 输出目录路径；未传时保存到默认快照目录并自动生成带时间戳的文件名。
  - `--no-packages`: 不记录当前 Python 环境已安装软件包。

### 恢复环境快照
```bash
sd-webui-all-in-one qwen-tts-webui restore <快照文件> [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--prune-packages`: 卸载快照外 Python 软件包，受保护的管理器和基础安装工具不会卸载。
  - `--prune-extensions`: 删除快照外扩展。
  - `--force-git-reset`: 允许覆盖 Git 仓库未提交变更。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 检查运行环境
```bash
sd-webui-all-in-one qwen-tts-webui check-env [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--no-uv`: 不使用 uv。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

### 启动 Qwen TTS WebUI
```bash
sd-webui-all-in-one qwen-tts-webui launch [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--launch-args <参数>`: 启动参数 (请使用引号包裹，例如 `"--theme dark"`)。
  - `--no-hf-mirror`: 禁用 HuggingFace 镜像源。
  - `--custom-hf-mirror <URL>`: 自定义 HuggingFace 镜像源。
  - `--no-github-mirror`: 禁用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 禁用 PyPI 镜像源。
  - `--no-cuda-malloc`: 禁用 CUDA Malloc 优化。
  - `--no-check-env`: 不检查运行环境完整性。
  - `--no-hotpatcher`: 禁用 Hotpatcher 补丁系统注入，默认启用。
  - `--hotpatcher-runtime`: 启用 Hotpatcher runtime host 连接，默认只做本地补丁注入。
  - `--hotpatcher-config <路径>`: Hotpatcher 配置文件路径。未指定时使用默认配置路径或内置默认配置。
  - `--hotpatcher-port <端口>`: Hotpatcher runtime 通信端口，仅在 `--hotpatcher-runtime` 启用时生效。

### 版本管理 GUI
```bash
sd-webui-all-in-one qwen-tts-webui gui version-manager [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 快照管理 GUI
```bash
sd-webui-all-in-one qwen-tts-webui gui snapshot-manager [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--snapshot-dir <路径>`: 快照目录。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 重装 PyTorch
```bash
sd-webui-all-in-one qwen-tts-webui reinstall-pytorch [选项]
```

- **高级选项**:
  - `--name <名称>`: PyTorch 版本组合名称。
  - `--index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。
