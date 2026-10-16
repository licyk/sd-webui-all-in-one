"""测试会话隔离

保证测试产生的文件 (Git 配置, 缓存, 快照, pycache 等) 只会落在临时目录中, 而不会写入项目目录:

- 在导入 ``sd_webui_all_in_one`` 之前, 将运行时的启动目录和缓存目录指向会话临时目录,
  使 ``SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / ".gitconfig"`` 等默认路径不再解析到项目目录
- 整个测试会话的工作目录切换到临时目录, 使相对路径和子进程的输出不会写入项目目录
- 每个测试结束后恢复 ``os.environ``, 防止被测代码直接修改的环境变量 (例如 ``PYTHONPYCACHEPREFIX``)
  泄漏到后续测试启动的子进程中
- 会话结束时检查项目目录, 若出现测试遗留的新文件则使测试会话失败
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
"""项目根目录"""

SESSION_ROOT = Path(tempfile.mkdtemp(prefix="sd-webui-all-in-one-tests-")).resolve()
"""测试会话使用的临时目录"""

SESSION_WORKDIR = SESSION_ROOT / "workdir"
"""测试会话的工作目录"""

# 必须在导入 sd_webui_all_in_one 之前设置, 这些路径在 sd_webui_all_in_one.config 导入时确定
os.environ["SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH"] = (SESSION_ROOT / "launch").as_posix()
os.environ["SD_WEBUI_ALL_IN_ONE_CACHE_PATH"] = (SESSION_ROOT / "launch" / "cache").as_posix()
os.environ["SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR"] = (SESSION_ROOT / "launch" / "snapshots").as_posix()
os.environ["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH"] = (SESSION_ROOT / "launch" / "patcher_config.json").as_posix()

IGNORED_PROJECT_ENTRIES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "build",
}
"""检查项目目录遗留文件时忽略的条目 (缓存和构建产物)"""

_PROJECT_FILES_KEY = pytest.StashKey[set[str]]()


def _snapshot_project_files(root: Path) -> set[str]:
    """收集项目目录中的文件和目录

    Args:
        root (Path): 项目根目录

    Returns:
        set[str]: 相对于项目根目录的路径集合
    """
    entries: set[str] = set()
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_PROJECT_ENTRIES and not d.endswith(".egg-info")]
        rel = Path(current).relative_to(root)
        entries.update((rel / name).as_posix() for name in dirs)
        entries.update((rel / name).as_posix() for name in files if name not in IGNORED_PROJECT_ENTRIES and not name.startswith(".coverage"))
    return entries


def pytest_sessionstart(session: pytest.Session) -> None:
    """记录测试开始前的项目文件

    Args:
        session (pytest.Session): pytest 测试会话
    """
    session.config.stash[_PROJECT_FILES_KEY] = _snapshot_project_files(PROJECT_ROOT)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """检查测试是否在项目目录中遗留了文件, 并清理会话临时目录

    Args:
        session (pytest.Session): pytest 测试会话
        exitstatus (int): 测试会话的退出状态
    """
    shutil.rmtree(SESSION_ROOT, ignore_errors=True)
    before = session.config.stash.get(_PROJECT_FILES_KEY, None)
    if before is None:
        return
    leaked = sorted(_snapshot_project_files(PROJECT_ROOT) - before)
    if leaked:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.ensure_newline()
            reporter.write_sep("=", "测试在项目目录中遗留了文件, 测试产生的文件应写入临时目录 (tmp_path)", red=True)
            for path in leaked:
                reporter.write_line(f"  {path}", red=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(autouse=True, scope="session")
def _isolate_session_workdir() -> Iterator[None]:
    """将测试会话的工作目录切换到临时目录"""
    SESSION_WORKDIR.mkdir(parents=True, exist_ok=True)
    origin = Path.cwd()
    os.chdir(SESSION_WORKDIR)
    try:
        yield
    finally:
        os.chdir(origin)


@pytest.fixture(autouse=True)
def _restore_environ() -> Iterator[None]:
    """测试结束后恢复环境变量"""
    saved = os.environ.copy()
    try:
        yield
    finally:
        if os.environ != saved:
            os.environ.clear()
            os.environ.update(saved)
