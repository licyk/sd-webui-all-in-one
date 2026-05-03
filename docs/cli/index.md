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
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml/badge.svg" alt="Ruff Lint">
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
