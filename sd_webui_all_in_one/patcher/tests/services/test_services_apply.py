"""Hotpatcher 服务配置应用测试"""

import sys
import types
from typing import cast

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.services import (
    apply_config,
    clear_current_config,
)
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess


def _coverage_tracing_active():
    tracer = sys.gettrace()
    return tracer is not None and tracer.__class__.__module__.startswith("coverage")


def coverage_trace_conflict(test_func):
    test_func = pytest.mark.coverage_trace_conflict(test_func)
    return pytest.mark.skipif(
        _coverage_tracing_active(),
        reason="coverage installs sys.settrace and conflicts with explicit trace-conflict tests",
    )(test_func)


@pytest.fixture(autouse=True)
def clean_service_state():
    clear_current_config()
    uninstall_error_capture()
    uninstall_log_capture()
    uninstall_import_hook()
    uninstall_stack_shadower()
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()
    yield
    clear_current_config()
    uninstall_error_capture()
    uninstall_log_capture()
    uninstall_import_hook()
    uninstall_stack_shadower()
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()


def test_apply_config_browser_modes_are_idempotent_and_open_variants_emit_once(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser

    calls = []

    class Client:
        def event(self, event_type, payload):
            calls.append((event_type, payload))

    original_calls = []
    module = types.ModuleType("webbrowser")

    def original(url, *args, **kwargs):
        original_calls.append((url, args, kwargs))
        return False

    setattr(module, "open", original)
    setattr(module, "open_new", lambda url: getattr(module, "open")(url, 1))
    setattr(module, "open_new_tab", lambda url: getattr(module, "open")(url, 2))
    monkeypatch.setitem(sys.modules, "webbrowser", module)
    monkeypatch.setattr(browser, "install_import_hook", lambda **_kwargs: None)
    registered = []
    monkeypatch.setattr(browser, "register_hook", lambda *args, **kwargs: registered.append((args, kwargs)))
    state = HotpatcherState()

    host_config = {"runtime": {"browser": {"enabled": True, "mode": "host"}}}
    first = apply_config(host_config, runtime_client=cast(RuntimeClient, Client()), state=state)
    wrapper = getattr(module, "open")
    second = apply_config(host_config, runtime_client=cast(RuntimeClient, Client()), state=state)
    assert first["errors"] == second["errors"] == []
    assert getattr(module, "open") is wrapper
    assert len(registered) == 1
    assert getattr(module, "open_new")("http://127.0.0.1:7860") is True
    assert getattr(module, "open_new_tab")("http://localhost:8188") is True
    assert [event[0] for event in calls] == ["browser.open", "browser.open"]

    apply_config(
        {"runtime": {"browser": {"enabled": True, "mode": "suppress"}}},
        runtime_client=cast(RuntimeClient, Client()),
        state=state,
    )
    assert getattr(module, "open")("http://localhost:3000", autoraise=False) is True
    assert len(calls) == 2

    apply_config(
        {"runtime": {"browser": {"enabled": True, "mode": "passthrough"}}},
        runtime_client=cast(RuntimeClient, Client()),
        state=state,
    )
    assert getattr(module, "open")("https://example.test", 0, autoraise=True) is False
    assert original_calls == [("https://example.test", (0,), {"autoraise": True})]


def test_host_mode_without_runtime_client_suppresses_and_reports_diagnostics(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser

    module = types.ModuleType("webbrowser")
    setattr(module, "open", lambda *_args, **_kwargs: pytest.fail("system browser must stay suppressed"))
    monkeypatch.setitem(sys.modules, "webbrowser", module)
    monkeypatch.setattr(browser, "install_import_hook", lambda **_kwargs: None)
    monkeypatch.setattr(browser, "register_hook", lambda *_args, **_kwargs: None)
    state = HotpatcherState()
    with pytest.warns(RuntimeWarning, match="remains suppressed"):
        result = apply_config(
            {"runtime": {"browser": {"enabled": True, "mode": "host"}}},
            state=state,
        )
    assert getattr(module, "open")("http://localhost:7860") is True
    assert result["warnings"][0]["feature"] == "runtime.browser"
    assert state.browser_diagnostics


def test_apply_config_enables_core_and_extension_patches(monkeypatch):
    calls = []

    def fake_zluda(config):
        calls.append(("zluda", config["compat"]))

    def fake_extension_index(config):
        calls.append(("extension_index", config["comfyui_manager"]["enabled"]))

    def fake_comfyui_auto_port(config):
        calls.append(("comfyui_auto_port", config["enabled"]))

    def fake_hf_endpoint(config):
        calls.append(("hf_endpoint_mirror", config["enabled"]))

    def fake_uv_pip(config):
        calls.append(("uv_pip", config["symlink"]))

    def fake_xformers_cutlass(config):
        calls.append(("xformers_cutlass", config["enabled"]))
        return True

    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.zluda.apply_from_config", fake_zluda)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.comfyui_auto_port.apply_from_config", fake_comfyui_auto_port)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.extension_index.apply_from_config", fake_extension_index)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror.apply_from_config", fake_hf_endpoint)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.xformers_cutlass.apply_from_config", fake_xformers_cutlass)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.uv_pip.apply_from_config", fake_uv_pip)

    result = apply_config(
        {
            "core": {
                "import_hook": {"enabled": True},
                "stack_shadow": {"enabled": True, "prefixes": "svc_hidden"},
            },
            "extensions": {
                "zluda": {"enabled": True, "compat": True},
                "comfyui_auto_port": {"enabled": True},
                "extension_index": {"comfyui_manager": {"enabled": True}},
                "hf_endpoint_mirror": {"enabled": True},
                "xformers_cutlass": {"enabled": True},
                "uv_pip": {"enabled": True, "symlink": True},
            },
        }
    )

    assert "core.import_hook" in result["applied"]
    assert "core.stack_shadow" in result["applied"]
    assert ("zluda", True) in calls
    assert ("comfyui_auto_port", True) in calls
    assert ("extension_index", True) in calls
    assert ("hf_endpoint_mirror", True) in calls
    assert ("xformers_cutlass", True) in calls
    assert ("uv_pip", True) in calls
    assert "extensions.xformers_cutlass" in result["applied"]
    assert result["errors"] == []


