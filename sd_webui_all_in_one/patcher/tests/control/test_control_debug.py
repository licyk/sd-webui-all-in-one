"""调试工具测试: 跟踪输出、事件环形缓冲区与转发、explain / 补丁后源码 / 预演校验 / 状态快照。"""

import ast
import importlib
import json
import os
import py_compile
import sys
import textwrap
import threading
import types
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher import install_import_hook, install_stack_shadower, set_strict_mode, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.control import load_patch, reload_patch, unload_patch
from sd_webui_all_in_one_hotpatcher.control.events import (
    MAX_EVENT_BYTES,
    MAX_FORWARD_PAYLOAD_BYTES,
    PatchEventLog,
    get_event_log,
    read_events,
    record_event,
    set_event_forwarding,
)
from sd_webui_all_in_one_hotpatcher.control.features import FeatureSpec, disable_feature, enable_feature, get_feature_registry
from sd_webui_all_in_one_hotpatcher.control.handles import PatchStatus
from sd_webui_all_in_one_hotpatcher.control.inspect import MAX_SOURCE_BYTES, explain, render_patched_source, status_snapshot, verify_source_patches
from sd_webui_all_in_one_hotpatcher.control.loader import DYNAMIC_PACKAGE, stop_patch_watcher
from sd_webui_all_in_one_hotpatcher.control.patchset import PatchSet, register_patch_set
from sd_webui_all_in_one_hotpatcher.control.trace import (
    REDACTED,
    TRACE_ENV,
    TRACE_FILE_ENV,
    TRACE_TAGS,
    HotpatchTracer,
    configure_tracer_from_env,
    get_trace,
    get_tracer,
    parse_trace_tags,
    redact_mapping,
    redact_url,
    set_trace,
)
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

MODULE_PREFIX = "hpd_"
DESKTOP_RESULT_LIMIT = 64 * 1024


def encoded_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8"))


def write_module(directory, name, source):
    path = directory / f"{name}.py"
    path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
    importlib.invalidate_caches()
    return path


def event_types(state, prefix=""):
    return [event["type"] for event in read_events(0, 1000, state=state)["events"] if event["type"].startswith(prefix)]


class Exploding:
    """转为字符串时抛出异常, 用于证明关闭的跟踪路径从不格式化值。"""

    def __str__(self) -> str:
        raise AssertionError("value was formatted")

    __repr__ = __str__

    def __format__(self, spec: str) -> str:
        raise AssertionError("value was formatted")


class FakeRuntimeClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[tuple[str, Any]] = []
        self.fail = fail

    def emit_event(self, event_type, payload=None):
        if self.fail:
            raise RuntimeError("transport down")
        self.events.append((event_type, payload))
        return True


class FakeLegacyTransport:
    host = "127.0.0.1"
    port = 4567
    token = "legacy-s3cret-token"
    closed = False


class FakeLegacyClient:
    def __init__(self) -> None:
        self.transport = FakeLegacyTransport()

    @property
    def host(self):
        return self.transport.host

    @property
    def port(self):
        return self.transport.port

    @property
    def token(self):
        return self.transport.token

    def status(self):
        return {"transport": "legacy", "status": "connected", "host": self.host, "port": self.port, "token": self.token}


@pytest.fixture
def state(monkeypatch):
    monkeypatch.delenv(TRACE_ENV, raising=False)
    monkeypatch.delenv(TRACE_FILE_ENV, raising=False)
    isolated = HotpatcherState()
    before_path = list(sys.path)
    before_meta_path = list(sys.meta_path)
    yield isolated
    stop_patch_watcher(state=isolated)
    for name in list(isolated.loaded_patches):
        unload_patch(name, state=isolated)
    uninstall_import_hook(state=isolated)
    uninstall_stack_shadower(state=isolated)
    if isolated.tracer is not None:
        isolated.tracer.close()
    sys.path[:] = before_path
    sys.meta_path[:] = before_meta_path
    for name in list(sys.modules):
        if name.startswith(MODULE_PREFIX) or name.startswith(f"{DYNAMIC_PACKAGE}."):
            del sys.modules[name]
    importlib.invalidate_caches()


@pytest.fixture
def module_dir(tmp_path):
    root = tmp_path / "modules"
    root.mkdir()
    sys.path.insert(0, str(root))
    importlib.invalidate_caches()
    return root


# ---------------------------------------------------------------------------
# 跟踪输出
# ---------------------------------------------------------------------------


def test_tracer_is_off_by_default_and_writer_is_never_called(state, module_dir, capsys):
    calls = []
    tracer = HotpatchTracer(writer=calls.append)
    assert tracer.active is False
    tracer.trace("patch", "never", {"value": 1})
    with tracer.section("patch", "never"):
        pass
    assert calls == []
    assert HotpatchTracer.from_env().active is False
    assert state.tracer is None

    install_import_hook(state=state)
    assert state.tracer is None
    write_module(module_dir, "hpd_quiet", "VALUE = 1\n")
    with state.monkey_zoo("hpd_quiet") as monkey:
        monkey.patch_sources(lambda source, filename: source.replace("1", "2"))
    module = importlib.import_module("hpd_quiet")
    assert module.VALUE == 2
    assert state.tracer is None
    assert "[hotpatch:" not in capsys.readouterr().err


