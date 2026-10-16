"""自更新测试"""

import importlib.metadata
import sys
from pathlib import Path

import pytest

from sd_webui_all_in_one import git_warpper, updater


@pytest.fixture(autouse=True)
def clear_git_exec_cache():
    git_warpper.get_git_exec.cache_clear()
    yield
    git_warpper.get_git_exec.cache_clear()


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
