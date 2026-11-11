"""统一控制命令测试: 注册表、载荷校验、传输策略、services 兼容、桌面映射、能力探测、远程加载门禁与 Python 门面。"""

import importlib
import importlib.util
import json
import socket
import subprocess
import sys
import textwrap
import threading
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher import bootstrap
from sd_webui_all_in_one_hotpatcher.control import DYNAMIC_PACKAGE, get_loaded_patch, get_patch_set, unload_patch
from sd_webui_all_in_one_hotpatcher.control.builtin_commands import check_config_borne_load
from sd_webui_all_in_one_hotpatcher.control.commands import (
    CONTROL_VERSION,
    ERROR_CODES,
    MAX_DESKTOP_RESULT_BYTES,
    CommandContext,
    CommandError,
    CommandRegistry,
    CommandSpec,
    PayloadField,
    error_envelope,
    run_after_send,
    unwrap_envelope,
    validate_payload,
)
from sd_webui_all_in_one_hotpatcher.control.controller import HotpatchController, get_controller
from sd_webui_all_in_one_hotpatcher.control.features import FeatureSpec, get_feature_registry
from sd_webui_all_in_one_hotpatcher.runtime.client import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import DesktopBrokerCommandError
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.runtime.protocol import PROTOCOL_VERSION, encode_message
from sd_webui_all_in_one_hotpatcher.services import (
    PatchService,
    ServiceControlChannel,
    apply_config,
    clear_current_config,
    get_current_config,
    handle_request_json,
    install_service_control_channel,
    set_current_config,
)
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess

PATCHER_ROOT = Path(__file__).resolve().parents[2]
# 复用 tests/runtime 的测试工具 (JsonlHost、FakeSocket); 单独运行本目录时该目录不在 sys.path 中。
RUNTIME_TEST_DIR = str(Path(__file__).resolve().parents[1] / "runtime")
if RUNTIME_TEST_DIR not in sys.path:
    sys.path.insert(0, RUNTIME_TEST_DIR)
_legacy_helpers: Any = importlib.import_module("legacy_transport_test_helpers")
_runtime_helpers: Any = importlib.import_module("runtime_test_helpers")
FakeSocket = _legacy_helpers.FakeSocket
ScriptedReader = _legacy_helpers.ScriptedReader
JsonlHost = _runtime_helpers.JsonlHost
TARGET = "hpcmd_target"
MODULE_PREFIX = "hpcmd_"
QUIET_CONFIG = {
    "core": {"import_hook": {"enabled": False}, "stack_shadow": {"enabled": False}},
    "extensions": {"comfyui_auto_port": {"enabled": False}, "xformers_cutlass": {"enabled": False}},
}
PATCH_SOURCE = """
import sys

TARGET = sys.modules["hpcmd_target"]


def setup(ctx):
    ctx.set_attr(TARGET, "VALUE", ctx.config.get("value", "patched"))
"""


def _reset(state: HotpatcherState) -> None:
    for name in list(state.loaded_patches):
        unload_patch(name, state=state)
    for target in (state, None):
        clear_current_config(state=target)
        uninstall_error_capture(state=target)
        uninstall_log_capture(state=target)
        uninstall_import_hook(state=target)
        uninstall_stack_shadower(state=target)
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()


@pytest.fixture
def state():
    isolated = HotpatcherState()
    _reset(isolated)
    meta_path_before = list(sys.meta_path)
    spec_from_file_location_before = importlib.util.spec_from_file_location
    sys_path_before = list(sys.path)
    yield isolated
    _reset(isolated)
    sys.path[:] = sys_path_before
    for name in list(sys.modules):
        if name.startswith(MODULE_PREFIX) or name.startswith(f"{DYNAMIC_PACKAGE}."):
            del sys.modules[name]
    importlib.invalidate_caches()
    assert sys.meta_path == meta_path_before
    assert importlib.util.spec_from_file_location is spec_from_file_location_before


@pytest.fixture
def target():
    module: Any = types.ModuleType(TARGET)
    module.VALUE = "original"
    sys.modules[TARGET] = module
    return module


@pytest.fixture
def patch_file(tmp_path):
    path = tmp_path / "hpcmd_fix.py"
    path.write_text(textwrap.dedent(PATCH_SOURCE).lstrip(), encoding="utf-8")
    return path


def _quiet_config(**sections):
    # 关闭会向默认状态全局补丁注册表登记补丁的功能, 避免推进默认状态的句柄计数器影响其他测试。
    config = json.loads(json.dumps(QUIET_CONFIG))
    config.update(sections)
    return config


def _dispatch(state, name, payload=None, *, transport="inprocess", token=None, runtime_client=None, after_send=None):
    envelope = get_controller(state).dispatch(name, payload, transport=transport, token=token, runtime_client=runtime_client, after_send=after_send)
    # 所有 envelope 都必须能直接写入 JSONL 通道
    assert json.loads(json.dumps(envelope)) == envelope
    return envelope


def _ok(envelope):
    assert envelope["ok"] is True, envelope
    return envelope["payload"]


def _err(envelope):
    assert envelope["ok"] is False, envelope
    assert envelope["error"]["code"] in ERROR_CODES
    return envelope["error"]


def _legacy(state, request, *, token="tok", after_send=None):
    return PatchService(state=state).handle_control_request(request, runtime_client=None, transport="legacy", token=token, after_send=after_send)


def _recording_spec(name, calls, **options):
    def handler(ctx, payload):
        calls.append((ctx.transport, payload))
        return {"echo": payload}

    return CommandSpec(name=name, handler=handler, **options)


# ---------------------------------------------------------------------------
# 注册表与载荷校验
# ---------------------------------------------------------------------------


