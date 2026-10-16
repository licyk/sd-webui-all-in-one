"""Git 命令封装与查询测试"""

import subprocess
from pathlib import Path

import pytest

from sd_webui_all_in_one import git_warpper
from tests.git.helpers import git_command


def test_run_git_passes_timeout_to_run_cmd(monkeypatch):
    calls = []

    monkeypatch.setattr(git_warpper, "build_git_command", lambda *args, path=None: ["git", *args])
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append((command, kwargs)) or "")

    assert git_warpper.run_git("ls-remote", "https://example.test/repo", live=False, shell=False, timeout=2.5) == ""
    assert calls == [
        (
            ["git", "ls-remote", "https://example.test/repo"],
            {
                "custom_env": None,
                "live": False,
                "shell": False,
                "cwd": None,
                "check": True,
                "timeout": 2.5,
            },
        )
    ]


@pytest.fixture(autouse=True)
def clear_git_exec_cache():
    git_warpper.get_git_exec.cache_clear()
    yield
    git_warpper.get_git_exec.cache_clear()


def _git_no_path(*args: str) -> list[str]:
    return ["/bin/git", "-c", "safe.directory=*", "-c", "core.longpaths=true", *args]


def test_get_git_exec_uses_which_and_caches(monkeypatch):
    calls = []

    def fake_which(name):
        calls.append(name)
        return "/usr/bin/git"

    monkeypatch.setattr(git_warpper.shutil, "which", fake_which)

    assert git_warpper.get_git_exec() == Path("/usr/bin/git")
    assert git_warpper.get_git_exec() == Path("/usr/bin/git")
    assert calls == ["git"]

    git_warpper.get_git_exec.cache_clear()
    monkeypatch.setattr(git_warpper.shutil, "which", lambda _name: None)
    with pytest.raises(FileNotFoundError):
        git_warpper.get_git_exec()


def test_build_git_command_adds_runtime_git_config(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))

    assert git_warpper.build_git_command("status", path=repo) == git_command(repo, "status")
    assert git_warpper.build_git_command("clone", "repo", repo.as_posix()) == _git_no_path("clone", "repo", repo.as_posix())


def test_clone_wraps_git_command_and_errors(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))

    def fake_run_cmd(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(git_warpper, "run_cmd", fake_run_cmd)

    result = git_warpper.clone("https://github.com/example/repo", tmp_path / "repo")

    assert result == tmp_path / "repo"
    assert calls == [
        (
            _git_no_path("clone", "--recurse-submodules", "https://github.com/example/repo", (tmp_path / "repo").as_posix()),
            {},
        )
    ]

    monkeypatch.setattr(git_warpper, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("nope")))
    with pytest.raises(RuntimeError) as exc:
        git_warpper.clone("bad", tmp_path / "bad")
    assert "使用 Git 下载 bad" in str(exc.value)


def test_git_query_helpers_and_main_branch_fallback(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    commands = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda path: path == repo)

    def fake_run_cmd(command, **kwargs):
        commands.append((command, kwargs))
        joined = " ".join(command)
        if command[-1] == "remote":
            return "upstream\norigin\n"
        if "symbolic-ref refs/remotes/origin/HEAD" in joined:
            return "refs/remotes/origin/main\n"
        if command[-2:] == ["branch", "--show-current"]:
            return "feature\n"
        if command[-3:] == ["rev-parse", "--short", "HEAD"]:
            return "abc123\n"
        if command[-2:] == ["config", "branch.feature.remote"]:
            return "origin\n"
        if command[-3:-1] == ["remote", "get-url"]:
            return "https://github.com/example/repo\n"
        if "show-ref" in joined:
            return ""
        raise AssertionError(command)

    monkeypatch.setattr(git_warpper, "run_cmd", fake_run_cmd)

    assert git_warpper.get_git_repo_remote_name(repo) == "origin"
    assert git_warpper.get_git_repo_main_branch(repo) == ("main", "origin/main")
    assert git_warpper.get_current_branch(repo) == "feature"
    assert git_warpper.get_current_commit(repo) == "abc123"
    assert git_warpper.get_current_branch_remote(repo) == "origin"
    assert git_warpper.get_current_branch_remote_url(repo) == "https://github.com/example/repo"
    assert git_warpper.check_local_branch_exists(repo, "feature") is True

    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: False)
    with pytest.raises(ValueError):
        git_warpper.get_current_branch(repo)