def test_disabled_tracing_never_formats_values_or_builds_lazy_payloads(state):
    tracer = HotpatchTracer(writer=lambda text: pytest.fail("writer called"))
    tracer.trace("patch", "message", {"value": Exploding()})
    with tracer.section("set", "message", {"value": Exploding()}):
        pass

    built = []

    def builder():
        built.append(True)
        return {"value": 1}

    record_event("patch.applied", {"value": Exploding()}, state=state)
    record_event("patch.applied", (builder,), state=state)
    assert built == []
    state.tracer = HotpatchTracer(writer=lambda text: pytest.fail("writer called"))
    record_event("patch.applied", (builder,), state=state)
    assert built == []

    events = read_events(state=state)["events"]
    assert events[1]["payload"] == {"value": 1}
    assert events[2]["payload"] == {"value": 1}
    assert built == [True, True]
    assert events[0]["payload"] == {"value": "<Exploding>"}


def test_tag_filtering_hierarchy_and_pluggy_style_format():
    lines: list[str] = []
    tracer = HotpatchTracer("patch,set.watch_reload", writer=lines.append)

    assert tracer.enabled_for("patch")
    assert tracer.enabled_for("patch.failed")
    assert not tracer.enabled_for("import")
    assert tracer.enabled_for("set.watch_reload")
    assert not tracer.enabled_for("set")

    tracer.trace("import", "skipped")
    tracer.trace("patch", "applied", {"module": "demo", "token": "abc"})
    with tracer.section("patch.apply", "outer"):
        tracer.trace("patch", "inner")
    text = "".join(lines)

    assert "skipped" not in text
    assert text.startswith("applied [hotpatch:patch]\n    module: demo\n    token: ***\n")
    assert "outer [hotpatch:patch.apply]\n" in text
    assert "  inner [hotpatch:patch]\n" in text
    assert "outer done [hotpatch:patch.apply]\n" in text
    assert "abc" not in text


def test_all_value_unknown_tags_and_set_get_trace():
    assert parse_trace_tags("all") == frozenset(TRACE_TAGS)
    assert parse_trace_tags(["import", " Patch "]) == frozenset({"import", "patch"})
    assert parse_trace_tags("import,bogus") == frozenset({"import"})
    with pytest.raises(ValueError, match="bogus"):
        parse_trace_tags("bogus", strict=True)

    isolated = HotpatcherState()
    result = set_trace("all", state=isolated)
    assert result["enabled"] is True
    assert result["tags"] == sorted(TRACE_TAGS)
    assert get_trace(state=isolated) == result
    with pytest.raises(ValueError):
        set_trace(["nope"], state=isolated)
    assert set_trace(None, state=isolated)["enabled"] is False
    assert isolated.tracer is not None and isolated.tracer.active is False
    assert event_types(isolated, "debug.trace") == ["debug.trace.changed", "debug.trace.changed"]


def test_file_writer_receives_traced_events(tmp_path, state):
    path = tmp_path / "trace.log"
    set_trace("set", file=str(path), state=state)
    record_event("set.loaded", {"name": "demo", "session_token": "secret-value"}, state=state)
    record_event("patch.applied", {"handle_id": "patch_1"}, state=state)
    assert state.tracer is not None
    state.tracer.close()

    text = path.read_text(encoding="utf-8")
    assert "set.loaded [hotpatch:set]\n" in text
    assert "    name: demo\n" in text
    assert "patch.applied" not in text
    assert "secret-value" not in text

    set_trace("set", file="", state=state)
    assert get_trace(state=state)["file"] is None


def test_tracer_initialised_from_environment(tmp_path, monkeypatch, capsys):
    path = tmp_path / "env-trace.log"
    monkeypatch.setenv(TRACE_ENV, "import,bogus")
    monkeypatch.setenv(TRACE_FILE_ENV, str(path))

    lazy = HotpatcherState()
    tracer = get_tracer(state=lazy)
    assert tracer.tags == ["import"]
    assert tracer.file == str(path)
    assert get_tracer(state=lazy) is tracer

    hooked = HotpatcherState()
    try:
        install_import_hook(state=hooked)
        assert hooked.tracer is not None and hooked.tracer.tags == ["import"]
    finally:
        uninstall_import_hook(state=hooked)

    monkeypatch.setenv(TRACE_ENV, "set")
    assert configure_tracer_from_env(state=lazy) is tracer
    assert tracer.tags == ["set"]
    tracer.close()