def test_payload_validation_errors_and_defaults():
    spec = CommandSpec(
        name="demo.validate",
        handler=lambda ctx, payload: payload,
        payload={
            "name": PayloadField("str", required=True, max_len=4),
            "count": PayloadField("int", default=3),
            "ratio": PayloadField("float"),
            "mode": PayloadField("str", choices=("a", "b")),
            "items": PayloadField("list", max_len=2),
            "extra": PayloadField("dict", nullable=True),
        },
    )

    assert validate_payload(spec, {"name": "ok", "ratio": 1, "unknown": True}) == {"name": "ok", "count": 3, "ratio": 1.0, "unknown": True}
    assert validate_payload(spec, {"name": "ok", "extra": None}) == {"name": "ok", "count": 3}
    cases = [
        ({}, "payload.name is required"),
        ({"name": "   "}, "payload.name must be a non-empty string"),
        ({"name": 1}, "payload.name must be of type str, got int"),
        ({"name": "toolong"}, "payload.name exceeds the maximum length of 4"),
        ({"name": "ok", "count": True}, "payload.count must be of type int, got bool"),
        ({"name": "ok", "ratio": "1"}, "payload.ratio must be of type float, got str"),
        ({"name": "ok", "mode": "c"}, "payload.mode must be one of 'a', 'b', got 'c'"),
        ({"name": "ok", "items": [1, 2, 3]}, "payload.items exceeds the maximum length of 2"),
        ({"name": "ok", "extra": []}, "payload.extra must be of type dict, got list"),
    ]
    for payload, message in cases:
        with pytest.raises(CommandError) as exc_info:
            validate_payload(spec, payload)
        assert (exc_info.value.code, exc_info.value.message) == ("invalid_payload", message)


def test_dispatch_validation_errors_become_invalid_payload_envelopes(state):
    assert _err(_dispatch(state, "hotpatch.patches.get", [])) == {"code": "invalid_payload", "message": "payload must be an object"}
    assert _err(_dispatch(state, "hotpatch.patches.get", {})) == {"code": "invalid_payload", "message": "payload.id is required"}
    assert _err(_dispatch(state, "hotpatch.debug.strict.set", {"enabled": "yes"}))["code"] == "invalid_payload"
    assert _err(_dispatch(state, "hotpatch.inspect.explain", {"module": ""}))["code"] == "invalid_payload"
    assert _err(_dispatch(state, "hotpatch.patches.list", {"limit": 0}))["code"] == "invalid_payload"
    assert _err(_dispatch(state, "hotpatch.debug.events.read", {"since_cursor": -1}))["code"] == "invalid_payload"


def test_registry_register_alias_resolution_and_conflicts():
    registry = CommandRegistry()
    calls: list = []
    spec = registry.register(_recording_spec("demo.cmd", calls, aliases=("demo.alias",)))

    assert registry.get("demo.cmd") is spec
    assert registry.get("demo.alias") is spec
    assert "demo.alias" in registry
    assert registry.names() == ["demo.cmd"]
    assert registry.names(include_aliases=True) == ["demo.alias", "demo.cmd"]
    assert registry.aliases() == {"demo.alias": "demo.cmd"}
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_recording_spec("demo.cmd", calls))
    with pytest.raises(ValueError, match="alias"):
        registry.register(_recording_spec("demo.other", calls, aliases=("demo.alias",)))
    with pytest.raises(ValueError, match="alias"):
        registry.register(_recording_spec("demo.alias", calls))

    replacement = registry.register(_recording_spec("demo.cmd", calls, aliases=("demo.new",)), replace=True)
    assert registry.get("demo.alias") is None
    assert registry.get("demo.new") is replacement

    ctx = CommandContext(state=HotpatcherState())
    assert registry.dispatch("demo.new", {"x": 1}, ctx) == {"ok": True, "payload": {"echo": {"x": 1}}}
    assert ctx.command == "demo.cmd"
    assert registry.unregister("demo.new") is replacement
    assert registry.dispatch("demo.cmd", {}, ctx) == {"ok": False, "error": {"code": "unknown_request", "message": "unknown services request: demo.cmd"}}

    with pytest.raises(ValueError, match="unknown payload field type"):
        PayloadField("tuple")
    with pytest.raises(ValueError):
        CommandSpec(name="", handler=lambda ctx, payload: {})
    with pytest.raises(TypeError):
        CommandSpec(name="demo.bad", handler=cast(Any, None))


def test_dispatch_never_raises_and_maps_handler_failures():
    registry = CommandRegistry()

    def boom(ctx, payload):
        raise RuntimeError("boom")

    def typed(ctx, payload):
        raise CommandError("conflict", "typed", details={"why": 1})

    registry.register(CommandSpec(name="demo.boom", handler=boom))
    registry.register(CommandSpec(name="demo.typed", handler=typed))
    registry.register(CommandSpec(name="demo.bad_result", handler=lambda ctx, payload: cast(Any, [1])))
    ctx = CommandContext(state=HotpatcherState())

    assert registry.dispatch("demo.boom", {}, ctx) == error_envelope("request_failed", "boom")
    assert registry.dispatch("demo.typed", {}, ctx) == {"ok": False, "error": {"code": "conflict", "message": "typed", "details": {"why": 1}}}
    assert _err(registry.dispatch("demo.bad_result", {}, ctx))["code"] == "request_failed"
    assert _err(registry.dispatch(cast(Any, 42), {}, ctx))["code"] == "unknown_request"
    assert _err(registry.dispatch("demo.boom", {}, CommandContext(state=HotpatcherState(), transport="carrier-pigeon")))["code"] == "unsupported_transport"

    with pytest.raises(CommandError) as exc_info:
        unwrap_envelope(registry.dispatch("demo.typed", {}, ctx))
    assert exc_info.value.details == {"why": 1}


def test_dispatch_traces_control_tag_with_timing(state):
    from sd_webui_all_in_one_hotpatcher.control.trace import HotpatchTracer

    lines: list[str] = []
    state.tracer = HotpatchTracer(["control"], writer=lines.append)
    _dispatch(state, "hotpatch.patches.list")
    _dispatch(state, "nope.command")
    state.tracer = None

    text = "".join(lines)
    assert "dispatch hotpatch.patches.list [hotpatch:control]" in text
    assert "elapsed_ms" in text
    assert "unknown_request" in text


# ---------------------------------------------------------------------------
# 传输策略
# ---------------------------------------------------------------------------


