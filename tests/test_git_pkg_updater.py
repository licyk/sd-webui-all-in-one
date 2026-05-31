import importlib.metadata
import sys
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
            ["/bin/git", "clone", "--recurse-submodules", "https://github.com/example/repo", (tmp_path / "repo").as_posix()],
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


def test_update_detached_repo_resets_remote_branch(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    calls = []

    monkeypatch.setattr(git_warpper, "get_git_exec", lambda: Path("/bin/git"))
    monkeypatch.setattr(git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(git_warpper, "check_point_offset", lambda _path: True)
    monkeypatch.setattr(git_warpper, "fix_point_offset", lambda path: calls.append(("fix", path)))
    monkeypatch.setattr(git_warpper, "get_current_branch", lambda _path: "main")
    monkeypatch.setattr(git_warpper, "get_git_repo_current_remote_branch", lambda _path: "origin/main")

    def fake_run_cmd(command, **kwargs):
        calls.append((command, kwargs))
        if command[-2:] == ["submodule", "status"]:
            return " abc submodule\n"
        return ""

    monkeypatch.setattr(git_warpper, "run_cmd", fake_run_cmd)

    git_warpper.update(repo)

    assert calls[0] == ("fix", repo)
    assert ["/bin/git", "-C", repo.as_posix(), "submodule", "init"] in [c[0] for c in calls if isinstance(c[0], list)]
    assert ["/bin/git", "-C", repo.as_posix(), "fetch", "--all", "--recurse-submodules"] in [c[0] for c in calls if isinstance(c[0], list)]
    assert ["/bin/git", "-C", repo.as_posix(), "reset", "--hard", "origin/main", "--recurse-submodules"] in [c[0] for c in calls if isinstance(c[0], list)]


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
    assert ["/bin/git", "-C", repo.as_posix(), "remote", "set-url", "origin", "https://new.example/repo"] in calls
    assert ["/bin/git", "-C", repo.as_posix(), "remote", "set-url", "origin", "https://old.example/repo"] in calls


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
    assert custom_env["KEEP"] == "1"
    assert custom_env["UV_PYTHON"] == Path(sys.executable).as_posix()


def test_pip_install_uses_uv_module_when_uv_command_missing(monkeypatch, tmp_path):
    calls = []
    custom_env = {"KEEP": "1"}

    monkeypatch.setattr(pkg_manager, "check_and_update_pip", lambda custom_env=None: calls.append(("pip-check", custom_env.copy())))
    monkeypatch.setattr(pkg_manager, "check_and_update_uv", lambda custom_env=None: calls.append(("uv-check", custom_env.copy())))
    monkeypatch.setattr(pkg_manager.shutil, "which", lambda name: None)
    monkeypatch.setattr(pkg_manager, "run_cmd", lambda command, custom_env=None, cwd=None: calls.append(("run", command, custom_env.copy(), cwd)))

    pkg_manager.pip_install("demo", "--upgrade", custom_env=custom_env, cwd=tmp_path)

    run_calls = [call for call in calls if call[0] == "run"]
    assert run_calls == [("run", [Path(sys.executable).as_posix(), "-m", "uv", "pip", "install", "demo", "--upgrade"], custom_env, tmp_path)]


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

    monkeypatch.setattr(git_warpper, "run_cmd", lambda *_args, **_kwargs: "dev\nmaster\n")
    assert git_warpper.get_git_repo_main_branch(repo) == ("master", None)

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

    assert ["/bin/git", "-C", repo.as_posix(), "submodule", "init"] in [call[0] for call in calls]
    assert ["/bin/git", "-C", repo.as_posix(), "checkout", "master"] in [call[0] for call in calls]
    assert ["/bin/git", "-C", repo.as_posix(), "reset", "--recurse-submodules", "--hard", "master"] in [call[0] for call in calls]

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
        (["/bin/git", "-C", repo.as_posix(), "submodule", "init"], {}),
        (["/bin/git", "-C", repo.as_posix(), "submodule", "update"], {}),
        (["/bin/git", "-C", repo.as_posix(), "reset", "--hard", "abc123"], {}),
        (["/bin/git", "config", "--global", "user.name", "tester"], {}),
        (["/bin/git", "config", "--global", "user.email", "tester@example.test"], {}),
    ]

    monkeypatch.setattr(git_warpper, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("git bad")))
    with pytest.raises(RuntimeError, match="Git 子模块"):
        git_warpper.update_submodule(repo)
    with pytest.raises(RuntimeError, match="abc123"):
        git_warpper.switch_commit(repo, "abc123")
    with pytest.raises(RuntimeError, match="配置 Git"):
        git_warpper.set_git_config(username="tester")