def test_bootstrap_initialises_tracer_from_environment(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.bootstrap import _BOOTSTRAPPED_ENV, configure_from_env

    monkeypatch.setenv(_BOOTSTRAPPED_ENV, "0")
    monkeypatch.delenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", raising=False)
    monkeypatch.delenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK", raising=False)
    monkeypatch.delenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW", raising=False)
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON", '{"services":{"apply_on_bootstrap":false}}')
    monkeypatch.setenv(TRACE_ENV, "conn,control")
    isolated = HotpatcherState()

    configure_from_env(state=isolated)

    assert isolated.tracer is not None
    assert isolated.tracer.tags == ["conn", "control"]


def test_redaction_helpers_hide_tokens_and_url_credentials():
    data = {
        "token": "abc",
        "empty_token": "",
        "nested": {"session_token": "x", "API_KEY": "y", "items": [{"password": "p"}]},
        "broker_url": "http://user:pw@127.0.0.1:9000/path?token=t#frag",
        "host": "127.0.0.1",
    }
    redacted = redact_mapping(data)
    assert redacted["token"] == REDACTED
    assert redacted["empty_token"] == ""
    assert redacted["nested"]["session_token"] == REDACTED
    assert redacted["nested"]["API_KEY"] == REDACTED
    assert redacted["nested"]["items"][0]["password"] == REDACTED
    assert redacted["broker_url"] == "http://***@127.0.0.1:9000/path?***#***"
    assert redacted["host"] == "127.0.0.1"
    assert data["token"] == "abc"
    assert redact_url("http://127.0.0.1/x") == "http://127.0.0.1/x"


# ---------------------------------------------------------------------------
# 事件环形缓冲区
# ---------------------------------------------------------------------------


def test_event_log_ring_cap_cursors_and_truncation():
    log = PatchEventLog(capacity=5)
    empty = log.read(0)
    assert empty == {"events": [], "start_cursor": 0, "next_cursor": 0, "truncated": False, "has_more": False}

    for index in range(8):
        assert log.record("set.loaded", {"index": index}) == index

    first = log.read(0)
    assert first["truncated"] is True
    assert first["start_cursor"] == 3
    assert [event["cursor"] for event in first["events"]] == [3, 4, 5, 6, 7]
    assert first["events"][0]["payload"] == {"index": 3}
    assert first["events"][0]["type"] == "set.loaded"
    assert isinstance(first["events"][0]["timestamp"], float)
    assert first["next_cursor"] == 8

    page = log.read(5, limit=2)
    assert page["truncated"] is False
    assert [event["cursor"] for event in page["events"]] == [5, 6]
    assert page["next_cursor"] == 7
    assert page["has_more"] is True

    tail = log.read(8)
    assert tail["events"] == [] and tail["next_cursor"] == 8 and tail["truncated"] is False
    assert log.read(-10, limit=0)["events"][0]["cursor"] == 3

    stats = log.stats()
    assert stats["capacity"] == 5 and stats["count"] == 5 and stats["dropped"] == 3 and stats["next_cursor"] == 8
    log.clear()
    assert log.read(7)["truncated"] is True
    with pytest.raises(ValueError):
        PatchEventLog(capacity=0)


def test_event_log_read_respects_byte_budget_and_bounds_payloads():
    log = PatchEventLog()
    for _ in range(50):
        log.record("patch.failed", {"error_message": "x" * 900, "items": list(range(100)), "obj": object(), "nan": float("nan")})
    log.record("set.loaded", {"blob": ["中" * 900] * 32})

    page = log.read(0, limit=1000, max_bytes=4096)
    assert 1 <= len(page["events"]) < 50
    assert page["next_cursor"] == page["events"][-1]["cursor"] + 1
    assert page["has_more"] is True
    event = page["events"][0]
    assert len(event["payload"]["items"]) == 33
    assert event["payload"]["nan"] == "nan"
    assert event["payload"]["obj"].startswith("<object")

    big = log.read(50)["events"][0]
    assert encoded_size(big) <= MAX_EVENT_BYTES + 200
    assert big["payload"]["truncated"] is True

    full = log.read(0, limit=1000)
    assert encoded_size(full) < DESKTOP_RESULT_LIMIT


def test_event_log_thread_safety_smoke():
    log = PatchEventLog(capacity=1000)
    errors: list[BaseException] = []

    def writer(worker: int) -> None:
        try:
            for index in range(500):
                log.record("patch.applied", {"worker": worker, "index": index})
        except BaseException as exc:
            errors.append(exc)

    def reader() -> None:
        try:
            cursor = 0
            for _ in range(200):
                page = log.read(cursor, limit=50)
                cursors = [event["cursor"] for event in page["events"]]
                assert cursors == sorted(cursors) and len(set(cursors)) == len(cursors)
                cursor = page["next_cursor"]
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(worker,)) for worker in range(8)] + [threading.Thread(target=reader) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)

    assert errors == []
    stats = log.stats()
    assert stats["next_cursor"] == 4000
    assert stats["count"] == 1000
    cursors = [event["cursor"] for event in log.read(0, limit=1000, max_bytes=10**7)["events"]]
    assert cursors == list(range(3000, 4000))


# ---------------------------------------------------------------------------
# 事件来源
# ---------------------------------------------------------------------------


