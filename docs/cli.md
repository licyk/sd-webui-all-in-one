<div align="center">

# SD WebUI ALl In One CLI

_✨小巧，强大的命令工具_
  <p align="center">
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pypi-release.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pypi-release.yml/badge.svg" alt="PyPI Release">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml/badge.svg" alt="Ruff Lint">
    </a>
    <a href="https://pypi.org/project/sd-webui-all-in-one" style="margin: 2px;">
      <img src="https://img.shields.io/pypi/v/sd-webui-all-in-one" alt="PyPI">
    </a>
    <a href="https://pypi.org/project/sd-webui-all-in-one" style="margin: 2px;">
      <img src="https://img.shields.io/pypi/pyversions/sd-webui-all-in-one.svg" alt="Python Version">
    </a>
  </p>

</div>

- [SD WebUI ALl In One CLI](#sd-webui-all-in-one-cli)
- [简介](#简介)
- [安装](#安装)
- [基础使用](#基础使用)
- [Stable Diffusion WebUI](#stable-diffusion-webui)
  - [安装 Stable Diffusion WebUI](#安装-stable-diffusion-webui)
  - [更新 Stable Diffusion WebUI](#更新-stable-diffusion-webui)
  - [检查运行环境](#检查运行环境)
  - [切换分支](#切换分支)
  - [启动 Stable Diffusion WebUI](#启动-stable-diffusion-webui)
  - [扩展管理](#扩展管理)
    - [安装扩展](#安装扩展)
    - [设置扩展状态](#设置扩展状态)
    - [列出扩展](#列出扩展)
    - [更新扩展](#更新扩展)
    - [卸载扩展](#卸载扩展)
  - [模型管理](#模型管理)
    - [从模型库安装模型](#从模型库安装模型)
    - [从链接安装模型](#从链接安装模型)
    - [列出模型](#列出模型)
    - [卸载模型](#卸载模型)
  - [重装 PyTorch](#重装-pytorch)
- [ComfyUI](#comfyui)
  - [安装 ComfyUI](#安装-comfyui)
  - [更新 ComfyUI](#更新-comfyui)
  - [检查运行环境](#检查运行环境-1)
  - [启动 ComfyUI](#启动-comfyui)
  - [扩展管理 (Custom Node)](#扩展管理-custom-node)
    - [安装扩展](#安装扩展-1)
    - [设置扩展状态](#设置扩展状态-1)
    - [列出扩展](#列出扩展-1)
    - [更新扩展](#更新扩展-1)
    - [卸载扩展](#卸载扩展-1)
  - [模型管理](#模型管理-1)
    - [从模型库安装模型](#从模型库安装模型-1)
    - [从链接安装模型](#从链接安装模型-1)
    - [列出模型](#列出模型-1)
    - [卸载模型](#卸载模型-1)
  - [重装 PyTorch](#重装-pytorch-1)
- [Fooocus](#fooocus)
  - [安装 Fooocus](#安装-fooocus)
  - [更新 Fooocus](#更新-fooocus)
  - [检查运行环境](#检查运行环境-2)
  - [切换分支](#切换分支-1)
  - [启动 Fooocus](#启动-fooocus)
  - [模型管理](#模型管理-2)
    - [从模型库安装模型](#从模型库安装模型-2)
    - [从链接安装模型](#从链接安装模型-2)
    - [列出模型](#列出模型-2)
    - [卸载模型](#卸载模型-2)
  - [重装 PyTorch](#重装-pytorch-2)
- [InvokeAI](#invokeai)
  - [安装 InvokeAI](#安装-invokeai)
  - [更新 InvokeAI](#更新-invokeai)
  - [检查运行环境](#检查运行环境-3)
  - [启动 InvokeAI](#启动-invokeai)
  - [扩展管理 (Custom Node)](#扩展管理-custom-node-1)
    - [安装扩展](#安装扩展-2)
    - [设置扩展状态](#设置扩展状态-2)
    - [列出扩展](#列出扩展-2)
    - [更新扩展](#更新扩展-2)
    - [卸载扩展](#卸载扩展-2)
  - [模型管理](#模型管理-3)
    - [从模型库安装模型](#从模型库安装模型-3)
    - [从链接安装模型](#从链接安装模型-3)
    - [列出模型](#列出模型-3)
    - [卸载模型](#卸载模型-3)
  - [重装 PyTorch](#重装-pytorch-3)
- [Qwen TTS WebUI](#qwen-tts-webui)
  - [安装 Qwen TTS WebUI](#安装-qwen-tts-webui)
  - [更新 Qwen TTS WebUI](#更新-qwen-tts-webui)
  - [检查运行环境](#检查运行环境-4)
  - [启动 Qwen TTS WebUI](#启动-qwen-tts-webui)
  - [重装 PyTorch](#重装-pytorch-4)
- [SD Trainer](#sd-trainer)
  - [安装 SD Trainer](#安装-sd-trainer)
  - [更新 SD Trainer](#更新-sd-trainer)
  - [检查运行环境](#检查运行环境-5)
  - [切换分支](#切换分支-2)
  - [启动 SD Trainer](#启动-sd-trainer)
  - [模型管理](#模型管理-4)
    - [从模型库安装模型](#从模型库安装模型-4)
    - [从链接安装模型](#从链接安装模型-4)
    - [列出模型](#列出模型-4)
    - [卸载模型](#卸载模型-4)
  - [重装 PyTorch](#重装-pytorch-5)
- [SD Scripts](#sd-scripts)
  - [安装 SD Scripts](#安装-sd-scripts)
  - [更新 SD Scripts](#更新-sd-scripts)
  - [检查运行环境](#检查运行环境-6)
  - [切换分支](#切换分支-3)
  - [模型管理](#模型管理-5)
    - [从模型库安装模型](#从模型库安装模型-5)
    - [从链接安装模型](#从链接安装模型-5)
    - [列出模型](#列出模型-5)
    - [卸载模型](#卸载模型-5)
  - [重装 PyTorch](#重装-pytorch-6)
- [SD WebUI All In One Manager](#sd-webui-all-in-one-manager)
  - [检查 Aria2](#检查-aria2)
  - [检查并更新 Pip](#检查并更新-pip)
  - [检查并更新 uv](#检查并更新-uv)
  - [获取补丁路径](#获取补丁路径)
- [SD WebUI All In One 环境变量配置](#sd-webui-all-in-one-环境变量配置)
  - [基础配置](#基础配置)
  - [软件根目录配置](#软件根目录配置)

***

# 简介
SD WebUI All Ine One CLI 提供了一个强大的命令行界面，用于管理各种 AI 绘画软件的安装、更新、环境检查、启动以及模型和扩展管理。


# 安装
使用前需确保系统已安装 [Python](https://www.python.org) 3.10+ 和 [Git](https://git-scm.com/)。

```bash
pip install sd-webui-all-in-one
```

安装完整依赖：

```bash
pip install "sd-webui-all-in-one[full]"
```


# 基础使用
可使用 `--help` 查看可用的命令。

```bash
sd-webui-all-in-one --help
```


# Stable Diffusion WebUI
Stable Diffusion WebUI 是目前最流行的 AI 绘画开源软件之一。

## 安装 Stable Diffusion WebUI
```bash
sd-webui-all-in-one sd-webui install [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录，默认为配置文件中的路径。
  - `--pytorch-mirror-type <类型>`: 设置使用的 PyTorch 镜像源类型。
  - `--custom-pytorch-package <包名>`: 自定义 PyTorch 软件包版本声明，例如：`torch==2.3.0+cu118 torchvision==0.18.0+cu118`。
  - `--custom-xformers-package <包名>`: 自定义 xFormers 软件包版本声明，例如：`xformers===0.0.26.post1+cu118`。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--install-branch <分支>`: 安装的 Stable Diffusion WebUI 分支（如 `master`, `v1.6.0` 等）。
  - `--no-pre-download-extension`: 禁用预下载 Stable Diffusion WebUI 扩展。
  - `--no-pre-download-model`: 禁用预下载模型。
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 Stable Diffusion WebUI
```bash
sd-webui-all-in-one sd-webui update [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

## 检查运行环境
```bash
sd-webui-all-in-one sd-webui check-env [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--no-uv`: 不使用 uv。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 切换分支
```bash
sd-webui-all-in-one sd-webui switch --branch <分支名> [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--branch <分支名>`: (必填) 要切换的分支。

## 启动 Stable Diffusion WebUI
```bash
sd-webui-all-in-one sd-webui launch [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--launch-args <参数>`: 启动参数 (请使用引号包裹，例如 `"--theme dark --xformers"`)。
  - `--no-hf-mirror`: 禁用 HuggingFace 镜像源。
  - `--custom-hf-mirror <URL>`: 自定义 HuggingFace 镜像源。
  - `--no-github-mirror`: 禁用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 禁用 PyPI 镜像源。
  - `--no-cuda-malloc`: 禁用 CUDA Malloc 优化。
  - `--no-uv`: 不使用 uv。
  - `--no-check-env`: 不检查运行环境完整性。

## 扩展管理

### 安装扩展
```bash
sd-webui-all-in-one sd-webui extension install --url <链接> [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--url <链接>`: (必填) 扩展下载链接。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 设置扩展状态
```bash
sd-webui-all-in-one sd-webui extension status --name <名称> [--enable|--disable] [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--name <名称>`: (必填) 扩展名称。
  - `--enable`: 启用扩展。
  - `--disable`: 禁用扩展。

### 列出扩展
```bash
sd-webui-all-in-one sd-webui extension list [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。

### 更新扩展
```bash
sd-webui-all-in-one sd-webui extension update [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 卸载扩展
```bash
sd-webui-all-in-one sd-webui extension uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--name <名称>`: (必填) 扩展名称。

## 模型管理

### 从模型库安装模型
```bash
sd-webui-all-in-one sd-webui model install-library [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

### 从链接安装模型
```bash
sd-webui-all-in-one sd-webui model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

### 列出模型
```bash
sd-webui-all-in-one sd-webui model list [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。

### 卸载模型
```bash
sd-webui-all-in-one sd-webui model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--sd-webui-path <路径>`: Stable Diffusion WebUI 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

## 重装 PyTorch
```bash
sd-webui-all-in-one sd-webui reinstall-pytorch [选项]
```

- **高级选项**:
  - `--pytorch-name <名称>`: PyTorch 版本组合名称。
  - `--pytorch-index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# ComfyUI
ComfyUI 是一个基于节点流的 Stable Diffusion GUI。

## 安装 ComfyUI
```bash
sd-webui-all-in-one comfyui install [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录，默认为配置文件中的路径。
  - `--pytorch-mirror-type <类型>`: 设置使用的 PyTorch 镜像源类型。
  - `--custom-pytorch-package <包名>`: 自定义 PyTorch 软件包版本声明。
  - `--custom-xformers-package <包名>`: 自定义 xFormers 软件包版本声明。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pre-download-extension`: 禁用预下载 ComfyUI 扩展。
  - `--no-pre-download-model`: 禁用预下载模型。
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 ComfyUI
```bash
sd-webui-all-in-one comfyui update [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

## 检查运行环境
```bash
sd-webui-all-in-one comfyui check-env [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--install-conflict`: 自动安装冲突组件依赖。
  - `--interactive`: 启用交互模式。
  - `--no-uv`: 不使用 uv。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 启动 ComfyUI
```bash
sd-webui-all-in-one comfyui launch [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--launch-args <参数>`: 启动参数 (请使用引号包裹，例如 `"--theme dark"`)。
  - `--no-hf-mirror`: 禁用 HuggingFace 镜像源。
  - `--custom-hf-mirror <URL>`: 自定义 HuggingFace 镜像源。
  - `--no-github-mirror`: 禁用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 禁用 PyPI 镜像源。
  - `--no-cuda-malloc`: 禁用 CUDA Malloc 优化。
  - `--no-uv`: 不使用 uv。
  - `--interactive`: 启用交互模式。
  - `--install-conflict`: 自动安装冲突组件依赖。
  - `--no-check-env`: 不检查运行环境完整性。

## 扩展管理 (Custom Node)

### 安装扩展
```bash
sd-webui-all-in-one comfyui custom-node install --url <链接> [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--url <链接>`: (必填) 扩展下载链接。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 设置扩展状态
```bash
sd-webui-all-in-one comfyui custom-node status --name <名称> [--enable|--disable] [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--name <名称>`: (必填) 扩展名称。
  - `--enable`: 启用扩展。
  - `--disable`: 禁用扩展。

### 列出扩展
```bash
sd-webui-all-in-one comfyui custom-node list [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。

### 更新扩展
```bash
sd-webui-all-in-one comfyui custom-node update [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 卸载扩展
```bash
sd-webui-all-in-one comfyui custom-node uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--name <名称>`: (必填) 扩展名称。

## 模型管理

### 从模型库安装模型
```bash
sd-webui-all-in-one comfyui model install-library [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

### 从链接安装模型
```bash
sd-webui-all-in-one comfyui model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

### 列出模型
```bash
sd-webui-all-in-one comfyui model list [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。

### 卸载模型
```bash
sd-webui-all-in-one comfyui model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--comfyui-path <路径>`: ComfyUI 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

## 重装 PyTorch
```bash
sd-webui-all-in-one comfyui reinstall-pytorch [选项]
```

- **高级选项**:
  - `--pytorch-name <名称>`: PyTorch 版本组合名称。
  - `--pytorch-index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# Fooocus
Fooocus 是一款专注于易用性的图像生成软件。

## 安装 Fooocus
```bash
sd-webui-all-in-one fooocus install [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录，默认为配置文件中的路径。
  - `--pytorch-mirror-type <类型>`: 设置使用的 PyTorch 镜像源类型。
  - `--custom-pytorch-package <包名>`: 自定义 PyTorch 软件包版本声明。
  - `--custom-xformers-package <包名>`: 自定义 xFormers 软件包版本声明。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--install-branch <分支>`: 安装的 Fooocus 分支。
  - `--no-pre-download-model`: 禁用预下载模型。
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 Fooocus
```bash
sd-webui-all-in-one fooocus update [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

## 检查运行环境
```bash
sd-webui-all-in-one fooocus check-env [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--no-uv`: 不使用 uv。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 切换分支
```bash
sd-webui-all-in-one fooocus switch --branch <分支名> [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--branch <分支名>`: (必填) 要切换的分支。

## 启动 Fooocus
```bash
sd-webui-all-in-one fooocus launch [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--launch-args <参数>`: 启动参数 (请使用引号包裹，例如 `"--theme dark"`)。
  - `--no-hf-mirror`: 禁用 HuggingFace 镜像源。
  - `--custom-hf-mirror <URL>`: 自定义 HuggingFace 镜像源。
  - `--no-github-mirror`: 禁用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 禁用 PyPI 镜像源。
  - `--no-cuda-malloc`: 禁用 CUDA Malloc 优化。
  - `--no-check-env`: 不检查运行环境完整性。

## 模型管理

### 从模型库安装模型
```bash
sd-webui-all-in-one fooocus model install-library [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

### 从链接安装模型
```bash
sd-webui-all-in-one fooocus model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

### 列出模型
```bash
sd-webui-all-in-one fooocus model list [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。

### 卸载模型
```bash
sd-webui-all-in-one fooocus model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--fooocus-path <路径>`: Fooocus 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

## 重装 PyTorch
```bash
sd-webui-all-in-one fooocus reinstall-pytorch [选项]
```

- **高级选项**:
  - `--pytorch-name <名称>`: PyTorch 版本组合名称。
  - `--pytorch-index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# InvokeAI
InvokeAI 是一款功能强大的 Stable Diffusion 创意引擎。

## 安装 InvokeAI
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
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 InvokeAI
```bash
sd-webui-all-in-one invokeai update [选项]
```

- **高级选项**:
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 Python 软件包。

## 检查运行环境
```bash
sd-webui-all-in-one invokeai check-env [选项]
```

- **高级选项**:
  - `--no-uv`: 不使用 uv。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 启动 InvokeAI
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

## 扩展管理 (Custom Node)

### 安装扩展
```bash
sd-webui-all-in-one invokeai custom-node install --url <链接> [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--url <链接>`: (必填) 扩展下载链接。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 设置扩展状态
```bash
sd-webui-all-in-one invokeai custom-node status --name <名称> [--enable|--disable] [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--name <名称>`: (必填) 扩展名称。
  - `--enable`: 启用扩展。
  - `--disable`: 禁用扩展。

### 列出扩展
```bash
sd-webui-all-in-one invokeai custom-node list [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。

### 更新扩展
```bash
sd-webui-all-in-one invokeai custom-node update [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

### 卸载扩展
```bash
sd-webui-all-in-one invokeai custom-node uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--name <名称>`: (必填) 扩展名称。

## 模型管理

### 从模型库安装模型
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

### 从链接安装模型
```bash
sd-webui-all-in-one invokeai model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--invokeai-path <路径>`: InvokeAI 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

### 列出模型
```bash
sd-webui-all-in-one invokeai model list
```

### 卸载模型
```bash
sd-webui-all-in-one invokeai model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--name <名称>`: (必填) 模型名称。
  - `--interactive`: 启用交互模式。

## 重装 PyTorch
```bash
sd-webui-all-in-one invokeai reinstall-pytorch [选项]
```

- **高级选项**:
  - `--device-type <类型>`: 设备类型 (`cuda`, `rocm`, `cpu`, `mps`)。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# Qwen TTS WebUI
Qwen TTS WebUI 是一款基于 Qwen 模型的文本转语音软件。

## 安装 Qwen TTS WebUI
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
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 Qwen TTS WebUI
```bash
sd-webui-all-in-one qwen-tts-webui update [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

## 检查运行环境
```bash
sd-webui-all-in-one qwen-tts-webui check-env [选项]
```

- **高级选项**:
  - `--qwen-tts-webui-path <路径>`: Qwen TTS WebUI 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--no-uv`: 不使用 uv。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 启动 Qwen TTS WebUI
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

## 重装 PyTorch
```bash
sd-webui-all-in-one qwen-tts-webui reinstall-pytorch [选项]
```

- **高级选项**:
  - `--pytorch-name <名称>`: PyTorch 版本组合名称。
  - `--pytorch-index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# SD Trainer
SD Trainer 是一款用于训练 Stable Diffusion 模型的工具。

## 安装 SD Trainer
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
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 SD Trainer
```bash
sd-webui-all-in-one sd-trainer update [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

## 检查运行环境
```bash
sd-webui-all-in-one sd-trainer check-env [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--no-uv`: 不使用 uv。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 切换分支
```bash
sd-webui-all-in-one sd-trainer switch --branch <分支名> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--branch <分支名>`: (必填) 要切换的分支。

## 启动 SD Trainer
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

## 模型管理

### 从模型库安装模型
```bash
sd-webui-all-in-one sd-trainer model install-library [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--source <源>`: 模型下载源类型 (默认: `modelscope`)。
  - `--name <名称>`: 模型名称。
  - `--index <索引>`: 模型索引。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出模型列表并退出。

### 从链接安装模型
```bash
sd-webui-all-in-one sd-trainer model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

### 列出模型
```bash
sd-webui-all-in-one sd-trainer model list [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。

### 卸载模型
```bash
sd-webui-all-in-one sd-trainer model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--sd-trainer-path <路径>`: SD Trainer 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

## 重装 PyTorch
```bash
sd-webui-all-in-one sd-trainer reinstall-pytorch [选项]
```

- **高级选项**:
  - `--pytorch-name <名称>`: PyTorch 版本组合名称。
  - `--pytorch-index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# SD Scripts
SD Scripts 是一组用于训练和处理 Stable Diffusion 模型的脚本集合。

## 安装 SD Scripts
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
  - `--no-cn-model-mirror`: 不使用国内镜像下载模型。

## 更新 SD Scripts
```bash
sd-webui-all-in-one sd-scripts update [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。

## 检查运行环境
```bash
sd-webui-all-in-one sd-scripts check-env [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--no-uv`: 不使用 uv。
  - `--no-github-mirror`: 不使用 Github 镜像源。
  - `--custom-github-mirror <URL>`: 自定义 Github 镜像源。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 切换分支
```bash
sd-webui-all-in-one sd-scripts switch --branch <分支名> [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--branch <分支名>`: (必填) 要切换的分支。

## 模型管理

### 从模型库安装模型
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

### 从链接安装模型
```bash
sd-webui-all-in-one sd-scripts model install-url --url <链接> --type <类型> [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--url <链接>`: (必填) 模型下载地址。
  - `--type <类型>`: (必填) 模型类型。
  - `--downloader <工具>`: 下载工具 (默认: `aria2`)。

### 列出模型
```bash
sd-webui-all-in-one sd-scripts model list [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。

### 卸载模型
```bash
sd-webui-all-in-one sd-scripts model uninstall --name <名称> [选项]
```

- **高级选项**:
  - `--sd-scripts-path <路径>`: SD Scripts 根目录。
  - `--name <名称>`: (必填) 模型名称。
  - `--type <类型>`: 模型类型。
  - `--interactive`: 启用交互模式。

## 重装 PyTorch
```bash
sd-webui-all-in-one sd-scripts reinstall-pytorch [选项]
```

- **高级选项**:
  - `--pytorch-name <名称>`: PyTorch 版本组合名称。
  - `--pytorch-index <索引>`: PyTorch 版本组合索引值。
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。
  - `--no-uv`: 不使用 uv 安装 PyTorch 软件包。
  - `--interactive`: 启用交互模式。
  - `--list-only`: 列出 PyTorch 列表并退出。


# SD WebUI All In One Manager
用于管理 `sd-webui-all-in-one` 自身的组件和补丁。

## 检查 Aria2
检查 Aria2 是否需要更新。
```bash
sd-webui-all-in-one self-manager check-aria2
```
*注：当退出代码非 0 时说明需要更新。*

## 检查并更新 Pip
```bash
sd-webui-all-in-one self-manager check-pip [选项]
```
- **高级选项**:
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 检查并更新 uv
```bash
sd-webui-all-in-one self-manager check-uv [选项]
```
- **高级选项**:
  - `--no-pypi-mirror`: 不使用国内 PyPI 镜像源。

## 获取补丁路径
获取 `SD WebUI All In One` 补丁的存储路径。
```bash
sd-webui-all-in-one self-manager get-patcher
```


# SD WebUI All In One 环境变量配置
SD WebUI All In One 支持通过环境变量来调整其行为。

## 基础配置
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

## 软件根目录配置
可以通过以下环境变量自定义各软件的默认根目录：
- `SD_WEBUI_ROOT`: Stable Diffusion WebUI 根目录。
- `COMFYUI_ROOT`: ComfyUI 根目录。
- `FOOOCUS_ROOT`: Fooocus 根目录。
- `INVOKEAI_ROOT`: InvokeAI 根目录。
- `SD_TRAINER_ROOT`: SD Trainer 根目录。
- `SD_SCRIPTS_ROOT`: SD Scripts 根目录。
- `QWEN_TTS_WEBUI_ROOT`: Qwen TTS WebUI 根目录。
