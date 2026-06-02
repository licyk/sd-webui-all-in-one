import argparse
import json
import os
import socket
import subprocess
import sys
import threading

import pytest

from sd_webui_all_in_one.base_manager import hotpatcher_manager
from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_HOTPATCHER_CONFIG_PATH,
    DEFAULT_RUNTIME_PORT,
    HOTPATCHER_PATH,
    HOTPATCHER_ENV_PREFIX,
    HotpatcherRuntimeHost,
    apply_hotpatcher_launch_env,
    build_hotpatcher_runtime_env,
    export_hotpatcher_default_config,
    get_hotpatcher_catalog,
    get_hotpatcher_default_config,
    load_hotpatcher_config,
    save_hotpatcher_config,
    wait_for_runtime_log,
    wait_for_service_channel,
)
from sd_webui_all_in_one.base_manager.base import launch_webui
from sd_webui_all_in_one.cli_manager.utils import register_manager


def _send_json_line(file, message):
    file.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
    file.flush()


def _read_json_line(file):
    return json.loads(file.readline().decode("utf-8"))


def test_hotpatcher_import_path_is_injected(monkeypatch):
    patcher_path = HOTPATCHER_PATH.as_posix()
    monkeypatch.setattr(sys, "path", [item for item in sys.path if item != patcher_path])

    config = get_hotpatcher_default_config()

    assert patcher_path in sys.path
    assert "core" in config


def test_hotpatcher_catalog_schema_is_json_serializable():
    catalog = get_hotpatcher_catalog()

    assert json.loads(json.dumps(catalog, ensure_ascii=False)) == catalog
    services = catalog["features"]["services"]
    assert services["title"] == "服务控制"
    assert services["settings"]["apply_on_bootstrap"]["type"] == "bool"
    assert "default" in services["settings"]["apply_on_bootstrap"]
    assert catalog["features"]["extensions.uv_pip"]["settings"]["symlink"]["type"] == "bool"


def test_hotpatcher_config_export_load_save_and_overwrite_guard(tmp_path):
    output = tmp_path / "hotpatcher.json"

    exported = export_hotpatcher_default_config(output)

    assert exported == output
    assert load_hotpatcher_config(output)["core"]["import_hook"]["enabled"] is True
    with pytest.raises(FileExistsError):
        export_hotpatcher_default_config(output)

    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"extensions": {"hf_endpoint_mirror": {"enabled": True}}}), encoding="utf-8")
    normalized = load_hotpatcher_config(partial, normalize=True)
    assert normalized["extensions"]["hf_endpoint_mirror"]["enabled"] is True
    assert "zluda" in normalized["extensions"]
    assert "uv_pip" in normalized["extensions"]

    saved = tmp_path / "saved.json"
    save_hotpatcher_config(saved, {"core": {"import_hook": {"enabled": True}}})
    saved_config = json.loads(saved.read_text(encoding="utf-8"))
    assert saved_config["core"]["import_hook"]["enabled"] is True
    assert "runtime" in saved_config


def test_build_hotpatcher_runtime_env():
    env = build_hotpatcher_runtime_env("127.0.0.1", 8765, token="secret")

    assert env["PYTHONPATH"] == HOTPATCHER_PATH.as_posix()
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME"] == "1"
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES"] == "1"
    assert env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] == "secret"


