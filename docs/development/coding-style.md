# 编码风格

本项目同时包含 Python、PowerShell、Jupyter Notebook 和 Zensical Markdown。维护时优先遵循现有代码风格，减少无关格式化和跨模块重构。

## Python

- 支持 Python 3.10+，`pyproject.toml` 中 pytest 覆盖 3.10 到 3.14。
- 使用 4 空格缩进，Ruff 配置 `line-length = 200`，格式化倾向双引号。
- 路径处理优先使用 `pathlib.Path`，需要传给命令、环境变量或日志时再转字符串。
- 外部命令走 `run_cmd()`，下载走 `downloader`，日志走 `get_logger()`。
- 公共能力放到 `base_manager/`、`downloader/`、`pytorch_manager/`、`model_downloader/` 等模块，不在 CLI 或 Notebook 中重复实现。
- 解析、版本比较、依赖判断、路径判断等纯逻辑应优先写测试。

## PowerShell

- 安装器需要兼容 Windows、Linux 和 macOS。
- 路径统一通过 `Join-NormalizedPath` 或已有路径工具处理。
- 参数新增时同步参数帮助、`Get-HelpMessage`、生成的管理脚本、`settings.ps1` 菜单、构建模式和用户文档。
- 管理脚本应复用安装器传入的环境变量、镜像、代理和内核路径前缀，不写死产品目录。
- 修改安装器后至少检查 PSScriptAnalyzer 的 Error / ParseError 级别结果。

## Notebook

- `notebook/ruff.toml` 使用 `line-length = 300`。
- Colab 参数单元要保持图形化配置体验，默认参数应能直接运行。
- 平台差异写在说明单元中：Colab 关注 GPU / Drive / 内网穿透，Kaggle 关注 Input / 输出保存 / 内容政策。
- 复用能力优先补到 `notebook_manager/`，不要把复杂逻辑长期留在单个 Notebook 单元里。

## Markdown

- 文档使用 Zensical 兼容 Markdown。
- 每个页面只保留一个真实一级标题。
- 使用 `!!! note`、`!!! info`、`!!! warning`、`!!! danger`，不要使用 GitHub 风格 callout 语法。
- 下载入口使用 Zensical 按钮语法，板块卡片使用 grid cards。
- 不写手动 `# 目录`，依赖站点目录生成。
- 站内链接使用相对 `.md` 路径，图片放在 `docs/assets/images/` 下并按文档结构整理。
