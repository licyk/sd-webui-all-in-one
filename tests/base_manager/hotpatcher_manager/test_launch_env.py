"""Hotpatcher 启动环境注入测试"""

import json
import os
import subprocess
import sys
import types

import pytest

from sd_webui_all_in_one.base_manager.base import launch_webui
from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_RUNTIME_PORT,
    HOTPATCHER_ENV_PREFIX,
    HOTPATCHER_PATH,
    apply_hotpatcher_launch_env,
    build_hotpatcher_runtime_env,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import config as hotpatcher_config


def test_invokeai_existing_webbrowser_module_is_intercepted(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser
    from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

    from sd_webui_all_in_one.base_manager import run_invokeai

    events = []
    client = types.SimpleNamespace(event=lambda kind, payload: events.append((kind, payload)))
    monkeypatch.setattr(browser, "install_import_hook", lambda **_kwargs: None)
    monkeypatch.setattr(browser, "register_hook", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_invokeai.webbrowser, "open", lambda *_args, **_kwargs: pytest.fail("system browser opened"))

    class ImmediateThread:
        def __init__(self, target, **_kwargs):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(run_invokeai.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(run_invokeai.time, "sleep", lambda _seconds: None)
    browser.patch_webbrowser(client, state=HotpatcherState())
    run_invokeai._open_browser_later("http://127.0.0.1:9090")
    assert events == [("browser.open", {"url": "http://127.0.0.1:9090"})]


def test_build_hotpatcher_runtime_env():
    env = build_hotpatcher_runtime_env("127.0.0.1", 8765, token="secret")

    assert env["PYTHONPATH"] == HOTPATCHER_PATH.as_posix()
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME"] == "1"
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES"] == "1"
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] == "secret"


def test_apply_hotpatcher_launch_env_uses_default_json_when_config_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(hotpatcher_config, "DEFAULT_HOTPATCHER_CONFIG_PATH", tmp_path / "missing.json")
    origin = {
        "PYTHONPATH": "existing",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN": "secret",
    }

    env = apply_hotpatcher_launch_env(origin, enabled=True, port=9876)

    assert env["PYTHONPATH"].split(os.pathsep)[0] == HOTPATCHER_PATH.as_posix()
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME" not in env
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST" not in env
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT" not in env
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES" not in env
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN" not in env
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] == "env"
    config = json.loads(env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON"])
    assert config["services"]["apply_on_bootstrap"] is True

    runtime_env = apply_hotpatcher_launch_env(origin, enabled=True, port=9876, enable_runtime=True)
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME"] == "1"
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST"] == "127.0.0.1"
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == "9876"
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES"] == "1"
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] == "secret"


def test_apply_hotpatcher_launch_env_prefers_config_file(monkeypatch, tmp_path):
    config_file = tmp_path / "patcher_config.json"
    config_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(hotpatcher_config, "DEFAULT_HOTPATCHER_CONFIG_PATH", config_file)

    env = apply_hotpatcher_launch_env({}, enabled=True)

    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] == "file"
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] == config_file.as_posix()
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT" not in env

    runtime_env = apply_hotpatcher_launch_env({}, enabled=True, enable_runtime=True)
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] == "file"
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] == config_file.as_posix()
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == str(DEFAULT_RUNTIME_PORT)


def test_apply_hotpatcher_launch_env_can_disable_and_clear_existing_values():
    env = apply_hotpatcher_launch_env(
        {
            "PYTHONPATH": "existing",
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "1",
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN": "secret",
        },
        enabled=False,
    )

    assert env["PYTHONPATH"] == "existing"
    assert all(not key.startswith(HOTPATCHER_ENV_PREFIX) for key in env)