def test_events_for_patch_apply_fail_and_revert(state, module_dir):
    install_import_hook(state=state)
    write_module(
        module_dir,
        "hpd_events",
        """
        VALUE = "original"

        def greet():
            return "hello"
        """,
    )

    def broken(original, module):
        raise RuntimeError("hooker broke")

    with state.monkey_zoo("hpd_events") as monkey:
        source_handle = monkey.patch_sources(lambda source, filename: source.replace('"original"', '"patched"'))
        noop_handle = monkey.patch_sources(lambda source, filename: source)
        function_handle = monkey.patch_function("greet", lambda original, module: lambda: "hi")
        broken_handle = monkey.patch_function("greet", broken)

    module = importlib.import_module("hpd_events")
    assert module.VALUE == "patched"
    assert module.greet() == "hi"
    assert monkey.remove(function_handle) is PatchStatus.REVERTED
    assert module.greet() == "hello"

    events = read_events(0, 1000, state=state)["events"]
    by_type: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_type.setdefault(event["type"], []).append(event["payload"])
    assert [payload["handle_id"] for payload in by_type["patch.registered"]] == [source_handle.id, noop_handle.id, function_handle.id, broken_handle.id]
    assert by_type["import.intercepted"][0]["module"] == "hpd_events"
    assert by_type["import.intercepted"][0]["wrapper"] == "MonkeySourceFileLoader"
    assert {payload["handle_id"] for payload in by_type["patch.applied"]} == {source_handle.id, function_handle.id}
    assert [payload["handle_id"] for payload in by_type["patch.noop"]] == [noop_handle.id]
    failed = by_type["patch.failed"][0]
    assert failed["handle_id"] == broken_handle.id
    assert failed["error_type"] == "RuntimeError" and failed["error_message"] == "hooker broke"
    assert "traceback" not in failed
    assert by_type["patch.reverted"] == [{"handle_id": function_handle.id, "module": "hpd_events", "stage": "function", "target": function_handle.target, "owner": None, "status": "reverted"}]


def test_import_skipped_event_for_missing_module(state, module_dir):
    install_import_hook(state=state)
    with state.monkey_zoo("hpd_missing_module") as monkey:
        monkey.patch_module(lambda module: None)
    with pytest.raises(ImportError):
        importlib.import_module("hpd_missing_module")
    skipped = [event["payload"] for event in read_events(state=state)["events"] if event["type"] == "import.skipped"]
    assert skipped and skipped[0]["reason"] == "spec_not_found"


def test_live_operation_events_and_strict_mode_event(state):
    target = types.SimpleNamespace(value=1)
    patch_set = PatchSet("demo", state=state)
    with patch_set as ctx:
        handle = ctx.set_attr(target, "value", 2)
    patch_set.close()
    assert event_types(state, "patch.") == ["patch.registered", "patch.applied"]
    assert read_events(state=state)["events"][0]["payload"]["handle_id"] == handle.id

    set_strict_mode(True, state=state)
    set_strict_mode(False, state=state)
    strict = [event["payload"] for event in read_events(state=state)["events"] if event["type"] == "debug.strict.changed"]
    assert strict == [{"enabled": True, "previous": False}, {"enabled": False, "previous": True}]


PATCH_TEMPLATE = """
import sys

TARGET = sys.modules["hpd_set_target"]


def setup(ctx):
    ctx.set_attr(TARGET, "VALUE", "{version}")
{extra}
"""


@pytest.fixture
def set_target():
    module: Any = types.ModuleType("hpd_set_target")
    module.VALUE = "original"
    sys.modules["hpd_set_target"] = module
    return module


def test_events_for_set_load_unload_reload_and_rollback(tmp_path, state, set_target):
    path = tmp_path / "demo_patch.py"
    path.write_text(PATCH_TEMPLATE.format(version="v1", extra=""), encoding="utf-8")
    os.utime(path, (1_700_000_000, 1_700_000_000))
    loaded = load_patch(path, name="demo", state=state)
    assert loaded["status"] == "loaded"

    path.write_text(PATCH_TEMPLATE.format(version="v2", extra=""), encoding="utf-8")
    os.utime(path, (1_700_000_010, 1_700_000_010))
    assert reload_patch("demo", state=state)["status"] == "reloaded"
    path.write_text("raise RuntimeError('broken v3')\n", encoding="utf-8")
    os.utime(path, (1_700_000_020, 1_700_000_020))
    assert reload_patch("demo", state=state)["status"] == "rolled_back"
    assert unload_patch("demo", state=state)["status"] == "reverted"
    broken = tmp_path / "broken_patch.py"
    broken.write_text("def setup(ctx):\n    raise RuntimeError('setup broke')\n", encoding="utf-8")
    assert load_patch(broken, name="broken", state=state)["status"] == "failed"

    events = [event for event in read_events(0, 1000, state=state)["events"] if event["type"].startswith("set.")]
    assert [event["type"] for event in events] == [
        "set.loaded",
        "set.unloaded",
        "set.reloaded",
        "set.unloaded",
        "set.rolled_back",
        "set.unloaded",
        "set.failed",
    ]
    assert events[0]["payload"]["set_id"] == loaded["set_id"] and events[0]["payload"]["handle_count"] == 1
    assert events[1]["payload"]["handles"][0]["status"] == "reverted"
    assert events[2]["payload"]["previous_set_id"] == loaded["set_id"]
    assert events[4]["payload"]["error"]["message"].endswith("broken v3")
    assert "traceback" not in events[4]["payload"]["error"]
    assert events[6]["payload"]["action"] == "load"
    assert events[6]["payload"]["error"]["code"] == "setup_failed"