def test_switch_branch_rolls_back_remote_on_failure(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    calls = []

    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(git_warpper, "get_current_branch_remote_url", lambda _path: "https://old.example/repo")
    monkeypatch.setattr(git_warpper, "check_local_branch_exists", lambda *_args: False)

    def fake_run_cmd(command, **kwargs):
        calls.append(command)
        if command[-1] == "fetch":
            raise RuntimeError("fetch failed")
        return ""

    monkeypatch.setattr(git_warpper, "run_cmd", fake_run_cmd)

    with pytest.raises(RuntimeError) as exc:
        git_warpper.switch_branch(repo, "dev", new_url="https://new.example/repo", recurse_submodules=True)

    assert "切换" in str(exc.value)
    assert git_command(repo, "remote", "set-url", "origin", "https://new.example/repo") in calls
    assert git_command(repo, "remote", "set-url", "origin", "https://old.example/repo") in calls


def test_git_main_branch_local_fallbacks(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(git_warpper, "get_git_repo_remote_name", lambda _path: None)

    commands = []
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **_kwargs: commands.append(command) or "dev\nmaster\n")
    assert git_warpper.get_git_repo_main_branch(repo) == ("master", None)
    assert commands == [git_command(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/")]

    monkeypatch.setattr(git_warpper, "run_cmd", lambda *_args, **_kwargs: "dev\nrelease\n")
    assert git_warpper.get_git_repo_main_branch(repo) == ("dev", None)

    monkeypatch.setattr(git_warpper, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad ref")))
    assert git_warpper.get_git_repo_main_branch(repo) == (None, None)


def test_fix_point_offset_uses_local_branch_and_reports_missing(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(git_warpper, "get_git_repo_main_branch", lambda _path: ("master", None))
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append((command, kwargs)))

    git_warpper.fix_point_offset(repo)

    assert git_command(repo, "submodule", "init") in [call[0] for call in calls]
    assert git_command(repo, "checkout", "master") in [call[0] for call in calls]
    assert git_command(repo, "reset", "--recurse-submodules", "--hard", "master") in [call[0] for call in calls]

    monkeypatch.setattr(git_warpper, "get_git_repo_main_branch", lambda _path: (None, None))
    with pytest.raises(FileNotFoundError):
        git_warpper.fix_point_offset(repo)


def test_update_submodule_switch_commit_and_git_config(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append((command, kwargs)))

    git_warpper.update_submodule(repo)
    git_warpper.switch_commit(repo, "abc123")
    git_warpper.set_git_config(username="tester", email="tester@example.test")

    assert calls == [
        (git_command(repo, "submodule", "init"), {}),
        (git_command(repo, "submodule", "update"), {}),
        (git_command(repo, "reset", "--hard", "abc123"), {}),
        (_git_no_path("config", "--global", "user.name", "tester"), {}),
        (_git_no_path("config", "--global", "user.email", "tester@example.test"), {}),
    ]

    monkeypatch.setattr(git_warpper, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("git bad")))
    with pytest.raises(RuntimeError, match="Git 子模块"):
        git_warpper.update_submodule(repo)
    with pytest.raises(RuntimeError, match="abc123"):
        git_warpper.switch_commit(repo, "abc123")
    with pytest.raises(RuntimeError, match="配置 Git"):
        git_warpper.set_git_config(username="tester")


def test_fetch_remote_is_non_interactive_and_retries_once(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "FETCH_RETRY_DELAY", 0)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/mirror/.gitconfig")

    def flaky_run_cmd(command, **kwargs):
        calls.append((command, kwargs["custom_env"]))
        if len(calls) == 1:
            raise RuntimeError("mirror reset connection")
        return ""

    monkeypatch.setattr(git_warpper, "run_cmd", flaky_run_cmd)
    git_warpper.fetch_remote(repo, "--all", live=False)

    assert [command for command, _env in calls] == [git_command(repo, "fetch", "--all")] * 2
    for _command, env in calls:
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GCM_INTERACTIVE"] == "never"
        assert env["GIT_CONFIG_GLOBAL"] == "/mirror/.gitconfig"

    calls.clear()
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append(command) or (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(RuntimeError, match="down"):
        git_warpper.fetch_remote(repo, live=False)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "message",
    [
        "remote: Repository not found.",
        "fatal: repository 'https://github.com/a/b/' not found",
        "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
        "fatal: couldn't find remote ref refs/heads/gone",
    ],
)
def test_fetch_remote_does_not_retry_permanent_errors(monkeypatch, tmp_path, message):
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "FETCH_RETRY_DELAY", 0)
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append(command) or (_ for _ in ()).throw(RuntimeError(message)))

    with pytest.raises(RuntimeError):
        git_warpper.fetch_remote(tmp_path, live=False)
    assert len(calls) == 1


def test_fetch_remote_converts_timeout_without_retry(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))

    def hanging_run_cmd(command, **kwargs):
        calls.append(kwargs["timeout"])
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(git_warpper, "run_cmd", hanging_run_cmd)

    with pytest.raises(RuntimeError, match="超时"):
        git_warpper.fetch_remote(tmp_path, live=False, timeout=5)
    assert calls == [5]
