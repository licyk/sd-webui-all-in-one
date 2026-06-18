# CLI - SD Trainer

## SD Trainer
SD Trainer 是一款用于训练 Stable Diffusion 模型的工具。

!!! note
    本页中包含镜像源设置的子命令默认启用自动镜像源选择，并支持 `--no-auto-mirror`。自动模式会根据网络检测结果强制覆盖 PyPI、Github、HuggingFace 和模型下载源参数；需要手动调整 `--no-*mirror`、`--custom-*`、`--model-resource` 或 `--source` 时，请同时添加 `--no-auto-mirror`。

### 安装 SD Trainer
```bash
sd-webui-all-in-one sd-trainer install [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录，默认为配置文件中的路径。
  - `--pytorch-mirror-type <类型>`: 设置使用的 PyTorch 镜像源类型。
  - `--custom-pytorch-package <包名>`: 自定义 PyTorch 软件包版本声明。
  - `--custom-xformers-package <包名>`: 自定义 xFormers 软件包版本声明。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--install-branch <分支>`: 安装的 SD Trainer 分支。
  - `--no-pre-download-model`: 禁用预下载模型。
  - `--model-resource`: 模型下载源类型 (默认: `modelscope`)。

### 更新 SD Trainer
```bash
sd-webui-all-in-one sd-trainer update [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 生成环境快照
```bash
sd-webui-all-in-one sd-trainer snapshot [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--output <路径>`: 输出目录路径；未传时保存到默认快照目录并自动生成带时间戳的文件名。
  - `--no-packages`: 不记录当前 Python 环境已安装软件包。

### 恢复环境快照
```bash
sd-webui-all-in-one sd-trainer restore <快照文件> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--prune-packages`: 卸载快照外 Python 软件包，受保护的管理器和基础安装工具不会卸载。
  - `--prune-extensions`: 删除快照外扩展。
  - `--force-git-reset`: 允许覆盖 Git 仓库未提交变更。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 检查运行环境
```bash
sd-webui-all-in-one sd-trainer check-env [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--no-uv`: 不使用 uv。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

### 切换分支
```bash
sd-webui-all-in-one sd-trainer switch --branch <分支名> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--branch <分支名>`: (必填) 要切换的分支。

### 启动 SD Trainer
```bash
sd-webui-all-in-one sd-trainer launch [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--launch-args <参数>`: 启动参数 (请使用引号包裹，例如 `"--theme dark"`)。
  - `--no-hf-mirror`: 禁用 HuggingFace 镜像源。
  - `--custom-hf-mirror <URL>`: 自定义 HuggingFace 镜像源。
  - `--no-github-mirror`: 禁用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 禁用 PyPI 镜像源。
  - `--no-cuda-malloc`: 禁用 CUDA Malloc 优化。
  - `--no-uv`: 不使用 uv。
  - `--no-check-env`: 不检查运行环境完整性。
  - `--no-hotpatcher`: 禁用 Hotpatcher 补丁系统注入，默认启用。
  - `--hotpatcher-runtime`: 启用 Hotpatcher runtime host 连接，默认只做本地补丁注入。
  - `--hotpatcher-config <路径>`: Hotpatcher 配置文件路径。未指定时使用默认配置路径或内置默认配置。
  - `--hotpatcher-port <端口>`: Hotpatcher runtime 通信端口，仅在 `--hotpatcher-runtime` 启用时生效。

### 版本管理 GUI
```bash
sd-webui-all-in-one sd-trainer gui version-manager [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 快照管理 GUI
```bash
sd-webui-all-in-one sd-trainer gui snapshot-manager [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--snapshot-dir <路径>`: 快照目录。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 模型管理

#### 从模型库安装模型
```bash
sd-webui-all-in-one sd-trainer model install-library [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `requests`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

#### 从链接安装模型
```bash
sd-webui-all-in-one sd-trainer model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `requests`)。

#### 列出模型
```bash
sd-webui-all-in-one sd-trainer model list [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。

#### 卸载模型
```bash
sd-webui-all-in-one sd-trainer model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

### 重装 PyTorch
```bash
sd-webui-all-in-one sd-trainer reinstall-pytorch [选项]
```

- **高级选项**:
  - `--name <名称>`: PyTorch 版本组合名称。
  - `--index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。
