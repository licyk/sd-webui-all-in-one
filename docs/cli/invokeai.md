# CLI - InvokeAI

## InvokeAI
InvokeAI 是一款功能强大的 Stable Diffusion 创意引擎。

### 安装 InvokeAI
```bash
sd-webui-all-in-one invokeai install [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录，默认为配置文件中的路径。
  - `--device-type <类型>`: 设备类型 (`cuda`, `rocm`, `cpu`, `mps`)。
  - `--version <版本>`: 自定义安装版本。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-pre-download-model`: 禁用预下载模型。
  - `--model-resource`: 模型下载源类型 (默认: `modelscope`)。

### 更新 InvokeAI
```bash
sd-webui-all-in-one invokeai update [选项]
```

- **高级选项**:
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。

### 检查运行环境
```bash
sd-webui-all-in-one invokeai check-env [选项]
```

- **高级选项**:
  - `--no-uv`: 不使用 uv。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

### 启动 InvokeAI
```bash
sd-webui-all-in-one invokeai launch [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--launch-args <参数>`: 启动参数 (请使用引号包裹，例如 `"--theme dark"`)。
  - `--no-hf-mirror`: 禁用 HuggingFace 镜像源。
  - `--custom-hf-mirror <URL>`: 自定义 HuggingFace 镜像源。
  - `--no-pypi-mirror`: 禁用 PyPI 镜像源。
  - `--no-cuda-malloc`: 禁用 CUDA Malloc 优化。
  - `--no-uv`: 不使用 uv。
  - `--no-check-env`: 不检查运行环境完整性。
  - `--hotpatcher`: 启用 Hotpatcher 补丁系统注入，默认禁用。
  - `--hotpatcher-config <路径>`: Hotpatcher 配置文件路径。未指定时使用默认配置路径或内置默认配置。
  - `--hotpatcher-port <端口>`: Hotpatcher runtime 通信端口。

### 版本管理 GUI
```bash
sd-webui-all-in-one invokeai gui version-manager [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--no-pypi-mirror`: 不使用 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 扩展管理 (Custom Node)

#### 安装扩展
```bash
sd-webui-all-in-one invokeai custom-node install --url <链接> [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--url <链接>`: (必填) 扩展下载链接。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

#### 设置扩展状态
```bash
sd-webui-all-in-one invokeai custom-node status --name <名称> [--enable|--disable] [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--name <名称>`: (必填) 扩展名称。
  - `--enable`: 启用扩展。
  - `--disable`: 禁用扩展。

#### 列出扩展
```bash
sd-webui-all-in-one invokeai custom-node list [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。

#### 更新扩展
```bash
sd-webui-all-in-one invokeai custom-node update [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

#### 卸载扩展
```bash
sd-webui-all-in-one invokeai custom-node uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--name <名称>`: (必填) 扩展名称。

### 模型管理

#### 从模型库安装模型
```bash
sd-webui-all-in-one invokeai model install-library [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

#### 从链接安装模型
```bash
sd-webui-all-in-one invokeai model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

#### 列出模型
```bash
sd-webui-all-in-one invokeai model list
```

#### 卸载模型
```bash
sd-webui-all-in-one invokeai model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--name <名称>`: (必填) 模型名称。
  - `--interactive`: 启用交互模式。

### 重装 PyTorch
```bash
sd-webui-all-in-one invokeai reinstall-pytorch [选项]
```

- **高级选项**:
  - `--device-type <类型>`: 设备类型 (`cuda`, `rocm`, `cpu`, `mps`)。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。
