"""Git 仓库更新检查测试"""

import pytest

import sd_webui_all_in_one.base_manager.version_manager as version_manager
from sd_webui_all_in_one.base_manager.version_manager import repository as version_repository
from tests.support.git import real_git


def _push_commits(upstream, count):
    for index in range(count):
        (upstream / "file.txt").write_text(f"upstream {index}\n", encoding="utf-8")
        real_git(upstream, "commit", "-q", "-am", f"upstream {index}")
    real_git(upstream, "push", "-q", "origin", "main")
    return real_git(upstream, "rev-parse", "HEAD")


def _record_git_commands(monkeypatch):
    commands = []
    real_run_cmd = version_repository.git_warpper.run_cmd

    def recording_run_cmd(command, *args, **kwargs):
        commands.append(command[command.index("-C") + 2 :] if "-C" in command else command)
        return real_run_cmd(command, *args, **kwargs)

    monkeypatch.setattr(version_repository.git_warpper, "run_cmd", recording_run_cmd)
    return commands


def test_check_repository_update_fetches_upstream_only_and_reads_state_with_one_git_call(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    remote_head = _push_commits(upstream, 3)
    (local / "local.txt").write_text("local\n", encoding="utf-8")
    real_git(local, "add", "local.txt")
    real_git(local, "commit", "-q", "-m", "local")
    (local / "file.txt").write_text("modified\n", encoding="utf-8")
    commands = _record_git_commands(monkeypatch)

    status = version_manager.check_repository_update(local)

    assert [command[0] for command in commands] == ["fetch", "status"]
    assert commands[0] == ["fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main"]
    assert status.error is None
    assert status.remote_branch == "origin/main"
    assert (status.ahead, status.behind) == (1, 3)
    assert status.has_update is True
    assert status.is_dirty is True
    assert status.current_commit == real_git(local, "rev-parse", "HEAD")
    assert status.remote_commit == remote_head


def test_check_repository_update_without_fetch_reuses_existing_refs_and_ignores_untracked(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    _push_commits(upstream, 2)
    (local / "untracked.bin").write_text("model\n", encoding="utf-8")
    commands = _record_git_commands(monkeypatch)

    status = version_manager.check_repository_update(local, fetch=False)

    assert [command[0] for command in commands] == ["status"]
    assert status.behind == 0
    assert status.has_update is False
    assert status.is_dirty is False


def test_check_then_update_without_fetch_applies_checked_update(git_remote_pair):
    upstream, local = git_remote_pair
    remote_head = _push_commits(upstream, 1)

    assert version_manager.check_repository_update(local).has_update is True
    assert version_repository.git_warpper.update(local, live=False, fetch=False) is True
    assert real_git(local, "rev-parse", "HEAD") == remote_head


def test_check_repository_update_falls_back_to_origin_branch_without_upstream(git_remote_pair):
    upstream, local = git_remote_pair
    remote_head = _push_commits(upstream, 1)
    real_git(local, "branch", "--unset-upstream")

    status = version_manager.check_repository_update(local)

    assert status.error is None
    assert status.remote_branch == "origin/main"
    assert status.behind == 1
    assert status.remote_commit == remote_head


def test_check_repository_update_skips_fetch_for_detached_head(monkeypatch, git_remote_pair):
    _upstream, local = git_remote_pair
    real_git(local, "checkout", "-q", "--detach")
    commands = _record_git_commands(monkeypatch)

    status = version_manager.check_repository_update(local)

    assert [command[0] for command in commands] == ["status"]
    assert status.has_update is False
    assert status.error == "未找到远程跟踪分支"


def test_check_repository_update_reports_fetch_failure(git_remote_pair):
    _upstream, local = git_remote_pair
    real_git(local, "remote", "set-url", "origin", (local.parent / "missing.git").as_posix())

    status = version_manager.check_repository_update(local)

    assert status.has_update is False
    assert status.error


def test_fetch_repository_upstream_bounds_slow_fetches(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(version_repository, "_upstream_fetch_args", lambda _path, _branch: ["--no-tags", "origin"])
    monkeypatch.setattr(version_repository.git_warpper, "fetch_remote", lambda path, *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.delenv("GIT_HTTP_LOW_SPEED_TIME", raising=False)
    monkeypatch.setenv("GIT_HTTP_LOW_SPEED_LIMIT", "5")

    version_repository.fetch_repository_upstream(tmp_path, "main")

    ((args, kwargs),) = calls
    assert args == ("--no-tags", "origin")
    assert kwargs["timeout"] == version_repository.CHECK_FETCH_TIMEOUT
    assert kwargs["custom_env"]["GIT_HTTP_LOW_SPEED_TIME"] == "20"
    assert kwargs["custom_env"]["GIT_HTTP_LOW_SPEED_LIMIT"] == "5"


def _write_git_config(repo_path, config):
    git_path = repo_path / ".git"
    git_path.mkdir(parents=True)
    (git_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_path / "config").write_text(config, encoding="utf-8")


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (
            '[remote "upstream"]\n\tfetch = +refs/heads/*:refs/remotes/upstream/*\n[branch "main"]\n\tremote = upstream\n\tmerge = refs/heads/dev\n',
            ["--no-tags", "upstream", "+refs/heads/dev:refs/remotes/upstream/dev"],
        ),
        (
            '[remote "origin"]\n\tfetch = +refs/heads/main:refs/remotes/origin/main\n[branch "main"]\n\tremote = origin\n\tmerge = refs/heads/main\n',
            ["--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main"],
        ),
        (
            '[remote "origin"]\n\tfetch = +refs/heads/*:refs/remotes/custom/*\n[branch "main"]\n\tremote = origin\n\tmerge = refs/heads/main\n',
            ["--no-tags", "origin"],
        ),
        ('[branch "main"]\n\tremote = .\n\tmerge = refs/heads/base\n', None),
        ("", ["--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main"]),
    ],
)
def test_upstream_fetch_args_follow_branch_config(tmp_path, config, expected):
    _write_git_config(tmp_path, config)

    assert version_repository._upstream_fetch_args(tmp_path, "main") == expected
    assert version_repository._upstream_fetch_args(tmp_path, None) is None


def test_list_commits_and_branches_parse_git_output(monkeypatch, tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    fetch_calls = []

    monkeypatch.setattr(version_repository.git_warpper, "is_git_repo", lambda _path: True)
    current = "abc1230000000000000000000000000000000000"
    older = "def4560000000000000000000000000000000000"
    monkeypatch.setattr(version_repository.git_warpper, "get_current_commit", lambda _path: current)
    monkeypatch.setattr(version_repository.git_warpper, "get_current_branch", lambda _path: "main")
    monkeypatch.setattr(version_repository, "fetch_repository", lambda path: fetch_calls.append(path))

    def fake_git_output(_path, *args):
        if args[:1] == ("log",):
            return "\n".join(
                [
                    f"{current}\x1fabc123\x1f2026-05-01\x1fAlice\x1f1777593600\x1fHEAD -> main, tag: v2.0\x1fcurrent",
                    f"{older}\x1fdef456\x1f2026-04-30\x1fBob\x1f1777507200\x1forigin/main\x1folder",
                    "malformed",
                ]
            )
        if args == ("branch", "--all", "--format=%(refname:short)"):
            return "\n".join(["origin/HEAD -> origin/main", "origin/dev", "main", "origin/main"])
        raise AssertionError(args)

    monkeypatch.setattr(version_repository, "run_git_output", fake_git_output)

    commits = version_manager.list_commits(repo_path, limit=2)
    assert [(item.commit, item.is_current) for item in commits] == [(current, True), (older, False)]
    assert commits[0].short_commit == "abc123"
    assert commits[0].author == "Alice"
    assert commits[0].timestamp == 1777593600
    assert commits[0].tags == ("v2.0",)
    assert commits[0].branches == ("main",)
    assert commits[1].branches == ("origin/main",)

    branches = version_manager.list_branches(repo_path, fetch=True)
    assert fetch_calls == [repo_path, repo_path]
    assert [(item.name, item.is_current, item.is_remote) for item in branches] == [
        ("main", True, False),
        ("dev", False, True),
    ]

    monkeypatch.setattr(version_repository.git_warpper, "is_git_repo", lambda _path: False)
    assert version_manager.list_commits(repo_path) == []
    assert version_manager.list_branches(repo_path) == []
