import json
import http.server
import threading
import time
import types

import pytest

from sd_webui_all_in_one_hotpatcher import bootstrap
from sd_webui_all_in_one_hotpatcher.runtime import browser
from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import (
    BROKER_URL_ENV,
    MAX_EVENT_PAYLOAD_BYTES,
    PROTOCOL_VERSION_ENV,
    RUNTIME_IDENTITY_ENV,
    SESSION_ID_ENV,
    SESSION_TOKEN_ENV,
    DesktopBrokerClient,
    DesktopBrokerConfigurationError,
    DesktopBrokerHttpError,
    DesktopBrokerProtocolError,
    DesktopBrokerSettings,
    DesktopTransportStatus,
)
from sd_webui_all_in_one_hotpatcher.runtime.transport_mode import TRANSPORT_MODE_ENV
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState


def _desktop_env(**updates):
    values = {
        TRANSPORT_MODE_ENV: "desktop_broker",
        BROKER_URL_ENV: "http://127.0.0.1:43123",
        SESSION_ID_ENV: "session-1",
        SESSION_TOKEN_ENV: "unpredictable-token",
        RUNTIME_IDENTITY_ENV: "runtime-1",
        PROTOCOL_VERSION_ENV: "1",
    }
    values.update(updates)
    return values


class ScriptedRequester:
    def __init__(self, scripts=None):
        self.scripts = {path: list(items) for path, items in (scripts or {}).items()}
        self.calls = []

    def request(self, method, path, *, body=None, query=None, timeout):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "body": body,
                "query": query,
                "timeout": timeout,
            }
        )
        items = self.scripts.setdefault(path, [])
        if items:
            value = items.pop(0)
            if isinstance(value, BaseException):
                raise value
            if callable(value):
                return value(self.calls[-1])
            return value
        if path == "/v1/runtime/connect":
            return {"status": "connected", "acknowledgedSequence": 0}
        if path == "/v1/runtime/events":
            events = body["events"]
            return {"acknowledgedSequence": events[-1]["sequence"]}
        if path == "/v1/runtime/commands":
            return {"commands": []}
        if path == "/v1/runtime/results":
            return {"acceptedCommandIds": [item["commandId"] for item in body["results"]]}
        return {}


def _client(requester=None, **kwargs):
    return DesktopBrokerClient(
        DesktopBrokerSettings.from_env(_desktop_env()),
        requester=requester or ScriptedRequester(),
        **kwargs,
    )


class _ProtocolHandler(http.server.BaseHTTPRequestHandler):
    requests = []

    def _respond(self, payload):
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _record(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length)) if length else None
        self.requests.append((self.command, self.path, dict(self.headers), body))
        return body

    def do_POST(self):
        body = self._record()
        if self.path == "/v1/runtime/connect":
            self._respond({"status": "connected", "acknowledgedSequence": 0})
        elif self.path == "/v1/runtime/events":
            self._respond({"acknowledgedSequence": body["events"][-1]["sequence"]})
        else:
            self._respond({})

    def do_GET(self):
        self._record()
        self._respond({"commands": []})

    def log_message(self, _format, *_args):
        return


class _RedirectTargetHandler(http.server.BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        self.requests.append((self.path, dict(self.headers)))
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, _format, *_args):
        return


class _RedirectingBrokerHandler(http.server.BaseHTTPRequestHandler):
    requests = []
    location = ""

    def do_POST(self):
        self.requests.append((self.path, dict(self.headers)))
        self.send_response(302)
        self.send_header("Location", self.location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, _format, *_args):
        return


def test_standard_library_http_uses_exact_protocol_and_ignores_proxy(monkeypatch):
    _ProtocolHandler.requests = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ProtocolHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    try:
        env = _desktop_env(**{BROKER_URL_ENV: f"http://127.0.0.1:{server.server_port}"})
        client = DesktopBrokerClient(DesktopBrokerSettings.from_env(env), wall_time=lambda: 100.0)
        client.emit_event("browser.open", {"url": "http://localhost:8188"})
        client._run_cycle()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert [item[1].split("?", 1)[0] for item in _ProtocolHandler.requests] == [
        "/v1/runtime/connect",
        "/v1/runtime/events",
        "/v1/runtime/heartbeat",
        "/v1/runtime/commands",
    ]
    for _method, _path, headers, _body in _ProtocolHandler.requests:
        assert headers["Authorization"] == "Bearer unpredictable-token"
        assert headers["X-Runtime-Protocol-Version"] == "1"
        assert headers["X-Runtime-Session-Id"] == "session-1"
        assert headers["X-Runtime-Identity"] == "runtime-1"
    event_body = _ProtocolHandler.requests[1][3]
    assert event_body["events"] == [
        {
            "sequence": 1,
            "eventType": "browser.open",
            "payload": {"url": "http://localhost:8188"},
            "createdAt": 100.0,
        }
    ]


