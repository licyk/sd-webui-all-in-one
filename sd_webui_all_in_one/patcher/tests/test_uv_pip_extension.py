import subprocess

import pytest

from sd_webui_all_in_one_hotpatcher_ext.uv_pip import (
    apply_from_config,
    is_uv_patch_installed,
    patch_uv_to_subprocess,
    preprocess_command,
    unpatch_uv_to_subprocess,
)


@pytest.fixture(autouse=True)
def clean_uv_patch():
    unpatch_uv_to_subprocess()
    yield
    unpatch_uv_to_subprocess()


def test_preprocess_command_keeps_windows_commands(monkeypatch):
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.uv_pip.sys.platform", "win32")

    assert preprocess_command(["uv", "pip", "install", "demo"], shell=True) == ["uv", "pip", "install", "demo"]


def test_preprocess_command_normalizes_posix_shell_commands(monkeypatch):
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.uv_pip.sys.platform", "linux")

    assert preprocess_command(["uv", "pip", "install", "demo package"], shell=True) == "uv pip install 'demo package'"
    assert preprocess_command("uv pip install demo", shell=False) == ["uv", "pip", "install", "demo"]


def test_patch_uv_to_subprocess_rewrites_pip_commands(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return "ok"

    monkeypatch.setattr(subprocess, "run", fake_run)

    patch_uv_to_subprocess()
    result = subprocess.run(["python", "-m", "pip", "install", "--prefer-binary", "demo"], check=True)

    assert result == "ok"
    assert is_uv_patch_installed() is True
    assert calls == [(["uv", "pip", "install", "demo"], {"check": True})]


def test_patch_uv_to_subprocess_keeps_non_pip_commands(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return "ok"

    monkeypatch.setattr(subprocess, "run", fake_run)

    patch_uv_to_subprocess()
    subprocess.run(["python", "--version"], check=True)

    assert calls == [(["python", "--version"], {"check": True})]


def test_patch_uv_to_subprocess_supports_symlink_mode(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return "ok"

    monkeypatch.setattr(subprocess, "run", fake_run)

    patch_uv_to_subprocess(symlink=True)
    subprocess.run("pip install demo")

    assert calls == [(["uv", "pip", "install", "demo", "--link-mode", "symlink"], {})]


def test_apply_from_config_installs_only_when_enabled(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return "ok"

    monkeypatch.setattr(subprocess, "run", fake_run)

    apply_from_config({"enabled": False})
    assert is_uv_patch_installed() is False

    apply_from_config({"enabled": True, "symlink": True})
    subprocess.run(["pip", "install", "demo"])

    assert is_uv_patch_installed() is True
    assert calls == [(["uv", "pip", "install", "demo", "--link-mode", "symlink"], {})]


def test_unpatch_uv_to_subprocess_only_restores_own_wrapper(monkeypatch):
    def fake_run(command, **kwargs):
        return command, kwargs

    def third_party_run(command, **kwargs):
        return command, kwargs

    monkeypatch.setattr(subprocess, "run", fake_run)

    patch_uv_to_subprocess()
    subprocess.run = third_party_run
    unpatch_uv_to_subprocess()

    assert subprocess.run is third_party_run
