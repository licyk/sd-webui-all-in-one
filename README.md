<div align="center">

# SD WebUI All In One

_✨快速部署，简单易用_
  <p align="center">
    <img src="https://img.shields.io/github/stars/licyk/sd-webui-all-in-one?style=flat&logo=github&logoColor=silver&color=bluegreen&labelColor=grey" alt="Stars">
    <a href="https://github.com/licyk/sd-webui-all-in-one/issues"><img src="https://img.shields.io/github/issues/licyk/sd-webui-all-in-one?style=flat&logo=github&logoColor=silver&color=bluegreen&labelColor=grey" alt="Issues"></a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/commits/dev"><img src="https://flat.badgen.net/github/last-commit/licyk/sd-webui-all-in-one/dev?icon=github&color=green&label=last%20dev%20commit" alt="Commit"></a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/sync_repo.yml"><img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/sync_repo.yml/badge.svg" alt="Sync"></a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/lint.yaml"><img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/lint.yaml/badge.svg" alt="Lint"></a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/check_version.yaml"><img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/check_version.yaml/badge.svg" alt="Check Installer Version"></a>
    <a href="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/release.yml"><img src="https://github.com/licyk/sd-webui-all-in-one/actions/workflows/release.yml/badge.svg" alt="Release"></a>
  </p>

</div>

