import importlib.metadata
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one import pkg_manager
from sd_webui_all_in_one import updater


@pytest.fixture(autouse=True)
def clear_git_exec_cache():
    git_warpper.get_git_exec.cache_clear()
    yield
    git_warpper.get_git_exec.cache_clear()


def _git(repo: Path, *args: str) -> list[str]:
    return ["/bin/git", "-c", "safe.directory=*", "-c", "core.longpaths=true", "-C", repo.as_posix(), *args]


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

    assert git_warpper.build_git_command("status", path=repo) == _git(repo, "status")
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


def _real_git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", repo.as_posix(), *args], check=True, capture_output=True, text=True).stdout.strip()


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
    _real_git(upstream, "checkout", "-q", "-b", "main")
    (upstream / "file.txt").write_text("v1\n", encoding="utf-8")
    _real_git(upstream, "add", "file.txt")
    _real_git(upstream, "commit", "-q", "-m", "v1")
    _real_git(upstream, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", origin.as_posix(), local.as_posix()], check=True)
    return upstream, local


def _push_commit(upstream: Path, content: str) -> str:
    (upstream / "file.txt").write_text(content, encoding="utf-8")
    _real_git(upstream, "commit", "-q", "-am", content.strip())
    _real_git(upstream, "push", "-q", "origin", "main")
    return _real_git(upstream, "rev-parse", "HEAD")


def _record_git_subcommands(monkeypatch) -> list[str]:
    subcommands: list[str] = []
    real_run_cmd = git_warpper.run_cmd

    def recording_run_cmd(command, *args, **kwargs):
        subcommands.append(command[command.index("-C") + 2] if "-C" in command else command[5])
        return real_run_cmd(command, *args, **kwargs)

    monkeypatch.setattr(git_warpper, "run_cmd", recording_run_cmd)
    return subcommands


def test_update_pulls_new_commits_and_skips_reset_when_up_to_date(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    new_commit = _push_commit(upstream, "v2\n")
    subcommands = _record_git_subcommands(monkeypatch)

    assert git_warpper.update(local, live=False) is True
    assert _real_git(local, "rev-parse", "HEAD") == new_commit
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
    _real_git(local, "checkout", "-q", "--detach", "HEAD")
    new_commit = _push_commit(upstream, "v2\n")

    assert git_warpper.update(local, live=False) is True
    assert _real_git(local, "branch", "--show-current") == "main"
    assert _real_git(local, "rev-parse", "HEAD") == new_commit


def test_update_falls_back_to_local_branch_without_upstream(git_remote_pair):
    _upstream, local = git_remote_pair
    _real_git(local, "branch", "--unset-upstream")
    head = _real_git(local, "rev-parse", "HEAD")

    assert git_warpper.update(local, live=False) is False
    assert _real_git(local, "rev-parse", "HEAD") == head


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
    assert _git(repo, "submodule", "init") in calls
    assert _git(repo, "fetch", "--recurse-submodules") in calls
    assert _git(repo, "reset", "--hard", "origin/main", "--recurse-submodules") in calls


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
    assert _git(repo, "remote", "set-url", "origin", "https://new.example/repo") in calls
    assert _git(repo, "remote", "set-url", "origin", "https://old.example/repo") in calls


def test_pip_install_prefers_uv_and_falls_back_to_pip(monkeypatch, tmp_path):
    calls = []
    custom_env = {"KEEP": "1"}

    monkeypatch.setattr(pkg_manager, "check_and_update_pip", lambda custom_env=None: calls.append(("pip-check", custom_env.copy())))
    monkeypatch.setattr(pkg_manager, "check_and_update_uv", lambda custom_env=None: calls.append(("uv-check", custom_env.copy())))
    monkeypatch.setattr(pkg_manager.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)

    def fake_run_cmd(command, custom_env=None, cwd=None):
        calls.append(("run", command, custom_env.copy(), cwd))
        if command[:3] == ["uv", "pip", "install"]:
            raise RuntimeError("uv failed")

    monkeypatch.setattr(pkg_manager, "run_cmd", fake_run_cmd)

    pkg_manager.pip_install("demo", "--upgrade", custom_env=custom_env, cwd=tmp_path)

    run_calls = [call for call in calls if call[0] == "run"]
    assert run_calls[0][1] == ["uv", "pip", "install", "demo", "--upgrade"]
    assert run_calls[0][2]["UV_PYTHON"] == Path(sys.executable).as_posix()
    assert run_calls[1][1] == [Path(sys.executable).as_posix(), "-m", "pip", "install", "demo", "--upgrade"]
    assert custom_env == {"KEEP": "1"}


def test_pip_install_uses_uv_module_when_uv_command_missing(monkeypatch, tmp_path):
    calls = []
    custom_env = {"KEEP": "1"}

    monkeypatch.setattr(pkg_manager, "check_and_update_pip", lambda custom_env=None: calls.append(("pip-check", custom_env.copy())))
    monkeypatch.setattr(pkg_manager, "check_and_update_uv", lambda custom_env=None: calls.append(("uv-check", custom_env.copy())))
    monkeypatch.setattr(pkg_manager.shutil, "which", lambda name: None)
    monkeypatch.setattr(pkg_manager, "run_cmd", lambda command, custom_env=None, cwd=None: calls.append(("run", command, custom_env.copy(), cwd)))

    pkg_manager.pip_install("demo", "--upgrade", custom_env=custom_env, cwd=tmp_path)

    run_calls = [call for call in calls if call[0] == "run"]
    assert run_calls == [
        (
            "run",
            [Path(sys.executable).as_posix(), "-m", "uv", "pip", "install", "demo", "--upgrade"],
            {"KEEP": "1", "UV_PYTHON": Path(sys.executable).as_posix()},
            tmp_path,
        )
    ]
    assert custom_env == {"KEEP": "1"}


def test_install_manager_depend_filters_optional_groups_and_runs_system_commands(monkeypatch):
    calls = []
    env = {"A": "B"}

    monkeypatch.setattr(
        pkg_manager,
        "get_categorized_dependencies",
        lambda _name: {
            "mandatory": ["core"],
            "optional": {"foo": ["foo-extra"], "full": ["skip-full"], "tunnel": ["skip-tunnel"]},
        },
    )
    monkeypatch.setattr(pkg_manager, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))
    monkeypatch.setattr(pkg_manager, "run_cmd", lambda command, custom_env=None: calls.append(("cmd", command, custom_env)))

    pkg_manager.install_manager_depend(use_uv=False, custom_env=env, custom_sys_pkg_cmd=[["apt", "update"], "apt install git"])

    assert calls[0][0] == "pip"
    assert calls[0][1] == ("core", "foo-extra", "--upgrade")
    assert calls[0][2]["use_uv"] is False
    assert calls[1:] == [("cmd", ["apt", "update"], env), ("cmd", "apt install git", env)]


def test_install_pytorch_and_requirements_delegate_and_wrap(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(pkg_manager, "pip_install", lambda *args, **kwargs: calls.append((args, kwargs)))

    pkg_manager.install_pytorch("torch torchvision", ["xformers"], custom_env={"X": "1"}, use_uv=False)
    pkg_manager.install_requirements(tmp_path / "requirements.txt", use_uv=False, custom_env={"Y": "2"}, cwd=tmp_path)
    pkg_manager.install_requirements([tmp_path / "requirements.txt", tmp_path / "requirements-dev.txt"], use_uv=False, custom_env={"Z": "3"}, cwd=tmp_path)

    assert calls[0] == (("torch", "torchvision"), {"use_uv": False, "custom_env": {"X": "1"}})
    assert calls[1] == (("xformers",), {"use_uv": False, "custom_env": {"X": "1"}})
    assert calls[2] == (("-r", (tmp_path / "requirements.txt").as_posix()), {"use_uv": False, "custom_env": {"Y": "2"}, "cwd": tmp_path})
    assert calls[3] == (
        ("-r", (tmp_path / "requirements.txt").as_posix(), "-r", (tmp_path / "requirements-dev.txt").as_posix()),
        {"use_uv": False, "custom_env": {"Z": "3"}, "cwd": tmp_path},
    )

    monkeypatch.setattr(pkg_manager, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(RuntimeError) as exc:
        pkg_manager.install_requirements([tmp_path / "requirements.txt", tmp_path / "requirements-dev.txt"])
    assert "requirements.txt" in str(exc.value)
    assert "requirements-dev.txt" in str(exc.value)


def test_updater_version_checks_and_install_commands(monkeypatch):
    calls = []

    def fake_version(name):
        if name == "uv":
            return "999.0.0"
        if name == "pip":
            return "0.0.1"
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(updater.importlib.metadata, "version", fake_version)
    monkeypatch.setattr(updater, "get_auto_pypi_mirror_config", lambda env=None: {"MIRROR": "1", **(env or {})})
    monkeypatch.setattr(updater, "run_cmd", lambda command, custom_env=None, **kwargs: calls.append((command, custom_env, kwargs)) or "aria2 version 1.37.0\n")

    updater.check_and_update_uv(custom_env={"A": "B"})
    assert calls == []

    updater.check_and_update_pip(custom_env={"A": "B"})
    assert calls[0][0] == [Path(sys.executable).as_posix(), "-m", "pip", "install", "pip", "--upgrade"]
    assert calls[0][1]["MIRROR"] == "1"

    assert updater.get_aria2_ver() == "1.37.0"
    assert updater.check_aria2_version() is False

    monkeypatch.setattr(updater, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("missing")))
    assert updater.get_aria2_ver() is None
    assert updater.check_aria2_version() is True


def test_git_main_branch_local_fallbacks(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(git_warpper, "get_git_repo_remote_name", lambda _path: None)

    commands = []
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **_kwargs: commands.append(command) or "dev\nmaster\n")
    assert git_warpper.get_git_repo_main_branch(repo) == ("master", None)
    assert commands == [_git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/")]

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

    assert _git(repo, "submodule", "init") in [call[0] for call in calls]
    assert _git(repo, "checkout", "master") in [call[0] for call in calls]
    assert _git(repo, "reset", "--recurse-submodules", "--hard", "master") in [call[0] for call in calls]

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
        (_git(repo, "submodule", "init"), {}),
        (_git(repo, "submodule", "update"), {}),
        (_git(repo, "reset", "--hard", "abc123"), {}),
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

    assert [command for command, _env in calls] == [_git(repo, "fetch", "--all")] * 2
    for _command, env in calls:
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GCM_INTERACTIVE"] == "never"
        assert env["GIT_CONFIG_GLOBAL"] == "/mirror/.gitconfig"

    calls.clear()
    monkeypatch.setattr(git_warpper, "run_cmd", lambda command, **kwargs: calls.append(command) or (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(RuntimeError, match="down"):
        git_warpper.fetch_remote(repo, live=False)
    assert len(calls) == 2


def test_update_without_fetch_reuses_already_fetched_refs(monkeypatch, git_remote_pair):
    upstream, local = git_remote_pair
    new_commit = _push_commit(upstream, "v2\n")
    _real_git(local, "fetch", "-q")
    subcommands = _record_git_subcommands(monkeypatch)

    assert git_warpper.update(local, live=False, fetch=False) is True
    assert _real_git(local, "rev-parse", "HEAD") == new_commit
    assert subcommands == ["status", "rev-parse", "reset"]
