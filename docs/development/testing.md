# 测试与检查

修改代码或文档后，应按变更范围选择对应检查。不要只依赖一次完整构建，先用静态搜索发现明显链接、语法和结构问题。

## Python 检查

Ruff 工作流只检查 `sd_webui_all_in_one/`：

```bash
ruff check sd_webui_all_in_one
```

pytest 工作流会在 Python 3.10 到 3.14 上运行：

```bash
pytest
```

本地可先针对相关测试文件运行，例如：

```bash
pytest tests/test_package_analyzer.py
pytest tests/test_version_manager.py
```

## PowerShell 检查

CI 会先用每个安装器的更新模式生成管理脚本，再对所有 `.ps1` 执行 PSScriptAnalyzer 的 Error / ParseError 检查。维护安装器时建议至少确认：

```powershell
pwsh -File installer/comfyui_installer.ps1 -InstallPath ./comfyui -UseUpdateMode
Invoke-ScriptAnalyzer -Path installer/comfyui_installer.ps1 -Severity @("Error", "ParseError")
```

实际修改哪个安装器，就对哪个安装器和生成的管理脚本做同类检查。

## 文档检查

常用静态检查需要覆盖旧 GitHub callout、HTML 折叠块、手写目录和已删除环境页链接。为了避免维护文档自身触发检查，实际命令可在终端中组合这些关键词后执行：

```bash
pattern='旧 callout|HTML details|HTML summary|手写目录|旧环境页链接'
rg -n "$pattern" docs zensical.toml
```

检查新增页面是否只有一个真实一级标题：

```bash
rg -n "^# " docs/development/*.md
```

构建 Zensical 文档：

```bash
zensical build
```

CI 文档构建使用 `zensical build --clean`，本地排查链接和 Markdown 问题时可先运行普通构建。

## 内容抽查

- Python 入口、依赖和工具配置以 `pyproject.toml` 为准。
- Lint、pytest、docs 构建流程以 `.github/workflows/` 为准。
- Installer 行为以 `installer/*.ps1` 为准。
- Notebook 参数和流程以 `notebook/*.ipynb` 与 `sd_webui_all_in_one/notebook_manager/` 为准。
- 用户说明以 `docs/` 中对应板块为准，修改实现后不要忘记同步用户文档。
