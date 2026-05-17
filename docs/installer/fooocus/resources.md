# Fooocus Installer 模型与资源

## 资源管理

### 下载模型
可以使用 `download_models.ps1` 脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。

### 设置模型下载源
!!! info
    该设置可通过 [管理 Fooocus Installer 设置](config.md#fooocus-installer_1) 中提到的 `settings.ps1` 进行修改。

禁用自动镜像源选择后，使用 `download_models.ps1` 脚本下载模型时默认下载源为 [ModelScope](https://modelscope.cn)；如果需要切换到 [HuggingFace](https://huggingface.co) 下载源，可以在和脚本同级的路径中创建一个 `disable_model_mirror.txt` 文件，再次启动 `download_models.ps1` 脚本时下载模型将使用 [HuggingFace](https://huggingface.co) 下载源。

!!! warning
    如果自动镜像源选择保持启用，模型下载源会由 Python CLI 自动决定，并会覆盖 `disable_model_mirror.txt` 的手动设置。需要固定使用 HuggingFace 或 ModelScope 时，请先在管理脚本同级目录创建 `disable_auto_mirror.txt`，或运行管理脚本时传入 `-DisableAutoMirror`。

### Fooocus 使用方法
- [Fooocus Advanced · lllyasviel/Fooocus · Discussion #117](https://github.com/lllyasviel/Fooocus/discussions/117)
- [Fooocus Advanced 2 · lllyasviel/Fooocus · Discussion #830](https://github.com/lllyasviel/Fooocus/discussions/830)
