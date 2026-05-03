<div align="center">

# SD WebUI All In One
![SD WebUI All In One](.github/head_image.jpg)

_✨快速部署，简单易用_
  <p align="center">
    <a href="https://github.com/licyk/sd-webui-all-in-one/stargazers" style="margin: 2px;">
      <img src="https://img.shields.io/github/stars/licyk/sd-webui-all-in-one?style=flat&logo=github&logoColor=silver&color=bluegreen&labelColor=grey" alt="Stars">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/issues">
      <img src="https://img.shields.io/github/issues/licyk/sd-webui-all-in-one?style=flat&logo=github&logoColor=silver&color=bluegreen&labelColor=grey" alt="Issues">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/commits/dev">
      <img src="https://flat.badgen.net/github/last-commit/licyk/sd-webui-all-in-one/dev?icon=github&color=green&label=last%20dev%20commit" alt="Commit">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/sync_repo.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/sync_repo.yml/badge.svg" alt="Sync">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pwsh-lint.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pwsh-lint.yml/badge.svg" alt="Lint">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/check_version.yaml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/check_version.yaml/badge.svg" alt="Check Installer Version">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/release.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/release.yml/badge.svg" alt="Release">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pypi-release.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pypi-release.yml/badge.svg" alt="PyPI Release">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/py-lint.yml/badge.svg" alt="Ruff Lint">
    </a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pytest.yml">
      <img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/pytest.yml/badge.svg" alt="Pytest">
    </a>
  </p>

</div>

