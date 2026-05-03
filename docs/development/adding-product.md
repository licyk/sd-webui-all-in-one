# 新增产品支持

新增一个 WebUI 或训练工具支持时，不只是加一个安装函数。项目中 Python CLI、Installer、Notebook、文档、构建脚本和整合包入口通常都需要同步。

## Python 内核

1. 在 `base_manager/` 中新增或扩展产品基础能力，包括安装、更新、启动、环境检查、模型 / 扩展管理和版本管理入口。
2. 在 `cli_manager/` 中新增产品 CLI 文件和注册函数，并在 `cli_manager/cli.py` 中注册。
3. 如果需要云端 Notebook 支持，在 `notebook_manager/` 中新增对应 Manager 类。
4. 如果需要模型预设，在 `model_downloader/` 中补充模型类型、保存路径和模型列表。
5. 如果涉及 PyTorch 特殊组合，在 `pytorch_manager/` 中确认版本选择和设备检测逻辑。

## Installer

1. 新增或复制一个产品安装器脚本，并调整参数区、默认安装路径、内核路径前缀候选、产品根目录环境变量。
2. 写清普通安装、更新模式和构建模式。
3. 生成必要管理脚本，例如 `launch.ps1`、`update.ps1`、`terminal.ps1`、`download_models.ps1`、`version_manager.ps1`。
4. 同步 `settings.ps1` 菜单、帮助信息和文档链接。
5. 检查 CI 或整合包构建是否需要加入该安装器。

## Notebook

1. 新增 Colab 或 Kaggle Notebook 时，优先通过 `notebook_manager` 调用 Python 能力。
2. 参数单元保持图形化配置，默认参数应能直接运行。
3. Colab Notebook 补充打开链接、Drive 挂载、内网穿透和模型下载。
4. Kaggle Notebook 补充 Input 导入、输出保存和 NSFW 风险提示。
5. 同步 [Notebook 文档](../notebook/index.md) 中的选择、参数和故障排查说明。

## 文档与入口

新增产品时至少检查这些文档入口：

- [快速开始](../quick-start/index.md)
- [安装器使用](../installer/index.md)
- [下载器与启动器](../tools/index.md)
- [Jupyter Notebook](../notebook/index.md)
- [命令行工具](../cli/index.md)
- [整合包与实用指南](../portable/index.md)

如果产品支持整合包，还需要检查下载器列表、Launcher 支持列表、截图和整合包构建工作流。

## 验收清单

- CLI 能显示新产品命令并执行基础操作。
- Installer 能普通安装、更新模式刷新管理脚本、构建模式无交互运行。
- Notebook 默认参数可完成基础运行。
- 用户文档入口和维护文档入口都能构建通过。
- 对应测试、lint 和 Zensical 构建通过。