def test_forbidden_paths_remote_false_and_requires_token(state):
    controller = get_controller(state)
    calls: list = []
    controller.register_command(_recording_spec("demo.local", calls, remote=False))
    controller.register_command(_recording_spec("demo.token", calls, requires_token=True))

    assert _ok(_dispatch(state, "demo.local", {})) == {"echo": {}}
    for transport in ("legacy", "desktop"):
        assert _err(_dispatch(state, "demo.local", {}, transport=transport, token="tok")) == {"code": "forbidden", "message": "command demo.local is only available in-process"}
    for token in (None, "", "   "):
        assert _err(_dispatch(state, "demo.token", {}, transport="legacy", token=token))["code"] == "forbidden"
    assert _ok(_dispatch(state, "demo.token", {}, transport="legacy", token="tok")) == {"echo": {}}
    assert _ok(_dispatch(state, "demo.token", {}, transport="desktop")) == {"echo": {}}
    assert [transport for transport, _ in calls] == ["inprocess", "legacy", "desktop"]


def test_trace_set_file_is_refused_on_remote_transports(state, tmp_path):
    trace_file = tmp_path / "trace.log"
    for transport in ("legacy", "desktop"):
        error = _err(_dispatch(state, "hotpatch.debug.trace.set", {"tags": ["control"], "file": str(trace_file)}, transport=transport, token="tok"))
        assert error["code"] == "forbidden"
    assert not trace_file.exists()
    assert _ok(_dispatch(state, "hotpatch.debug.trace.get"))["enabled"] is False

    remote = _ok(_dispatch(state, "hotpatch.debug.trace.set", {"tags": "control"}, transport="legacy", token="tok"))
    assert remote["tags"] == ["control"]
    local = _ok(_dispatch(state, "hotpatch.debug.trace.set", {"tags": ["patch"], "file": str(trace_file)}))
    assert local["file"] == str(trace_file)
    assert _err(_dispatch(state, "hotpatch.debug.trace.set", {"tags": ["no-such-tag"]}))["code"] == "invalid_payload"
    assert _err(_dispatch(state, "hotpatch.debug.trace.set", {"tags": 3}))["code"] == "invalid_payload"
    assert _ok(_dispatch(state, "hotpatch.debug.trace.set", {"tags": None, "file": ""}))["enabled"] is False


def test_blocking_commands_are_refused_on_desktop_without_invoking_handler(state, monkeypatch):
    from sd_webui_all_in_one_hotpatcher.control import builtin_commands

    controller = get_controller(state)
    calls: list = []
    controller.register_command(_recording_spec("demo.blocking", calls, blocking=True))
    loader_calls: list = []
    monkeypatch.setattr(builtin_commands, "load_patch", lambda *args, **kwargs: loader_calls.append(args) or {"ok": True})

    error = _err(_dispatch(state, "demo.blocking", {}, transport="desktop"))
    assert error["code"] == "unsupported_transport"
    assert calls == []
    for name, payload in [
        ("hotpatch.sets.load", {"source": "anything"}),
        ("hotpatch.sets.reload", {"key": "x"}),
        ("hotpatch.sets.update", {"key": "x", "config": {}}),
        ("hotpatch.modules.reload", {"module": "json"}),
    ]:
        assert _err(_dispatch(state, name, payload, transport="desktop"))["code"] == "unsupported_transport"
    assert loader_calls == []
    with pytest.raises(DesktopBrokerCommandError) as exc_info:
        bootstrap._handle_desktop_command("demo.blocking", {}, state=state)
    assert exc_info.value.code == "unsupported_transport"
    assert calls == []

    assert _ok(_dispatch(state, "demo.blocking", {}, transport="legacy", token="tok")) == {"echo": {}}
    assert calls == [("legacy", {})]


def test_feature_first_time_resolution_is_refused_on_desktop(state):
    registry = get_feature_registry(state)
    registry.register(FeatureSpec(key="thirdparty.lazy", title="Lazy", description="x", defaults={"enabled": False}, apply="hpcmd_never_imported_module:apply"))

    error = _err(_dispatch(state, "hotpatch.features.enable", {"key": "thirdparty.lazy"}, transport="desktop"))
    assert error["code"] == "unsupported_transport"
    assert "has not been imported" in error["message"]
    assert get_patch_set("feature:thirdparty.lazy", state=state) is None
    # 进程内照常执行 (这里因模块不存在而失败, 报告放在 details 中)。
    failed = _err(_dispatch(state, "hotpatch.features.enable", {"key": "thirdparty.lazy"}))
    assert failed["code"] == "request_failed"
    assert failed["details"]["errors"][0]["code"] == "FeatureReferenceError"


# ---------------------------------------------------------------------------
# services 兼容 (与 P0 test_services_wire_compat 的期望一致)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "request_body",
    [
        {"type": "services.catalog.get", "payload": {}},
        {"type": "services.defaults.get", "payload": {}},
        {"type": "services.config.current", "payload": {}},
        {"type": "services.config.normalize", "payload": {"config": {"extensions": {"uv_pip": {"enabled": True}}}}},
        {"type": "services.unknown", "payload": {}},
        {"type": "services.defaults.get", "payload": []},
        [],
        {"payload": {}},
        {"type": "services.config.load", "payload": {}},
        {"type": "services.config.normalize", "payload": {"config": []}},
    ],
)
def test_services_requests_are_byte_identical_on_every_entry_point(state, request_body):
    inprocess = handle_request_json(request_body, state=state)
    as_text = handle_request_json(json.dumps(request_body), state=state)
    legacy = _legacy(state, request_body)
    via_controller = (
        get_controller(state).call(request_body["type"], request_body["payload"])
        if isinstance(request_body, dict) and isinstance(request_body.get("payload"), dict) and "type" in request_body
        else inprocess
    )

    encoded = json.dumps(inprocess, sort_keys=False)
    assert json.dumps(as_text) == encoded
    assert json.dumps(legacy) == encoded
    assert json.dumps(via_controller) == encoded
    if inprocess["ok"]:
        assert list(inprocess) == ["ok", "payload"]
    else:
        assert list(inprocess["error"]) == ["code", "message"]


