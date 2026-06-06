# 管理器 API

Notebook 使用 `sd_webui_all_in_one.notebook_manager` 中的 Manager 类封装安装、启动、下载、上传和持久化逻辑。需要改写 Notebook 流程时，可以直接调用这些 API。

## 公开类

`sd_webui_all_in_one.notebook_manager.__init__` 导出以下类：

- `BaseManager`
- `SDWebUIManager`
- `ComfyUIManager`
- `FooocusManager`
- `InvokeAIManager`
- `QwenTTSWebUIManager`
- `SDTrainerManager`
- `SDTrainerScriptsManager`
- `SDScriptsManager`

!!! warning
    `SDScriptsManager` 在源码中已标记为弃用，并提示使用 `SDTrainerScriptsManager` 代替。旧 Notebook 仍可能使用它以保持兼容。

## 初始化

Manager 初始化通常需要工作区、项目目录、可选 Token 和端口：

```python
from sd_webui_all_in_one import SDWebUIManager

sd_webui = SDWebUIManager(
    workspace="/content",
    workfolder="stable-diffusion-webui",
    hf_token=None,
    ms_token=None,
    port=7860,
)
```

## 公共能力

`BaseManager` 提供所有产品通用的能力：

- `check_avaliable_gpu()`：检查当前环境是否有 GPU。
- `mount_google_drive_for_notebook()`：在 Colab 中挂载 Google Drive。
- `link_to_google_drive()`：将本地目录或文件链接到 Google Drive。
- `get_model()`：从 URL 下载单个模型文件。
- `get_model_from_list()`：按列表下载多个模型。
- `download_and_extract()`：下载压缩包并解压。
- `download_file_from_url()`：从链接下载任意文件。
- `upload_files_to_repo()`：上传文件到 HuggingFace 或 ModelScope。
- `download_files_from_repo()`：从 HuggingFace 或 ModelScope 下载文件。
- `get_repo_files_metadata()`：获取 HuggingFace 或 ModelScope 仓库文件元数据。
- `get_repo_file_download_url()`：获取 HuggingFace 或 ModelScope 仓库中文件的下载地址。
- `get_tunnel_url()`：启动内网穿透并打印访问地址。
- `stop_all_tunnels()`：停止已启动的内网穿透。
- `clear_output()`：清理 Jupyter Notebook 输出。
- `display_directories_tree()`：显示目录内容。
- `import_file_from_kaggle_input()`：从 Kaggle Input 导入文件。

## 安装和启动

各产品 Manager 都提供 `install()`，用于配置镜像源、安装管理器依赖、安装目标项目、下载模型并配置优化项。

常见调用：

```python
comfyui.install(
    use_uv=True,
    use_pypi_mirror=False,
    use_github_mirror=False,
    use_cn_model_mirror=False,
    check_avaliable_gpu=True,
)
```

WebUI 类 Manager 通常提供 `run()`：

```python
comfyui.run("--listen 0.0.0.0")
```

也可以先拿到启动命令：

```python
cmd = comfyui.get_launch_command("--listen 0.0.0.0")
```

`InvokeAIManager.run()` 直接调用 InvokeAI 的 `run_app()`。

## 产品差异

| Manager | 主要差异 |
| --- | --- |
| `SDWebUIManager` | 支持安装扩展、更新扩展、下载不同类型的 SD 模型。 |
| `ComfyUIManager` | 支持安装和更新自定义节点，默认模型类型为 `checkpoints`。 |
| `FooocusManager` | 支持根据 preset 配置预下载模型。 |
| `InvokeAIManager` | 支持设置 `INVOKEAI_ROOT` 并导入下载的模型。 |
| `QwenTTSWebUIManager` | 面向 Qwen TTS WebUI，默认持久化输出和 `config.json`。 |
| `SDTrainerManager` | 安装后会检查 `protobuf` 版本，并启动 `gui.py` 或 `kohya_gui.py`。 |
| `SDTrainerScriptsManager` | 面向训练脚本环境，支持配置 WandB Token 和 Git 用户信息。 |

## 内网穿透示例

```python
with sd_webui.tun_manager:
    urls = sd_webui.get_tunnel_url(
        use_remote_moe=True,
        use_localhost_run=True,
        webui_name="Stable Diffusion WebUI",
    )
    sd_webui.run("--xformers")
```

也可以直接调用，但需要自行停止：

```python
urls = sd_webui.get_tunnel_url(use_ngrok=True, ngrok_token="your-token")
sd_webui.stop_all_tunnels()
```

## 仓库上传下载

从仓库下载文件：

```python
manager.download_files_from_repo(
    api_type="huggingface",
    repo_id="owner/repo",
    local_dir="/kaggle/dataset",
    repo_type="model",
    folder="dataset",
    revision="main",
)
```

获取仓库文件元数据：

```python
files = manager.get_repo_files_metadata(
    api_type="modelscope",
    repo_id="owner/repo",
    repo_type="model",
    revision="master",
)
```

获取仓库中单个文件的下载地址：

```python
url = manager.get_repo_file_download_url(
    api_type="huggingface",
    repo_id="owner/repo",
    file_path="dataset/data.json",
    repo_type="model",
    revision="main",
)
```

上传训练结果：

```python
manager.upload_files_to_repo(
    api_type="modelscope",
    repo_id="owner/repo",
    upload_path="/kaggle/output",
    repo_type="model",
    visibility=False,
)
```
