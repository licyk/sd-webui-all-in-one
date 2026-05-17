# SD WebUI All In One CLI

## 阅读导引

- [Stable Diffusion WebUI](sd-webui.md)
- [ComfyUI](comfyui.md)
- [Fooocus](fooocus.md)
- [InvokeAI](invokeai.md)
- [Qwen TTS WebUI](qwen-tts-webui.md)
- [SD Trainer](sd-trainer.md)
- [SD Scripts](sd-scripts.md)
- [管理器命令](manager.md)
- [环境变量配置](env.md)

_✨小巧，强大的命令工具_
  <p align="center">
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pypi-release.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pypi-release.yml/badge.svg" alt="PyPI Release">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml/badge.svg" alt="Python Lint">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pytest.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pytest.yml/badge.svg" alt="Pytest">
    </a>
    <a href="https://pypi.org/project/sd-webui-all-in-one" style="margin: 2px;">
      <img src="https://img.shields.io/pypi/v/sd-webui-all-in-one" alt="PyPI">
    </a>
    <a href="https://pypi.org/project/sd-webui-all-in-one" style="margin: 2px;">
      <img src="https://img.shields.io/pypi/pyversions/sd-webui-all-in-one.svg" alt="Python Version">
    </a>
  </p>

## 简介
SD WebUI All Ine One CLI 提供了一个强大的命令行界面，用于管理各种 AI 绘画软件的安装、更新、环境检查、启动以及模型和扩展管理。

## 安装
使用前需确保系统已安装 [Python](https://www.python.org) 3.10+ 和 [Git](https://git-scm.com/)。

```bash
pip install sd-webui-all-in-one
```

安装完整依赖：

```bash
pip install "sd-webui-all-in-one[full]"
```

## 基础使用
可使用 `--help` 查看可用的命令。

```bash
sd-webui-all-in-one --help
```

## 自动镜像源选择

CLI 中涉及 PyPI、Github、HuggingFace 或模型下载源的子命令默认启用自动镜像源选择。执行命令时会调用 `network_gfw_test()` 判断当前网络是否需要镜像源：

- 当检测结果为 `True` 时，CLI 会强制使用官方源：关闭 PyPI、Github、HuggingFace 镜像源，并将模型下载源设为 `huggingface`。
- 当检测结果为 `False` 时，CLI 会强制使用镜像源：启用 PyPI、Github、HuggingFace 镜像源，并将模型下载源设为 `modelscope`。

!!! warning
    自动镜像源选择会强制覆盖命令中已有的 `--no-pypi-mirror`、`--no-github-mirror`、`--no-hf-mirror`、`--custom-github-mirror`、`--custom-hf-mirror`、`--model-resource` 和 `--source`。如果需要手动调整这些镜像源设置，请显式添加 `--no-auto-mirror`。

CLI 会在日志中提示是否启用了自动镜像源选择，以及最终使用官方源还是镜像源。

示例：

```bash
# 默认自动模式，手动镜像参数可能会被网络检测结果覆盖
sd-webui-all-in-one comfyui install --no-pypi-mirror --model-resource huggingface

# 禁用自动模式后，才会遵守手动镜像参数
sd-webui-all-in-one comfyui install --no-auto-mirror --no-pypi-mirror --model-resource huggingface
```
