# Kaggle 使用

Kaggle Notebook 适合训练任务，尤其是需要导入 Kaggle Dataset、运行训练脚本并将结果上传到 HuggingFace 或 ModelScope 的场景。

## 推荐 Notebook

| Notebook | 用途 | 配套教程 | 源码 |
| --- | --- | --- | --- |
| `sd_trainer_scripts_kaggle.ipynb` | 部署 sd-scripts、ai-toolkit、finetrainers、diffusion-pipe、musubi-tuner 等训练环境 | [Kaggle 训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)、[HF / ModelScope 文件保存](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_trainer_scripts_kaggle.ipynb) |
| `sd_scripts_kaggle.ipynb` | 旧版 sd-scripts 训练流程 | [Kaggle 训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)、[HF / ModelScope 文件保存](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/sd_scripts_kaggle.ipynb) |
| `hdm_train_kaggle.ipynb` | HDM 训练脚本 | [Kaggle 训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model) | [源码](https://github.com/licyk/sd-webui-all-in-one/blob/main/notebook/hdm_train_kaggle.ipynb) |

旧版 `fooocus_kaggle.ipynb` 和 `sd_trainer_kaggle.ipynb` 已停止维护，不建议作为新手首选。

!!! info
    使用 `sd_trainer_scripts_kaggle.ipynb` 或 `sd_scripts_kaggle.ipynb` 前，建议先阅读 [使用 Kaggle 进行模型训练](https://licyk.netlify.app/2025/01/16/use-kaggle-to-training-sd-model)。如果需要把训练结果保存到 HuggingFace / ModelScope，继续阅读 [使用 HuggingFace / ModelScope 保存和下载文件](https://licyk.netlify.app/2025/01/16/use-huggingface-or-modelscope-to-save-file/)。

## 基本流程

1. 在 Kaggle 创建 Notebook。
2. 打开右侧 `Session options`，将 `ACCELERATOR` 设置为 GPU。
3. 如需导入训练集，在右侧 `Input` 添加 Kaggle Dataset。
4. 根据 Notebook 参数单元设置 `WORKSPACE`、`WORKFOLDER`、镜像源、Token 和训练输出路径。
5. 运行安装环境单元。
6. 通过 Kaggle Input 导入训练集和模型。
7. 编写或修改训练命令。
8. 运行训练单元。
9. 根据需要上传训练结果到 HuggingFace 或 ModelScope。

## 数据导入

训练类 Notebook 使用管理器方法从 Kaggle Input 复制文件：

```python
sd_trainer_scripts.import_file_from_kaggle_input(INPUT_DATASET_PATH)
```

旧版 `SDScriptsManager` 中也保留了兼容方法：

```python
sd_scripts.import_kaggle_input(INPUT_DATASET_PATH)
```

导入后可使用 `display_directories_tree()` 查看目录结构，确认训练集、模型和配置文件是否在预期位置。

## 保存模型

训练完成后，可通过 `upload_files_to_repo()` 将输出上传到 HuggingFace 或 ModelScope。常见参数包括：

- `api_type`：`huggingface` 或 `modelscope`。
- `repo_id`：目标仓库 ID。
- `repo_type`：仓库类型，常用 `model`。
- `upload_path`：要上传的本地目录。
- `visibility`：仓库不存在时创建仓库的可见性。

使用前需要配置 `HF_TOKEN` 或 `MS_TOKEN`。训练类 Notebook 的参数单元中也包含 `USE_HF_TO_SAVE_MODEL` 和 `USE_MS_TO_SAVE_MODEL` 开关。

## 内网穿透限制

README 中明确提示：Cloudflare 和 Gradio 内网穿透可能导致 Kaggle 平台强制关机。在 Kaggle 中运行 WebUI 时，不建议启用这两项。

!!! warning
    Kaggle 平台对运行时、网络和内容有额外限制。训练前建议先确认 GPU 可用、账号已满足平台要求，并保留必要输出到外部仓库。

!!! danger
    Kaggle 不允许上传 NSFW 内容。尝试上传包含 NSFW 图片的训练集可能导致 Kaggle 账号被封禁。
