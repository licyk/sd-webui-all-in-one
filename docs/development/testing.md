# 测试与检查

修改代码或文档后，应按变更范围选择对应检查。不要只依赖一次完整构建，先用静态搜索发现明显链接、语法和结构问题。

## Python 检查

Python 静态检查以 `pyproject.toml` 中的 `[tool.ruff]`、`[tool.ty]` 和 `[tool.python-docstring-checker]` 为准。默认检查范围聚焦 `sd_webui_all_in_one/`，排除 `sv_ttk` 主题源码和 patcher examples。

Ruff 负责 lint 和格式化检查。提交前至少运行 lint：

```bash
ruff check sd_webui_all_in_one
```

需要确认格式化状态时运行：

```bash
ruff format --check sd_webui_all_in_one
```

需要实际格式化时再运行：

```bash
ruff format sd_webui_all_in_one
```

ty 负责类型检查。运行时必须显式传入当前环境的 Python 可执行文件路径，避免 ty 使用到错误解释器或搜索路径：

```bash
python -m ty check --python /path/to/python --output-format concise sd_webui_all_in_one
```

如果使用当前 shell 中的解释器，可以先用 `python -c "import sys; print(sys.executable)"` 确认路径，再填入 `--python`。

只有在已经创建虚拟环境、安装项目依赖，并确认当前 shell 已激活该环境时，才可以省略 `--python`，直接运行 `python -m ty check sd_webui_all_in_one`。

python-docstring-checker 负责检查文档字符串完整性和参数说明。项目配置已限制默认 include / exclude 范围：

```bash
python -m python_docstring_checker .
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

## 测试贡献准则

新增或修改 Python 功能时，优先补充可离线运行的 pytest 用例。测试应验证行为边界、异常包装、命令参数、环境变量合并、路径处理和平台分支，而不是依赖真实外部服务。

- 测试文件放在 `tests/`，命名为 `test_*.py`；patcher 自身测试仍放在 `sd_webui_all_in_one/patcher/tests/`。
- 优先使用 `tmp_path`、`monkeypatch`、fake subprocess result、fake downloader、fake API client，避免污染用户环境。
- 不在测试中访问真实网络，不执行真实 `git clone`、`pip/uv install`、`aria2` 下载、WebUI 启动、GPU 检测或隧道启动。
- 涉及 Windows / Linux / macOS 差异时，断言行为结果，不依赖目录遍历顺序、POSIX 权限、命令字符串转义细节或某个平台专有路径。
- 需要模拟可选依赖缺失时，优先 monkeypatch 对应模块导入或入口函数，不通过卸载本机依赖实现。
- 修复 bug 时先补能复现问题的回归测试，再修实现；若现有行为本身不明确，应在测试名或断言中表达新的预期。

常用的测试粒度：

- 纯函数、解析器、版本比较：直接参数化输入输出。
- 下载、Git、包管理、隧道、Notebook / CLI 编排：mock 外部命令和网络边界，只断言传参、路径和异常。
- 产品级 manager：参数化覆盖相同行为，避免为每个产品复制大量重复断言。
- 文档或配置改动：至少跑相关静态搜索或文档构建，确认链接、标题和工作流说明没有失效。

本地补测建议先跑变更相关文件，再跑完整回归：

```bash
pytest tests/test_pytorch_manager_more.py
pytest tests/test_low_level_downloaders.py tests/test_downloader_file_ops.py
pytest
```

需要查看覆盖率时可运行：

```bash
pytest --cov=sd_webui_all_in_one --cov-report=term:skip-covered
```

覆盖率只作为发现缺口的辅助信号。优先补高风险路径：外部命令生成、安装/下载/更新编排、平台分支、异常处理和用户可见配置。

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