def _demo_feature(target):
    def apply(ctx, section):
        ctx.patch_set.context.set_attr(target, "value", section.get("level", 1))
        return True

    return FeatureSpec(key="thirdparty.debugdemo", title="Demo", description="demo", defaults={"enabled": False, "level": 1}, apply=apply)


def test_events_for_feature_enable_disable_and_update(state):
    target = types.SimpleNamespace(value=0)
    get_feature_registry(state).register(_demo_feature(target))

    assert enable_feature("thirdparty.debugdemo", {"level": 2}, state=state)["status"] == "applied"
    assert disable_feature("thirdparty.debugdemo", state=state)["status"] == "reverted"
    assert target.value == 0

    feature_events = [event["payload"] for event in read_events(0, 1000, state=state)["events"] if event["type"].startswith("feature.")]
    assert [payload["key"] for payload in feature_events] == ["thirdparty.debugdemo", "thirdparty.debugdemo"]
    assert event_types(state, "feature.") == ["feature.enabled", "feature.disabled"]
    assert feature_events[1]["status"] == "reverted" and feature_events[1]["ok"] is True


# ---------------------------------------------------------------------------
# 转发
# ---------------------------------------------------------------------------


def test_forwarding_is_off_by_default(state):
    client = FakeRuntimeClient()
    state.bootstrap_runtime_client = client
    record_event("set.loaded", {"name": "demo"}, state=state)
    record_event("patch.failed", {"handle_id": "patch_1"}, state=state)
    assert client.events == []
    assert get_event_log(state=state).stats()["forward"]["enabled"] is False


def test_forwarding_through_control_feature_and_runtime_client(state):
    client = FakeRuntimeClient()
    state.bootstrap_runtime_client = client

    report = enable_feature("control", {"forward_events": True}, state=state)
    assert report["ok"] is True and report["status"] == "applied"
    record_event("patch.applied", {"handle_id": "patch_1"}, state=state)
    record_event("patch.failed", {"handle_id": "patch_2", "token": "abc"}, state=state)
    record_event("set.loaded", {"name": "demo"}, state=state)
    record_event("connection.changed", {"host": "127.0.0.1"}, state=state)

    forwarded = [payload for event_type, payload in client.events if event_type == "hotpatch.event"]
    assert [event_type for event_type, _ in client.events] == ["hotpatch.event"] * len(client.events)
    assert [payload["type"] for payload in forwarded] == ["feature.enabled", "patch.failed", "set.loaded", "connection.changed"]
    body = forwarded[1]
    assert set(body) == {"cursor", "timestamp", "type", "payload"}
    assert body["payload"]["handle_id"] == "patch_2"
    assert body["payload"]["token"] == REDACTED
    read_back = [event for event in read_events(0, 1000, state=state)["events"] if event["type"] == "patch.failed"]
    assert read_back[0]["payload"]["token"] == REDACTED
    json.dumps(forwarded)

    disable_feature("control", state=state)
    count = len(client.events)
    record_event("set.loaded", {"name": "after"}, state=state)
    assert len(client.events) == count
    assert get_event_log(state=state).forward_enabled is False


def test_forwarding_rate_cap_failures_and_payload_bound():
    now = [100.0]
    client = FakeRuntimeClient()
    log = PatchEventLog(sink=lambda: client, monotonic=lambda: now[0], forward_rate=3)
    log.configure_forwarding(True)
    for index in range(10):
        log.record("set.loaded", {"index": index})
    assert len(client.events) == 3
    now[0] += 1.0
    log.record("feature.disabled", {"key": "x"})
    log.record("set.loaded", {"blob": ["x" * 1000] * 32})
    assert len(client.events) == 5
    assert encoded_size(client.events[-1][1]) <= MAX_FORWARD_PAYLOAD_BYTES + 200
    stats = log.stats()["forward"]
    assert stats == {"enabled": True, "max_per_second": 3, "forwarded": 5, "rate_limited": 7, "failed": 0}

    failing = PatchEventLog(sink=lambda: FakeRuntimeClient(fail=True))
    failing.configure_forwarding(True)
    failing.record("set.failed", {"name": "x"})
    assert failing.stats()["forward"]["failed"] == 1

    no_client = PatchEventLog(sink=lambda: None)
    no_client.configure_forwarding(True)
    no_client.record("set.failed", {"name": "x"})
    assert no_client.stats()["forward"]["failed"] == 1