def test_apply_config_does_not_report_skipped_xformers_cutlass_patch(monkeypatch):
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.xformers_cutlass.apply_from_config", lambda _config: False)

    result = apply_config({"extensions": {"xformers_cutlass": {"enabled": True}}})

    assert "extensions.xformers_cutlass" not in result["applied"]
    assert result["errors"] == []


def test_apply_config_warns_when_logs_enabled_without_runtime_client():
    result = apply_config({"runtime": {"logs": {"enabled": True}}})

    assert result["warnings"] == [
        {
            "feature": "runtime.logs",
            "message": "runtime_client is required to enable logs",
        }
    ]


def test_apply_config_warns_when_errors_enabled_without_runtime_client():
    result = apply_config({"runtime": {"errors": {"enabled": True}}})

    assert result["warnings"] == [
        {
            "feature": "runtime.errors",
            "message": "runtime_client is required to enable errors",
        }
    ]


@coverage_trace_conflict
def test_apply_config_reports_error_when_caught_tracer_conflicts():
    def existing_trace(frame, event, arg):
        return existing_trace

    sys.settrace(existing_trace)
    try:
        result = apply_config(
            {
                "runtime": {
                    "errors": {
                        "enabled": True,
                        "caught_exceptions": {
                            "enabled": True,
                        },
                    }
                }
            },
            runtime_client=object(),  # ty: ignore[invalid-argument-type]
        )
        assert result["errors"]
        assert result["errors"][0]["feature"] == "runtime.errors"
        assert result["errors"][0]["code"] == "RuntimeError"
        assert "another sys trace function" in result["errors"][0]["message"]
        assert sys.gettrace() is existing_trace
    finally:
        sys.settrace(None)
