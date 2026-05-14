# 开发维护

这个板块面向项目维护者和贡献者，用来记录 `sd_webui_all_in_one/`、`installer/`、`notebook/` 以及 patcher 热补丁框架的架构、编码约定和验证方式。它不替代用户文档，而是帮助后续维护时快速判断“改哪里、同步哪里、怎么检查”。

## 核心代码

| 模块 | 作用 | 主要维护入口 |
| --- | --- | --- |
| Python 内核 | 提供 CLI、WebUI 管理能力、下载、镜像、PyTorch 版本、模型、隧道和环境检查。 | [Python 内核](./python-core.md) |
| Patcher 热补丁框架 | 提供 import-time 补丁、环境变量 bootstrap、runtime 通信和扩展补丁配方。 | [Patcher 使用文档](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_webui_all_in_one/patcher/README.md) |
| PowerShell Installer | 在 Windows / Linux / macOS 上安装 WebUI / 训练工具，并生成启动、更新、模型下载、版本管理等管理脚本。 | [Installer](./installer.md) |
| Notebook | 在 Colab / Kaggle 中用图形化参数单元调用 Python 管理器完成云端安装、模型下载、启动和训练。 | [Notebook](./notebook.md) |

## 推荐阅读顺序

1. 先读 [整体架构](./architecture.md)，了解 CLI、Installer、Notebook 和 Python 内核之间的关系。
2. 按要维护的区域阅读 [Python 内核](./python-core.md)、[Patcher 使用文档](https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_webui_all_in_one/patcher/README.md)、[Installer](./installer.md) 或 [Notebook](./notebook.md)。
3. 修改前阅读 [编码风格](./coding-style.md)，确认命名、路径、日志、参数和文档同步规则。
4. 修改后按 [测试与检查](./testing.md) 跑对应检查。
5. 如果是新增 WebUI 或训练工具支持，按 [新增产品支持](./adding-product.md) 的清单逐项同步。

## 和用户文档的关系

用户文档位于 [快速开始](../quick-start/index.md)、[安装器使用](../installer/index.md)、[下载器与启动器](../tools/index.md)、[Jupyter Notebook](../notebook/index.md)、[命令行工具](../cli/index.md) 等板块。开发维护文档只记录实现结构和维护规则；当源码行为、参数、入口或生成脚本变化时，需要同时更新用户文档中对应的使用说明。