def test_set_event_forwarding_records_change(state):
    assert set_event_forwarding(True, max_per_second=5, state=state)["max_per_second"] == 5
    assert set_event_forwarding(True, state=state)["enabled"] is True
    set_event_forwarding(False, state=state)
    assert event_types(state, "debug.forwarding") == ["debug.forwarding.changed", "debug.forwarding.changed"]


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------


def reason_codes(result):
    return [reason["code"] for reason in result["reasons"]]


def test_explain_not_registered_and_finder_missing(state, module_dir):
    result = explain("hpd_nothing", state=state)
    assert reason_codes(result) == ["not_registered"]
    assert result["registered"] is False
    json.dumps(result)

    write_module(module_dir, "hpd_plain", "VALUE = 1\n")
    from sd_webui_all_in_one_hotpatcher.hook import MonkeyZoo

    state.monkey_zoo = MonkeyZoo(state=state)
    with state.monkey_zoo("hpd_plain") as monkey:
        monkey.patch_module(lambda module: None)
    result = explain("hpd_plain", state=state)
    assert "finder_not_installed" in reason_codes(result)
    assert result["loader"]["kind"] == "source"
    assert result["finder"]["installed"] is False


def test_explain_already_imported_cache_and_handle_outcomes(state, module_dir):
    install_import_hook(state=state)
    write_module(module_dir, "hpd_early", "def greet():\n    return 'hello'\n")
    module = importlib.import_module("hpd_early")
    with state.monkey_zoo("hpd_early") as monkey:
        late = monkey.patch_function("greet", lambda original, module: lambda: "late")
        late_source = monkey.patch_sources(lambda source, filename: source)
    result = explain("hpd_early", state=state)
    codes = reason_codes(result)
    assert "already_imported" in codes
    already = result["reasons"][codes.index("already_imported")]
    assert set(already["handle_ids"]) == {late.id, late_source.id}
    assert already["restart_required"] == [late_source.id]
    assert "no_cached_spec" in codes
    assert result["loaded"] is True and result["loaded_via_hook"] is False

    write_module(module_dir, "hpd_late", "def greet():\n    return 'hello'\n\ndef other():\n    return 1\n")
    with state.monkey_zoo("hpd_late") as monkey:
        noop = monkey.patch_sources(lambda source, filename: source.replace("NOT PRESENT", "x"))
        failing = monkey.patch_function("greet", lambda original, module: 1 / 0)
        skipped = monkey.patch_function("missing", lambda original, module: original)
    before = explain("hpd_late", state=state)
    assert "no_cached_spec" in reason_codes(before)
    assert state.import_hook_finder is not None and state.import_hook_finder.cache == {}
    assert "hpd_late" not in sys.modules

    importlib.import_module("hpd_late")
    after = explain("hpd_late", state=state)
    codes = reason_codes(after)
    assert "cached_spec" in codes and "imported_with_hook" in codes
    assert "already_imported" not in codes
    flagged = {reason["code"]: reason["handle_id"] for reason in after["reasons"] if "handle_id" in reason}
    assert flagged == {"handle_noop": noop.id, "handle_failed": failing.id, "handle_skipped": skipped.id}
    failed_summary = next(item for item in after["handles"] if item["id"] == failing.id)
    assert failed_summary["last_outcome"]["error_type"] == "ZeroDivisionError"
    assert "traceback" not in failed_summary["last_outcome"]
    del module


def test_explain_unsupported_loader_and_code_stages_on_sourceless_module(state, module_dir):
    install_import_hook(state=state)
    with state.monkey_zoo("sys") as monkey:
        monkey.patch_function("never_called", lambda original, module: original)
    result = explain("sys", state=state)
    assert "unsupported_loader" in reason_codes(result)
    assert result["loader"]["kind"] == "unsupported"
    state.monkey_zoo.discard("sys")

    source = write_module(module_dir, "hpd_sourceless", "VALUE = 1\n")
    py_compile.compile(str(source), cfile=str(module_dir / "hpd_sourceless.pyc"), doraise=True)
    source.unlink()
    importlib.invalidate_caches()
    with state.monkey_zoo("hpd_sourceless") as monkey:
        code_handle = monkey.patch_sources(lambda text, filename: text)
    result = explain("hpd_sourceless", state=state)
    assert result["loader"]["kind"] == "post_exec"
    codes = reason_codes(result)
    assert "code_stages_unsupported" in codes
    assert result["reasons"][codes.index("code_stages_unsupported")]["handle_ids"] == [code_handle.id]

    with state.monkey_zoo("hpd_absent_module") as monkey:
        monkey.patch_module(lambda module: None)
    assert "module_not_found" in reason_codes(explain("hpd_absent_module", state=state))