def test_standard_library_http_rejects_redirect_without_forwarding_credentials():
    _RedirectTargetHandler.requests = []
    _RedirectingBrokerHandler.requests = []
    target = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RedirectTargetHandler)
    redirecting_broker = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RedirectingBrokerHandler)
    _RedirectingBrokerHandler.location = f"http://127.0.0.1:{target.server_port}/credential-target"
    target_thread = threading.Thread(target=target.serve_forever, daemon=True)
    broker_thread = threading.Thread(target=redirecting_broker.serve_forever, daemon=True)
    target_thread.start()
    broker_thread.start()
    try:
        env = _desktop_env(**{BROKER_URL_ENV: f"http://127.0.0.1:{redirecting_broker.server_port}"})
        client = DesktopBrokerClient(DesktopBrokerSettings.from_env(env))
        with pytest.raises(DesktopBrokerHttpError) as error:
            client._run_cycle()
    finally:
        redirecting_broker.shutdown()
        target.shutdown()
        redirecting_broker.server_close()
        target.server_close()
        broker_thread.join(timeout=2)
        target_thread.join(timeout=2)

    assert error.value.code == "redirect_rejected"
    assert error.value.retryable is False
    assert str(error.value) == "runtime broker redirects are not permitted by protocol version 1"
    assert len(_RedirectingBrokerHandler.requests) == 1
    assert _RedirectingBrokerHandler.requests[0][1]["Authorization"] == "Bearer unpredictable-token"
    assert _RedirectTargetHandler.requests == []


def test_desktop_settings_require_exact_loopback_session_environment():
    settings = DesktopBrokerSettings.from_env(_desktop_env())
    assert settings.broker_url == "http://127.0.0.1:43123"
    assert settings.headers() == {
        "Authorization": "Bearer unpredictable-token",
        "X-Runtime-Protocol-Version": "1",
        "X-Runtime-Session-Id": "session-1",
        "X-Runtime-Identity": "runtime-1",
    }

    for invalid_url in (
        "https://127.0.0.1:43123",
        "http://example.com:43123",
        "http://localhost:43123",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://user@127.0.0.1:43123",
        "http://127.0.0.1:43123/path",
    ):
        with pytest.raises(DesktopBrokerConfigurationError, match="HTTP loopback origin"):
            DesktopBrokerSettings.from_env(_desktop_env(**{BROKER_URL_ENV: invalid_url}))

    with pytest.raises(DesktopBrokerConfigurationError) as missing:
        DesktopBrokerSettings.from_env(_desktop_env(**{SESSION_TOKEN_ENV: ""}))
    assert SESSION_TOKEN_ENV in str(missing.value)
    with pytest.raises(DesktopBrokerConfigurationError, match="supported value: 1"):
        DesktopBrokerSettings.from_env(_desktop_env(**{PROTOCOL_VERSION_ENV: "2"}))


def test_emit_is_nonblocking_bounded_and_does_not_create_sequence_gaps():
    requester = ScriptedRequester()
    client = _client(requester, event_capacity=2, wall_time=lambda: 123.5)

    assert client.emit_event("browser.open", {"url": "http://localhost:1"}) is True
    assert client.emit_event("log.record", {"message": "second"}) is True
    assert client.emit_event("browser.open", {"url": "http://localhost:3"}) is False
    assert requester.calls == []
    status = client.status()
    assert status["queuedEventCount"] == 2
    assert status["diagnostics"][-1]["code"] == "queue_overflow"

    client._connect()
    client._upload_events()
    event_call = next(call for call in requester.calls if call["path"] == "/v1/runtime/events")
    assert [item["sequence"] for item in event_call["body"]["events"]] == [1, 2]
    assert all(item["createdAt"] == 123.5 for item in event_call["body"]["events"])

    assert client.emit_event("browser.open", {"url": "http://localhost:4"}) is True
    client._upload_events()
    assert requester.calls[-1]["body"]["events"][0]["sequence"] == 3


def test_event_validation_is_bounded_and_diagnostic():
    client = _client()
    assert client.emit_event("browser.open", {"text": "x" * (MAX_EVENT_PAYLOAD_BYTES + 1)}) is False
    assert client.emit_event("browser.open", {"bad": object()}) is False
    assert client.emit_event("browser.open", []) is False
    assert [item["code"] for item in client.status()["diagnostics"]] == [
        "event_rejected",
        "event_rejected",
        "event_rejected",
    ]