- [SD WebUI All In One](#sd-webui-all-in-one)
- [项目文档](#项目文档)
- [SD WebUI All In One CLI](#sd-webui-all-in-one-cli)
- [SD WebUI All In One Notebook](#sd-webui-all-in-one-notebook)
  - [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)
  - [SD Trainer Scripts Kaggle Jupyter NoteBook](#sd-trainer-scripts-kaggle-jupyter-notebook)
  - [SD Scripts Colab Jupyter NoteBook](#sd-scripts-colab-jupyter-notebook)
  - [SD Trainer Colab Jupyter NoteBook](#sd-trainer-colab-jupyter-notebook)
  - [HDM Train Kaggle Jupyter NoteBook](#hdm-train-kaggle-jupyter-notebook)
  - [Stable Diffusion WebUI Colab NoteBook](#stable-diffusion-webui-colab-notebook)
  - [ComfyUI Colab NoteBook](#comfyui-colab-notebook)
  - [InvokeAI Colab NoteBook](#invokeai-colab-notebook)
  - [Fooocus Colab Jupyter NoteBook](#fooocus-colab-jupyter-notebook)
  - [Qwen TTS WebUI Colab Jupyter NoteBook](#qwen-tts-webui-colab-jupyter-notebook)
  - [旧版 Notebook](#旧版-notebook)
- [Installer](#installer)
  - [SD WebUI Installer](#sd-webui-installer)
  - [ComfyUI Installer](#comfyui-installer)
  - [InvokeAI Installer](#invokeai-installer)
  - [Fooocus Installer](#fooocus-installer)
  - [SD-Trainer Installer](#sd-trainer-installer)
  - [SD-Trainer-Script Installer](#sd-trainer-script-installer)
  - [Qwen TTS WebUI Installer](#qwen-tts-webui-installer)
  - [Python Installer](#python-installer)
  - [Installer 自动化构建状态](#installer-自动化构建状态)
- [项目协议](#项目协议)
- [Third-party Notices](#third-party-notices)

***

# 项目文档
SD WebUI All In One 提供本地安装、整合包下载、Launcher 管理、Jupyter Notebook 云端运行和 CLI 管理等多种入口，用于快速安装、启动和维护常见 AI WebUI / 训练工具。

完整文档站点：[SD WebUI All In One 文档](https://licyk.github.io/sd-webui-all-in-one/)

| 想做什么 | 推荐入口 |
| --- | --- |
| 不确定该用哪种方式 | [快速开始](docs/quick-start/index.md) |
| 在 Colab / Kaggle 云端运行 | [云端运行快速开始](docs/quick-start/cloud.md) / [Jupyter Notebook 文档](docs/notebook/index.md) |
| 下载 Windows 免安装整合包 | [整合包快速开始](docs/quick-start/portable.md) / [AI 整合包下载器](docs/tools/portable-downloader.md) |
| 在本地安装 WebUI / 训练工具 | [本地安装快速开始](docs/quick-start/local-install.md) / [安装器使用](docs/installer/index.md) |
| 用图形界面或终端统一管理 | [Launcher 快速开始](docs/quick-start/launcher.md) / [下载器与启动器](docs/tools/index.md) |
| 使用命令行管理 | [命令行工具](docs/cli/index.md) |
| 维护项目源码和文档 | [开发维护](docs/development/index.md) |

***

# SD WebUI All In One CLI
`sd-webui-all-in-one` 是用于多平台安装、启动和管理 WebUI / 训练工具的 CLI。它复用项目的 Python 管理核心，可用于管理仓库、模型、扩展、PyTorch、内网穿透和运行环境。支持部署的 WebUI / 训练工具如下：

- [Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
- [Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)
- [Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic)
- [Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)
- [SD.Next](https://github.com/vladmandic/automatic)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [InvokeAI](https://github.com/invoke-ai/InvokeAI)
- [Fooocus](https://github.com/lllyasviel/Fooocus)
- [SD-Trainer](https://github.com/Akegarasu/lora-scripts)
- [Kohya GUI](https://github.com/bmaltais/kohya_ss)
- [sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [ai-toolkit](https://github.com/ostris/ai-toolkit)
- [finetrainers](https://github.com/a-r-r-o-w/finetrainers)
- [diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)
- [musubi-tuner](https://github.com/kohya-ss/musubi-tuner)
- [Qwen TTS WebUI](https://github.com/licyk/qwen-tts-webui)

完整命令说明请阅读：[命令行工具文档](docs/cli/index.md)。


# SD WebUI All In One Notebook
支持部署不同 WebUI 的各种 Notebook，基于 [SD WebUI All In One](https://github.com/licyk/sd-webui-all-in-one/tree/main/sd_webui_all_in_one) Python 内核，提供 Colab / Kaggle 云端运行入口。Colab Notebook 支持图形化参数配置，默认参数通常可以直接运行。支持部署的 WebUI / 训练工具如下：

- [Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)
- [Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)
- [Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic)
- [Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)
- [SD.Next](https://github.com/vladmandic/automatic)
- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [InvokeAI](https://github.com/invoke-ai/InvokeAI)
- [Fooocus](https://github.com/lllyasviel/Fooocus)
- [SD-Trainer](https://github.com/Akegarasu/lora-scripts)
- [Kohya GUI](https://github.com/bmaltais/kohya_ss)
- [sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [ai-toolkit](https://github.com/ostris/ai-toolkit)
- [finetrainers](https://github.com/a-r-r-o-w/finetrainers)
- [diffusion-pipe](https://github.com/tdrussell/diffusion-pipe)
- [musubi-tuner](https://github.com/kohya-ss/musubi-tuner)
- [Qwen TTS WebUI](https://github.com/licyk/qwen-tts-webui)

详细使用方法可查看 Notebook 中的说明，使用时请按顺序执行 Jupyter Notebook 单元。

>[!NOTE]  
>点击蓝色名称可下载对应的 Jupyter NoteBook。

完整使用说明请阅读：[Jupyter Notebook 文档](docs/notebook/index.md)。


## SD Scripts Kaggle Jupyter NoteBook
[sd_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_kaggle.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_kaggle.ipynb))：适用于 Kaggle 部署 [sd-scripts](https://github.com/kohya-ss/sd-scripts)，可用于不同种类的模型训练，使用前需熟悉 sd-scripts 的使用方法。

>[!IMPORTANT]  
>使用方法可阅读：  
>[使用 HuggingFace / ModelScope 保存和下载文件 - licyk的小窝](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/)  
>[使用 Kaggle 进行模型训练 - licyk的小窝](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)

>[!Caution]
>Kaggle 不允许上传 NSFW 的内容，尝试上传包含 NSFW 图片的训练集将导致 Kaggle 账号被封禁！


## SD Trainer Scripts Kaggle Jupyter NoteBook
[sd_trainer_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_scripts_kaggle.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_scripts_kaggle.ipynb))：适用于 Kaggle 部署 [sd-scripts](https://github.com/kohya-ss/sd-scripts) / [ai-toolkit](https://github.com/ostris/ai-toolkit) / [finetrainers](https://github.com/a-r-r-o-w/finetrainers) / [diffusion-pipe](https://github.com/tdrussell/diffusion-pipe) / [musubi-tuner](https://github.com/kohya-ss/musubi-tuner)，可用于不同种类的模型训练。

>[!IMPORTANT]  
>1. 使用方法可参考：  
>[使用 HuggingFace / ModelScope 保存和下载文件 - licyk的小窝](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/)  
>[使用 Kaggle 进行模型训练 - licyk的小窝](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)
>2. 该 NoteBook 相对于 [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)，在配置环境部分有点区别，并且使用的命令也有些改变，如果需要旧版可使用 [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)。

>[!Caution]
>Kaggle 不允许上传 NSFW 的内容，尝试上传包含 NSFW 图片的训练集将导致 Kaggle 账号被封禁！


## SD Scripts Colab Jupyter NoteBook
[sd_scripts_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_colab.ipynb))：适用于 Colab 部署 [sd-scripts](https://github.com/kohya-ss/sd-scripts)，**自己写来玩的，还有用来开发和测试管理核心**，要用的话就参考 [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## SD Trainer Colab Jupyter NoteBook
[sd_trainer_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb))：适用于 Colab 一键部署 [SD-Trainer](https://github.com/Akegarasu/lora-scripts) / [Kohya GUI](https://github.com/bmaltais/kohya_ss)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## HDM Train Kaggle Jupyter NoteBook
[hdm_train_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/hdm_train_kaggle.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/hdm_train_kaggle.ipynb))：适用于 Kaggle / Colab 部署 [HDM](https://github.com/KohakuBlueleaf/HDM)，**写来玩的脚本，可能有 BUG**，要用的话就参考 [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/hdm_train_kaggle.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

>[!Caution]
>Kaggle 不允许上传 NSFW 的内容，尝试上传包含 NSFW 图片的训练集将导致 Kaggle 账号被封禁！


## Stable Diffusion WebUI Colab NoteBook
[stable_diffusion_webui_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/stable_diffusion_webui_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb))：适用于 Colab 一键部署 [Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / [Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) / [Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) / [Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic) / [Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu) / [SD.Next](https://github.com/vladmandic/automatic)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## ComfyUI Colab NoteBook
[comfyui_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/comfyui_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb))：适用于 Colab 一键部署 [ComfyUI](https://github.com/Comfy-Org/ComfyUI)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## InvokeAI Colab NoteBook
[invokeai_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/invokeai_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb))：适用于 Colab 一键部署 [InvokeAI](https://github.com/invoke-ai/InvokeAI)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## Fooocus Colab Jupyter NoteBook
[fooocus_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/fooocus_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb))：适用于 Colab 一键部署 [Fooocus](https://github.com/lllyasviel/Fooocus)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## Qwen TTS WebUI Colab Jupyter NoteBook
[qwen_tts_webui_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/qwen_tts_webui_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb))：适用于 Colab 一键部署 [Qwen TTS WebUI](https://github.com/licyk/qwen-tts-webui)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

***

## 旧版 Notebook
以下 Notebook 已停止维护，不推荐新用户优先使用。保留这些入口仅用于历史回溯或兼容旧流程，新的使用方式请优先阅读 [Jupyter Notebook 文档](docs/notebook/index.md)。

| Notebook | 下载 | 源码 | 状态 |
| --- | --- | --- | --- |
| SD WebUI All In One | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_webui_all_in_one.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_webui_all_in_one.ipynb) | 已停止维护 |
| SD WebUI All In One Colab | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_webui_all_in_one_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_webui_all_in_one_colab.ipynb) | 已停止维护 |
| Fooocus Kaggle | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/fooocus_kaggle.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_kaggle.ipynb) | 已停止维护 |
| SD Trainer Kaggle | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_kaggle.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_kaggle.ipynb) | 已停止维护 |

***

# Installer
Installer 是适用于 Windows / Linux / macOS 的 WebUI / 训练工具安装与管理脚本。它不依赖系统中已有的 [Git](https://git-scm.com) / [Python](https://www.python.org/)，会在独立目录中准备运行环境，并生成启动、更新、终端、模型下载、PyTorch 重装和版本管理等脚本。

>[!IMPORTANT]  
>1. Installer 并不会使用系统中安装的 Git / Python，这是为了保证环境的独立性和可迁移性。并且因为环境的独立性和可迁移性，Installer 也可用做整合包制作器。
>2. 基于 Installer 的构建模式，可实现整合包制作全自动化，由 Installer 自动构建的整合包可在此列表查看：[AI 绘画 / 训练整合包列表](https://licyk.github.io/t/sd_portable)
>3. 由 Installer 制作的整合包说明可阅读：[AI 绘画 / 训练整合包 · licyk/sd-webui-all-in-one · Discussion #1](https://github.com/licyk/sd-webui-all-in-one/discussions/1)
>4. Windows 用户可使用下载器进行下载，内置高速下载器和解压工具，安装更方便。下载地址：[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat) / [下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat)

[configure_env.bat](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/installer/configure_env.bat))：（仅适用 Windows 平台）配置 Installer 运行环境的一键配置脚本，首次使用 Installer 时需要运行一次该脚本。

[sd_portable_downloader.bat](https://github.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/sd_portable_downloader.ps1))：（仅适用 Windows 平台）AI 整合包下载器。


## SD WebUI Installer
Windows / Linux / macOS 平台安装、启动和管理 [Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / [Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) / [Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) / [Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic) / [Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu) / [SD.Next](https://github.com/vladmandic/automatic)。

使用说明：[SD WebUI Installer 文档](docs/installer/sd-webui/index.md)。


## ComfyUI Installer
Windows / Linux / macOS 平台安装、启动和管理 [ComfyUI](https://github.com/Comfy-Org/ComfyUI)。

使用说明：[ComfyUI Installer 文档](docs/installer/comfyui/index.md)。


## InvokeAI Installer
Windows / Linux / macOS 平台安装、启动和管理 [InvokeAI](https://github.com/invoke-ai/InvokeAI)。

使用说明：[InvokeAI Installer 文档](docs/installer/invokeai/index.md)。


## Fooocus Installer
Windows / Linux / macOS 平台安装、启动和管理 [Fooocus](https://github.com/lllyasviel/Fooocus) / [Fooocus-MRE](https://github.com/MoonRide303/Fooocus-MRE) / [RuinedFooocus](https://github.com/runew0lf/RuinedFooocus)。

使用说明：[Fooocus Installer 文档](docs/installer/fooocus/index.md)。


## SD-Trainer Installer
Windows / Linux / macOS 平台安装、启动和管理 [SD-Trainer](https://github.com/Akegarasu/lora-scripts) / [Kohya GUI](https://github.com/bmaltais/kohya_ss)。

使用说明：[SD Trainer Installer 文档](docs/installer/sd-trainer/index.md)。


## SD-Trainer-Script Installer
>[!WARNING]  
>此部署工具部署的训练工具需要一定的编写训练命令基础，如果需要使用简单的模型训练工具，请使用 [SD-Trainer Installer](docs/installer/sd-trainer/index.md) 部署训练工具并使用。

Windows / Linux / macOS 平台安装和管理 [sd-scripts](https://github.com/kohya-ss/sd-scripts) / [ai-toolkit](https://github.com/ostris/ai-toolkit) / [finetrainers](https://github.com/a-r-r-o-w/finetrainers) / [diffusion-pipe](https://github.com/tdrussell/diffusion-pipe) / [musubi-tuner](https://github.com/kohya-ss/musubi-tuner)。

使用说明：[SD Trainer Script Installer 文档](docs/installer/sd-trainer-script/index.md)。


## Qwen TTS WebUI Installer
Windows / Linux / macOS 平台安装、启动和管理 [Qwen TTS WebUI](https://github.com/licyk/qwen-tts-webui)。

使用说明：[Qwen TTS WebUI Installer 文档](docs/installer/qwen-tts-webui/index.md)。


## Python Installer
[install_embed_python.ps1](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/install_embed_python.ps1)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/installer/install_embed_python.ps1))：Windows 平台一键安装便携式 Python，可用做测试。


## Installer 自动化构建状态
|Github Action|Status|
|---|---|
|Build [SD WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) Portable|[![Build SD WebUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui.yml)|
|Build [SD WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) Portable|[![Build SD WebUI Forge](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge.yml)|
|Build [SD WebUI reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) Portable|[![Build SD WebUI reForge](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_reforge.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_reforge.yml)|
|Build [SD WebUI Forge Classic](https://github.com/Haoming02/sd-webui-forge-classic) Portable|[![SD WebUI Forge Classic](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge_classic.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge_classic.yml)|
|Build [SD Next](https://github.com/vladmandic/automatic) Portable|[![Build SD WebUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_next.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_next.yml)|
|Build [ComfyUI](https://github.com/Comfy-Org/ComfyUI) Portable|[![Build ComfyUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui.yml)|
|Build [ComfyUI](https://github.com/Comfy-Org/ComfyUI) (ROCm) Portable|[![Build ComfyUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui_rocm.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui_rocm.yml)|
|Build [ComfyUI](https://github.com/Comfy-Org/ComfyUI) (XPU) Portable|[![Build ComfyUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui_xpu.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui_xpu.yml)|
|Build [Fooocus](https://github.com/lllyasviel/Fooocus) Portable|[![Build Fooocus](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_fooocus.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_fooocus.yml)|
|Build [InvokeAI](https://github.com/invoke-ai/InvokeAI) Portable|[![Build InvokeAI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_invokeai.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_invokeai.yml)|
|Build [SD-Trainer](https://github.com/Akegarasu/lora-scripts) Portable|[![Build SD-Trainer](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_trainer.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_trainer.yml)|
|Build [Kohya GUI](https://github.com/bmaltais/kohya_ss) Portable|[![Build Kohya GUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_kohya_gui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_kohya_gui.yml)|
|Build [SD Scripts](https://github.com/kohya-ss/sd-scripts) Portable|[![Build SD Scripts](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_scripts.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_scripts.yml)|
|Build [Musubi Tuner](https://github.com/kohya-ss/musubi-tuner) Portable|[![Build Musubi Tuner](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_musubi_tuner.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_musubi_tuner.yml)|
|Build [Qwen TTS WebUI](https://github.com/licyk/qwen-tts-webui) Portable|[![Build Qwen TTS WebUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_qwen_tts_webui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_qwen_tts_webui.yml)|

***

# 项目协议
本项目主体使用 [GNU General Public License v3.0](LICENSE)（GPL-3.0）发布。你可以在 GPL-3.0 条款下使用、复制、修改和分发本项目；分发修改版本时，请遵守 GPL-3.0 的源代码开放和许可证保留要求。

项目中引用或内置的第三方组件按其各自许可证使用。

***

# Third-party Notices
本项目的 tkinter 版本管理 GUI 内置了 [Sun Valley ttk theme](https://github.com/rdbende/Sun-Valley-ttk-theme)（`sv_ttk`）作为可选界面主题资源。

Sun Valley ttk theme 使用 MIT License，版权归 `rdbende <rdbende@proton.me>` 所有，许可证原文保留在 [sd_webui_all_in_one/base_manager/gui/sv_ttk/LICENSE](sd_webui_all_in_one/base_manager/gui/sv_ttk/LICENSE)。
