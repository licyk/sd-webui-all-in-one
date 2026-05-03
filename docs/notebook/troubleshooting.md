# Notebook 故障排查

Notebook 出错时，先确认运行平台、GPU、工作目录、网络和 Token。多数问题发生在运行时类型未切换、云端网络不稳定、输出目录未持久化或内网穿透不可用。

## 没有可用 GPU

如果启用了 `check_avaliable_gpu`，Manager 会在没有 GPU 时抛出错误。

Colab 中需要进入 `代码执行程序` -> `更改运行时类型`，将硬件加速器设置为 GPU。

Kaggle 中需要进入 `Notebook` -> `Session options`，将 `ACCELERATOR` 设置为 GPU。源码提示如果 Kaggle 无法使用 GPU，需要检查账号是否绑定手机号或尝试更换账号。

## Google Drive 挂载失败

`mount_drive()` 只在 Colab 环境中可用。非 Colab 环境调用时会输出当前环境无法挂载 Google Drive 的警告。

如果 Colab 挂载失败，重新运行挂载单元，或在左侧文件面板确认 `/content/drive/MyDrive` 是否已经存在。

## Kaggle 强制关机

README 中提示 Cloudflare 和 Gradio 内网穿透可能导致 Kaggle 平台强制关机。在 Kaggle 中运行 WebUI 时，关闭 `USE_CLOUDFLARE` 和 `USE_GRADIO_SHARE`，优先使用 remote.moe、localhost.run 或其他可用方式。

!!! danger
    Kaggle 不允许上传 NSFW 内容。上传包含 NSFW 图片的训练集可能导致账号被封禁。

## 内网穿透没有地址

检查以下项目：

- 目标 WebUI 的端口是否和 Manager 初始化的 `port` 一致。
- Ngrok 或 Zrok 是否填写了有效 Token。
- 当前平台是否允许该隧道方式。
- WebUI 是否已经成功启动并监听端口。

可以先只启用一种内网穿透方式，确认可用后再增加其他方式。

## 依赖安装失败

安装失败通常和网络、镜像源或 PyTorch 包版本有关。

- 国内网络可尝试启用 `USE_PYPI_MIRROR`、`USE_GITHUB_MIRROR`、`USE_HF_MIRROR` 或 `USE_CN_MODEL_MIRROR`。
- 如果自定义了 PyTorch 或 xFormers 包名，先恢复默认值确认流程能否跑通。
- 如果 uv 安装异常，可把 `USE_UV` 改为 `False` 退回 Pip。

## 模型没有下载

检查模型列表格式是否符合对应 Manager：

- SD WebUI、ComfyUI、Fooocus 使用带 `url` 的字典列表。
- `BaseManager.get_model_from_list()` 使用 `[url, status, filename]` 列表，只有 `status >= 1` 才下载。
- 文件名参数为空时，下载器会从 URL 中解析保存名称。

## 输出没有保存

Colab 运行时释放后，本地 `/content` 下的文件会丢失。需要保存输出时，先运行 `mount_drive()`，确认 Google Drive 中出现对应输出目录。

Kaggle 训练结果建议上传到 HuggingFace 或 ModelScope，或确认输出位于 Kaggle 会保留的输出目录中。

## Notebook 单元顺序错误

如果直接跳到启动或训练单元，可能因为变量、Manager 实例或依赖未初始化而失败。重新从初始化、参数配置、安装环境开始按顺序执行。

## 旧版 Notebook 问题

`sd_webui_all_in_one.ipynb`、`sd_webui_all_in_one_colab.ipynb`、`fooocus_kaggle.ipynb`、`sd_trainer_kaggle.ipynb` 已停止维护。遇到旧版问题时，优先切换到当前按产品拆分的 Notebook 或训练类 Notebook。
