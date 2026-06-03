# Notebook 快速开始

Notebook 是 SD WebUI All In One 的云端运行入口。只想尽快启动 WebUI 时，优先使用 Colab Notebook；需要训练模型或处理 Kaggle 数据集时，再使用 Kaggle Notebook。

## 最快路径

1. 在下表选择目标工具，点击 `进入 Colab`。
2. 在 Colab 中选择 `代码执行程序` -> `更改运行时类型`，硬件加速器选择 GPU。
3. 保持默认参数，从上到下运行 Notebook 单元。
4. 等待安装完成，复制输出日志里的访问地址打开 WebUI。

默认参数已经按可直接运行的方式配置。第一次使用不需要修改代码，也不需要先理解全部参数。

打开 WebUI 后，如果需要学习 SD WebUI、ComfyUI、InvokeAI 的界面使用、模型使用、提示词或工作流，可以继续阅读 [SD Note](https://licyk.github.io/SDNote/)。

## 直接运行

| 目标 | 进入 Colab | 适合场景 |
| --- | --- | --- |
| Stable Diffusion WebUI / Forge / reForge / SD.Next | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb) | 在 Colab 中运行 SD WebUI 系列。 |
| ComfyUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb) | 在 Colab 中运行 ComfyUI。 |
| Fooocus | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb) | 在 Colab 中运行 Fooocus。 |
| InvokeAI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb) | 在 Colab 中运行 InvokeAI。 |
| Qwen TTS WebUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb) | 在 Colab 中运行 Qwen TTS WebUI。 |
| SD Trainer / SD Trainer Next / Kohya GUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb) | 在 Colab 中运行训练 WebUI。 |

## 图形化配置

Colab 会把参数显示成图形化表单。常见控件包括：

- 输入框：填写路径、启动参数、模型链接、Token。
- 下拉框：选择分支预设、PyTorch 类型、模型种类。
- 复选框：启用镜像源、内网穿透、快速启动、GPU 检查、扩展和模型下载。

普通使用只需要操作这些表单，不需要展开“显示代码”。如果没有特殊需求，保持默认参数即可。

## 什么时候需要改参数

| 需求 | 修改位置 |
| --- | --- |
| 下载自己的模型 | 自定义模型下载单元中的模型类型、下载链接、文件名。 |
| 安装额外扩展或节点 | 扩展下载单元，或扩展/节点复选框。 |
| 使用私有模型或上传结果 | 填写 HuggingFace、ModelScope 或 WandB Token。 |
| 网络访问不稳定 | 启用 PyPI、GitHub、HuggingFace 或国内模型镜像。 |
| 更换启动方式 | 修改内网穿透复选框或启动参数文本框。 |
| 保存输出到 Google Drive | 保持快速启动或挂载选项启用，按提示授权 Google Drive。 |

## Kaggle 训练入口

训练任务建议阅读 [Kaggle 使用](./kaggle.md)。常用入口：

- [sd_trainer_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_trainer_scripts_kaggle.ipynb)：通用训练脚本。
- [sd_scripts_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/sd_scripts_kaggle.ipynb)：旧版 sd-scripts 流程。

!!! danger
    Kaggle 不允许上传 NSFW 内容。尝试上传包含 NSFW 图片的训练集可能导致 Kaggle 账号被封禁。

## 下一步

- 想看所有 Notebook：阅读 [选择 Notebook](./selection.md)。
- 想理解表单参数：阅读 [参数配置](./parameters.md)。
- 遇到运行问题：阅读 [故障排查](./troubleshooting.md)。
- 想学习 WebUI 实际使用：阅读 [SD Note](https://licyk.github.io/SDNote/)。
