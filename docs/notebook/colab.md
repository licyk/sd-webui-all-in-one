# Colab 使用

Colab Notebook 适合临时部署 WebUI 或运行轻量训练任务。使用前需要先把运行时切换到 GPU，再按 Notebook 中的单元顺序执行。

Colab 版 Notebook 的参数通过图形化表单呈现。大多数情况下不需要编辑代码，保持默认参数即可直接运行；需要自定义时，在对应单元的输入框、下拉框和复选框中修改即可。

!!! note
    第一次使用时可以按 [Notebook 快速开始](./quick-start.md) 的流程直接运行。只要 Colab 已切换到 GPU，默认参数通常就能完成安装、启动和内网穿透。

## 打开 Notebook

下表中的 `Open in Colab` 是 README 中提供的直接运行入口，点击后会在 Google Colab 中打开对应 Notebook。需要离线保存或手动上传时，再使用源码或 release 下载链接。

| Notebook | Colab 打开 | 源码 |
| --- | --- | --- |
| Stable Diffusion WebUI | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb) | [stable_diffusion_webui_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/stable_diffusion_webui_colab.ipynb) |
| ComfyUI | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb) | [comfyui_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/comfyui_colab.ipynb) |
| Fooocus | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb) | [fooocus_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/fooocus_colab.ipynb) |
| InvokeAI | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb) | [invokeai_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/invokeai_colab.ipynb) |
| Qwen TTS WebUI | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb) | [qwen_tts_webui_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/qwen_tts_webui_colab.ipynb) |
| SD Trainer | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb) | [sd_trainer_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_colab.ipynb) |
| sd-scripts | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_colab.ipynb) | [sd_scripts_colab.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_colab.ipynb) |
| HDM Train | [Open in Colab](https://colab.research.google.com/github/licyk/sd-webui-all-in-one/blob/main/notebook/hdm_train_kaggle.ipynb) | [hdm_train_kaggle.ipynb](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/hdm_train_kaggle.ipynb) |

## 基本流程

1. 打开 Notebook。
2. 在 Colab 菜单中选择 `代码执行程序` -> `更改运行时类型`，硬件加速器选择 GPU。
3. 保持默认参数，或在图形化参数单元中调整镜像源、模型列表、Token、内网穿透方式。
4. 运行初始化和安装单元。
5. 需要持久化输出时运行 Google Drive 挂载逻辑。
6. 运行启动单元，从输出日志复制访问地址。

## 图形化参数面板

Colab 会把 Notebook 单元中的 `# @param` 配置渲染成表单控件。常见控件包括：

- 文本框：用于填写安装路径、启动参数、镜像源地址、模型下载链接、保存文件名、Token。
- 下拉框：用于选择 WebUI 分支预设、PyTorch 安装类型、模型种类。
- 复选框：用于启用 uv、镜像源、内网穿透、快速启动、GPU 检查、日志清理、扩展下载和模型下载。

默认参数已经覆盖常见 Colab 使用场景。第一次运行时可以只做两件事：

1. 切换 Colab 运行时到 GPU。
2. 从上到下点击运行按钮执行 Notebook。

如果需要更精细的配置，再修改这些表单项：

| 场景 | 建议修改的表单项 |
| --- | --- |
| 更换 WebUI 分支 | 分支预设下拉框，例如 `SD_WEBUI_BRANCH_PRESET`。 |
| 添加启动参数 | 启动参数文本框，例如 `SD_WEBUI_LAUNCH_ARGS_OPT`。 |
| 加速依赖安装 | `USE_UV`、`USE_PYPI_MIRROR`、`USE_GITHUB_MIRROR`。 |
| 改用模型镜像 | `USE_HF_MIRROR`、`HUGGINGFACE_MIRROR`、`USE_CN_MODEL_MIRROR`。 |
| 选择访问方式 | `USE_REMOTE_MOE`、`USE_LOCALHOST_RUN`、`USE_PINGGY_IO`、`USE_CLOUDFLARE`、`USE_GRADIO`、`USE_NGROK`。 |
| 安装扩展或节点 | 扩展、节点复选框，或扩展下载链接输入框。 |
| 下载内置模型 | 模型设置中的模型复选框。 |
| 下载自定义模型 | 自定义模型下载单元中的模型类型、下载链接和文件名。 |
| 持久化已有模型目录 | 额外挂载目录设置，例如 Stable Diffusion、LoRA、VAE 等目录链接选项。 |

!!! note
    表单下方的“显示代码”用于展开实际 Python 代码。普通使用不需要展开；只有在调试或二次开发时才需要查看。

!!! info
    默认值一般已经启用了适合 Colab 的快速路径，例如常用内网穿透、快速启动、GPU 检查和基础优化。除非知道自己要改什么，否则保持默认值更稳。

## 输出保存

Colab Notebook 通过各产品 Manager 的 `mount_drive()` 方法挂载 Google Drive，并将常用输出目录或配置文件链接到 `MyDrive` 下的固定目录。

| Manager | Google Drive 输出目录 | 默认持久化内容 |
| --- | --- | --- |
| `SDWebUIManager` | `MyDrive/sd_webui_output` | `outputs`、`config_states`、`params.txt`、`config.json`、`ui-config.json`、`styles.csv` |
| `ComfyUIManager` | `MyDrive/comfyui_output` | `output`、`user`、`input`、`extra_model_paths.yaml` |
| `FooocusManager` | `MyDrive/fooocus_output` | `outputs`、`presets`、`language`、`wildcards`、`config.txt` |
| `QwenTTSWebUIManager` | `MyDrive/qwen_tts_webui_output` | `outputs`、`config.json` |
| `SDTrainerManager` | `MyDrive/sd_trainer_output` | `outputs`、`output`、`config`、`train`、`logs` |
| `InvokeAIManager` | `MyDrive/invokeai_output` | 设置 `INVOKEAI_ROOT` 到该目录 |

## 内网穿透

WebUI 启动前通常会调用 `get_tunnel_url()`。可用方式包括 Ngrok、Cloudflare、remote.moe、localhost.run、Gradio、pinggy.io、Zrok。

Ngrok 和 Zrok 需要填写对应 Token。其他方式不一定需要账号，但稳定性取决于平台和网络环境。

## Colab 限制

!!! warning
    旧版 `sd_webui_all_in_one.ipynb` 在 Colab 免费账号中可能触发警告或强制关机。新用户优先使用按产品拆分的 Colab Notebook。

!!! note
    如果安装过程中 Colab 断开，重新连接后通常需要重新执行初始化和安装相关单元；保存在 Google Drive 的输出目录不会随运行时释放而消失。
