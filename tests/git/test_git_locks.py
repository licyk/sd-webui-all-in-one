"""Git 锁文件处理测试"""

import os
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from sd_webui_all_in_one import git_warpper
from tests.git.helpers import push_commit, real_git, record_git_subcommands


@pytest.fixture(autouse=True)
def clear_git_exec_cache():
    git_warpper.get_git_exec.cache_clear()
    yield
    git_warpper.get_git_exec.cache_clear()


def _make_lock(path: Path, age: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    mtime = time.time() - age
    os.utime(path, (mtime, mtime))
    return path


def test_update_removes_stale_index_lock_and_retries(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    new_commit = push_commit(upstream, "v2\n")
    lock = _make_lock(local / ".git" / "index.lock", git_warpper.STALE_LOCK_AGE + 60)
    subcommands = record_git_subcommands(monkeypatch)

    assert git_warpper.update(local, live=False) is True
    assert not lock.exists()
    assert real_git(local, "rev-parse", "HEAD") == new_commit
    assert subcommands == ["status", "fetch", "reset", "reset"]


def test_switch_commit_removes_stale_index_lock_in_live_mode(git_remote_pair):
    upstream, local = git_remote_pair
    old_commit = real_git(local, "rev-parse", "HEAD")
    push_commit(upstream, "v2\n")
    real_git(local, "pull", "-q")
    lock = _make_lock(local / ".git" / "index.lock", git_warpper.STALE_LOCK_AGE + 60)

    git_warpper.switch_commit(local, old_commit)
    assert not lock.exists()
    assert real_git(local, "rev-parse", "HEAD") == old_commit


def test_update_keeps_fresh_index_lock(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    push_commit(upstream, "v2\n")
    lock = _make_lock(local / ".git" / "index.lock", 0)
    monkeypatch.setattr(git_warpper, "LOCK_WAIT_TIMEOUT", 0.1)
    monkeypatch.setattr(git_warpper, "LOCK_POLL_INTERVAL", 0.02)

    with pytest.raises(RuntimeError, match="index.lock"):
        git_warpper.update(local, live=False)
    assert lock.exists()


def test_update_waits_for_fresh_index_lock_to_be_released(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    new_commit = push_commit(upstream, "v2\n")
    lock = _make_lock(local / ".git" / "index.lock", 0)
    subcommands = record_git_subcommands(monkeypatch)
    # 模拟持锁方在更新流程第一次等待时释放锁。
    clock = Mock(wraps=time)
    clock.sleep.side_effect = lambda _seconds: lock.unlink()
    monkeypatch.setattr(git_warpper, "time", clock)

    assert git_warpper.update(local, live=False) is True
    clock.sleep.assert_called_once()
    assert subcommands.count("reset") == 2
    assert real_git(local, "rev-parse", "HEAD") == new_commit


def test_find_lock_files_covers_submodules_and_worktrees(git_remote_pair, tmp_path):
    _upstream, local = git_remote_pair
    module_lock = _make_lock(local / ".git" / "modules" / "a" / "modules" / "b" / "index.lock", 0)
    _make_lock(local / ".git" / "modules" / "a" / "objects" / "index.lock", 0)

    assert git_warpper._find_lock_files(local, "") == [module_lock.resolve()]

    worktree = tmp_path / "worktree"
    real_git(local, "worktree", "add", "-q", "-b", "wt", worktree.as_posix())
    worktree_lock = _make_lock(Path(real_git(worktree, "rev-parse", "--absolute-git-dir")) / "index.lock", 0)

    assert git_warpper._find_lock_files(worktree, "") == [worktree_lock.resolve(), module_lock.resolve()]


def test_run_git_ignores_lock_paths_outside_git_dir(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    outside = _make_lock(tmp_path / "outside.lock", git_warpper.STALE_LOCK_AGE + 60)
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    message = f"fatal: Unable to create '{outside.as_posix()}': File exists."
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append(command) or (_ for _ in ()).throw(RuntimeError(message)))

    with pytest.raises(RuntimeError, match="outside.lock"):
        git_warpper.run_git("reset", "--hard", path=repo, live=False)
    assert outside.exists()
    assert len(calls) == 1


def test_run_git_removes_stale_lock_named_in_localized_error(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    head_lock = _make_lock(repo / ".git" / "HEAD.lock", git_warpper.STALE_LOCK_AGE + 60)
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))

    def locked_run_cmd(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise RuntimeError(f"致命错误：无法创建 '{head_lock.as_posix()}'：文件已存在。")
        return "ok"

    monkeypatch.setattr(git_warpper, "run_cmd", locked_run_cmd)

    assert git_warpper.run_git("checkout", "main", path=repo, live=False) == "ok"
    assert not head_lock.exists()
    assert len(calls) == 2