def test_services_error_envelopes_match_p0_expectations(state, tmp_path):
    assert handle_request_json({"type": "services.unknown", "payload": {}}, state=state) == {"ok": False, "error": {"code": "unknown_request", "message": "unknown services request: services.unknown"}}
    assert handle_request_json({"type": "services.defaults.get", "payload": []}, state=state) == {"ok": False, "error": {"code": "invalid_request", "message": "payload must be an object"}}
    assert handle_request_json("{not json", state=state)["error"]["code"] == "invalid_json"
    assert handle_request_json([], state=state) == {"ok": False, "error": {"code": "request_failed", "message": "request must be an object"}}  # ty: ignore[invalid-argument-type]
    assert handle_request_json({"payload": {}}, state=state) == {"ok": False, "error": {"code": "request_failed", "message": "request type is required"}}
    assert handle_request_json({"type": "services.config.load", "payload": {}}, state=state) == {"ok": False, "error": {"code": "request_failed", "message": "payload.path must be a non-empty string"}}
    assert handle_request_json({"type": "services.config.normalize", "payload": {"config": []}}, state=state) == {
        "ok": False,
        "error": {"code": "request_failed", "message": "payload.config must be an object"},
    }
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert handle_request_json({"type": "services.config.load", "payload": {"path": str(broken)}}, state=state)["error"]["code"] == "invalid_json"


def test_services_config_apply_is_identical_through_alias_and_legacy(state):
    request = {"type": "services.config.apply", "payload": {"config": _quiet_config(runtime={"errors": {"enabled": True}})}}
    first = handle_request_json(request, state=state)
    _reset(state)
    second = _legacy(state, request)
    _reset(state)
    third = _ok(get_controller(state).dispatch("config.apply", request["payload"], runtime_client=None))

    assert list(first) == ["ok", "payload"]
    assert list(first["payload"]) == ["result"]
    assert first == second
    assert third == first["payload"]
    assert first["payload"]["result"]["warnings"] == [{"feature": "runtime.errors", "message": "runtime_client is required to enable errors"}]


# ---------------------------------------------------------------------------
# 桌面映射
# ---------------------------------------------------------------------------


def test_desktop_config_apply_maps_apply_result_and_errors(state):
    result = bootstrap._handle_desktop_command("config.apply", {"config": _quiet_config(runtime={"errors": {"enabled": True}})}, state=state)
    assert list(result) == ["applyResult"]
    assert list(result["applyResult"]) == ["applied", "warnings", "errors"]

    for payload in ({}, {"config": []}):
        with pytest.raises(DesktopBrokerCommandError) as exc_info:
            bootstrap._handle_desktop_command("config.apply", payload, state=state)
        assert exc_info.value.code == "invalid_command_payload"

    with pytest.raises(DesktopBrokerCommandError) as exc_info:
        bootstrap._handle_desktop_command("hotpatch.nope", {}, state=state)
    assert (exc_info.value.code, str(exc_info.value)) == ("unknown_command", "unsupported desktop broker command: hotpatch.nope")
    assert _err(_legacy(state, {"type": "hotpatch.nope", "payload": {}})) == {"code": "unknown_request", "message": "unknown services request: hotpatch.nope"}

    listed = bootstrap._handle_desktop_command("hotpatch.patches.list", {}, state=state)
    assert set(listed) == {"patches", "count", "truncated"}
    with pytest.raises(DesktopBrokerCommandError) as exc_info:
        bootstrap._handle_desktop_command("hotpatch.patches.get", {"id": "patch_missing"}, state=state)
    assert exc_info.value.code == "not_found"


def test_desktop_result_size_guard(state):
    controller = get_controller(state)
    controller.register_command(CommandSpec(name="demo.huge", handler=lambda ctx, payload: {"blob": "x" * (70 * 1024)}))
    controller.register_command(CommandSpec(name="demo.fits", handler=lambda ctx, payload: {"blob": "x" * (MAX_DESKTOP_RESULT_BYTES - 100)}))

    error = _err(_dispatch(state, "demo.huge", {}, transport="desktop"))
    assert error["code"] == "request_failed"
    assert error["message"].startswith("result_too_large:")
    with pytest.raises(DesktopBrokerCommandError) as exc_info:
        bootstrap._handle_desktop_command("demo.huge", {}, state=state)
    assert exc_info.value.code == "request_failed"
    assert _ok(_dispatch(state, "demo.fits", {}, transport="desktop"))
    # 旧版与进程内传输没有该上限。
    assert len(_ok(_dispatch(state, "demo.huge", {}, transport="legacy", token="tok"))["blob"]) == 70 * 1024
    assert _ok(_dispatch(state, "demo.huge", {}))


# ---------------------------------------------------------------------------
# 能力探测
# ---------------------------------------------------------------------------


def test_capabilities_content_per_transport(state):
    controller = get_controller(state)
    controller.register_command(_recording_spec("demo.local", [], remote=False))
    inprocess = _ok(_dispatch(state, "hotpatch.capabilities"))
    legacy = _ok(_dispatch(state, "hotpatch.capabilities", transport="legacy", token="tok"))
    desktop = _ok(_dispatch(state, "hotpatch.capabilities", transport="desktop"))

    assert inprocess["control_version"] == CONTROL_VERSION == 1
    assert inprocess["protocol_version"] == PROTOCOL_VERSION
    assert (inprocess["transport"], legacy["transport"], desktop["transport"]) == ("inprocess", "legacy", "desktop")
    expected_builtin = {
        "hotpatch.capabilities",
        "hotpatch.status",
        "hotpatch.patches.list",
        "hotpatch.patches.get",
        "hotpatch.patches.unload",
        "hotpatch.sets.list",
        "hotpatch.sets.load",
        "hotpatch.sets.unload",
        "hotpatch.sets.reload",
        "hotpatch.sets.update",
        "hotpatch.features.list",
        "hotpatch.features.enable",
        "hotpatch.features.disable",
        "hotpatch.features.update",
        "hotpatch.modules.reload",
        "hotpatch.inspect.explain",
        "hotpatch.inspect.source",
        "hotpatch.inspect.verify",
        "hotpatch.debug.trace.get",
        "hotpatch.debug.trace.set",
        "hotpatch.debug.strict.set",
        "hotpatch.debug.events.read",
        "hotpatch.connection.get",
        # P8: 连接测试与切换命令
        "hotpatch.connection.test",
        "hotpatch.connection.update",
        "services.catalog.get",
        "services.defaults.get",
        "services.config.current",
        "services.config.normalize",
        "services.config.load",
        "services.config.save",
        "services.config.apply",
    }
    blocking = ["hotpatch.modules.reload", "hotpatch.sets.load", "hotpatch.sets.reload", "hotpatch.sets.update"]
    assert set(inprocess["commands"]) == expected_builtin | {"demo.local"}
    assert set(legacy["commands"]) == expected_builtin
    # P8: services.config.load/save 读写任意路径, 不对桌面传输开放 (transports 白名单)。
    assert set(desktop["commands"]) == expected_builtin - set(blocking) - {"services.config.load", "services.config.save"}
    assert inprocess["blocking_commands"] == blocking
    assert desktop["blocking_commands"] == blocking
    assert inprocess["conditional_blocking_commands"] == ["hotpatch.features.enable", "hotpatch.features.update"]
    # P8: 连接测试与切换命令在旧版通道上要求非空 token。
    assert inprocess["token_required_commands"] == sorted(blocking + ["hotpatch.connection.test", "hotpatch.connection.update"])
    assert "hotpatch.debug.trace.set" in inprocess["mutating_commands"]
    assert "hotpatch.patches.list" not in inprocess["mutating_commands"]
    assert desktop["aliases"] == {"config.apply": "services.config.apply"}
    assert inprocess["features"] == ["connection", "debug", "demo", "features", "inspect", "meta", "modules", "patches", "services", "sets"]
    assert legacy["features"] == ["connection", "debug", "features", "inspect", "meta", "modules", "patches", "services", "sets"]
    assert "remote_load" not in legacy["features"]
    assert "modules" not in desktop["features"]

    set_current_config({"control": {"allow_remote_load": True}}, state=state)
    assert "remote_load" not in _ok(_dispatch(state, "hotpatch.capabilities"))["features"]
    assert "remote_load" in _ok(_dispatch(state, "hotpatch.capabilities", transport="desktop"))["features"]
    assert "remote_load" in _ok(_dispatch(state, "hotpatch.capabilities", transport="legacy", token="tok"))["features"]
    assert "remote_load" not in _ok(_dispatch(state, "hotpatch.capabilities", transport="legacy", token=""))["features"]