def test_sitecustomize_bootstrap_does_not_reapply_in_python_children(monkeypatch, tmp_path):
    monkeypatch.setattr(hotpatcher_config, "DEFAULT_HOTPATCHER_CONFIG_PATH", tmp_path / "missing.json")
    env = apply_hotpatcher_launch_env(dict(os.environ), enabled=True)
    env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON"] = json.dumps(
        {
            "services": {"apply_on_bootstrap": True},
            "core": {
                "import_hook": {"enabled": False},
                "stack_shadow": {"enabled": False},
            },
            "extensions": {
                "xformers_cutlass": {"enabled": False},
            },
        },
        separators=(",", ":"),
    )

    child_code = """
import json
import os
from sd_webui_all_in_one_hotpatcher.bootstrap import get_service_apply_result

print(json.dumps({
    "marker": os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_BOOTSTRAPPED"),
    "result": get_service_apply_result(),
}, sort_keys=True))
"""
    parent_code = f"""
import json
import os
import subprocess
import sys
from sd_webui_all_in_one_hotpatcher.bootstrap import get_service_apply_result

child_output = subprocess.check_output(
    [sys.executable, "-c", {child_code!r}],
    text=True,
    timeout=10,
)
print(json.dumps({{
    "parent_marker": os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_BOOTSTRAPPED"),
    "parent_result": get_service_apply_result(),
    "child": json.loads(child_output),
}}, sort_keys=True))
"""

    output = subprocess.check_output([sys.executable, "-c", parent_code], env=env, text=True, timeout=10)
    result = json.loads(output)

    assert result["parent_marker"] == "1"
    assert result["parent_result"]["applied"] == ["extensions.comfyui_auto_port"]
    assert result["parent_result"]["errors"] == []
    assert (
        any(warning.get("feature") == "core.import_hook" and "already installed" in warning.get("message", "") for warning in result["parent_result"].get("warnings", []))
        or result["parent_result"]["warnings"] == []
    )
    assert result["child"] == {"marker": "1", "result": None}


def test_launch_webui_keeps_hotpatcher_pythonpath_first(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager.base import runtime as base_runtime

    captured = {}

    def fake_run_process_tree(cmd, custom_env=None, cwd=None):
        captured["cmd"] = cmd
        captured["custom_env"] = custom_env
        captured["cwd"] = cwd

    monkeypatch.setattr(base_runtime, "run_process_tree", fake_run_process_tree)
    env = apply_hotpatcher_launch_env({"PYTHONPATH": "existing"}, enabled=True)

    launch_webui(tmp_path, "launch.py", launch_args=["--demo"], custom_env=env)

    pythonpath = captured["custom_env"]["PYTHONPATH"].split(os.pathsep)
    assert pythonpath[:3] == [HOTPATCHER_PATH.as_posix(), tmp_path.as_posix(), "existing"]
    assert captured["cwd"] == tmp_path
    assert captured["cmd"][-1] == "--demo"


def _capture_webui_launch_env(monkeypatch, module, launch_func, path_arg: str, tmp_path, **kwargs):
    captured = {}
    implementation = sys.modules[launch_func.__module__]
    git_config_path = (tmp_path / ".gitconfig").as_posix()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", git_config_path)

    def fake_git_env(*, origin_env=None, **_kwargs):
        env = (origin_env or os.environ.copy()).copy()
        env["GIT_CONFIG_GLOBAL"] = git_config_path
        return env

    def fake_env_passthrough(*, origin_env=None, **_kwargs):
        return (origin_env or os.environ.copy()).copy()

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", fake_git_env)
    monkeypatch.setattr(implementation, "apply_hf_mirror", fake_env_passthrough)
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", fake_env_passthrough)
    monkeypatch.setattr(implementation, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(implementation, "launch_webui", lambda **launch_kwargs: captured.update(launch_kwargs))

    launch_kwargs = {
        path_arg: tmp_path,
        "launch_args": [],
        "use_cuda_malloc": False,
    }
    launch_kwargs.update(kwargs)
    launch_func(**launch_kwargs)
    return captured["custom_env"]


def test_base_launch_functions_inject_hotpatcher_env(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager import comfyui_base, fooocus_base, mizuoto_tts_webui_base, qwen_tts_webui_base, rvc_next_webui_base, sd_trainer_base, sd_webui_base

    targets = (
        (sd_webui_base, sd_webui_base.launch_sd_webui, "sd_webui_path"),
        (comfyui_base, comfyui_base.launch_comfyui, "comfyui_path"),
        (fooocus_base, fooocus_base.launch_fooocus, "fooocus_path"),
        (qwen_tts_webui_base, qwen_tts_webui_base.launch_qwen_tts_webui, "qwen_tts_webui_path"),
        (rvc_next_webui_base, rvc_next_webui_base.launch_rvc_next_webui, "rvc_next_webui_path"),
        (mizuoto_tts_webui_base, mizuoto_tts_webui_base.launch_mizuoto_tts_webui, "mizuoto_tts_webui_path"),
        (sd_trainer_base, sd_trainer_base.launch_sd_trainer, "sd_trainer_path"),
    )

    for module, launch_func, path_arg in targets:
        config_path = tmp_path / f"{module.__name__.rsplit('.', maxsplit=1)[-1]}.json"
        env = _capture_webui_launch_env(monkeypatch, module, launch_func, path_arg, tmp_path)
        assert all(not key.startswith(HOTPATCHER_ENV_PREFIX) for key in env)

        enabled_env = _capture_webui_launch_env(
            monkeypatch,
            module,
            launch_func,
            path_arg,
            tmp_path,
            enable_hotpatcher=True,
        )
        assert enabled_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"]
        assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME" not in enabled_env
        assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT" not in enabled_env

        disabled_env = _capture_webui_launch_env(
            monkeypatch,
            module,
            launch_func,
            path_arg,
            tmp_path,
            enable_hotpatcher=False,
        )
        assert all(not key.startswith(HOTPATCHER_ENV_PREFIX) for key in disabled_env)

        custom_env = _capture_webui_launch_env(
            monkeypatch,
            module,
            launch_func,
            path_arg,
            tmp_path,
            enable_hotpatcher=True,
            hotpatcher_config_path=config_path,
            hotpatcher_port=9901,
        )
        assert custom_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] == "file"
        assert custom_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] == config_path.as_posix()
        assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT" not in custom_env

        runtime_env = _capture_webui_launch_env(
            monkeypatch,
            module,
            launch_func,
            path_arg,
            tmp_path,
            enable_hotpatcher=True,
            enable_hotpatcher_runtime=True,
            hotpatcher_config_path=config_path,
            hotpatcher_port=9901,
        )
        assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME"] == "1"
        assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] == config_path.as_posix()
        assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == "9901"


