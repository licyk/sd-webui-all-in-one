"""软件包安装管理测试"""

import sys
from pathlib import Path

import pytest

from sd_webui_all_in_one import git_warpper, pkg_manager


@pytest.fixture(autouse=True)
def clear_git_exec_cache():
    git_warpper.get_git_exec.cache_clear()
    yield
    git_warpper.get_git_exec.cache_clear()


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
