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

### 获取补丁路径
获取 `SD WebUI All In One` 补丁的存储路径。
```bash
sd-webui-all-in-one self-manager get-patcher
```

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
