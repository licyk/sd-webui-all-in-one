# 云端运行快速开始

云端运行适合不想配置本地环境的用户。Colab 更适合快速体验 WebUI；Kaggle 更适合训练任务、数据集输入和保存输出。

## Colab 最快流程

1. 打开 [Notebook 快速开始](../notebook/quick-start.md)，选择目标工具并点击 `进入 Colab`。
2. 在 Colab 中选择 `代码执行程序` -> `更改运行时类型`，硬件加速器选择 GPU。
3. 保持默认参数，从上到下运行 Notebook 单元。
4. 等待安装完成，在输出日志中复制访问地址打开 WebUI。

Colab Notebook 已提供图形化参数表单。普通使用不需要展开代码，也不需要修改默认参数。

## 什么时候选 Kaggle

需要训练模型、导入 Kaggle 数据集、保存训练输出时，阅读 [Kaggle 使用](../notebook/kaggle.md)。训练相关 Notebook 的选择建议见 [选择 Notebook](../notebook/selection.md)。

!!! danger
    Kaggle 不允许上传 NSFW 内容。上传包含 NSFW 图片的训练集可能导致 Kaggle 账号被封禁。

## 下一步

- 想理解 Notebook 参数：阅读 [参数配置](../notebook/parameters.md)。
- 遇到 GPU、内网穿透、依赖安装或输出保存问题：阅读 [Notebook 故障排查](../notebook/troubleshooting.md)。
- WebUI 已经打开后：阅读 [启动后的下一步](./after-start.md)。