# ---------------------------------------------------------------------------
# 各命令组端到端
# ---------------------------------------------------------------------------


def test_meta_and_connection_commands(state):
    status = _ok(_dispatch(state, "hotpatch.status"))
    assert {"version", "transport", "hooks", "sets", "features", "debug", "connection"} <= set(status)

    assert _ok(_dispatch(state, "hotpatch.connection.get")) == {"mode": "legacy", "connected": False, "settings": {"transport": None, "editable": False}, "status": None}
    state.bootstrap_runtime_client = cast(Any, SimpleNamespace(host="127.0.0.1", port=9000, token="secret-token", transport=object(), status=lambda: {"token": "secret-token", "connected": True}))
    connection = _ok(_dispatch(state, "hotpatch.connection.get", transport="legacy", token="tok"))
    assert connection["settings"] == {"transport": "legacy", "editable": False, "host": "127.0.0.1", "port": 9000, "token": "***", "token_set": True}
    assert connection["status"] == {"token": "***", "connected": True}
    assert "secret-token" not in json.dumps(connection)


def test_patch_commands_list_get_and_unload(state):
    controller = get_controller(state)
    flag_module: Any = types.ModuleType("hpcmd_flag")
    flag_module.FLAG = False

    def upper(func, module):
        return lambda name: func(name).upper()

    with controller.patch_set("hpcmd-plan") as ctx:
        with ctx.module("hpcmd_planned") as monkey:
            plan_handle = monkey.patch_function("greet", upper)
        live_handle = ctx.set_attr(flag_module, "FLAG", True)
    patch_set = get_patch_set("hpcmd-plan", state=state)
    assert patch_set is not None

    listing = _ok(_dispatch(state, "hotpatch.patches.list", {"owner": patch_set.id}))
    assert {item["id"] for item in listing["patches"]} == {plan_handle.id, live_handle.id}
    assert listing["count"] == 2 and listing["truncated"] is False
    assert _ok(_dispatch(state, "hotpatch.patches.list", {"limit": 1}))["truncated"] is True
    detail = _ok(_dispatch(state, "hotpatch.patches.get", {"id": plan_handle.id}))["patch"]
    assert (detail["id"], detail["stage"], detail["owner"]) == (plan_handle.id, "function", patch_set.id)
    assert _err(_dispatch(state, "hotpatch.patches.get", {"id": "patch_404"}))["code"] == "not_found"

    assert _err(_dispatch(state, "hotpatch.patches.unload", {"id": live_handle.id}))["code"] == "conflict"
    assert _ok(_dispatch(state, "hotpatch.patches.unload", {"id": plan_handle.id})) == {"id": plan_handle.id, "status": "deregistered"}
    assert _err(_dispatch(state, "hotpatch.patches.unload", {"id": "patch_404"}))["code"] == "not_found"

    assert controller.unload_patch("hpcmd-plan")["status"] == "closed"
    assert flag_module.FLAG is False


def test_set_commands_load_update_reload_unload(state, target, patch_file):
    loaded = _ok(_dispatch(state, "hotpatch.sets.load", {"source": str(patch_file), "name": "hpcmd-fix", "config": {"value": "one"}}))
    assert loaded["status"] == "loaded"
    assert target.VALUE == "one"
    listing = _ok(_dispatch(state, "hotpatch.sets.list"))
    item = next(entry for entry in listing["sets"] if entry["name"] == "hpcmd-fix")
    assert item["kind"] == "loaded"
    assert item["loaded"]["origin"] == "api"

    duplicate = _err(_dispatch(state, "hotpatch.sets.load", {"source": str(patch_file), "name": "hpcmd-fix"}))
    assert duplicate["code"] == "conflict"
    assert duplicate["details"]["status"] == "failed"
    assert _err(_dispatch(state, "hotpatch.sets.load", {"source": str(patch_file.with_name("missing.py"))}))["code"] in {"not_found", "invalid_payload"}

    updated = _ok(_dispatch(state, "hotpatch.sets.update", {"key": "hpcmd-fix", "config": {"value": "two"}}))
    assert updated["status"] == "reloaded"
    assert target.VALUE == "two"
    reloaded = _ok(_dispatch(state, "hotpatch.sets.reload", {"key": "hpcmd-fix"}))
    assert reloaded["status"] == "reloaded"

    patch_file.write_text("def setup(ctx):\n    raise RuntimeError('broken v2')\n", encoding="utf-8")
    rolled_back = _err(_dispatch(state, "hotpatch.sets.reload", {"key": "hpcmd-fix"}))
    assert rolled_back["code"] == "request_failed"
    assert rolled_back["message"].startswith("reload failed and was rolled back")
    assert rolled_back["details"]["status"] == "rolled_back"
    assert target.VALUE == "two"

    unloaded = _ok(_dispatch(state, "hotpatch.sets.unload", {"key": "hpcmd-fix"}))
    assert unloaded["status"] == "reverted"
    assert target.VALUE == "original"
    for name, payload in [
        ("hotpatch.sets.unload", {"key": "hpcmd-fix"}),
        ("hotpatch.sets.reload", {"key": "hpcmd-fix"}),
        ("hotpatch.sets.update", {"key": "hpcmd-fix", "config": {}}),
    ]:
        assert _err(_dispatch(state, name, payload))["code"] == "not_found"