def test_explain_reports_stack_shadow_order(state, module_dir):
    write_module(module_dir, "hpd_shadowed", "VALUE = 'original'\n")
    install_stack_shadower(["hpd_shadowed"], state=state)
    install_import_hook(state=state)
    with state.monkey_zoo("hpd_shadowed") as monkey:
        monkey.patch_sources(lambda source, filename: source.replace("original", "patched"))
    conflict = explain("hpd_shadowed", state=state)
    assert conflict["finder"]["finder_first"] is True and conflict["finder"]["stack_shadow_matches"] is True
    assert "stack_shadow_conflict" in reason_codes(conflict)
    assert conflict["loader"]["effective_kind"] == "post_exec"

    uninstall_import_hook(state=state)
    uninstall_stack_shadower(state=state)
    install_import_hook(state=state)
    install_stack_shadower(["hpd_shadowed"], state=state)
    ordered = explain("hpd_shadowed", state=state)
    assert ordered["finder"]["finder_first"] is False
    assert "finder_after_stack_shadow" in reason_codes(ordered)
    assert importlib.import_module("hpd_shadowed").VALUE == "patched"

    install_stack_shadower(["hpd_shadowed"], include_source_loaders=False, state=state)
    sourceless_shadow = explain("hpd_shadowed", state=state)
    assert sourceless_shadow["finder"]["stack_shadow_matches"] is False
    assert not {"finder_after_stack_shadow", "stack_shadow_conflict"} & set(reason_codes(sourceless_shadow))


def test_explain_is_bounded_with_many_handles(state):
    install_import_hook(state=state)
    with state.monkey_zoo("hpd_many") as monkey:
        for index in range(300):
            monkey.patch_function(f"function_{index}_" + "x" * 200, lambda original, module: original)
    result = explain("hpd_many", state=state)
    assert result["handles_truncated"] is True
    assert encoded_size(result) < DESKTOP_RESULT_LIMIT


# ---------------------------------------------------------------------------
# 补丁后源码与预演校验
# ---------------------------------------------------------------------------


SENTINEL_SOURCE = """
import sys

sys.modules.setdefault("hpd_sentinel_hits", []).append("executed")
VALUE = "original"
"""


def test_render_patched_source_does_not_execute_or_mark_handles(state, module_dir):
    install_import_hook(state=state)
    write_module(module_dir, "hpd_render", SENTINEL_SOURCE)

    class Upper(ast.NodeTransformer):
        def visit_Constant(self, node):
            if node.value == "patched":
                return ast.copy_location(ast.Constant("PATCHED"), node)
            return node

    with state.monkey_zoo("hpd_render") as monkey:
        source_handle = monkey.patch_sources(lambda source, filename: source.replace('"original"', '"patched"'))
        ast_handle = monkey.patch_ast(Upper())

    result = render_patched_source("hpd_render", state=state)

    assert result["error"] is None
    assert "VALUE = 'PATCHED'" in result["source"]
    assert result["truncated"] is False
    assert result["bytes"] == result["total_bytes"] > 0
    assert [entry["outcome"] for entry in result["handles"]] == ["applied", "applied"]
    assert "hpd_render" not in sys.modules
    assert "hpd_sentinel_hits" not in sys.modules
    assert source_handle.status is PatchStatus.REGISTERED and ast_handle.status is PatchStatus.REGISTERED
    assert source_handle.outcome_counts == {} and ast_handle.outcome_counts == {}
    assert event_types(state, "patch.") == ["patch.registered", "patch.registered"]
    assert state.import_hook_finder is not None and state.import_hook_finder.cache == {}
    json.dumps(result)

    module = importlib.import_module("hpd_render")
    assert module.VALUE == "PATCHED"
    assert sys.modules.pop("hpd_sentinel_hits") == ["executed"]


def test_render_patched_source_truncates_to_encoded_bytes(state, module_dir):
    lines = [f"VALUE_{index} = '中文\\t引号\"{index}'" for index in range(4000)]
    write_module(module_dir, "hpd_large", "\n".join(lines) + "\n")

    default = render_patched_source("hpd_large", state=state)
    assert default["truncated"] is True
    assert default["max_bytes"] == 48 * 1024
    assert default["bytes"] <= 48 * 1024
    assert encoded_size(default["source"]) - 2 == default["bytes"]
    assert default["total_bytes"] > default["bytes"]
    assert encoded_size(default) < DESKTOP_RESULT_LIMIT
    assert "hpd_large" not in sys.modules

    small = render_patched_source("hpd_large", max_bytes=1000, state=state)
    assert small["truncated"] is True and small["bytes"] <= 1000
    assert small["source"].startswith("VALUE_0 = ")

    clamped = render_patched_source("hpd_large", max_bytes=10**9, state=state)
    assert clamped["max_bytes"] == MAX_SOURCE_BYTES
    assert encoded_size(clamped) < DESKTOP_RESULT_LIMIT

    missing = render_patched_source("hpd_not_a_module", state=state)
    assert missing["source"] is None and missing["error"]["code"] == "module_not_found"


