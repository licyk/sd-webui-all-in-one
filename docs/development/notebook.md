# Notebook

`notebook/*.ipynb` 是云端运行入口，主要服务 Colab 和 Kaggle 用户。Notebook 不应复制大量安装逻辑，而是通过 `sd_webui_all_in_one.notebook_manager` 调用 Python 内核能力。

## Notebook 类型

| 类型 | 文件示例 | 维护重点 |
| --- | --- | --- |
| Colab WebUI | `stable_diffusion_webui_colab.ipynb`、`comfyui_colab.ipynb`、`fooocus_colab.ipynb`、`invokeai_colab.ipynb`、`qwen_tts_webui_colab.ipynb` | 图形化参数、默认参数直接运行、内网穿透、Drive 挂载和模型下载。 |
| Colab 训练 | `sd_trainer_colab.ipynb`、`sd_scripts_colab.ipynb` | 训练工具安装、素材路径、模型保存和训练命令入口。 |
| Kaggle 训练 | `sd_trainer_kaggle.ipynb`、`sd_scripts_kaggle.ipynb`、`sd_trainer_scripts_kaggle.ipynb`、`hdm_train_kaggle.ipynb` | Kaggle Input 导入、输出保存、HuggingFace / ModelScope 上传下载、NSFW 风险提示。 |
| All In One | `sd_webui_all_in_one.ipynb`、`sd_webui_all_in_one_colab.ipynb` | 多产品选择、统一参数配置和 Manager 组合调用。 |
| 旧版 / 实验用途 | README 或 Notebook 文档中标注为旧版、开发或测试用途的 Notebook | 保留来源说明，不作为新手优先入口。 |

## 图形化参数单元

Colab Notebook 使用表单单元让用户通过输入框、下拉框和勾选框设置参数。维护时要保持：

- 默认参数可以直接运行，用户不改参数也能完成基础安装和启动。
- 参数名和 Notebook 文档中的 [参数配置](../notebook/parameters.md) 保持一致。
- 复杂参数保留清晰说明，不把新手必须填写的项目藏到代码块内部。
- 启动、模型下载、扩展下载、文件下载等操作尽量拆成独立单元，方便用户按需执行。

## Manager API 调用

Notebook 中的产品管理逻辑应优先通过这些类完成：

- `SDWebUIManager`
- `ComfyUIManager`
- `FooocusManager`
- `InvokeAIManager`
- `QwenTTSWebUIManager`
- `SDTrainerManager`
- `SDTrainerScriptsManager`

公共能力来自 `notebook_manager.BaseManager`，包括 GPU 检查、Google Drive 挂载、模型下载、压缩包下载解压、HuggingFace / ModelScope 上传下载、内网穿透、清理 Notebook 输出和 Kaggle Input 导入。新增 Notebook 功能时，如果能力具有复用价值，应先补到 Manager，而不是只写在单个 `.ipynb` 单元里。

## Colab 与 Kaggle 差异

Colab 重点是 GPU 运行时、Google Drive 挂载、图形化参数、内网穿透链接和交互启动。Kaggle 重点是 GPU Session、Input 数据集、输出目录、HuggingFace / ModelScope 保存，以及平台内容政策风险。

涉及 Kaggle 训练素材时，文档和 Notebook 都需要保留 NSFW 风险提示。涉及 Colab 免费版时，需要提醒 GPU 可用性和运行时重置限制。

## 维护检查

- 修改 Notebook 后检查对应的用户文档：[Notebook 快速开始](../notebook/quick-start.md)、[选择 Notebook](../notebook/selection.md)、[Colab 使用](../notebook/colab.md)、[Kaggle 使用](../notebook/kaggle.md)。
- 参数新增或改名时，同步 [参数配置](../notebook/parameters.md) 和 [管理器 API](../notebook/manager-api.md)。
- Notebook 内导入的 Python API 改动时，同步 `notebook_manager/` 和测试说明。

