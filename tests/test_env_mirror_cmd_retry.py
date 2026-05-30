import os
import shlex
import subprocess

import pytest

from sd_webui_all_in_one import cmd as cmd_module
from sd_webui_all_in_one import env_manager
from sd_webui_all_in_one import mirror_manager
from sd_webui_all_in_one import retry_decorator
from sd_webui_all_in_one.pytorch_manager.types import (
    PYPI_INDEX_MIRROR_OFFICIAL,
    PYPI_INDEX_MIRROR_TENCENT,
)


def test_generate_uv_and_pip_env_mirror_config_sets_lists_and_clears():
    origin = {
        "KEEP": "1",
        "PIP_INDEX_URL": "old",
        "UV_DEFAULT_INDEX": "old",
        "PIP_EXTRA_INDEX_URL": "old",
        "UV_INDEX": "old",
        "PIP_FIND_LINKS": "old",
        "UV_FIND_LINKS": "old",
    }

    env = env_manager.generate_uv_and_pip_env_mirror_config(
        index_url=[" https://a.example/simple ", "", "https://b.example/simple"],
        extra_index_url="",
        find_links=" https://wheels.example/a  https://wheels.example/b ",
        origin_env=origin,
    )

    assert origin["PIP_INDEX_URL"] == "old"
    assert env["KEEP"] == "1"
    assert env["PIP_INDEX_URL"] == "https://a.example/simple https://b.example/simple"
    assert env["UV_DEFAULT_INDEX"] == "https://a.example/simple https://b.example/simple"
    assert "PIP_EXTRA_INDEX_URL" not in env
    assert "UV_INDEX" not in env
    assert env["PIP_FIND_LINKS"] == "https://wheels.example/a https://wheels.example/b"
    assert env["UV_FIND_LINKS"] == "https://wheels.example/a,https://wheels.example/b"


def test_mirror_env_helpers_set_and_clear(monkeypatch):
    for key in [
        "PIP_INDEX_URL",
        "UV_DEFAULT_INDEX",
        "PIP_EXTRA_INDEX_URL",
        "UV_INDEX",
        "PIP_FIND_LINKS",
        "UV_FIND_LINKS",
        "HF_ENDPOINT",
    ]:
        monkeypatch.delenv(key, raising=False)

    mirror_manager.set_pypi_index_mirror("https://pypi.example/simple")
    mirror_manager.set_pypi_extra_index_mirror("https://extra.example/simple")
    mirror_manager.set_pypi_find_links_mirror(" https://wheel-a.example  https://wheel-b.example ")
    mirror_manager.set_huggingface_mirror("https://hf.example")

    assert os.environ["PIP_INDEX_URL"] == "https://pypi.example/simple"
    assert os.environ["UV_DEFAULT_INDEX"] == "https://pypi.example/simple"
    assert os.environ["PIP_EXTRA_INDEX_URL"] == "https://extra.example/simple"
    assert os.environ["UV_INDEX"] == "https://extra.example/simple"
    assert os.environ["PIP_FIND_LINKS"] == "https://wheel-a.example https://wheel-b.example"
    assert os.environ["UV_FIND_LINKS"] == "https://wheel-a.example,https://wheel-b.example"
    assert os.environ["HF_ENDPOINT"] == "https://hf.example"

    mirror_manager.set_pypi_index_mirror()
    mirror_manager.set_pypi_extra_index_mirror()
    mirror_manager.set_pypi_find_links_mirror()
    mirror_manager.set_huggingface_mirror()

    assert "PIP_INDEX_URL" not in os.environ
    assert "UV_DEFAULT_INDEX" not in os.environ
    assert "PIP_EXTRA_INDEX_URL" not in os.environ
    assert "UV_INDEX" not in os.environ
    assert "PIP_FIND_LINKS" not in os.environ
    assert "UV_FIND_LINKS" not in os.environ
    assert "HF_ENDPOINT" not in os.environ


