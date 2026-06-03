# Jupyter Notebook 概览

SD WebUI All In One 提供一组面向 Colab、Kaggle 和通用 Jupyter 环境的 Notebook，用于在云端快速部署 WebUI、准备训练环境、下载模型和保存输出文件。

Notebook 基于 `sd_webui_all_in_one` 内核和 `notebook_manager` 管理器封装。多数页面按“配置参数、安装环境、启动服务、下载或上传资源”的顺序组织，第一次使用时建议从上到下依次执行单元。

Colab 版 Notebook 支持图形化方式配置参数。用户通常不需要打开或修改 Python 代码，只需要在页面中使用输入框、下拉框和复选框设置安装路径、分支预设、镜像源、内网穿透、扩展和模型等选项。默认参数已经按可直接运行的方式配置，首次使用可以保留默认值运行。

## 立即开始

如果目标是在云端快速打开一个 WebUI，直接选择下面的 Colab 入口即可。打开后切换到 GPU，保持默认参数，从上到下运行单元。

| 目标 | 进入 Colab | 说明 |
| --- | --- | --- |
| Stable Diffusion WebUI / Forge / reForge / SD.Next | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb) | 运行 SD WebUI 系列。 |
| ComfyUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb) | 运行 ComfyUI。 |
| Fooocus | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb) | 运行 Fooocus。 |
| InvokeAI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb) | 运行 InvokeAI。 |
| Qwen TTS WebUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb) | 运行 Qwen TTS WebUI。 |
| SD Trainer / SD Trainer Next / Kohya GUI | [进入 Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb) | 运行训练 WebUI。 |

更完整的新手流程见 [Notebook 快速开始](./quick-start.md)。

## 支持内容

当前 Notebook 覆盖以下工具：

- Stable Diffusion WebUI、Forge、reForge、Forge Classic、AMDGPU、SD.Next。
- ComfyUI。
- Fooocus。
- InvokeAI。
- Qwen TTS WebUI。
- SD Trainer、SD Trainer Next、Kohya GUI。
- sd-scripts、ai-toolkit、finetrainers、diffusion-pipe、musubi-tuner。
- HDM 训练脚本。

## 推荐阅读顺序

1. 想立刻运行：阅读 [Notebook 快速开始](./quick-start.md)。
2. 不确定选哪个：阅读 [选择 Notebook](./selection.md)。
3. 根据平台阅读 [Colab 使用](./colab.md) 或 [Kaggle 使用](./kaggle.md)。
4. 在运行前查看 [参数配置](./parameters.md)，尤其是工作目录、镜像源、Token 和内网穿透。
5. 需要自定义流程时参考 [管理器 API](./manager-api.md)。
6. 出错时参考 [故障排查](./troubleshooting.md)。

## Notebook 文件位置

源码位于仓库的 `notebook/` 目录。发布版下载链接通常位于 GitHub Release 的 `archive` 附件中，源码链接可直接打开对应 `.ipynb` 文件。

!!! note
    README 中的蓝色 Notebook 名称通常指向可下载的发布版 `.ipynb` 文件；源码链接指向仓库中的当前文件。

## 运行原则

- 先选择运行时 GPU，再执行安装单元。
- 不熟悉参数时保留默认值；默认配置通常可以直接完成安装和启动。
- 需要调整时优先使用 Colab 页面上的图形化控件，只修改工作目录、模型链接、Token、内网穿透方式等必要项目。
- Colab 中需要保存输出时使用 Google Drive 挂载。
- Kaggle 中需要导入数据时使用 Kaggle Input，再通过管理器复制到工作区。
- WebUI 启动后，从输出日志中复制内网穿透地址访问界面。
