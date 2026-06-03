# 选择 Notebook

不同 Notebook 面向不同平台和任务。优先选择仍在维护、功能单一的 Notebook；旧版 All In One Notebook 只建议用于回看旧流程或临时测试。

## Colab 部署 WebUI

如果只想在线运行，点击“进入 Colab”即可直接打开。需要保存到本地时再使用“下载”链接。

| 目标 | 进入 Colab | 下载 | 源码 | 说明 |
| --- | --- | --- | --- | --- |
| Stable Diffusion WebUI / Forge / reForge / SD.Next | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/stable_diffusion_webui_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb) | 适用于 Colab 一键部署 SD WebUI 系列。 |
| ComfyUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/comfyui_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb) | 适用于 Colab 一键部署 ComfyUI。 |
| Fooocus | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/fooocus_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb) | 适用于 Colab 一键部署 Fooocus。 |
| InvokeAI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/invokeai_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb) | 适用于 Colab 一键部署 InvokeAI。 |
| Qwen TTS WebUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/qwen_tts_webui_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb) | 适用于 Colab 一键部署 Qwen TTS WebUI。 |
| SD Trainer / SD Trainer Next / Kohya GUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb) | 适用于 Colab 部署训练 WebUI。 |
| sd-scripts | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_colab.ipynb) | [下载](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_colab.ipynb) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_colab.ipynb) | 用于开发和测试管理核心，正式训练建议参考 Kaggle 训练 Notebook。 |

## Kaggle 训练

`sd_trainer_scripts_kaggle.ipynb` 和 `sd_scripts_kaggle.ipynb` 有配套教程。首次使用 Kaggle 训练时，建议先读 [使用 Kaggle 进行模型训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)；需要上传或下载 HuggingFace / ModelScope 文件时，再读 [使用 HuggingFace / ModelScope 保存和下载文件](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/)。

| 目标 | 推荐 Notebook | 配套教程 | 说明 |
| --- | --- | --- | --- |
| 通用训练脚本 | [sd_trainer_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_scripts_kaggle.ipynb) | [Kaggle 训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)、[HF / ModelScope 文件保存](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/) | 适用于 sd-scripts、ai-toolkit、finetrainers、diffusion-pipe、musubi-tuner。 |
| 旧版 sd-scripts 训练 | [sd_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_kaggle.ipynb) | [Kaggle 训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)、[HF / ModelScope 文件保存](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/) | 需要旧版 sd-scripts 流程时使用。 |
| HDM 训练 | [hdm_train_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/hdm_train_kaggle.ipynb) | [Kaggle 训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model) | 适用于 Kaggle / Colab 部署 HDM，属于测试性质脚本。 |

!!! danger
    Kaggle 不允许上传 NSFW 内容。尝试上传包含 NSFW 图片的训练集可能导致 Kaggle 账号被封禁。

## 开发或测试用途

- [sd_scripts_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_colab.ipynb)：用于 Colab 部署 sd-scripts，也可用于开发和测试管理核心；正式训练建议参考 Kaggle 训练 Notebook。
- `notebook/ruff.toml`：Notebook 目录下的 Ruff 配置，不是用户运行的 Notebook。

## 旧版 Notebook

以下 Notebook 已停止维护，可能存在的 BUG 不再修复：

- [sd_webui_all_in_one.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_webui_all_in_one.ipynb)：支持在一个 Notebook 中部署多种 WebUI。
- [sd_webui_all_in_one_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_webui_all_in_one_colab.ipynb)：面向 Colab 免费用户的旧版多 WebUI Notebook，可 [直接进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_webui_all_in_one_colab.ipynb)。
- [fooocus_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/fooocus_kaggle.ipynb)：旧版 Kaggle Fooocus Notebook。
- [sd_trainer_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_kaggle.ipynb)：旧版 Kaggle SD Trainer Notebook。

!!! warning
    旧版 Notebook 不建议作为新手首选。需要稳定部署时，优先使用按产品拆分的 Colab Notebook 或新的训练类 Kaggle Notebook。