def test_apply_hotpatcher_launch_env_uses_default_json_when_config_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(hotpatcher_manager, "DEFAULT_HOTPATCHER_CONFIG_PATH", tmp_path / "missing.json")
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
    monkeypatch.setattr(hotpatcher_manager, "DEFAULT_HOTPATCHER_CONFIG_PATH", config_file)

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
    monkeypatch.setattr(hotpatcher_manager, "DEFAULT_HOTPATCHER_CONFIG_PATH", tmp_path / "missing.json")
    env = apply_hotpatcher_launch_env(dict(os.environ), enabled=True)
    env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON"] = json.dumps(
        {
            "services": {"apply_on_bootstrap": True},
            "core": {
                "import_hook": {"enabled": False},
                "stack_shadow": {"enabled": False},
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
    assert result["parent_result"] == {"applied": [], "warnings": [], "errors": []}
    assert result["child"] == {"marker": "1", "result": None}


def test_launch_webui_keeps_hotpatcher_pythonpath_first(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager import base as base_module

    captured = {}

    def fake_run_cmd(cmd, custom_env=None, cwd=None):
        captured["cmd"] = cmd
        captured["custom_env"] = custom_env
        captured["cwd"] = cwd

    monkeypatch.setattr(base_module, "run_cmd", fake_run_cmd)
    env = apply_hotpatcher_launch_env({"PYTHONPATH": "existing"}, enabled=True)

    launch_webui(tmp_path, "launch.py", launch_args=["--demo"], custom_env=env)

    pythonpath = captured["custom_env"]["PYTHONPATH"].split(os.pathsep)
    assert pythonpath[:3] == [HOTPATCHER_PATH.as_posix(), tmp_path.as_posix(), "existing"]
    assert captured["cwd"] == tmp_path
    assert captured["cmd"][-1] == "--demo"


def test_default_hotpatcher_config_path_uses_launch_path():
    assert DEFAULT_HOTPATCHER_CONFIG_PATH.name == "patcher_config.json"


def test_runtime_host_serves_config_and_records_logs():
    with HotpatcherRuntimeHost(port=0, get_config=lambda: {"answer": 42}) as host:
        with socket.create_connection(host.server_address, timeout=2) as sock:
            file = sock.makefile("rwb")
            _send_json_line(file, {"type": "hello", "version": 1, "features": ["config", "logs"]})
            _send_json_line(file, {"id": "cfg", "type": "config.get", "payload": {}})
            response = _read_json_line(file)
            assert response == {"id": "cfg", "ok": True, "payload": {"config": {"answer": 42}}}

            _send_json_line(
                file,
                {
                    "type": "log.record",
                    "payload": {
                        "logger": "demo",
                        "level": "WARNING",
                        "message": "hello",
                    },
                },
            )
            entry = wait_for_runtime_log(host, lambda item: item.payload.get("message") == "hello")
            assert entry is not None
            assert entry.format_line() == "[WARNING] demo: hello"


def test_runtime_client_optional_connection_failure_is_quiet(monkeypatch, capsys):
    from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", "127.0.0.1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(port))
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT", "0.1")

    assert RuntimeClient.connect_from_env(required=False) is None
    assert "ConnectionRefusedError" not in capsys.readouterr().err

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG", "1")
    assert RuntimeClient.connect_from_env(required=False) is None
    debug_err = capsys.readouterr().err
    assert "Traceback" in debug_err
    assert "ConnectionRefusedError" in debug_err or "TimeoutError" in debug_err


def test_runtime_host_services_channel_roundtrip():
    with HotpatcherRuntimeHost(port=0) as host:
        with socket.create_connection(host.server_address, timeout=2) as sock:
            file = sock.makefile("rwb")
            _send_json_line(file, {"type": "channel.open", "channel": "services", "token": ""})
            assert wait_for_service_channel(host)

            result = {}
            error = {}

            def _request():
                try:
                    result["value"] = host.request_services("services.config.apply", {"config": {"core": {}}}, timeout=2)
                except Exception as exc:  # pragma: no cover - makes thread assertion readable
                    error["value"] = exc

            thread = threading.Thread(target=_request)
            thread.start()
            request = _read_json_line(file)
            assert request["type"] == "services.config.apply"
            assert request["payload"] == {"config": {"core": {}}}
            _send_json_line(file, {"id": request["id"], "ok": True, "payload": {"result": {"applied": ["core.import_hook"]}}})
            thread.join(timeout=2)

            assert error == {}
            assert result["value"] == {"result": {"applied": ["core.import_hook"]}}


def test_self_manager_patcher_cli_parser(tmp_path):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_manager(subparsers)

    export_args = parser.parse_args(["self-manager", "patcher", "export-config", "--output", str(tmp_path / "config.json"), "--force"])
    assert export_args.patcher_action == "export-config"
    assert export_args.force is True
    assert callable(export_args.func)

    pythonpath_args = parser.parse_args(["self-manager", "patcher", "get-pythonpath"])
    assert pythonpath_args.patcher_action == "get-pythonpath"
    assert callable(pythonpath_args.func)

    tcmalloc_args = parser.parse_args(["self-manager", "get-tcmalloc"])
    assert tcmalloc_args.sd_webui_all_in_one_action == "get-tcmalloc"
    assert tcmalloc_args.path is False
    assert callable(tcmalloc_args.func)

    tcmalloc_path_args = parser.parse_args(["self-manager", "get-tcmalloc", "--path"])
    assert tcmalloc_path_args.sd_webui_all_in_one_action == "get-tcmalloc"
    assert tcmalloc_path_args.path is True
    assert callable(tcmalloc_path_args.func)

    gui_args = parser.parse_args(["self-manager", "patcher", "gui"])
    assert gui_args.patcher_action == "gui"
    assert gui_args.config == DEFAULT_HOTPATCHER_CONFIG_PATH
    assert gui_args.host == "127.0.0.1"
    assert gui_args.port == 8765
    assert callable(gui_args.func)


def test_self_manager_patcher_get_pythonpath_cli(monkeypatch, capsys):
    from sd_webui_all_in_one.cli_manager import utils as cli_utils

    monkeypatch.setenv("PYTHONPATH", "existing")

    cli_utils.get_hotpatcher_pythonpath_cli()

    pythonpath = capsys.readouterr().out.strip().split(os.pathsep)
    assert pythonpath[:2] == [HOTPATCHER_PATH.as_posix(), "existing"]


def _capture_webui_launch_env(monkeypatch, module, launch_func, path_arg: str, tmp_path, **kwargs):
    captured = {}

    def fake_git_env(*, origin_env=None, **_kwargs):
        env = (origin_env or os.environ.copy()).copy()
        env["GIT_CONFIG_GLOBAL"] = "test-git-config"
        return env

    def fake_env_passthrough(*, origin_env=None, **_kwargs):
        return (origin_env or os.environ.copy()).copy()

    monkeypatch.setattr(module, "apply_git_base_config_and_github_mirror", fake_git_env)
    monkeypatch.setattr(module, "apply_hf_mirror", fake_env_passthrough)
    monkeypatch.setattr(module, "get_pypi_mirror_config", fake_env_passthrough)
    monkeypatch.setattr(module, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(module, "launch_webui", lambda **launch_kwargs: captured.update(launch_kwargs))

    launch_kwargs = {
        path_arg: tmp_path,
        "launch_args": [],
        "use_cuda_malloc": False,
    }
    launch_kwargs.update(kwargs)
    launch_func(**launch_kwargs)
    return captured["custom_env"]


def test_base_launch_functions_inject_hotpatcher_env(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager import comfyui_base
    from sd_webui_all_in_one.base_manager import fooocus_base
    from sd_webui_all_in_one.base_manager import qwen_tts_webui_base
    from sd_webui_all_in_one.base_manager import sd_trainer_base
    from sd_webui_all_in_one.base_manager import sd_webui_base

    targets = (
        (sd_webui_base, sd_webui_base.launch_sd_webui, "sd_webui_path"),
        (comfyui_base, comfyui_base.launch_comfyui, "comfyui_path"),
        (fooocus_base, fooocus_base.launch_fooocus, "fooocus_path"),
        (qwen_tts_webui_base, qwen_tts_webui_base.launch_qwen_tts_webui, "qwen_tts_webui_path"),
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


def test_invokeai_launch_injects_hotpatcher_in_current_process(monkeypatch, tmp_path):
    from sd_webui_all_in_one.base_manager import invokeai_base

    configure_calls = []
    events = []
    fake_env = {
        "PYTHONPATH": "existing",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "stale",
    }

    def fake_env_passthrough(*, origin_env=None, **_kwargs):
        return (origin_env or fake_env).copy()

    def fake_exit(code):
        raise SystemExit(code)

    def fake_print_divider(char=None):
        events.append(("divider", char))

    def fake_run_invokeai():
        events.append("run")

    monkeypatch.setattr(invokeai_base.os, "environ", fake_env)
    monkeypatch.setattr(invokeai_base.os, "_exit", fake_exit)
    monkeypatch.setattr(invokeai_base.sys, "argv", ["invokeai"])
    monkeypatch.setattr(invokeai_base, "apply_hf_mirror", fake_env_passthrough)
    monkeypatch.setattr(invokeai_base, "get_pypi_mirror_config", fake_env_passthrough)
    monkeypatch.setattr(invokeai_base, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(invokeai_base, "print_divider", fake_print_divider)
    monkeypatch.setattr(invokeai_base, "run_invokeai", fake_run_invokeai)
    monkeypatch.setattr(
        invokeai_base,
        "configure_hotpatcher_for_current_process",
        lambda enabled=False: configure_calls.append(enabled),
    )

    with pytest.raises(SystemExit):
        invokeai_base.launch_invokeai(tmp_path, use_cuda_malloc=False)

    assert configure_calls == [False]
    assert all(not key.startswith(HOTPATCHER_ENV_PREFIX) for key in fake_env)
    assert events == [("divider", "="), "run", ("divider", "=")]

    configure_calls.clear()
    events.clear()
    config_path = tmp_path / "invokeai_patcher.json"
    with pytest.raises(SystemExit):
        invokeai_base.launch_invokeai(
            tmp_path,
            use_cuda_malloc=False,
            enable_hotpatcher=True,
            hotpatcher_config_path=config_path,
            hotpatcher_port=9902,
        )

    assert configure_calls == [True]
    assert fake_env["PYTHONPATH"].split(os.pathsep)[0] == HOTPATCHER_PATH.as_posix()
    assert fake_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] == config_path.as_posix()
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME" not in fake_env
    assert "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT" not in fake_env
    assert events == [("divider", "="), "run", ("divider", "=")]

    configure_calls.clear()
    events.clear()
    with pytest.raises(SystemExit):
        invokeai_base.launch_invokeai(
            tmp_path,
            use_cuda_malloc=False,
            enable_hotpatcher=True,
            enable_hotpatcher_runtime=True,
            hotpatcher_config_path=config_path,
            hotpatcher_port=9902,
        )

    assert configure_calls == [True]
    assert fake_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME"] == "1"
    assert fake_env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == "9902"
    assert events == [("divider", "="), "run", ("divider", "=")]


@pytest.mark.parametrize(
    ("register_name", "command"),
    (
        ("register_sd_webui", "sd-webui"),
        ("register_comfyui", "comfyui"),
        ("register_fooocus", "fooocus"),
        ("register_qwen_tts_webui", "qwen-tts-webui"),
        ("register_sd_trainer", "sd-trainer"),
        ("register_invokeai", "invokeai"),
    ),
)
def test_webui_launch_cli_hotpatcher_parser(register_name, command, tmp_path):
    modules = {
        "register_sd_webui": "sd_webui_all_in_one.cli_manager.sd_webui_cli",
        "register_comfyui": "sd_webui_all_in_one.cli_manager.comfyui_cli",
        "register_fooocus": "sd_webui_all_in_one.cli_manager.fooocus_cli",
        "register_qwen_tts_webui": "sd_webui_all_in_one.cli_manager.qwen_tts_webui_cli",
        "register_sd_trainer": "sd_webui_all_in_one.cli_manager.sd_trainer_cli",
        "register_invokeai": "sd_webui_all_in_one.cli_manager.invokeai_cli",
    }
    module = __import__(modules[register_name], fromlist=[register_name])
    register_func = getattr(module, register_name)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_func(subparsers)

    default_args = parser.parse_args([command, "launch"])
    assert default_args.enable_hotpatcher is True
    assert default_args.enable_hotpatcher_runtime is False
    assert default_args.hotpatcher_config_path is None
    assert default_args.hotpatcher_port is None

    config_path = tmp_path / "patcher.json"
    custom_args = parser.parse_args(
        [
            command,
            "launch",
            "--no-hotpatcher",
            "--hotpatcher-runtime",
            "--hotpatcher-config",
            config_path.as_posix(),
            "--hotpatcher-port",
            "9901",
        ]
    )
    assert custom_args.enable_hotpatcher is False
    assert custom_args.enable_hotpatcher_runtime is True
    assert custom_args.hotpatcher_config_path == config_path
    assert custom_args.hotpatcher_port == 9901


def test_hotpatcher_gui_module_importable():
    from sd_webui_all_in_one.base_manager.gui import hotpatcher_manager_gui

    assert hotpatcher_manager_gui.HotpatcherManagerApp is not None


def test_hotpatcher_gui_schema_helpers():
    from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui import (
        _metadata_field_kind,
        _value_to_text,
    )

    assert _metadata_field_kind({"type": "choice"}, "safe") == "choice"
    assert _metadata_field_kind({"type": "list[str]"}, []) == "list"
    assert _metadata_field_kind({"type": "object"}, False) == "object"
    assert _value_to_text({"enabled": True}, "object") == '{"enabled":true}'