def test_invokeai_launch_delegates_to_launch_webui(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager import invokeai_base

    implementation = sys.modules[invokeai_base.launch_invokeai.__module__]

    launch_calls = []
    fake_env = {
        "PYTHONPATH": "existing",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "stale",
    }
    original_fake_env = fake_env.copy()

    def fake_env_passthrough(*, origin_env=None, **_kwargs):
        return dict(origin_env or {})

    def fake_launch_webui(**kwargs):
        launch_calls.append(kwargs)

    monkeypatch.setattr(implementation.os, "environ", fake_env)
    monkeypatch.setattr(implementation, "apply_hf_mirror", fake_env_passthrough)
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", fake_env_passthrough)
    monkeypatch.setattr(implementation, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(implementation, "launch_webui", fake_launch_webui)

    invokeai_base.launch_invokeai(tmp_path, use_cuda_malloc=False)

    assert fake_env == original_fake_env
    assert launch_calls[-1]["webui_path"] == tmp_path
    assert launch_calls[-1]["launch_script"] == invokeai_base.INVOKEAI_RUNNER_SCRIPT
    assert launch_calls[-1]["webui_name"] == "InvokeAI"
    assert launch_calls[-1]["launch_args"] is None
    assert launch_calls[-1]["custom_env"]["INVOKEAI_ROOT"] == tmp_path.as_posix()
    assert all(not key.startswith(HOTPATCHER_ENV_PREFIX) for key in launch_calls[-1]["custom_env"])

    config_path = tmp_path / "invokeai_patcher.json"
    invokeai_base.launch_invokeai(
        tmp_path,
        launch_args=["--host", "127.0.0.1"],
        use_cuda_malloc=False,
        enable_hotpatcher=True,
        hotpatcher_config_path=config_path,
        hotpatcher_port=9902,
    )

    custom_env = launch_calls[-1]["custom_env"]
    assert launch_calls[-1]["launch_args"] == ["--host", "127.0.0.1"]
    assert custom_env["PYTHONPATH"].split(os.pathsep)[0] == HOTPATCHER_PATH.as_posix()
    assert custom_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] == config_path.as_posix()
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME" not in custom_env
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT" not in custom_env

    invokeai_base.launch_invokeai(
        tmp_path,
        use_cuda_malloc=False,
        enable_hotpatcher=True,
        enable_hotpatcher_runtime=True,
        hotpatcher_config_path=config_path,
        hotpatcher_port=9902,
    )

    runtime_env = launch_calls[-1]["custom_env"]
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME"] == "1"
    assert runtime_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == "9902"
    assert fake_env == original_fake_env
