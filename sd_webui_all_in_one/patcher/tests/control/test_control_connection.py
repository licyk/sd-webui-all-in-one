"""连接参数与连接管理器测试: 环境变量兼容、参数校验、连接测试、先建后拆切换与回滚、自动重连、桌面只读、脱敏。"""

import importlib
import json
import math
import os
import socket
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from sd_webui_all_in_one_hotpatcher import bootstrap
from sd_webui_all_in_one_hotpatcher.control.commands import ERROR_CODES, CommandError, CommandSpec
from sd_webui_all_in_one_hotpatcher.control.controller import get_controller
from sd_webui_all_in_one_hotpatcher.control.events import read_events
from sd_webui_all_in_one_hotpatcher.control.inspect import status_snapshot
from sd_webui_all_in_one_hotpatcher.control.trace import HotpatchTracer
from sd_webui_all_in_one_hotpatcher.runtime import connection as connection_module
from sd_webui_all_in_one_hotpatcher.runtime.client import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.connection import (
    PENDING_SWITCH_TIMEOUT,
    ConnectionBusyError,
    ConnectionFailedError,
    ConnectionManager,
    RuntimeConnectionSettings,
    get_connection_manager,
    is_loopback_host,
)
from sd_webui_all_in_one_hotpatcher.runtime.faults import install_faulthandler
from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message
from sd_webui_all_in_one_hotpatcher.services import PatchService, install_service_control_channel
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

# 复用 tests/runtime 的 JsonlHost; 单独运行本目录时该目录不在 sys.path 中。
RUNTIME_TEST_DIR = str(Path(__file__).resolve().parents[1] / "runtime")
if RUNTIME_TEST_DIR not in sys.path:
    sys.path.insert(0, RUNTIME_TEST_DIR)
_runtime_helpers: Any = importlib.import_module("runtime_test_helpers")
JsonlHost = _runtime_helpers.JsonlHost

ENV_NAMES = (
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONNECT_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REQUEST_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_EVENT_WRITE_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RECONNECT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ALLOW_NON_LOOPBACK",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG",
)
SECRET_A = "tok-secret-alpha"
SECRET_B = "tok-secret-bravo"
WAIT = 5


# ---------------------------------------------------------------------------
# 测试宿主
# ---------------------------------------------------------------------------


class _Log:
    """跨多个测试宿主共享的有序消息日志。"""

    def __init__(self):
        self.entries: list[tuple[str, str, dict]] = []
        self.cond = threading.Condition()

    def add(self, host, kind, message):
        with self.cond:
            self.entries.append((host, kind, message))
            self.cond.notify_all()

    def wait(self, predicate, timeout=WAIT):
        with self.cond:
            return self.cond.wait_for(lambda: any(predicate(*entry) for entry in self.entries), timeout)

    def find(self, predicate):
        with self.cond:
            return [entry for entry in self.entries if predicate(*entry)]


class _ControlHost(JsonlHost):
    """保持通道打开、记录每条消息与 EOF、可关闭全部连接并在同一端口重启的 JsonlHost。"""

    def __init__(self, name, log, *, port=0):
        super().__init__()
        self._sock.close()
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", port))
        self._sock.listen()
        self.host, self.port = self._sock.getsockname()
        self.name = name
        self.log = log
        self.lock = threading.Lock()
        self.connections: list[socket.socket] = []
        self.channels: dict[str, list[socket.socket]] = {}

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.kill()

    def _handle(self, conn):
        with self.lock:
            self.connections.append(conn)
        kind = "main"
        try:
            for line in conn.makefile("rb"):
                message = json.loads(line.decode("utf-8"))
                if message.get("type") == "channel.open":
                    kind = message.get("channel", "?")
                    with self.lock:
                        self.channels.setdefault(kind, []).append(conn)
                self.log.add(self.name, kind, message)
                if kind == "main" and message.get("id") is not None:
                    conn.sendall(encode_message({"id": message["id"], "ok": True, "payload": {}}))
        except (OSError, ValueError):
            pass
        finally:
            self.log.add(self.name, kind, {"type": "<eof>"})
            try:
                conn.close()
            except OSError:
                pass

    def send(self, request, channel="services"):
        with self.lock:
            conn = self.channels[channel][-1]
        conn.sendall(encode_message(request))

    def kill(self):
        self._stop.set()
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()
        self._thread.join(timeout=2)
        with self.lock:
            connections = list(self.connections)
        for conn in connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass


def _is(host, kind, message_type=None, **fields):
    def predicate(entry_host, entry_kind, message):
        if entry_host != host or entry_kind != kind:
            return False
        if message_type is not None and message.get("type") != message_type:
            return False
        return all(message.get(key) == value for key, value in fields.items())

    return predicate


