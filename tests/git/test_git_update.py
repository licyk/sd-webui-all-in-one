"""Git 仓库更新测试"""

import shutil
import threading
from pathlib import Path

import pytest

from sd_webui_all_in_one import git_warpper
from tests.git.helpers import git_command, push_commit, real_git, record_git_subcommands


@pytest.fixture(autouse=True)
def clear_git_exec_cache():
    git_warpper.get_git_exec.cache_clear()
    yield
    git_warpper.get_git_exec.cache_clear()


def test_update_pulls_new_commits_and_skips_reset_when_up_to_date(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    new_commit = push_commit(upstream, "v2\n")
    subcommands = record_git_subcommands(monkeypatch)

    assert git_warpper.update(local, live=False) is True
    assert real_git(local, "rev-parse", "HEAD") == new_commit
    assert subcommands == ["status", "fetch", "rev-parse", "reset"]

    subcommands.clear()
    assert git_warpper.update(local, live=False) is False
    assert subcommands == ["status", "fetch", "rev-parse"]


def test_update_resets_tracked_changes_even_when_up_to_date(git_remote_pair):
    _upstream, local = git_remote_pair
    (local / "file.txt").write_text("local edit\n", encoding="utf-8")
    (local / "untracked.txt").write_text("keep\n", encoding="utf-8")

    assert git_warpper.update(local, live=False) is True
    assert (local / "file.txt").read_text(encoding="utf-8") == "v1\n"
    assert (local / "untracked.txt").exists()


def test_update_fixes_detached_head(git_remote_pair):
    upstream, local = git_remote_pair
    real_git(local, "checkout", "-q", "--detach", "HEAD")
    new_commit = push_commit(upstream, "v2\n")

    assert git_warpper.update(local, live=False) is True
    assert real_git(local, "branch", "--show-current") == "main"
    assert real_git(local, "rev-parse", "HEAD") == new_commit


def test_update_falls_back_to_local_branch_without_upstream(git_remote_pair):
    _upstream, local = git_remote_pair
    real_git(local, "branch", "--unset-upstream")
    head = real_git(local, "rev-parse", "HEAD")

    assert git_warpper.update(local, live=False) is False
    assert real_git(local, "rev-parse", "HEAD") == head


def test_update_rejects_non_git_directory(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git is not available")
    with pytest.raises(ValueError):
        git_warpper.update(tmp_path, live=False)


def test_update_uses_submodule_flags_when_gitmodules_exists(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitmodules").write_text("", encoding="utf-8")
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))

    def fake_run_cmd(command, **_kwargs):
        calls.append(command)
        if "status" in command:
            return "# branch.oid aaa\n# branch.head main\n# branch.upstream origin/main\n"
        if "rev-parse" in command:
            return "bbb\n"
        return ""

    monkeypatch.setattr(git_warpper, "run_cmd", fake_run_cmd)

    assert git_warpper.update(repo) is True
    assert git_command(repo, "submodule", "init") in calls
    assert git_command(repo, "fetch", "--recurse-submodules") in calls
    assert git_command(repo, "reset", "--hard", "origin/main", "--recurse-submodules") in calls


def test_update_git_repositories_runs_in_parallel_and_collects_errors(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager.base import update_git_repositories

    paths = [tmp_path / name for name in ("a", "b", "bad", "c")]
    barrier = threading.Barrier(len(paths), timeout=5)
    calls = []

    def fake_update(path, live=True, fetch=True):
        calls.append((path.name, live, fetch))
        barrier.wait()
        if path.name == "bad":
            raise RuntimeError("boom")
        return path.name != "c"

    monkeypatch.setattr(git_warpper, "update", fake_update)

    results = update_git_repositories(paths, max_workers=len(paths), fetch=False)

    assert [result.path for result in results] == paths
    assert [result.updated for result in results] == [True, True, False, False]
    assert isinstance(results[2].error, RuntimeError)
    assert all(live is False and fetch is False for _name, live, fetch in calls)
    assert update_git_repositories([]) == []


def test_update_without_fetch_reuses_already_fetched_refs(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    new_commit = push_commit(upstream, "v2\n")
    real_git(local, "fetch", "-q")
    subcommands = record_git_subcommands(monkeypatch)

    assert git_warpper.update(local, live=False, fetch=False) is True
    assert real_git(local, "rev-parse", "HEAD") == new_commit
    assert subcommands == ["status", "rev-parse", "reset"]
