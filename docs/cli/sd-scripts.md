# CLI - SD Scripts

## SD Scripts
SD Scripts 是一组用于训练和处理 Stable Diffusion 模型的脚本集合。

### 安装 SD Scripts
```bash
sd-webui-all-in-one sd-scripts install [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录，默认为配置文件中的路径。
  - `--pytorch-mirror-type <类型>`: 设置使用的 PyTorch 镜像源类型。
  - `--custom-pytorch-package <包名>`: 自定义 PyTorch 软件包版本声明。
  - `--custom-xformers-package <包名>`: 自定义 xFormers 软件包版本声明。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--install-branch <分支>`: 安装的 SD Scripts 分支。
  - `--no-pre-download-model`: 禁用预下载模型。
  - `--model-resource`: 模型下载源类型 (默认: `modelscope`)。

### 更新 SD Scripts
```bash
sd-webui-all-in-one sd-scripts update [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 检查运行环境
```bash
sd-webui-all-in-one sd-scripts check-env [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--no-uv`: 不使用 uv。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

### 切换分支
```bash
sd-webui-all-in-one sd-scripts switch --branch <分支名> [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--branch <分支名>`: (必填) 要切换的分支。

### 版本管理 GUI
```bash
sd-webui-all-in-one sd-scripts gui version-manager [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 模型管理

#### 从模型库安装模型
```bash
sd-webui-all-in-one sd-scripts model install-library [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

#### 从链接安装模型
```bash
sd-webui-all-in-one sd-scripts model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

#### 列出模型
```bash
sd-webui-all-in-one sd-scripts model list [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。

#### 卸载模型
```bash
sd-webui-all-in-one sd-scripts model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

### 重装 PyTorch
```bash
sd-webui-all-in-one sd-scripts reinstall-pytorch [选项]
```

- **高级选项**:
  - `--name <名称>`: PyTorch 版本组合名称。
  - `--index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。
