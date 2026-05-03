# 参数配置

Notebook 的参数通常集中在前几个代码单元中。Colab 版 Notebook 会把参数渲染为图形化表单，用户可以通过输入框、下拉框和复选框配置，不需要直接修改 Python 代码。

首次使用时建议保留默认值直接运行。默认参数已经覆盖常见安装和启动路径；确认能成功运行后，再按需要调整模型、扩展、镜像源和训练参数。

## 图形化表单

Colab 使用 `# @param` 标记生成表单控件。参数名通常显示在控件旁边，例如 `USE_UV`、`USE_REMOTE_MOE`、`SD_WEBUI_BRANCH_PRESET`。

| 控件 | 用途 | 示例参数 |
| --- | --- | --- |
| 文本框 | 填写路径、下载链接、Token、启动参数、镜像源地址 | `SD_WEBUI_PATH`、`model_url`、`NGROK_TOKEN`、`PIP_INDEX_MIRROR` |
| 下拉框 | 从预设选项中选择分支、模型类型或安装类型 | `SD_WEBUI_BRANCH_PRESET`、`PYTORCH_DEVICE_TYPE`、`model_type` |
| 复选框 | 开关某个功能 | `USE_UV`、`USE_GITHUB_MIRROR`、`USE_REMOTE_MOE`、`QUICK_LAUNCH` |

Notebook 页面中的“显示代码”只用于展开源码。普通用户只操作表单即可。

## 默认参数

默认参数可以直接运行，通常不需要先改配置。默认值会尽量选择适合 Colab 的安装路径、包管理器、内网穿透、快速启动和 GPU 检查选项。

建议新手只在这些情况修改参数：

- 需要下载指定模型或扩展。
- 需要填写 Ngrok、HuggingFace、ModelScope 或 WandB Token。
- 当前网络无法访问 GitHub、PyPI 或 HuggingFace，需要启用镜像。
- 需要切换 WebUI 分支或传入自定义启动参数。
- 需要把 Google Drive 中已有的模型目录挂载到 WebUI。

## 工作目录

- `WORKSPACE`：工作区路径。Colab 常见值为 `/content`，Kaggle 常见值为 `/kaggle`。
- `WORKFOLDER`：工作区中的项目目录名，例如 `stable-diffusion-webui`、`ComfyUI`、`Fooocus`、`sd-scripts`。

最终安装路径通常是：

```text
{WORKSPACE}/{WORKFOLDER}
```

## 安装加速

- `USE_UV`：使用 uv 安装 Python 软件包。
- `USE_PYPI_MIRROR`：启用 PyPI 镜像源。
- `USE_GITHUB_MIRROR`：启用 GitHub 镜像源。
- `USE_HF_MIRROR`：启用 HuggingFace 镜像源。
- `USE_CN_MODEL_MIRROR`：使用国内模型下载源，源码中会将模型资源切换到 ModelScope。

Manager 的 `install()` 方法还支持更细的镜像参数，例如 `pypi_index_mirror`、`pypi_extra_index_mirror`、`pypi_find_links_mirror`、`github_mirror`、`huggingface_mirror`。

## Token

- `HF_TOKEN` / `huggingface_token`：HuggingFace Token，用于私有资源下载或上传模型。
- `MS_TOKEN` / `modelscope_token`：ModelScope SDK 令牌。
- `WANDB_TOKEN` / `wandb_token`：训练类 Notebook 中用于配置 WandB。
- `NGROK_TOKEN` / `ngrok_token`：启用 Ngrok 内网穿透时需要。
- `zrok_token`：启用 Zrok 内网穿透时需要。

Token 为空时通常会被转换为 `None`，对应功能不会启用。

## GPU 检查

多数 Manager 的 `install()` 方法提供 `check_avaliable_gpu` 参数。启用后，如果当前环境没有可用 GPU，会抛出错误并给出 Colab 或 Kaggle 的运行时设置提示。

## 模型列表

不同 Manager 的模型列表格式略有差异。

SD WebUI、ComfyUI、Fooocus 常用字典列表：

```python
model_list = [
    {"url": "https://example.com/model.safetensors"},
    {"url": "https://example.com/lora.safetensors", "type": "loras", "filename": "demo.safetensors"},
]
```

SD Trainer 常用字典列表：

```python
model_list = [
    {"url": "https://example.com/base-model.safetensors"},
    {"url": "https://example.com/other-model.safetensors", "filename": "other.safetensors"},
]
```

通用 `BaseManager.get_model_from_list()` 和旧版 `SDScriptsManager` 使用列表格式：

```python
model_list = [
    ["https://example.com/skip.safetensors", 0],
    ["https://example.com/download.safetensors", 1],
    ["https://example.com/rename.safetensors", 1, "renamed.safetensors"],
]
```

其中第二项大于等于 `1` 时才会下载。

## 扩展和节点

- `extension_list`：Stable Diffusion WebUI 扩展列表，由 `SDWebUIManager.install_extension()` 安装。
- `custom_node_list`：ComfyUI 自定义节点列表，由 `ComfyUIManager.install_custom_node()` 安装。
- `EXTRA_LINK_DIR`：Colab 挂载 Google Drive 时额外持久化的目录或文件。

`EXTRA_LINK_DIR` 的格式：

```python
EXTRA_LINK_DIR = [
    {"link_dir": "models/loras"},
    {"link_dir": "custom_nodes"},
    {"link_dir": "extra_model_paths.yaml", "is_file": True},
]
```

## 启动参数和端口

WebUI Manager 通常通过 `run(params=...)` 或 `get_launch_command(params=...)` 传入启动参数。`params` 可以是字符串，也可以是列表。

```python
sd_webui.run("--xformers --listen")
comfyui.run(["--listen", "0.0.0.0"])
```

端口由 Manager 初始化时的 `port` 参数或 Notebook 中的端口配置控制，内网穿透会围绕该端口生成外部访问地址。

## 内网穿透

`get_tunnel_url()` 支持以下开关：

- `use_ngrok`
- `use_cloudflare`
- `use_remote_moe`
- `use_localhost_run`
- `use_gradio`
- `use_pinggy_io`
- `use_zrok`

!!! warning
    Kaggle 中不建议启用 Cloudflare 和 Gradio 内网穿透，README 中提示它们可能导致 Kaggle 强制关机。