- [SD WebUI All In One](#sd-webui-all-in-one)
- [SD WebUI All In One Notebook](#sd-webui-all-in-one-notebook)
  - [可用的 Jupyter Notebook](#可用的-jupyter-notebook)
    - [SD WebUI All In One Jupyter NoteBook](#sd-webui-all-in-one-jupyter-notebook)
    - [SD WebUI All In One Colab Jupyter NoteBook](#sd-webui-all-in-one-colab-jupyter-notebook)
    - [Fooocus Colab Jupyter NoteBook](#fooocus-colab-jupyter-notebook)
    - [Fooocus kaggle Jupyter NoteBook](#fooocus-kaggle-jupyter-notebook)
    - [SD Trainer Kaggle Jupyter NoteBook](#sd-trainer-kaggle-jupyter-notebook)
    - [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)
    - [SD Scripts Colab Jupyter NoteBook](#sd-scripts-colab-jupyter-notebook)
  - [主要功能](#主要功能)
  - [其他功能](#其他功能)
  - [提示](#提示)
- [Installer](#installer)
  - [InvokeAI Installer](#invokeai-installer)
  - [SD-Trainer Installer](#sd-trainer-installer)
  - [ComfyUI Installer](#comfyui-installer)
  - [SD WebUI Installer](#sd-webui-installer)
  - [SD-Trainer-Script Installer](#sd-trainer-script-installer)
  - [Fooocus Installer](#fooocus-installer)
  - [Python Installer](#python-installer)
  - [Installer 自动化构建状态](#installer-自动化构建状态)

***

# SD WebUI All In One Notebook
这是一个支持部署多种 WebUI 的 Jupyter Notebook，支持部署以下 WebUI：
- 1、[Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- 2、[ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- 3、[InvokeAI](https://github.com/invoke-ai/InvokeAI)
- 4、[Fooocus](https://github.com/lllyasviel/Fooocus)
- 5、[lora-scripts](https://github.com/Akegarasu/lora-scripts)
- 6、[kohya_ss](https://github.com/bmaltais/kohya_ss)

使用时请按顺序执行 Jupyter Notebook 单元。


## 可用的 Jupyter Notebook 
>[!NOTE]  
>点击蓝色名称可下载对应的 Jupyter NoteBook。


### SD WebUI All In One Jupyter NoteBook
[sd_webui_all_in_one.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_webui_all_in_one.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_webui_all_in_one.ipynb))：支持部署多种 WebUI 的 Jupyter Notebook。


### SD WebUI All In One Colab Jupyter NoteBook
[sd_webui_all_in_one_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_webui_all_in_one_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_webui_all_in_one_colab.ipynb))：支持部署多种 WebUI 的 Jupyter Notebook，但移除了 Colab 免费版中会导致警告的 WebUI，适用于 Colab 免费用户。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/sd_webui_all_in_one_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


### Fooocus Colab Jupyter NoteBook
[fooocus_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/fooocus_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_colab.ipynb))：适用于 Colab 一键部署 [Fooocus](https://github.com/lllyasviel/Fooocus)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/fooocus_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

### Fooocus kaggle Jupyter NoteBook
[fooocus_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/fooocus_kaggle.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_kaggle.ipynb))：适用于 Kaggle 部署 [Fooocus](https://github.com/lllyasviel/Fooocus)。


### SD Trainer Kaggle Jupyter NoteBook
[sd_trainer_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_kaggle.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_kaggle.ipynb))：适用于 Kaggle 部署 [SD Trainer](https://github.com/Akegarasu/lora-scripts)，解决 Kaggle 环境问题导致无法运行 SD Trainer 的问题。


### SD Scripts Kaggle Jupyter NoteBook
[sd_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_kaggle.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_scripts_kaggle.ipynb))：适用于 Kaggle 部署 [sd-scripts](https://github.com/kohya-ss/sd-scripts)，可用于不同种类的模型训练，使用前需熟悉 sd-scripts 的使用方法。

>[!IMPORTANT]  
>使用方法可阅读：  
>[使用 HuggingFace / ModelScope 保存和下载文件 - licyk的小窝](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/)  
>[使用 Kaggle 进行模型训练 - licyk的小窝](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)


### SD Scripts Colab Jupyter NoteBook
[sd_scripts_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_colab.ipynb)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_scripts_colab.ipynb))：适用于 Colab 部署 [sd-scripts](https://github.com/kohya-ss/sd-scripts)，**自己写来玩的，还有用来开发和测试管理核心**，要用的话就参考 [SD Scripts Kaggle Jupyter NoteBook](#sd-scripts-kaggle-jupyter-notebook)。

Colab 链接：<a href="https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/sd_scripts_colab.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>


## 主要功能
1. 功能初始化：导入 SD WebUI All In One 所使用的功能
2. 参数配置：配置安装参数和远程访问方式
3. 应用参数配置：应用已设置的参数
4. 安装：根据配置安装对应的 WebUI
5. 启动：根据配置启动对应的 WebUI


## 其他功能
1. 自定义模型 / 扩展下载配置：设置要下载的模型 / 扩展参数
2. 自定义模型 / 扩展下载：根据配置进行下载模型 / 扩展
3. 更新：将已安装的 WebUI 进行更新


## 提示
1. 在参数配置界面，请填写工作区路径，选择要使用的 WebUI，根据自己的需求选择内网穿透方式（用于访问 WebUI 界面），再根据自己的需求选择模型和扩展。
2. 已知 CloudFlare、Gradio 内网穿透会导致 [Kaggle](https://www.kaggle.com) 平台强制关机，在使用 [Kaggle](https://www.kaggle.com) 平台时请勿勾选这两个选项。
3. 若使用 [Colab](https://colab.research.google.com) 平台，请注意该 Jupyter Notebook 无法在免费版的 Colab 账号中使用，运行前将会收到 Colab 的警告提示，强行运行将会导致 Colab 强制关机（如果 Colab 账号已付费订阅可直接使用该 Jupyter Notebook），可选择仓库中其他的  Jupyter Notebook（将 Colab 中禁止的 WebUI 移除了）。
4. [Ngrok](https://ngrok.com) 内网穿透的稳定性高，使用前需要填写 Ngrok Token，可在 [Ngrok](https://ngrok.com) 官网获取。
5. 在启动时将启动内网穿透，可在控制台输出中看到内网穿透地址，用于访问 WebUI 界面。

***

# Installer
适用于 Windows 平台部署 AI 的工具，无需提前安装任何环境（[Git](https://git-scm.com) / [Python](https://www.python.org/)），只需一键运行即可部署。

>[!IMPORTANT]  
>1. Installer 并不会使用系统中安装的 Git / Python，这是为了保证环境的独立性和可迁移性。并且因为环境的独立性和可迁移性，Installer 也可用做整合包制作器。
>2. 基于 Installer 的构建模式，可实现整合包制作全自动化，由 Installer 自动构建的整合包可在此列表查看：[AI 绘画 / 训练整合包列表](https://licyk.github.io/t/sd_portable)
>3. 由 Installer 制作的整合包说明可阅读：[AI 绘画 / 训练整合包 · licyk/sd-webui-all-in-one · Discussion #1](https://github.com/licyk/sd-webui-all-in-one/discussions/1)

[configure_env.bat](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/configure_env.bat))：配置 Installer 运行环境的一键配置脚本，首次使用 Installer 时需要运行一次该脚本。


## InvokeAI Installer
Windows 平台一键部署 [InvokeAI](https://github.com/invoke-ai/InvokeAI) 的脚本，包含启动，管理 InvokeAI 的工具。

详细的说明[点击此处](./invokeai_installer.md)阅读。


## SD-Trainer Installer
Windows 平台一键部署 [SD-Trainer](https://github.com/Akegarasu/lora-scripts) / [Kohya GUI](https://github.com/bmaltais/kohya_ss) 的脚本，包含启动，管理 SD-Trainer 的工具。

详细的说明[点击此处](./sd_trainer_installer.md)阅读。


## ComfyUI Installer
Windows 平台一键部署 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 的脚本，包含启动，管理 ComfyUI 的工具。

详细的说明[点击此处](./comfyui_installer.md)阅读。


## SD WebUI Installer
Windows 平台一键部署 [Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) / [Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) / [Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) / [Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic) / [Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu) / [SD.Next](https://github.com/vladmandic/automatic) 的脚本，包含启动，管理 Stable Diffusion WebUI 的工具。

详细的说明[点击此处](./stable_diffusion_webui_installer.md)阅读。


## SD-Trainer-Script Installer
>[!WARNING]  
>此部署工具部署的训练工具需要一定的编写训练命令基础，如果需要使用简单的模型训练工具，请使用 [SD-Trainer Installer](./sd_trainer_installer.md) 部署训练工具并使用。

Windows 平台一键部署 [sd-scripts](https://github.com/kohya-ss/sd-scripts) / [~~SimpleTuner~~](https://github.com/bghira/SimpleTuner) / [ai-toolkit](https://github.com/ostris/ai-toolkit) / [finetrainers](https://github.com/a-r-r-o-w/finetrainers) / [diffusion-pipe](https://github.com/tdrussell/diffusion-pipe) / [musubi-tuner](https://github.com/kohya-ss/musubi-tuner) 的脚本，包含启动，管理 SD-Trainer-Script 的工具。

详细的说明[点击此处](./sd_trainer_script_installer.md)阅读。


## Fooocus Installer
Windows 平台一键部署 [Fooocus](https://github.com/lllyasviel/Fooocus) / [Fooocus-MRE](https://github.com/MoonRide303/Fooocus-MRE) / [RuinedFooocus](https://github.com/runew0lf/RuinedFooocus) 的脚本，包含启动，管理 Fooocus 的工具。

详细的说明[点击此处](./fooocus_installer.md)阅读。


## Python Installer
[install_embed_python.ps1](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/install_embed_python.ps1)([源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/install_embed_python.ps1))：Windows 平台一键安装便携式 Python，可用做测试。


## Installer 自动化构建状态
|Github Action|Status|
|---|---|
|Build [SD WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) Portable|[![Build SD WebUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui.yml)|
|Build [SD WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) Portable|[![Build SD WebUI Forge](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge.yml)|
|Build [SD WebUI reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) Portable|[![Build SD WebUI reForge](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_reforge.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_reforge.yml)|
|Build [SD WebUI Forge Classic](https://github.com/Haoming02/sd-webui-forge-classic) Portable|[![SD WebUI Forge Classic](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge_classic.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_webui_forge_classic.yml)|
|Build [SD Next](https://github.com/vladmandic/automatic) Portable|[![Build SD WebUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_next.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_next.yml)|
|Build [ComfyUI](https://github.com/comfyanonymous/ComfyUI) Portable|[![Build ComfyUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_comfyui.yml)|
|Build [Fooocus](https://github.com/lllyasviel/Fooocus) Portable|[![Build Fooocus](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_fooocus.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_fooocus.yml)|
|Build [InvokeAI](https://github.com/invoke-ai/InvokeAI) Portable|[![Build InvokeAI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_invokeai.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_invokeai.yml)|
|Build [SD-Trainer](https://github.com/Akegarasu/lora-scripts) Portable|[![Build SD-Trainer](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_trainer.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_trainer.yml)|
|Build [Kohya GUI](https://github.com/bmaltais/kohya_ss) Portable|[![Build Kohya GUI](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_kohya_gui.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_kohya_gui.yml)|
|Build [SD Scripts](https://github.com/kohya-ss/sd-scripts) Portable|[![Build SD Scripts](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_scripts.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_sd_scripts.yml)|
|Build [Musubi Tuner](https://github.com/kohya-ss/musubi-tuner) Portable|[![Build Musubi Tuner](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_musubi_tuner.yml/badge.svg)](https://github.com/licyk/sd-webui-all-in-one/actions/workflows/build_musubi_tuner.yml)|