def test_configure_env_helpers_and_wandb_token(monkeypatch):
    for key in [
        "UV_HTTP_TIMEOUT",
        "UV_CONCURRENT_DOWNLOADS",
        "UV_INDEX_STRATEGY",
        "UV_PYTHON",
        "UV_NO_PROGRESS",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "PIP_NO_WARN_SCRIPT_LOCATION",
        "PIP_TIMEOUT",
        "PIP_RETRIES",
        "PIP_PREFER_BINARY",
        "PIP_YES",
        "WANDB_API_KEY",
        "EXTRA_ENV",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_manager.configure_pip()
    assert os.environ["UV_PYTHON"]
    assert os.environ["PIP_PREFER_BINARY"] == "1"
    assert os.environ["PIP_YES"] == "1"

    monkeypatch.setattr(env_manager, "DEFAULT_ENV_VARS", [("EXTRA_ENV", "enabled")])
    env_manager.configure_env_var()
    assert os.environ["EXTRA_ENV"] == "enabled"

    env_manager.config_wandb_token()
    assert "WANDB_API_KEY" not in os.environ
    env_manager.config_wandb_token("token")
    assert os.environ["WANDB_API_KEY"] == "token"


def test_set_mirror_delegates_and_sets_git_config_env(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(mirror_manager, "set_pypi_index_mirror", lambda mirror=None: calls.append(("index", mirror)))
    monkeypatch.setattr(mirror_manager, "set_pypi_extra_index_mirror", lambda mirror=None: calls.append(("extra", mirror)))
    monkeypatch.setattr(mirror_manager, "set_pypi_find_links_mirror", lambda mirror=None: calls.append(("links", mirror)))
    monkeypatch.setattr(mirror_manager, "set_github_mirror", lambda mirror=None: calls.append(("github", mirror)) or (tmp_path / ".gitconfig"))
    monkeypatch.setattr(mirror_manager, "set_huggingface_mirror", lambda mirror=None: calls.append(("hf", mirror)))
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)

    mirror_manager.set_mirror(
        pypi_index_mirror="index-url",
        pypi_extra_index_mirror="extra-url",
        pypi_find_links_mirror="links-url",
        github_mirror=["gh"],
        huggingface_mirror="hf-url",
    )

    assert calls == [
        ("index", "index-url"),
        ("extra", "extra-url"),
        ("links", "links-url"),
        ("github", ["gh"]),
        ("hf", "hf-url"),
    ]
    assert os.environ["GIT_CONFIG_GLOBAL"] == (tmp_path / ".gitconfig").as_posix()


def test_set_github_mirror_writes_or_clears_config(monkeypatch, tmp_path):
    calls = []

    def fake_run_cmd(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(mirror_manager, "run_cmd", fake_run_cmd)
    config_path = tmp_path / ".gitconfig"

    result = mirror_manager.set_github_mirror("https://mirror.example/https://github.com", config_path=config_path)

    assert result == config_path
    assert calls == [
        (
            [
                "git",
                "config",
                "--file",
                config_path.as_posix(),
                "url.https://mirror.example/https://github.com.insteadOf",
                "https://github.com",
            ],
            {},
        )
    ]

    config_path.write_text("old", encoding="utf-8")
    mirror_manager.set_github_mirror([], config_path=config_path)

    assert not config_path.exists()


def test_get_auto_pypi_mirror_config_selects_by_network(monkeypatch):
    monkeypatch.setattr(mirror_manager, "network_gfw_test", lambda: True)
    official = mirror_manager.get_auto_pypi_mirror_config({})
    assert official["PIP_INDEX_URL"] == PYPI_INDEX_MIRROR_OFFICIAL

    monkeypatch.setattr(mirror_manager, "network_gfw_test", lambda: False)
    cn = mirror_manager.get_auto_pypi_mirror_config({})
    assert cn["PIP_INDEX_URL"] == PYPI_INDEX_MIRROR_TENCENT


def test_preprocess_command_platform_rules(monkeypatch):
    monkeypatch.setattr(cmd_module.sys, "platform", "linux")
    assert cmd_module.preprocess_command(["python", "-c", "print(1)"], shell=True) == shlex.join(["python", "-c", "print(1)"])
    assert cmd_module.preprocess_command("python -V", shell=False) == ["python", "-V"]

    monkeypatch.setattr(cmd_module.sys, "platform", "darwin")
    assert cmd_module.preprocess_command(["python", "-V"], shell=False) == ["python", "-V"]

    command = ["python", "-V"]
    monkeypatch.setattr(cmd_module.sys, "platform", "win32")
    assert cmd_module.preprocess_command(command, shell=True) is command


def test_run_cmd_returns_output_and_raises_on_nonzero(monkeypatch):
    monkeypatch.setattr(cmd_module, "in_jupyter", lambda: False)
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args=kwargs["args"], returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(cmd_module.subprocess, "run", fake_run)

    assert cmd_module.run_cmd(["python", "-V"], live=False, shell=False) == "ok\n"
    assert calls[0]["stdout"] == subprocess.PIPE
    assert calls[0]["stderr"] == subprocess.PIPE

    def fake_fail(**kwargs):
        return subprocess.CompletedProcess(args=kwargs["args"], returncode=7, stdout="bad out", stderr="bad err")

    monkeypatch.setattr(cmd_module.subprocess, "run", fake_fail)

    with pytest.raises(RuntimeError) as exc:
        cmd_module.run_cmd("python -V", live=False, shell=False)

    assert "bad out" in str(exc.value)
    assert "bad err" in str(exc.value)


def test_retryable_retries_none_and_unretryable(monkeypatch):
    monkeypatch.setattr(retry_decorator.time, "sleep", lambda _delay: None)
    attempts = {"value": 0}

    @retry_decorator.retryable(times=3, delay=0, catch_exceptions=ValueError, raise_exception=RuntimeError)
    def eventually_ok():
        attempts["value"] += 1
        if attempts["value"] == 1:
            raise ValueError("temporary")
        return "done"

    assert eventually_ok() == "done"
    assert attempts["value"] == 2

    none_attempts = {"value": 0}

    @retry_decorator.retryable(times=2, delay=0, retry_on_none=True)
    def always_none():
        none_attempts["value"] += 1
        return None

    with pytest.raises(RuntimeError):
        always_none()
    assert none_attempts["value"] == 2

    @retry_decorator.retryable(times=3, delay=0, catch_exceptions=ValueError)
    def fatal():
        raise TypeError("no retry")

    with pytest.raises(TypeError):
        fatal()
