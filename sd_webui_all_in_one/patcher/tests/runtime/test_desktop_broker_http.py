"""桌面端代理 HTTP 传输与配置测试"""

import http.server
import json
import threading

import pytest
from desktop_broker_test_helpers import ScriptedRequester, make_client, make_desktop_env

from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import (
    BROKER_URL_ENV,
    PROTOCOL_VERSION_ENV,
    SESSION_TOKEN_ENV,
    DesktopBrokerClient,
    DesktopBrokerConfigurationError,
    DesktopBrokerHttpError,
    DesktopBrokerSettings,
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
            self._respond(
                {
                    "status": "connected",
                    "acknowledgedSequence": 0,
                    "acknowledgedDiagnosticSequence": 0,
                }
            )
        elif self.path == "/v1/runtime/events":
            self._respond({"acknowledgedSequence": body["events"][-1]["sequence"]})
        elif self.path == "/v1/runtime/heartbeat":
            acknowledged_diagnostic_sequence = body["diagnostics"][-1]["sequence"] if body["diagnostics"] else 0
            self._respond(
                {
                    "status": "connected",
                    "acknowledgedSequence": body["lastAcknowledgedSequence"],
                    "acknowledgedDiagnosticSequence": acknowledged_diagnostic_sequence,
                }
            )
        else:
            self._respond({})

    def do_GET(self):
        self._record()
        self._respond({"commands": []})

    def log_message(self, format, *args):
        del format, args


class _RedirectTargetHandler(http.server.BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        self.requests.append((self.path, dict(self.headers)))
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format, *args):
        del format, args


class _RedirectingBrokerHandler(http.server.BaseHTTPRequestHandler):
    requests = []
    location = ""

    def do_POST(self):
        self.requests.append((self.path, dict(self.headers)))
        self.send_response(302)
        self.send_header("Location", self.location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        del format, args


def test_standard_library_http_uses_exact_protocol_and_ignores_proxy(monkeypatch):
    _ProtocolHandler.requests = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ProtocolHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    try:
        env = make_desktop_env(**{BROKER_URL_ENV: f"http://127.0.0.1:{server.server_port}"})
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
        assert headers["X-Runtime-Protocol-Version"] == "2"
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
        env = make_desktop_env(**{BROKER_URL_ENV: f"http://127.0.0.1:{redirecting_broker.server_port}"})
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
    assert str(error.value) == "runtime broker redirects are not permitted by protocol version 2"
    assert len(_RedirectingBrokerHandler.requests) == 1
    assert _RedirectingBrokerHandler.requests[0][1]["Authorization"] == "Bearer unpredictable-token"
    assert _RedirectTargetHandler.requests == []


def test_desktop_settings_require_exact_loopback_session_environment():
    settings = DesktopBrokerSettings.from_env(make_desktop_env())
    assert settings.broker_url == "http://127.0.0.1:43123"
    assert settings.headers() == {
        "Authorization": "Bearer unpredictable-token",
        "X-Runtime-Protocol-Version": "2",
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
            DesktopBrokerSettings.from_env(make_desktop_env(**{BROKER_URL_ENV: invalid_url}))

    with pytest.raises(DesktopBrokerConfigurationError) as missing:
        DesktopBrokerSettings.from_env(make_desktop_env(**{SESSION_TOKEN_ENV: ""}))
    assert SESSION_TOKEN_ENV in str(missing.value)
    with pytest.raises(DesktopBrokerConfigurationError, match="supported value: 2"):
        DesktopBrokerSettings.from_env(make_desktop_env(**{PROTOCOL_VERSION_ENV: "3"}))


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
    client = make_client(requester)
    with pytest.raises(DesktopBrokerHttpError) as error:
        client._run_cycle()
    client._handle_transport_failure(error.value.code, str(error.value), retryable=error.value.retryable)

    status = client.status()
    assert status["transport"] == "desktop_broker"
    assert status["status"] == "degraded"
    assert status["activeDiagnostic"]["code"] == "authentication_rejected"
    assert status["unacknowledgedDiagnostics"][-1]["code"] == "authentication_rejected"
    assert all(call["path"].startswith("/v1/runtime/") for call in requester.calls)


def test_close_final_flush_wait_is_bounded_even_when_http_is_stuck():
    entered = threading.Event()
    release = threading.Event()
    close_completed = threading.Event()

    class BlockingRequester(ScriptedRequester):
        def request(self, method, path, *, body=None, query=None, timeout):
            entered.set()
            release.wait()
            raise DesktopBrokerHttpError("connection_failed", "blocked")

    client = make_client(BlockingRequester(), final_flush_seconds=0.02)
    client.emit_event("browser.open", {"url": "http://localhost:1"})
    client.start()
    assert entered.wait(timeout=1)

    def close_client():
        client.close()
        close_completed.set()

    closer = threading.Thread(target=close_client, daemon=True)
    closer.start()
    try:
        # HTTP 替身不会自行返回，因此这里成功只能说明 close() 遵守了自己的
        # 最终刷新截止时间，而不是等待网络调用结束。宽松看门狗避免把共享 CI
        # runner 的线程调度延迟误判成产品回归。
        assert close_completed.wait(timeout=1)
    finally:
        release.set()
        closer.join(timeout=1)
        if client._thread is not None:
            client._thread.join(timeout=1)

    assert not closer.is_alive()
    assert client._thread is not None and not client._thread.is_alive()
    assert client.status()["status"] == "closed"
    assert client.status()["unacknowledgedDiagnostics"][-1]["code"] == "final_flush_incomplete"
