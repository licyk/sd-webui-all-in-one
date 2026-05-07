# CLI - SD WebUI All In One Manager

## SD WebUI All In One Manager
用于管理 `sd-webui-all-in-one` 自身的组件和补丁。

### 检查 Aria2
检查 Aria2 是否需要更新。
```bash
sd-webui-all-in-one self-manager check-aria2
```
*注：当退出代码非 0 时说明需要更新。*

### 检查并更新 Pip
```bash
sd-webui-all-in-one self-manager check-pip [选项]
```

高级选项：

- `--no-pypi-mirror`：不使用国内 PyPI 镜像源。

### 检查并更新 uv
```bash
sd-webui-all-in-one self-manager check-uv [选项]
```

高级选项：

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
sd-webui-all-in-one self-manager get-proxy
```

### 获取适合当前系统的 CUDA 内存分配器配置
```bash
sd-webui-all-in-one self-manager get-cuda-malloc
```

### 获取 SD WebUI All In One 使用的环境变量配置
```bash
sd-webui-all-in-one self-manager get-env-config
```

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
