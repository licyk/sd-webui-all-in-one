"""测试共享夹具"""

import shutil
import subprocess

import pytest

from tests.support.git import real_git


@pytest.fixture
def git_remote_pair(monkeypatch, tmp_path):
    """创建本地裸仓库作为远程源, 并返回 (上游工作区, 本地克隆) 路径。"""
    if shutil.which("git") is None:
        pytest.skip("git is not available")
    global_config = tmp_path / "gitconfig"
    global_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", global_config.as_posix())
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key, value in {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}.items():
        monkeypatch.setenv(key, value)

    origin = tmp_path / "origin.git"
    upstream = tmp_path / "upstream"
    local = tmp_path / "local"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin.as_posix()], check=True)
    subprocess.run(["git", "clone", "-q", origin.as_posix(), upstream.as_posix()], check=True)
    real_git(upstream, "checkout", "-q", "-b", "main")
    (upstream / "file.txt").write_text("v1\n", encoding="utf-8")
    real_git(upstream, "add", "file.txt")
    real_git(upstream, "commit", "-q", "-m", "v1")
    real_git(upstream, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", origin.as_posix(), local.as_posix()], check=True)
    return upstream, local
