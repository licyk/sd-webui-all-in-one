"""Hotpatcher 管理 GUI "运行时控制" 标签页的逻辑测试 (不需要显示器)。"""

from typing import Any

import pytest

from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui.runtime_control import (
    EVENT_PAGE_SIZE,
    RuntimeControlController,
    format_event_line,
    format_feature_rows,
    format_patch_rows,
    format_set_rows,
    parse_rebind_target,
    redact_token,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import HotpatcherRuntimeHost, RemoteServiceError


class _FakeHost:
    """只记录调用的 runtime host 替身。"""

    def __init__(self, *, connected=True, legacy=False, token="secret"):
        self.service_channel_available = connected
        self.legacy = legacy
        self.token = token
        self.server_address = ("127.0.0.1", 8765)
        self.calls: list[tuple[str, Any]] = []

    def _control(self, name, *args):
        self.calls.append((name, args))
        if self.legacy:
            raise RemoteServiceError("unsupported", "legacy")

    def get_capabilities(self):
        self._control("get_capabilities")
        return {"control_version": 1, "transport": "legacy", "commands": ["a", "b"]}

    def get_status(self):
        self._control("get_status")
        return {"pid": 42, "version": {"package": "2.6.2", "python": "3.11"}, "debug": {"strict": True}}

    def list_patches(self):
        self._control("list_patches")
        return {"patches": [{"id": "hp-1", "kind": "function", "target": "m:f", "owner": "set-a", "stage": "post", "status": "active"}], "truncated": False}

    def list_sets(self):
        self._control("list_sets")
        return {"sets": [{"id": "ps-1", "name": "demo", "kind": "loaded", "status": "open", "handle_count": 2}], "truncated": True}

    def list_features(self):
        self._control("list_features")
        return {"features": [{"key": "extensions.uv_pip", "title": "uv", "applied": True, "active": False}]}

    def unload_patch(self, patch_id):
        self._control("unload_patch", patch_id)
        return {"id": patch_id, "status": "reverted"}

    def unload_patch_set(self, key):
        self._control("unload_patch_set", key)
        return {"ok": True}

    def enable_feature(self, key):
        self._control("enable_feature", key)
        return {"ok": True}

    def disable_feature(self, key):
        self._control("disable_feature", key)
        return {"ok": True}

    def read_patch_events(self, since_cursor, limit):
        self._control("read_patch_events", since_cursor, limit)
        events = [{"cursor": since_cursor, "timestamp": 0.0, "type": "patch.unload", "payload": {"id": "hp-1"}}]
        return {"events": events, "start_cursor": since_cursor, "next_cursor": since_cursor + 1, "truncated": since_cursor == 0, "has_more": True}

    def get_trace(self):
        self._control("get_trace")
        return {"enabled": True, "tags": ["patch"], "file": None, "available_tags": ["patch", "conn"]}

    def set_trace(self, tags):
        self._control("set_trace", tags)
        return {"enabled": tags is not None}

    def set_strict(self, enabled):
        self._control("set_strict", enabled)
        return {"strict": enabled, "previous": not enabled}

    def test_connection(self, changes):
        self._control("test_connection", changes)
        return {"ok": True}

    def get_connection(self):
        self._control("get_connection")
        return {"connected": True}

    def rebind(self, **changes):
        self._control("rebind", changes)
        return {"status": "switched"}


def _controller(host):
    return RuntimeControlController(lambda: host)


def test_describe_reports_each_connection_state():
    assert _controller(None).describe()["state"] == "stopped"
    assert _controller(_FakeHost(connected=False)).describe()["state"] == "not_connected"
    assert _controller(_FakeHost(legacy=True)).describe()["state"] == "legacy"

    summary = _controller(_FakeHost()).describe()
    assert summary["state"] == "control"
    assert "v1" in summary["text"] and "PID 42" in summary["text"] and "命令 2 个" in summary["text"]


def test_describe_reports_other_errors():
    host = _FakeHost()

    def failing():
        raise RemoteServiceError("timeout", "slow")

    host.get_capabilities = failing  # type: ignore[method-assign]
    summary = _controller(host).describe()
    assert summary["state"] == "error" and "timeout" in summary["text"]


def test_lists_and_actions_call_the_host_wrappers():
    host = _FakeHost()
    controller = _controller(host)

    lists = controller.load_lists()
    assert lists["patches"] == [("hp-1", ("hp-1", "function", "m:f", "set-a", "post", "active"))]
    assert lists["sets"] == [("ps-1", ("ps-1", "demo", "loaded", "open", "2"))]
    assert lists["features"] == [("extensions.uv_pip", ("extensions.uv_pip", "uv", "是", "否"))]
    assert lists["truncated"] is True

    controller.unload_patch("hp-1")
    controller.unload_set("ps-1")
    controller.set_feature("extensions.uv_pip", True)
    controller.set_feature("extensions.uv_pip", False)
    controller.set_trace("  ")
    controller.set_trace("patch,conn")
    controller.set_strict(True)
    assert controller.get_debug() == {"trace": host.get_trace(), "strict": True}
    assert controller.test_connection() == {"test": {"ok": True}, "connection": {"connected": True}}
    assert controller.apply_rebind({"port": 0, "token": "new"}) == {"status": "switched"}

    names = [name for name, _args in host.calls]
    assert names[:3] == ["list_patches", "list_sets", "list_features"]
    assert ("unload_patch", ("hp-1",)) in host.calls and ("unload_patch_set", ("ps-1",)) in host.calls
    assert ("enable_feature", ("extensions.uv_pip",)) in host.calls and ("disable_feature", ("extensions.uv_pip",)) in host.calls
    assert ("set_trace", (None,)) in host.calls and ("set_trace", ("patch,conn",)) in host.calls
    assert ("test_connection", ({},)) in host.calls
    assert ("rebind", ({"port": 0, "token": "new"},)) in host.calls


def test_event_paging_follows_the_cursor():
    host = _FakeHost()
    controller = _controller(host)

    first = controller.read_events(0)
    assert first["next_cursor"] == 1 and first["has_more"] and first["truncated"]
    assert first["lines"][0].startswith("[0] ") and "patch.unload" in first["lines"][0]
    second = controller.read_events(first["next_cursor"])
    assert second["next_cursor"] == 2 and not second["truncated"]
    assert ("read_patch_events", (1, EVENT_PAGE_SIZE)) in host.calls


def test_actions_without_host_raise_channel_unavailable():
    with pytest.raises(RemoteServiceError) as exc_info:
        _controller(None).load_lists()
    assert exc_info.value.code == "channel_unavailable"
    assert _controller(None).connection_view() == {"host": None, "port": None, "token": None}


def test_connection_view_redacts_the_token():
    assert _controller(_FakeHost(token="secret")).connection_view() == {"host": "127.0.0.1", "port": 8765, "token": "***"}
    assert _controller(_FakeHost(token="")).connection_view()["token"] == "(未设置)"
    assert redact_token("x") == "***"


def test_parse_rebind_target():
    current = ("127.0.0.1", 8765, "old")
    assert parse_rebind_target("", "0", "", current=current) == {"port": 0}
    assert parse_rebind_target("localhost", "8765", "new", current=current) == {"host": "localhost", "token": "new"}
    for host_text, port_text, token_text in (("", "", ""), ("127.0.0.1", "8765", "old"), ("", "abc", ""), ("", "70000", "")):
        with pytest.raises(ValueError):
            parse_rebind_target(host_text, port_text, token_text, current=current)


def test_formatters_tolerate_partial_results():
    assert format_patch_rows({}) == [] and format_set_rows({"sets": [None]}) == [] and format_feature_rows({"features": "x"}) == []
    assert format_event_line({"cursor": 3, "type": "x", "payload": None}) == "[3] --:--:-- x null"


def test_controller_against_a_real_host_without_child():
    with HotpatcherRuntimeHost(port=0, token="tok") as host:
        controller = _controller(host)
        assert controller.describe()["state"] == "not_connected"
        view = controller.connection_view()
        assert view["port"] == host.server_address[1] and view["token"] == "***"
        report = controller.apply_rebind(parse_rebind_target("", "0", "", current=(view["host"], view["port"], host.token)))
        assert report["status"] == "switched" and report["child"] is None