def test_verify_reports_noops_and_failures_without_marking_handles(state, module_dir):
    install_import_hook(state=state)
    write_module(module_dir, "hpd_verify", "VALUE = 'original'\n")
    write_module(module_dir, "hpd_verify_ok", "VALUE = 1\n")

    class NoChange(ast.NodeTransformer):
        pass

    def broken(source, filename):
        raise ValueError("pattern drifted")

    with state.monkey_zoo("hpd_verify") as monkey:
        applied = monkey.patch_sources(lambda source, filename: source.replace("original", "patched"))
        noop = monkey.patch_sources(lambda source, filename: source.replace("REMOVED_IN_V2", "x"))
        failed = monkey.patch_sources(broken)
        ast_noop = monkey.patch_ast(NoChange())
        bytecode = monkey.patch_bytecode(lambda wrapper: None)
        monkey.patch_module(lambda module: None)
    with state.monkey_zoo("hpd_verify_ok") as monkey:
        monkey.patch_sources(lambda source, filename: source.replace("1", "2"))

    set_strict_mode(True, state=state)
    report = verify_source_patches(state=state)
    set_strict_mode(False, state=state)

    assert report["checked"] == 2
    assert report["ok"] is False
    assert report["noop_count"] == 2 and report["failed_count"] == 1
    modules = {item["module"]: item for item in report["modules"]}
    assert modules["hpd_verify_ok"]["ok"] is True
    verify = modules["hpd_verify"]
    assert verify["noop"] == [noop.id, ast_noop.id]
    assert verify["failed"] == [failed.id]
    outcomes = {entry["id"]: entry["outcome"] for entry in verify["handles"]}
    assert outcomes == {applied.id: "applied", noop.id: "noop", failed.id: "failed", ast_noop.id: "noop", bytecode.id: "applied"}
    failed_entry = next(entry for entry in verify["handles"] if entry["id"] == failed.id)
    assert failed_entry["error_type"] == "ValueError"

    for handle in (applied, noop, failed, ast_noop, bytecode):
        assert handle.status is PatchStatus.REGISTERED
        assert handle.outcome_counts == {}
    assert not [name for name in event_types(state, "patch.") if name != "patch.registered"]
    assert "hpd_verify" not in sys.modules

    single = verify_source_patches("hpd_verify_ok", state=state)
    assert single["checked"] == 1 and single["ok"] is True
    assert verify_source_patches("hpd_unknown", state=state)["modules"][0]["error"]["code"] == "not_registered"
    json.dumps(report)


# ---------------------------------------------------------------------------
# 状态快照
# ---------------------------------------------------------------------------


def test_status_snapshot_is_json_safe_bounded_and_redacted(state):
    install_import_hook(state=state)
    state.bootstrap_runtime_client = FakeLegacyClient()
    for module_index in range(150):
        with state.monkey_zoo(f"hpd_snapshot_{module_index}") as monkey:
            for patch_index in range(4):
                monkey.patch_function(f"function_{patch_index}", lambda original, module: original)
    for set_index in range(150):
        register_patch_set(PatchSet(f"snapshot-set-{set_index}-" + "n" * 100, state=state), state=state)
    for index in range(1200):
        record_event("patch.applied", {"index": index}, state=state)
    set_trace("patch", state=state)
    assert state.tracer is not None
    state.tracer.configure("patch", file=os.devnull)

    snapshot = status_snapshot(state=state)

    text = json.dumps(snapshot, ensure_ascii=False)
    assert len(text.encode("utf-8")) < DESKTOP_RESULT_LIMIT
    assert "legacy-s3cret-token" not in text
    assert snapshot["connection"] == {"transport": "legacy", "editable": False, "host": "127.0.0.1", "port": 4567, "token": REDACTED, "token_set": True}
    assert snapshot["transport"]["status"]["token"] == REDACTED
    assert snapshot["hooks"]["import_hook"] is True
    assert snapshot["hooks"]["plans"] == 150
    assert snapshot["hooks"]["handles"] >= 600
    assert snapshot["sets_truncated"] is True and snapshot["set_count"] == 150
    assert snapshot["debug"]["strict"] is False
    assert snapshot["debug"]["trace"]["tags"] == ["patch"]
    assert snapshot["debug"]["events"]["count"] == 1000
    assert snapshot["debug"]["events"]["dropped"] > 0
    assert "control" in snapshot["features"]["registered"]
    assert snapshot["pid"] == os.getpid()


def test_status_snapshot_redacts_desktop_settings():
    isolated = HotpatcherState()
    settings = types.SimpleNamespace(
        broker_url="http://127.0.0.1:9000/?secret=1",
        session_id="sess-123",
        session_token="desk-s3cret",
        runtime_identity="runtime-a",
        protocol_version="2",
    )
    client: Any = types.SimpleNamespace(settings=settings, status=lambda: {"sessionId": "sess-123", "status": "connected", "unacknowledgedDiagnostics": list(range(50))})
    isolated.bootstrap_runtime_client = client
    isolated.bootstrap_transport_mode = "desktop_broker"

    snapshot = status_snapshot(state=isolated)

    text = json.dumps(snapshot)
    assert "desk-s3cret" not in text and "sess-123" not in text and "secret=1" not in text
    assert snapshot["connection"]["session_token"] == REDACTED
    assert snapshot["connection"]["runtime_identity"] == "runtime-a"
    assert len(snapshot["transport"]["status"]["unacknowledgedDiagnostics"]) == 11