def test_feature_commands_and_feature_set_conflict(state):
    module: Any = types.ModuleType("hpcmd_feature_target")
    module.VALUE = 0
    sys.modules["hpcmd_feature_target"] = module

    def apply(ctx, section):
        ctx.patch_set.context.set_attr(module, "VALUE", section["value"])

    get_feature_registry(state).register(FeatureSpec(key="thirdparty.cmd", title="Cmd", description="x", defaults={"enabled": False, "value": 1}, apply=apply))

    listing = _ok(_dispatch(state, "hotpatch.features.list"))
    assert "thirdparty.cmd" in [item["key"] for item in listing["features"]]
    enabled = _ok(_dispatch(state, "hotpatch.features.enable", {"key": "thirdparty.cmd", "config": {"value": 5}}, transport="desktop"))
    assert enabled["status"] == "applied"
    assert module.VALUE == 5
    assert _err(_dispatch(state, "hotpatch.sets.unload", {"key": "feature:thirdparty.cmd"}))["code"] == "conflict"
    updated = _ok(_dispatch(state, "hotpatch.features.update", {"key": "thirdparty.cmd", "config": {"value": 7}}))
    assert updated["mode"] == "restart"
    assert module.VALUE == 7
    disabled = _ok(_dispatch(state, "hotpatch.features.disable", {"key": "thirdparty.cmd"}, transport="legacy", token=""))
    assert disabled["status"] == "reverted"
    assert module.VALUE == 0

    missing = _err(_dispatch(state, "hotpatch.features.enable", {"key": "thirdparty.missing"}))
    assert missing["code"] == "not_found"
    assert missing["details"]["errors"][0]["code"] == "unknown_feature"
    assert _err(_dispatch(state, "hotpatch.features.enable", {"key": "services"}))["code"] == "conflict"


