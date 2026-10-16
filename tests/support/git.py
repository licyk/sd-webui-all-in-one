"""使用真实 Git 命令的测试辅助工具"""

import subprocess
from pathlib import Path


def real_git(repo: Path, *args: str) -> str:
    """在指定仓库中执行 Git 命令并返回标准输出"""
    return subprocess.run(["git", "-C", repo.as_posix(), *args], check=True, capture_output=True, text=True).stdout.strip()