def _closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def state():
    isolated = HotpatcherState()
    yield isolated
    manager = isolated.connection_manager
    if manager is not None:
        manager.close()
    channel = isolated.bootstrap_service_control_channel
    if channel is not None:
        channel.close()
    if isolated.fault_channel is not None:
        isolated.fault_channel.close()
    client = isolated.bootstrap_runtime_client
    if client is not None and hasattr(client, "close"):
        client.close()


@pytest.fixture
def log():
    return _Log()


def _wire(state, host, *, token=SECRET_A, fault=True):
    """像 bootstrap 一样连接宿主: 主连接、services 通道、(可选) fault 通道。"""

    client = RuntimeClient.connect(host.host, host.port, token=token, timeout=2)
    state.bootstrap_runtime_client = client
    state.bootstrap_service_control_channel = install_service_control_channel(client, state=state)
    assert host.log.wait(_is(host.name, "services", "channel.open"))
    if fault:
        install_faulthandler(client, enable=False, state=state, timeout=2)
        assert host.log.wait(_is(host.name, "fault", "channel.open"))
    return client


def _legacy(state, name, payload=None, *, token=SECRET_A, after_send=None):
    envelope = PatchService(state=state).handle_control_request({"type": name, "payload": payload or {}}, transport="legacy", token=token, after_send=after_send)
    assert json.loads(json.dumps(envelope)) == envelope
    return envelope


def _manager(state) -> ConnectionManager:
    manager = get_connection_manager(state)
    assert manager is not None
    return manager


def _err(envelope):
    assert envelope["ok"] is False, envelope
    assert envelope["error"]["code"] in ERROR_CODES
    return envelope["error"]


# ---------------------------------------------------------------------------
# RuntimeConnectionSettings
# ---------------------------------------------------------------------------