def test_desktop_maps_existing_producer_families_without_mutating_payloads():
    requester = ScriptedRequester()
    client = _client(requester, wall_time=lambda: 100.0)
    payloads = [
        {"message": "hello"},
        {"message": "failed"},
        {"id": 1, "value": 2},
        {"value": "future"},
    ]
    for event_type, payload in zip(
        ("log.record", "error.exception", "progress.update", "audit.event"),
        payloads,
        strict=True,
    ):
        assert client.emit_event(event_type, payload)
    assert all("sourceEventType" not in payload for payload in payloads)

    client._connect()
    client._upload_events()
    events = requester.calls[-1]["body"]["events"]
    assert [event["eventType"] for event in events] == [
        "runtime.log",
        "runtime.error",
        "runtime.progress",
        "audit.event",
    ]
    assert [event["payload"].get("sourceEventType") for event in events] == [
        "log.record",
        "error.exception",
        "progress.update",
        None,
    ]


def test_unacknowledged_events_retry_with_the_same_sequences_after_reconnect():
    requester = ScriptedRequester(
        {
            "/v1/runtime/connect": [
                {"status": "connected", "acknowledgedSequence": 0},
                {"status": "reconnecting", "acknowledgedSequence": 0},
            ],
            "/v1/runtime/events": [
                DesktopBrokerHttpError("connection_failed", "temporary outage"),
                {"acknowledgedSequence": 1},
                {"acknowledgedSequence": 2},
            ],
        }
    )
    client = _client(requester)
    client.emit_event("browser.open", {"url": "http://localhost:1"})
    client.emit_event("browser.open", {"url": "http://localhost:2"})
    client._connect()

    with pytest.raises(DesktopBrokerHttpError):
        client._upload_events()
    client._handle_transport_failure("connection_failed", "temporary outage", retryable=True)
    assert client.status()["status"] == DesktopTransportStatus.RECONNECTING.value
    assert client.status()["queuedEventCount"] == 2

    client._connect()
    client._upload_events()
    assert client.status()["acknowledgedSequence"] == 1
    assert client.status()["queuedEventCount"] == 1
    client._upload_events()
    assert client.status()["acknowledgedSequence"] == 2
    event_calls = [call for call in requester.calls if call["path"] == "/v1/runtime/events"]
    assert [item["sequence"] for item in event_calls[0]["body"]["events"]] == [1, 2]
    assert [item["sequence"] for item in event_calls[1]["body"]["events"]] == [1, 2]
    assert [item["sequence"] for item in event_calls[2]["body"]["events"]] == [2]