def test_module_reload_command(state, tmp_path):
    (tmp_path / "hpcmd_reloadable.py").write_text("COUNTER = []\nCOUNTER.append(1)\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    importlib.import_module("hpcmd_reloadable")

    assert _err(_dispatch(state, "hotpatch.modules.reload", {"module": "hpcmd_reloadable"}, transport="legacy", token=""))["code"] == "forbidden"
    assert _err(_dispatch(state, "hotpatch.modules.reload", {"module": "hpcmd_not_imported"}))["code"] == "not_found"
    result = _ok(_dispatch(state, "hotpatch.modules.reload", {"module": "hpcmd_reloadable"}, transport="legacy", token="tok"))
    assert result["status"] == "requires_restart"
    assert result["handle"]["kind"] == "reload"
    assert sys.modules["hpcmd_reloadable"].COUNTER == [1]


def test_inspect_and_debug_commands(state):
    explained = _ok(_dispatch(state, "hotpatch.inspect.explain", {"module": "hpcmd_unknown_module"}))
    assert explained["module"] == "hpcmd_unknown_module"
    assert explained["registered"] is False
    source = _ok(_dispatch(state, "hotpatch.inspect.source", {"module": "colorsys", "max_bytes": 1024}))
    assert source["truncated"] is True
    assert source["bytes"] <= 1024
    verified = _ok(_dispatch(state, "hotpatch.inspect.verify"))
    assert verified["ok"] is True

    assert _ok(_dispatch(state, "hotpatch.debug.strict.set", {"enabled": True})) == {"strict": True, "previous": False}
    assert state.strict_mode is True
    assert _ok(_dispatch(state, "hotpatch.debug.strict.set", {"enabled": False}, transport="desktop")) == {"strict": False, "previous": True}
    events = _ok(_dispatch(state, "hotpatch.debug.events.read", {"since_cursor": 0, "limit": 10}))
    assert [event["type"] for event in events["events"]] == ["debug.strict.changed", "debug.strict.changed"]
    assert events["next_cursor"] == 2


# ---------------------------------------------------------------------------
# 远程加载门禁 (D6): 配置携带的补丁集
# ---------------------------------------------------------------------------


def _control_config(**control):
    return _quiet_config(control=control)


def _entry(patch_file, **extra):
    return {"source": str(patch_file), "name": "hpcmd-config", **extra}


def test_config_borne_gate_closed_rejects_whole_request(state, target, patch_file):
    for config in (
        _control_config(patch_sets=[_entry(patch_file)]),
        _control_config(allow_remote_load=True),
        _control_config(allow_remote_load=True, patch_sets=[_entry(patch_file)]),
    ):
        response = _legacy(state, {"type": "services.config.apply", "payload": {"config": config}})
        assert _err(response)["code"] == "remote_load_disabled"
        assert list(response["error"]) == ["code", "message"]
        assert state.current_config is None
        with pytest.raises(DesktopBrokerCommandError) as exc_info:
            bootstrap._handle_desktop_command("config.apply", {"config": config}, state=state)
        assert exc_info.value.code == "remote_load_disabled"
        assert state.current_config is None
    assert get_loaded_patch("hpcmd-config", state=state) is None
    assert target.VALUE == "original"


def test_config_borne_gate_allows_harmless_configs(state, target, patch_file):
    # GUI 回传的完整默认配置: 空列表与未改变的 false 不触发门禁。
    full = get_current_config(state=state)
    assert full["control"]["patch_sets"] == [] and full["control"]["allow_remote_load"] is False
    full.update(_quiet_config())
    assert _ok(_legacy(state, {"type": "services.config.apply", "payload": {"config": full}}))["result"]["errors"] == []
    disabled_entry = _control_config(patch_sets=[_entry(patch_file, enabled=False)], allow_remote_load=False)
    assert _ok(_legacy(state, {"type": "services.config.apply", "payload": {"config": disabled_entry}}))
    assert get_loaded_patch("hpcmd-config", state=state) is None

    # 本地 (进程内) 应用不受影响, 之后远程回传相同条目也不会被拒绝。
    local = apply_config(_control_config(patch_sets=[_entry(patch_file, config={"value": "local"})]), state=state)
    assert local["errors"] == []
    assert target.VALUE == "local"
    echoed = _legacy(state, {"type": "services.config.apply", "payload": {"config": _control_config(patch_sets=[_entry(patch_file, config={"value": "local"})])}})
    assert _ok(echoed)["result"]["errors"] == []
    changed = _legacy(state, {"type": "services.config.apply", "payload": {"config": _control_config(patch_sets=[_entry(patch_file, config={"value": "remote"})])}})
    assert _err(changed)["code"] == "remote_load_disabled"
    assert target.VALUE == "local"


def test_config_borne_gate_open_requires_token_on_legacy_only(state, target, patch_file):
    apply_config(_control_config(allow_remote_load=True), state=state)
    config = _control_config(allow_remote_load=True, patch_sets=[_entry(patch_file, config={"value": "remote"})])

    assert _err(_legacy(state, {"type": "services.config.apply", "payload": {"config": config}}, token=""))["code"] == "forbidden"
    assert target.VALUE == "original"
    applied = _ok(_legacy(state, {"type": "services.config.apply", "payload": {"config": config}}, token="tok"))
    assert applied["result"]["errors"] == []
    assert target.VALUE == "remote"

    config["control"]["patch_sets"][0]["config"] = {"value": "desktop"}
    result = bootstrap._handle_desktop_command("config.apply", {"config": config}, state=state)
    assert result["applyResult"]["errors"] == []
    assert target.VALUE == "desktop"


def test_config_borne_gate_covers_control_feature_and_config_save(state, target, patch_file, tmp_path):
    for name, payload in [
        ("hotpatch.features.enable", {"key": "control", "config": {"patch_sets": [_entry(patch_file)]}}),
        ("hotpatch.features.update", {"key": "control", "config": {"allow_remote_load": True}}),
    ]:
        assert _err(_dispatch(state, name, payload, transport="legacy", token="tok"))["code"] == "remote_load_disabled"
    saved = tmp_path / "saved.json"
    save = _legacy(state, {"type": "services.config.save", "payload": {"path": str(saved), "config": _control_config(patch_sets=[_entry(patch_file)])}})
    assert _err(save)["code"] == "remote_load_disabled"
    assert not saved.exists()
    assert get_loaded_patch("hpcmd-config", state=state) is None

    ctx = CommandContext(state=state, transport="inprocess")
    check_config_borne_load(ctx, {"allow_remote_load": True, "patch_sets": [_entry(patch_file)]})
    remote = CommandContext(state=state, transport="legacy", token="tok")
    check_config_borne_load(remote, None)
    check_config_borne_load(remote, {"patch_sets": "not-a-list"})


# ---------------------------------------------------------------------------
# 旧版通道: 端到端与响应后回调
# ---------------------------------------------------------------------------


class _ServicesJsonlHost(JsonlHost):
    def __init__(self, requests):
        super().__init__()
        self.requests = requests
        self.responses = []
        self.done = threading.Event()

    def _handle(self, conn):
        with conn:
            file = conn.makefile("rb")
            for line in file:
                message = json.loads(line.decode("utf-8"))
                self.messages.append(message)
                if message.get("type") == "channel.open":
                    for request in self.requests:
                        conn.sendall(encode_message(request))
                        self.responses.append(json.loads(file.readline().decode("utf-8")))
                    self.done.set()
                    file.readline()
                    return
                if message.get("id") is not None:
                    conn.sendall(encode_message({"id": message["id"], "ok": True, "payload": {}}))


def test_legacy_services_channel_end_to_end(state):
    requests = [
        {"id": "cap", "type": "hotpatch.capabilities", "payload": {}},
        {"id": "list", "type": "hotpatch.patches.list", "payload": {}},
        {"id": "load", "type": "hotpatch.sets.load", "payload": {"source": "json"}},
    ]
    with _ServicesJsonlHost(requests) as host:
        with RuntimeClient.connect(host.host, host.port, token="svc-token") as client:
            channel = install_service_control_channel(client, state=state)
            assert host.done.wait(5)
            channel.close()

    # hello 与 channel.open 由宿主两个线程分别记录, 顺序不确定。
    hellos = [message for message in host.messages if message.get("type") == "hello"]
    assert len(hellos) == 1
    assert "control" in hellos[0]["features"]
    assert any(message.get("type") == "channel.open" and message.get("token") == "svc-token" for message in host.messages)
    capabilities, listing, load = host.responses
    assert capabilities["id"] == "cap"
    assert capabilities["payload"]["transport"] == "legacy"
    assert capabilities["payload"]["control_version"] == CONTROL_VERSION
    assert "hotpatch.patches.list" in capabilities["payload"]["commands"]
    assert listing == {"ok": True, "payload": {"patches": [], "count": 0, "truncated": False}, "id": "list"}
    assert load["error"]["code"] == "remote_load_disabled"


def test_after_send_callbacks_run_after_response_and_failures_are_isolated(monkeypatch, state):
    lines = [
        {"id": "a1", "type": "demo.after", "payload": {}},
        {"id": "a2", "type": "demo.after_failed", "payload": {}},
        {"id": "a3", "type": "hotpatch.patches.list", "payload": {}},
    ]
    sock = FakeSocket(ScriptedReader([encode_message(line) for line in lines]))
    observed: list = []

    def record(label, ctx):
        observed.append((label, len(sock.send_attempts), ctx.transport, ctx.token))

    def raise_error():
        raise RuntimeError("callback boom")

    def handler(ctx, payload):
        ctx.after_send.append(lambda: record("first", ctx))
        ctx.after_send.append(raise_error)
        ctx.after_send.append(lambda: record("third", ctx))
        return {"scheduled": 3}

    def failing(ctx, payload):
        ctx.after_send.append(lambda: record("never", ctx))
        raise CommandError("conflict", "nope")

    controller = get_controller(state)
    controller.register_command(CommandSpec(name="demo.after", handler=handler))
    controller.register_command(CommandSpec(name="demo.after_failed", handler=failing))
    monkeypatch.setattr(socket, "create_connection", lambda address, *, timeout: sock)
    client = cast(RuntimeClient, SimpleNamespace(host="127.0.0.1", port=8123, token="tok"))
    channel = ServiceControlChannel(client, PatchService(state=state)).start()
    channel.thread.join(5)
    assert not channel.thread.is_alive()

    # 发送序列: channel.open, a1 响应 (回调在其后运行), a2 响应, a3 响应。
    assert observed == [("first", 2, "legacy", "tok"), ("third", 2, "legacy", "tok")]
    responses = [json.loads(data) for data in sock.send_attempts[1:]]
    assert [response["id"] for response in responses] == ["a1", "a2", "a3"]
    assert responses[0]["payload"] == {"scheduled": 3}
    assert responses[1]["error"]["code"] == "conflict"
    assert responses[2]["ok"] is True
    assert {"stage": "after_send", "message": "RuntimeError: callback boom"} in channel.diagnostics


def test_inprocess_call_runs_after_send_immediately_and_isolates_failures(state):
    observed: list = []

    def handler(ctx, payload):
        ctx.after_send.append(lambda: observed.append("ran"))
        ctx.after_send.append(lambda: 1 / 0)
        return {}

    controller = get_controller(state)
    controller.register_command(CommandSpec(name="demo.after", handler=handler))
    assert controller.call("demo.after") == {"ok": True, "payload": {}}
    assert observed == ["ran"]
    callbacks: list = [lambda: observed.append("again"), lambda: 1 / 0]
    errors: list = []
    run_after_send(callbacks, on_error=errors.append)
    assert callbacks == []
    assert observed == ["ran", "again"]
    assert [type(error).__name__ for error in errors] == ["ZeroDivisionError"]
    assert handle_request_json({"type": "demo.after", "payload": {}}, state=state) == {"ok": True, "payload": {}}
    assert observed == ["ran", "again", "ran"]


# ---------------------------------------------------------------------------
# Python 门面
# ---------------------------------------------------------------------------


def test_controller_is_per_state_and_facade_methods_unwrap(state, target, patch_file):
    controller = get_controller(state)
    assert get_controller(state) is controller
    assert state.controller is controller
    assert isinstance(controller, HotpatchController)
    assert get_controller(HotpatcherState()) is not controller

    assert controller.capabilities()["transport"] == "inprocess"
    assert controller.load_patch(str(patch_file), name="hpcmd-facade", config={"value": "facade"})["status"] == "loaded"
    assert target.VALUE == "facade"
    assert controller.update_patch("hpcmd-facade", {"value": "updated"})["status"] == "reloaded"
    assert controller.reload_patch("hpcmd-facade")["status"] == "reloaded"
    assert [item["name"] for item in controller.list_sets()["sets"]] == ["hpcmd-facade"]
    assert controller.unload_patch("hpcmd-facade")["status"] == "reverted"
    with pytest.raises(CommandError) as exc_info:
        controller.unload_patch("hpcmd-facade")
    assert exc_info.value.code == "not_found"

    assert controller.debug.trace(["control"])["tags"] == ["control"]
    assert controller.debug.get_trace()["enabled"] is True
    assert controller.debug.trace(None)["enabled"] is False
    assert controller.debug.strict(True)["strict"] is True
    assert controller.debug.strict(False)["previous"] is True
    assert controller.debug.events(limit=1)["has_more"] is True
    assert controller.inspect.explain("hpcmd_target")["loaded"] is True
    assert controller.inspect.verify()["ok"] is True
    assert controller.inspect.source("colorsys", max_bytes=200)["truncated"] is True
    assert "hooks" in controller.inspect.status()
    assert controller.connection.get()["connected"] is False
    assert controller.patches.list()["count"] == 0
    assert any(item["key"] == "control" for item in controller.features.list())
    assert "hotpatch.capabilities" in controller.commands()


def test_patch_set_context_manager_registers_and_rolls_back(state):
    controller = get_controller(state)
    module: Any = types.ModuleType("hpcmd_ps_target")
    module.FLAG = "original"
    sys.modules["hpcmd_ps_target"] = module

    with controller.patch_set("hpcmd-ps") as ctx:
        ctx.set_attr("hpcmd_ps_target:FLAG", "patched")
    assert module.FLAG == "patched"
    with pytest.raises(ValueError, match="already registered"):
        with controller.patch_set("hpcmd-ps"):
            pass
    assert controller.unload_patch("hpcmd-ps")["handles"][0]["status"] == "reverted"
    assert module.FLAG == "original"

    with pytest.raises(RuntimeError, match="boom"):
        with controller.patch_set("hpcmd-ps") as ctx:
            ctx.set_attr(module, "FLAG", "partial")
            raise RuntimeError("boom")
    assert module.FLAG == "original"
    assert get_patch_set("hpcmd-ps", state=state) is None


def test_hotpatch_facade_is_lazy_in_a_fresh_interpreter():
    script = textwrap.dedent(
        """
        import json
        import sys

        sys.path.insert(0, sys.argv[1])
        import sd_webui_all_in_one_hotpatcher as package

        def control_modules():
            return sorted(name for name in sys.modules if name.startswith("sd_webui_all_in_one_hotpatcher.control"))

        before = control_modules()
        package.install_import_hook()
        after_hook = control_modules()
        from sd_webui_all_in_one_hotpatcher import hotpatch

        after_access = control_modules()
        same = hotpatch is package.hotpatch is package.get_default_state().controller
        print(json.dumps([before, after_hook, after_access, type(hotpatch).__name__, same, "hotpatch" in package.__all__]))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script, str(PATCHER_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    before, after_hook, after_access, type_name, same, exported = json.loads(completed.stdout.strip().splitlines()[-1])
    assert before == []
    assert after_hook == []
    assert "sd_webui_all_in_one_hotpatcher.control.controller" in after_access
    assert type_name == "HotpatchController"
    assert same is True
    assert exported is True


def test_package_getattr_rejects_unknown_names():
    import sd_webui_all_in_one_hotpatcher as package

    with pytest.raises(AttributeError, match="no attribute 'definitely_missing'"):
        package.definitely_missing  # noqa: B018