def _old_connect_from_env(cls, *, required=False):
    """P8 之前 ``RuntimeClient.connect_from_env`` 的实现, 作为行为对照。"""

    host = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST")
    port = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT")
    token = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN", "")
    compatibility_timeout = float(os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT", "5.0"))
    connect_timeout = float(os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONNECT_TIMEOUT", str(compatibility_timeout)))
    default_request_timeout = float(os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REQUEST_TIMEOUT", str(compatibility_timeout)))
    event_write_timeout = float(os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_EVENT_WRITE_TIMEOUT", str(compatibility_timeout)))
    if not host or not port:
        if required:
            raise RuntimeError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST and SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT are required")
        return None
    try:
        return cls.connect(
            host,
            int(port),
            token=token,
            timeout=compatibility_timeout,
            connect_timeout=connect_timeout,
            default_request_timeout=default_request_timeout,
            event_write_timeout=event_write_timeout,
        )
    except Exception:
        if required:
            raise
        return None


H, P, T = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"
TO, CT, RT, ET = (
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONNECT_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REQUEST_TIMEOUT",
    "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_EVENT_WRITE_TIMEOUT",
)
ENV_TABLE = [
    {},
    {H: "127.0.0.1"},
    {P: "8123"},
    {H: "", P: "8123"},
    {H: "127.0.0.1", P: ""},
    {H: "127.0.0.1", P: "8123"},
    {H: "127.0.0.1", P: "8123", T: "secret"},
    {H: "localhost", P: " 8123 ", TO: "2"},
    {H: "127.0.0.1", P: "8123", TO: "2", CT: "0.5"},
    {H: "127.0.0.1", P: "8123", TO: "0.5", CT: "0.1", RT: "0.2", ET: "0.3", T: "s"},
    {H: "127.0.0.1", P: "8123", RT: "7", ET: "8"},
    {H: "192.168.1.20", P: "8123"},
    {H: "127.0.0.1", P: "8123", CT: "0", ET: "-1"},
    {H: "127.0.0.1", P: "8123", "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RECONNECT": "1", "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ALLOW_NON_LOOPBACK": "1"},
    {H: "127.0.0.1", P: "not-a-port"},
    {H: "127.0.0.1", P: "70000"},
    {TO: "abc"},
    {H: "127.0.0.1", P: "8123", RT: "soon"},
    {H: "127.0.0.1", P: "8123", TO: ""},
]


def _outcome(function, monkeypatch, required):
    calls: list = []

    def connect(cls, host, port, **kwargs):
        calls.append({"host": host, "port": port, **kwargs})
        if not 0 < port < 65536:
            raise OverflowError("port out of range")
        for key in ("timeout", "connect_timeout", "default_request_timeout", "event_write_timeout"):
            value = kwargs[key]
            if not value > 0 or math.isnan(value):
                raise ValueError(f"{key} must be a positive finite number")
        return "connected"

    monkeypatch.setattr(RuntimeClient, "connect", classmethod(connect))
    try:
        result = function(required=required)
    except Exception as exc:
        return ("raised", type(exc).__name__, calls)
    return ("returned", result, calls)


@pytest.mark.parametrize("env", ENV_TABLE, ids=[str(index) for index in range(len(ENV_TABLE))])
@pytest.mark.parametrize("required", [False, True])
def test_connect_from_env_matches_previous_implementation(monkeypatch, env, required):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    expected = _outcome(lambda **kwargs: _old_connect_from_env(RuntimeClient, **kwargs), monkeypatch, required)
    actual = _outcome(RuntimeClient.connect_from_env, monkeypatch, required)
    assert actual == expected


def test_from_env_reads_the_same_defaults_and_precedence():
    assert RuntimeConnectionSettings.from_env({}) is None
    assert RuntimeConnectionSettings.from_env({H: "127.0.0.1"}) is None
    default = RuntimeConnectionSettings.from_env({H: "127.0.0.1", P: "8123"})
    assert default == RuntimeConnectionSettings(host="127.0.0.1", port=8123)
    assert (default.token, default.connect_timeout, default.request_timeout, default.event_write_timeout) == ("", 5.0, 5.0, 5.0)
    assert (default.reconnect, default.reconnect_initial, default.reconnect_max, default.allow_non_loopback) == (False, 0.1, 5.0, False)

    settings = RuntimeConnectionSettings.from_env(
        {
            H: "10.0.0.5",
            P: "9000",
            T: SECRET_A,
            TO: "2",
            RT: "3",
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RECONNECT": "1",
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ALLOW_NON_LOOPBACK": "yes",
        }
    )
    assert settings is not None
    # 启动环境中的非回环地址按原有行为直接使用, 不做回环校验。
    assert (settings.host, settings.port, settings.token) == ("10.0.0.5", 9000, SECRET_A)
    assert (settings.compatibility_timeout, settings.connect_timeout, settings.request_timeout, settings.event_write_timeout) == (2.0, 2.0, 3.0, 2.0)
    assert settings.reconnect is True
    assert settings.allow_non_loopback is False  # 只有 "1" 开启
    with pytest.raises(ValueError):
        RuntimeConnectionSettings.from_env({TO: "abc"})
    with pytest.raises(ValueError):
        RuntimeConnectionSettings.from_env({H: "127.0.0.1", P: "x"})


@pytest.mark.parametrize(
    "host,expected",
    [
        ("localhost", True),
        ("LOCALHOST.", True),
        ("127.0.0.1", True),
        ("127.8.9.10", True),
        ("::1", True),
        ("[::1]", True),
        ("::ffff:127.0.0.1", True),
        ("0.0.0.0", False),
        ("192.168.1.2", False),
        ("10.0.0.1", False),
        ("::", False),
        ("example.com", False),
        ("localhost.example.com", False),
        ("", False),
    ],
)
def test_loopback_detection_does_not_use_dns(host, expected):
    assert is_loopback_host(host) is expected


@pytest.mark.parametrize(
    "changes",
    [
        {"port": 0},
        {"port": 65536},
        {"port": True},
        {"port": "8123"},
        {"host": ""},
        {"host": "   "},
        {"host": "local host"},
        {"host": 127},
        {"host": "x" * 300},
        {"token": 5},
        {"connect_timeout": 0},
        {"request_timeout": -1},
        {"event_write_timeout": float("inf")},
        {"connect_timeout": float("nan")},
        {"connect_timeout": "1"},
        {"connect_timeout": True},
        {"reconnect": "yes"},
        {"allow_non_loopback": 1},
        {"reconnect_initial": 2.0, "reconnect_max": 1.0},
        {"unknown": 1},
        {"compatibility_timeout": 1.0},
        {"host": "192.168.1.2"},
        {"host": "example.com"},
        {"host": "0.0.0.0"},
    ],
)
def test_merged_rejects_invalid_changes(changes):
    base = RuntimeConnectionSettings(host="127.0.0.1", port=8123, token=SECRET_A)
    with pytest.raises(ValueError) as info:
        base.merged(changes)
    assert SECRET_A not in str(info.value)


def test_merged_accepts_valid_changes_and_loopback_rules():
    base = RuntimeConnectionSettings(host="127.0.0.1", port=8123, token=SECRET_A)
    merged = base.merged({"host": " localhost ", "port": 9000, "token": SECRET_B, "connect_timeout": 1, "reconnect": True, "reconnect_max": 2})
    assert (merged.host, merged.port, merged.token, merged.connect_timeout, merged.reconnect, merged.reconnect_max) == ("localhost", 9000, SECRET_B, 1.0, True, 2.0)
    assert isinstance(merged.connect_timeout, float)
    assert base.port == 8123  # 原对象不变
    for host in ("127.0.0.2", "::1", "[::1]"):
        assert base.merged({"host": host}).host == host
    assert base.merged({"host": "192.168.1.2", "allow_non_loopback": True}).host == "192.168.1.2"
    assert base.merged({"allow_non_loopback": True}).merged({"host": "example.com"}).host == "example.com"
    # 启动环境给出的非回环地址不变时, 其他字段仍可修改。
    lan = RuntimeConnectionSettings(host="192.168.1.2", port=8123)
    assert lan.merged({"port": 9001}).port == 9001
    assert base.merged({}) == base

    redacted = merged.redacted()
    assert redacted["token"] == "***" and redacted["token_set"] is True
    assert SECRET_B not in json.dumps(redacted)
    assert SECRET_B not in repr(merged)
    assert RuntimeConnectionSettings(host="127.0.0.1", port=1).redacted()["token"] == ""


# ---------------------------------------------------------------------------
# rebind 与管理器创建
# ---------------------------------------------------------------------------


def test_rebind_swaps_transport_and_derives_endpoint(log):
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = RuntimeClient.connect(host_a.host, host_a.port, token=SECRET_A, timeout=2)
        other = RuntimeClient.connect(host_b.host, host_b.port, token=SECRET_B, timeout=2)
        old = client.rebind(other.transport)
        assert (client.host, client.port, client.token) == (host_b.host, host_b.port, SECRET_B)
        assert client.status()["port"] == host_b.port
        assert client.emit_event("progress.update", {"value": 1}) is True
        assert log.wait(_is("B", "main", "progress.update"))
        assert client.rebind(old) is other.transport
        assert client.port == host_a.port
        # 未登记连接管理器时客户端行为不变。
        assert client.connection_listener is None
        assert client.report_connection_lost("x") is False
        client.close()
        other.close()


def test_manager_exists_only_for_rebindable_legacy_clients(state, log):
    assert get_connection_manager(state) is None
    state.bootstrap_runtime_client = cast(Any, SimpleNamespace(host="127.0.0.1", port=1, token="", transport=object()))
    assert get_connection_manager(state) is None
    with _ControlHost("A", log) as host_a:
        client = RuntimeClient.connect(host_a.host, host_a.port, token=SECRET_A, timeout=2)
        state.bootstrap_runtime_client = client
        manager = get_connection_manager(state)
        assert manager is not None and manager is get_connection_manager(state)
        assert client.connection_listener == manager._on_transport_failure
        assert manager.settings.port == host_a.port and manager.settings.token == SECRET_A
        snapshot = manager.get()
        assert snapshot["settings"]["editable"] is True and snapshot["settings"]["token"] == "***"
        assert snapshot["state"] == "connected" and snapshot["connected"] is True
        # 换成另一个客户端时旧管理器被关闭并注销通知。
        replacement = RuntimeClient.connect(host_a.host, host_a.port, timeout=2)
        state.bootstrap_runtime_client = replacement
        assert get_connection_manager(state) is not manager
        assert client.connection_listener is None
        client.close()


def test_bootstrap_creates_manager_only_when_reconnect_is_enabled(monkeypatch, log):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    with _ControlHost("A", log) as host_a:
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
        monkeypatch.setenv(H, host_a.host)
        monkeypatch.setenv(P, str(host_a.port))
        plain = HotpatcherState()
        client = bootstrap.initialize_legacy_runtime(state=plain)
        assert client is not None
        assert plain.connection_manager is None
        assert client.connection_listener is None
        client.close()

        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RECONNECT", "1")
        reconnecting = HotpatcherState()
        client = bootstrap.initialize_legacy_runtime(state=reconnecting)
        assert client is not None
        manager = reconnecting.connection_manager
        assert manager is not None and manager.settings.reconnect is True
        manager.close()
        client.close()


# ---------------------------------------------------------------------------
# test()
# ---------------------------------------------------------------------------


def test_connection_test_connects_sends_hello_and_closes_without_swap(state, log):
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = _wire(state, host_a)
        transport = client.transport
        result = get_controller(state).connection.test(port=host_b.port, token=SECRET_B)
        assert result["ok"] is True and result["settings"]["port"] == host_b.port
        assert SECRET_B not in json.dumps(result)
        assert log.wait(_is("B", "main", "hello", token=SECRET_B))
        assert log.wait(_is("B", "main", "<eof>"))
        assert client.transport is transport and client.port == host_a.port
        assert _manager(state).settings.port == host_a.port
        assert not log.find(_is("B", "services"))

        # 旧版通道: 需要非空 token; 失败映射为 connection_failed。
        assert _err(_legacy(state, "hotpatch.connection.test", {"port": host_b.port}, token=""))["code"] == "forbidden"
        assert _legacy(state, "hotpatch.connection.test", {"port": host_b.port})["ok"] is True
        assert _err(_legacy(state, "hotpatch.connection.test", {"port": _closed_port()}))["code"] == "connection_failed"
        assert _err(_legacy(state, "hotpatch.connection.test", {"port": 0}))["code"] == "invalid_payload"
        assert _err(_legacy(state, "hotpatch.connection.test", {"bogus": 1}))["code"] == "invalid_payload"


# ---------------------------------------------------------------------------
# update(): 先建后拆
# ---------------------------------------------------------------------------


def test_update_over_services_channel_switches_after_response(state, log):
    observed: list = []
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = _wire(state, host_a)
        old_channel = state.bootstrap_service_control_channel
        old_fault = state.fault_channel
        old_transport = client.transport
        error_capture_like = SimpleNamespace(client=client)  # 持有客户端对象的组件

        def gated_opener(manager, settings, previous):
            # 切换只能发生在旧通道写出响应之后: 等宿主 A 收到响应再打开新通道。
            observed.append(log.wait(_is("A", "services", id="u1")))
            # 新主连接的 hello 在命令处理函数内、响应之前发送。
            observed.append(log.wait(_is("B", "main", "hello", token=SECRET_B)))
            return connection_module._open_services_channel(manager, settings, previous)

        state.connection_manager = ConnectionManager(client, state=state, services_opener=gated_opener).attach()
        host_a.send({"id": "u1", "type": "hotpatch.connection.update", "payload": {"port": host_b.port, "token": SECRET_B}})

        assert log.wait(_is("B", "services", "channel.open", token=SECRET_B))
        assert log.wait(_is("B", "fault", "channel.open", token=SECRET_B))
        assert observed == [True, True]
        response = log.find(_is("A", "services", id="u1"))[0][2]
        assert response["ok"] is True and response["payload"]["status"] == "scheduled"
        assert SECRET_B not in json.dumps(response)

        # 旧通道、旧 fault 通道与旧主连接全部关闭。
        assert log.wait(_is("A", "services", "<eof>"))
        assert log.wait(_is("A", "fault", "<eof>"))
        assert log.wait(_is("A", "main", "<eof>"))
        old_channel.thread.join(WAIT)
        assert old_channel.closed and not old_channel.thread.is_alive()
        assert old_fault.closed and old_transport.closed

        new_channel = state.bootstrap_service_control_channel
        assert new_channel is not old_channel and not new_channel.closed
        assert state.fault_channel is not old_fault and state.fault_channel.client is client
        assert (client.host, client.port, client.token) == (host_b.host, host_b.port, SECRET_B)
        assert error_capture_like.client.emit_event("progress.update", {"value": 2}) is True
        assert log.wait(_is("B", "main", "progress.update"))
        assert not log.find(_is("A", "main", "progress.update"))

        # 新 services 通道可用, 并以新 token 鉴权。
        host_b.send({"id": "g1", "type": "hotpatch.connection.get", "payload": {}})
        assert log.wait(_is("B", "services", id="g1"))
        connection = log.find(_is("B", "services", id="g1"))[0][2]["payload"]
        assert connection["settings"]["port"] == host_b.port and connection["settings"]["editable"] is True
        assert connection["manager"]["switches"] == 1
        assert SECRET_A not in json.dumps(connection) and SECRET_B not in json.dumps(connection)

        events = read_events(state=state)["events"]
        changed = [event for event in events if event["type"] == "connection.changed"]
        assert changed[-1]["payload"]["status"] == "switched"
        assert SECRET_B not in json.dumps(events)


def test_inprocess_update_switches_immediately(state, log):
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = _wire(state, host_a, fault=False)
        report = get_controller(state).connection.update(port=host_b.port, token=SECRET_B, request_timeout=3)
        assert report["status"] == "switched" and report["settings"]["request_timeout"] == 3.0
        assert client.port == host_b.port and client.transport.default_request_timeout == 3.0
        assert log.wait(_is("B", "services", "channel.open"))
        assert log.wait(_is("A", "main", "<eof>"))
        assert _manager(state).settings.token == SECRET_B


def test_failed_connect_leaves_everything_unchanged(state, log):
    with _ControlHost("A", log) as host_a:
        client = _wire(state, host_a)
        transport, channel, fault = client.transport, state.bootstrap_service_control_channel, state.fault_channel
        manager = _manager(state)
        with pytest.raises(CommandError) as info:
            get_controller(state).connection.update(port=_closed_port())
        assert info.value.code == "connection_failed"
        envelope = _legacy(state, "hotpatch.connection.update", {"port": _closed_port()}, after_send=(after := []))
        assert _err(envelope)["code"] == "connection_failed" and after == []
        assert client.transport is transport and not transport.closed
        assert state.bootstrap_service_control_channel is channel and not channel.closed
        assert state.fault_channel is fault and not fault.closed
        assert manager.settings.port == host_a.port
        assert manager.get()["pending_switch"] is False
        assert client.emit_event("progress.update", {}) is True
        assert log.wait(_is("A", "main", "progress.update"))


@pytest.mark.parametrize("stage", ["services", "fault"])
def test_failure_during_switch_rolls_back_and_old_channel_still_works(state, log, stage):
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = _wire(state, host_a)
        transport, channel, fault = client.transport, state.bootstrap_service_control_channel, state.fault_channel

        def boom(manager, settings, previous):
            raise ConnectionRefusedError(f"{stage} channel refused")

        options: dict[str, Any] = {"services_opener": boom} if stage == "services" else {"fault_opener": boom}
        state.connection_manager = ConnectionManager(client, state=state, **options).attach()
        host_a.send({"id": "u2", "type": "hotpatch.connection.update", "payload": {"port": host_b.port}})
        assert log.wait(_is("A", "services", id="u2"))
        # 新主连接已建立 (hello), 回滚后被关闭; fault 阶段失败时新 services 通道也被关闭。
        assert log.wait(_is("B", "main", "<eof>"))
        if stage == "fault":
            assert log.wait(_is("B", "services", "<eof>"))
        else:
            assert not log.find(_is("B", "services"))

        manager = state.connection_manager
        snapshot = manager.get()
        assert snapshot["last_change"]["status"] == "rolled_back" and snapshot["last_change"]["stage"] == stage
        assert any(item["stage"] == stage for item in snapshot["diagnostics"])
        assert client.transport is transport and not transport.closed
        assert state.bootstrap_service_control_channel is channel and not channel.closed
        assert state.fault_channel is fault and not fault.closed
        assert manager.settings.port == host_a.port
        events = [event for event in read_events(state=state)["events"] if event["type"] == "connection.changed"]
        assert events[-1]["payload"]["status"] == "rolled_back"

        host_a.send({"id": "after", "type": "hotpatch.patches.list", "payload": {}})
        assert log.wait(_is("A", "services", id="after", ok=True))
        assert client.emit_event("progress.update", {}) is True
        assert log.wait(_is("A", "main", "progress.update"))

        # 进程内调用的回滚映射为 connection_failed, details 携带报告。
        with pytest.raises(CommandError) as info:
            get_controller(state).connection.update(port=host_b.port)
        assert info.value.code == "connection_failed" and info.value.details is not None
        assert info.value.details["status"] == "rolled_back"


def test_dropped_switch_callback_becomes_stale_and_is_discarded(state, log):
    now = [100.0]
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = _wire(state, host_a, fault=False)
        manager = ConnectionManager(client, state=state, clock=lambda: now[0]).attach()
        state.connection_manager = manager
        dropped: list = []
        assert manager.update({"port": host_b.port}, defer=dropped.append)["status"] == "scheduled"
        with pytest.raises(ConnectionBusyError):
            manager.update({"port": host_b.port})
        now[0] += PENDING_SWITCH_TIMEOUT + 1
        assert manager.update({"port": host_b.port})["status"] == "switched"
        # 过期的新连接被关闭; 迟到的旧回调不会再切换。
        assert dropped[0]() == {"status": "discarded"}
        assert log.wait(_is("B", "main", "<eof>"))
        assert client.port == host_b.port and not client.transport.closed


# ---------------------------------------------------------------------------
# 信任边界与桌面
# ---------------------------------------------------------------------------


def test_non_loopback_is_rejected_by_default_and_remote_cannot_allow_it(state, log):
    attempts: list = []

    def connector(settings):
        attempts.append(settings.host)
        raise ConnectionRefusedError("refused")

    with _ControlHost("A", log) as host_a:
        client = _wire(state, host_a, fault=False)
        state.connection_manager = ConnectionManager(client, state=state, connector=connector).attach()
        assert _err(_legacy(state, "hotpatch.connection.update", {"host": "192.0.2.10"}))["code"] == "invalid_payload"
        assert _err(_legacy(state, "hotpatch.connection.update", {"host": "192.0.2.10", "allow_non_loopback": True}))["code"] == "forbidden"
        assert _err(_legacy(state, "hotpatch.connection.test", {"host": "192.0.2.10", "allow_non_loopback": True}))["code"] == "forbidden"
        assert _err(_legacy(state, "hotpatch.connection.update", {"allow_non_loopback": True}))["code"] == "forbidden"
        assert _err(_legacy(state, "hotpatch.connection.update", {}))["code"] == "invalid_payload"
        assert _err(_legacy(state, "hotpatch.connection.update", {"port": host_a.port}, token=""))["code"] == "forbidden"
        with pytest.raises(CommandError) as info:
            get_controller(state).connection.update(host="example.com")
        assert info.value.code == "invalid_payload"
        assert attempts == []
        # 进程内可以开启, 随后才尝试连接。
        with pytest.raises(CommandError) as info:
            get_controller(state).connection.update(host="192.0.2.10", allow_non_loopback=True)
        assert info.value.code == "connection_failed"
        assert attempts == ["192.0.2.10"]
        assert client.port == host_a.port


def test_desktop_is_read_only(state):
    class FakeDesktop:
        settings = SimpleNamespace(
            broker_url="http://user:pw@127.0.0.1:9/broker?session=abc",
            runtime_identity="rid",
            protocol_version=2,
            session_id="session-123",
            session_token=SECRET_A,
        )

        def status(self):
            return {"transport": "desktop_broker", "status": "connected", "sessionId": "session-123", "runtimeIdentity": "rid"}

    state.bootstrap_transport_mode = "desktop_broker"
    state.bootstrap_runtime_client = cast(Any, FakeDesktop())
    controller = get_controller(state)
    for transport in ("desktop", "inprocess"):
        for name in ("hotpatch.connection.update", "hotpatch.connection.test"):
            envelope = controller.dispatch(name, {"port": 9000}, transport=transport)
            assert _err(envelope)["code"] == "unsupported_transport"
    connection = controller.dispatch("hotpatch.connection.get", {}, transport="desktop")["payload"]
    assert connection["mode"] == "desktop_broker" and connection["settings"]["editable"] is False
    assert connection["status"]["status"] == "connected" and connection["status"]["sessionId"] == "***"
    text = json.dumps(connection)
    assert "session-123" not in text and SECRET_A not in text and "pw@" not in text
    assert status_snapshot(state=state)["connection"]["editable"] is False


def test_services_config_load_and_save_are_forbidden_on_desktop(state, tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    controller = get_controller(state)
    for name, payload in (("services.config.load", {"path": str(path)}), ("services.config.save", {"path": str(tmp_path / "out.json"), "config": {}})):
        assert _err(controller.dispatch(name, payload, transport="desktop"))["code"] == "forbidden"
        assert controller.dispatch(name, payload, transport="legacy", token="tok")["ok"] is True
        assert controller.dispatch(name, payload)["ok"] is True
    capabilities = controller.dispatch("hotpatch.capabilities", {}, transport="desktop")["payload"]
    assert "services.config.load" not in capabilities["commands"] and "services.config.save" not in capabilities["mutating_commands"]
    assert "services.config.apply" in capabilities["commands"]
    load_spec, apply_spec = controller.registry.get("services.config.load"), controller.registry.get("services.config.apply")
    assert load_spec is not None and apply_spec is not None
    assert load_spec.flags()["transports"] == ["inprocess", "legacy"]
    assert apply_spec.flags()["transports"] is None
    with pytest.raises(ValueError):
        CommandSpec(name="demo.bad", handler=lambda ctx, payload: {}, transports=frozenset({"carrier-pigeon"}))


def test_token_is_redacted_in_get_status_events_and_trace(state, log):
    lines: list[str] = []
    state.tracer = HotpatchTracer("conn,control", writer=lines.append)
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        _wire(state, host_a, fault=False)
        controller = get_controller(state)
        controller.connection.test(port=host_b.port, token=SECRET_B)
        controller.connection.update(port=host_b.port, token=SECRET_B)
        with pytest.raises(CommandError):
            controller.connection.update(port=_closed_port(), token="tok-secret-charlie")
        outputs = {
            "get": controller.connection.get(),
            "status": controller.inspect.status(),
            "events": read_events(state=state),
            "trace": "".join(lines),
            "diagnostics": _manager(state).diagnostics,
        }
    text = json.dumps(outputs, default=str)
    for secret in (SECRET_A, SECRET_B, "tok-secret-charlie"):
        assert secret not in text
    assert outputs["get"]["settings"]["token"] == "***"
    assert outputs["status"]["connection"]["token"] == "***" and outputs["status"]["connection"]["editable"] is True
    assert "connection switch" in outputs["trace"] and "connection.changed" in outputs["trace"]


# ---------------------------------------------------------------------------
# 自动重连
# ---------------------------------------------------------------------------


def test_reconnect_after_host_restart_with_injected_sleep(state, log):
    delays: list[float] = []
    restarted: list = []
    host_a = _ControlHost("A", log).__enter__()
    try:
        client = _wire(state, host_a)
        port = host_a.port

        def fake_sleep(delay):
            delays.append(delay)
            if len(delays) == 1:
                # 断开期间的事件尽力丢弃并计数, 不抛出异常。
                assert client.emit_event("progress.update", {"value": 1}) is False
                assert client.emit_event("progress.update", {"value": 2}) is False
            if len(delays) == 2:
                restarted.append(_ControlHost("A2", log, port=port).__enter__())

        settings = RuntimeConnectionSettings.from_transport(client.transport).merged({"reconnect": True, "reconnect_initial": 0.1, "reconnect_max": 0.15})
        manager = ConnectionManager(client, state=state, settings=settings, sleep=fake_sleep).attach()
        state.connection_manager = manager

        host_a.kill()
        assert log.wait(_is("A2", "main", "log.dropped"))
        assert log.wait(_is("A2", "services", "channel.open", token=SECRET_A))
        assert log.wait(_is("A2", "fault", "channel.open", token=SECRET_A))
        dropped = log.find(_is("A2", "main", "log.dropped"))[0][2]
        assert dropped["payload"] == {"count": 2, "reason": "disconnected"}
        assert delays == [0.1, 0.15]

        snapshot = manager.get()
        assert snapshot["state"] == "connected" and snapshot["connected"] is True
        assert snapshot["reconnects"] == 1 and snapshot["dropped_events"] == 2 and snapshot["reconnect_attempts"] == 3
        assert client.emit_event("progress.update", {"value": 3}) is True
        assert log.wait(_is("A2", "main", "progress.update"))
        restarted[0].send({"id": "r1", "type": "hotpatch.patches.list", "payload": {}})
        assert log.wait(_is("A2", "services", id="r1", ok=True))
        statuses = [event["payload"]["status"] for event in read_events(state=state)["events"] if event["type"] == "connection.changed"]
        assert statuses == ["disconnected", "reconnected"]
    finally:
        host_a.kill()
        for host in restarted:
            host.kill()


def test_reconnect_is_off_by_default_and_close_stops_the_loop(state, log):
    with _ControlHost("A", log) as host_a:
        client = _wire(state, host_a, fault=False)
        manager = _manager(state)
        assert manager.settings.reconnect is False
        assert client.report_connection_lost("gone") is False
        assert manager.get()["state"] == "connected"

    gate = threading.Event()
    sleeps: list[float] = []

    def blocking_sleep(delay):
        sleeps.append(delay)
        gate.wait(WAIT)

    with _ControlHost("B", log) as host_b:
        other = HotpatcherState()
        client_b = RuntimeClient.connect(host_b.host, host_b.port, timeout=2)
        other.bootstrap_runtime_client = client_b
        settings = RuntimeConnectionSettings.from_transport(client_b.transport).merged({"reconnect": True, "port": _closed_port()})
        manager_b = ConnectionManager(client_b, state=other, settings=settings, sleep=blocking_sleep).attach()
        assert client_b.report_connection_lost("gone") is True
        assert manager_b.get()["state"] == "reconnecting"
        thread = manager_b._reconnect_thread
        assert thread is not None
        gate.set()
        manager_b.close()
        thread.join(WAIT)
        assert not thread.is_alive()
        assert client_b.connection_listener is None
        with pytest.raises(RuntimeError):
            manager_b.update({"port": host_b.port})
        assert isinstance(ConnectionFailedError("x"), RuntimeError)


def test_reconnect_clears_a_stale_pending_switch_instead_of_spinning(state, log):
    now = [100.0]
    delays: list[float] = []
    with _ControlHost("A", log) as host_a, _ControlHost("B", log) as host_b:
        client = _wire(state, host_a, fault=False)

        def fake_sleep(delay):
            delays.append(delay)
            if len(delays) == 1:
                now[0] += PENDING_SWITCH_TIMEOUT + 1

        settings = RuntimeConnectionSettings.from_transport(client.transport).merged({"reconnect": True})
        manager = ConnectionManager(client, state=state, settings=settings, sleep=fake_sleep, clock=lambda: now[0]).attach()
        state.connection_manager = manager
        dropped: list = []
        # 响应写出失败: 切换回调被丢弃, 忙标记残留。
        assert manager.update({"port": host_b.port}, defer=dropped.append)["status"] == "scheduled"
        old_channel = state.bootstrap_service_control_channel
        assert client.report_connection_lost("gone", origin=old_channel) is True
        assert log.wait(_is("A", "services", "channel.open"), timeout=WAIT)
        thread = manager._reconnect_thread
        assert thread is not None
        thread.join(WAIT)
        assert not thread.is_alive()
        snapshot = manager.get()
        assert snapshot["state"] == "connected" and snapshot["reconnects"] == 1 and snapshot["pending_switch"] is False
        assert delays == [0.1]
        assert len(log.find(_is("A", "services", "channel.open"))) == 2
        assert log.wait(_is("B", "main", "<eof>"))
        assert client.port == host_a.port and not client.transport.closed
        assert dropped[0]() == {"status": "discarded"}