def test_heartbeat_reports_bounded_local_diagnostics():
    requester = ScriptedRequester()
    client = _client(requester, event_capacity=1, monotonic=lambda: 10.0, wall_time=lambda: 20.0)
    client.emit_event("first", {})
    client.emit_event("overflow", {})
    client._connect()
    client._heartbeat()

    heartbeat = next(call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat")
    assert heartbeat["body"]["lastAcknowledgedSequence"] == 0
    assert heartbeat["body"]["queuedEventCount"] == 1
    assert heartbeat["body"]["diagnostics"][-1]["code"] == "queue_overflow"
    assert len(heartbeat["body"]["diagnostics"]) <= 8


def test_heartbeat_and_command_poll_recover_after_transient_failure():
    requester = ScriptedRequester(
        {
            "/v1/runtime/connect": [
                {"status": "connected", "acknowledgedSequence": 0},
                {"status": "reconnecting", "acknowledgedSequence": 0},
            ],
            "/v1/runtime/commands": [
                DesktopBrokerHttpError("connection_failed", "poll outage"),
                {"commands": []},
            ],
        }
    )
    client = _client(requester)
    client._connect()
    client._heartbeat()
    with pytest.raises(DesktopBrokerHttpError) as error:
        client._poll_commands()
    client._handle_transport_failure(error.value.code, str(error.value), retryable=True)
    assert client.status()["status"] == "reconnecting"

    client._connect()
    client._heartbeat()
    client._poll_commands()
    assert client.status()["status"] == "connected"
    assert client.status()["lastHeartbeatAt"] is not None


def test_commands_are_idempotent_and_results_are_acknowledged_once():
    command = {
        "commandId": "command-1",
        "sequence": 1,
        "commandType": "config.apply",
        "payload": {"config": {"runtime": {}}},
        "createdAt": 100.0,
        "deadline": 200.0,
    }
    requester = ScriptedRequester(
        {
            "/v1/runtime/commands": [
                {"commands": [command]},
                {"commands": [command]},
            ],
            "/v1/runtime/results": [
                {"acceptedCommandIds": ["command-1"]},
                {"acceptedCommandIds": ["command-1"]},
            ],
        }
    )
    handled = []
    client = _client(
        requester,
        command_handler=lambda kind, payload: handled.append((kind, payload)) or {"applied": True},
        wall_time=lambda: 150.0,
    )
    client._connect()
    client._poll_commands()
    client._upload_results()
    client._poll_commands()
    client._upload_results()

    assert handled == [("config.apply", {"config": {"runtime": {}}})]
    result_calls = [call for call in requester.calls if call["path"] == "/v1/runtime/results"]
    assert len(result_calls) == 2
    result = result_calls[0]["body"]["results"][0]
    assert result == {
        "commandId": "command-1",
        "ok": True,
        "payload": {"applied": True},
        "completedAt": 150.0,
    }
    assert client.status()["queuedResultCount"] == 0


def test_unknown_command_returns_deterministic_typed_error(monkeypatch):
    state = HotpatcherState()
    client = _client(command_handler=lambda kind, payload: bootstrap._handle_desktop_command(kind, payload, state=state))
    client._accept_command(
        {
            "commandId": "unknown-1",
            "sequence": 1,
            "commandType": "file.delete",
            "payload": {},
            "createdAt": 100.0,
            "deadline": 9_999_999_999.0,
        }
    )
    result = client._results[0]
    assert result["ok"] is False
    assert result["error"] == {
        "code": "unknown_command",
        "message": "unsupported desktop broker command: file.delete",
    }


def test_expired_command_is_not_executed_and_skipped_sequences_are_supported():
    handled = []
    client = _client(
        command_handler=lambda kind, payload: handled.append((kind, payload)) or {},
        wall_time=lambda: 50.0,
    )
    client._accept_command(
        {
            "commandId": "expired-1",
            "sequence": 1,
            "commandType": "config.apply",
            "payload": {"config": {}},
            "createdAt": 10.0,
            "deadline": 20.0,
        }
    )
    assert handled == []
    assert client._results[0]["error"]["code"] == "command_expired"

    client._accept_command(
        {
            "commandId": "after-expired-3",
            "sequence": 3,
            "commandType": "config.apply",
            "payload": {"config": {}},
            "createdAt": 30.0,
            "deadline": 60.0,
        }
    )
    assert handled == [("config.apply", {"config": {}})]

    with pytest.raises(DesktopBrokerProtocolError, match="must advance beyond 3, received 2"):
        client._accept_command(
            {
                "commandId": "stale-2",
                "sequence": 2,
                "commandType": "config.apply",
                "payload": {"config": {}},
                "createdAt": 30.0,
                "deadline": 60.0,
            }
        )


def test_authentication_rejection_is_degraded_without_transport_fallback():
    requester = ScriptedRequester(
        {
            "/v1/runtime/connect": [
                DesktopBrokerHttpError(
                    "authentication_rejected",
                    "rejected session credential",
                    retryable=False,
                )
            ]
        }
    )
    client = _client(requester)
    with pytest.raises(DesktopBrokerHttpError) as error:
        client._run_cycle()
    client._handle_transport_failure(error.value.code, str(error.value), retryable=error.value.retryable)

    status = client.status()
    assert status["transport"] == "desktop_broker"
    assert status["status"] == "degraded"
    assert status["diagnostics"][-1]["code"] == "authentication_rejected"
    assert all(call["path"].startswith("/v1/runtime/") for call in requester.calls)


def test_config_apply_command_uses_existing_service_with_selected_sink(monkeypatch):
    from sd_webui_all_in_one_hotpatcher import services

    state = HotpatcherState()
    sink = object()
    state.bootstrap_runtime_client = sink
    calls = []
    monkeypatch.setattr(
        services,
        "apply_config",
        lambda config, *, runtime_client, state: calls.append((config, runtime_client, state)) or {"applied": ["runtime.browser"], "warnings": [], "errors": []},
    )

    response = bootstrap._handle_desktop_command(
        "config.apply",
        {"config": {"runtime": {"browser": {"enabled": True, "mode": "host"}}}},
        state=state,
    )
    assert response["applyResult"]["applied"] == ["runtime.browser"]
    assert calls[0][1] is sink
    assert calls[0][2] is state


def test_browser_host_mode_suppresses_locally_without_network(monkeypatch):
    registered = {}
    state = HotpatcherState()
    sink = types.SimpleNamespace(emit_event=lambda *_args, **_kwargs: False)
    monkeypatch.setattr(browser, "install_import_hook", lambda **_kwargs: None)
    monkeypatch.setattr(
        browser,
        "register_hook",
        lambda module, function, hook, **_kwargs: registered.update(hook=hook),
    )
    monkeypatch.delitem(__import__("sys").modules, "webbrowser", raising=False)
    browser.patch_webbrowser(sink, mode="host", state=state)
    original_calls = []

    def original(*_args, **_kwargs):
        original_calls.append(True)
        return False

    wrapped = registered["hook"](original, types.SimpleNamespace())

    started = time.monotonic()
    assert wrapped("http://localhost:8188") is True
    assert time.monotonic() - started < 0.05
    assert original_calls == []


def test_explicit_desktop_bootstrap_never_initializes_legacy(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import client as legacy_client
    from sd_webui_all_in_one_hotpatcher.runtime import desktop_broker

    class FakeDesktopClient:
        def __init__(self):
            self.started = False

        def start(self):
            self.started = True
            return self

        def status(self):
            return {"transport": "desktop_broker", "status": "starting"}

        def emit_event(self, *_args, **_kwargs):
            return True

    fake = FakeDesktopClient()
    monkeypatch.setattr(
        desktop_broker.DesktopBrokerClient,
        "from_env",
        lambda **_kwargs: fake,
    )
    monkeypatch.setattr(
        legacy_client.RuntimeClient,
        "connect_from_env",
        lambda **_kwargs: pytest.fail("desktop mode must not initialize legacy transport"),
    )
    for name, value in _desktop_env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        json.dumps({"services": {"apply_on_bootstrap": False}}),
    )

    result = bootstrap.configure_from_env(state=HotpatcherState())
    assert result.transport_mode == "desktop_broker"
    assert result.runtime_client is fake
    assert fake.started is True
    assert result.service_control_channel is None


def test_explicit_legacy_bootstrap_uses_existing_runtime_client(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import client as legacy_client

    fake = types.SimpleNamespace(status=lambda: {"transport": "legacy", "status": "connected"})
    calls = []
    monkeypatch.setattr(
        legacy_client.RuntimeClient,
        "connect_from_env",
        lambda **kwargs: calls.append(kwargs) or fake,
    )
    monkeypatch.setenv(TRANSPORT_MODE_ENV, "legacy")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        json.dumps({"services": {"apply_on_bootstrap": False}}),
    )

    result = bootstrap.configure_from_env(state=HotpatcherState())
    assert calls == [{"required": False}]
    assert result.transport_mode == "legacy"
    assert result.runtime_client is fake


def test_desktop_initialization_failure_still_allows_local_suppression(monkeypatch):
    calls = []
    monkeypatch.setenv(TRANSPORT_MODE_ENV, "desktop_broker")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        json.dumps(
            {
                "services": {"apply_on_bootstrap": False},
                "runtime": {"browser": {"enabled": True, "mode": "host"}},
            }
        ),
    )
    for name in (BROKER_URL_ENV, SESSION_ID_ENV, SESSION_TOKEN_ENV, RUNTIME_IDENTITY_ENV, PROTOCOL_VERSION_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        browser,
        "patch_webbrowser",
        lambda sink, *, mode, state: calls.append((sink, mode, state)),
    )

    result = bootstrap.configure_from_env(state=HotpatcherState())
    assert result.transport_mode == "desktop_broker"
    assert result.runtime_client is None
    assert result.transport_diagnostics
    assert "desktop_broker initialization failed" in result.transport_diagnostics[0]
    assert calls and calls[0][0] is None and calls[0][1] == "host"


def test_close_final_flush_wait_is_bounded_even_when_http_is_stuck():
    entered = threading.Event()
    release = threading.Event()

    class BlockingRequester(ScriptedRequester):
        def request(self, method, path, *, body=None, query=None, timeout):
            entered.set()
            release.wait(timeout=1)
            raise DesktopBrokerHttpError("connection_failed", "blocked")

    client = _client(BlockingRequester(), final_flush_seconds=0.02)
    client.emit_event("browser.open", {"url": "http://localhost:1"})
    client.start()
    assert entered.wait(timeout=1)
    started = time.monotonic()
    client.close()
    elapsed = time.monotonic() - started
    release.set()
    assert elapsed < 0.15
    assert client.status()["status"] == "closed"
    assert client.status()["diagnostics"][-1]["code"] == "final_flush_incomplete"
