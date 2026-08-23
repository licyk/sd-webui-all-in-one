import errno
import json
import logging
import socket
import threading
import time
from types import SimpleNamespace
from typing import cast

import pytest

from sd_webui_all_in_one_hotpatcher.runtime import client as runtime_client_module
from sd_webui_all_in_one_hotpatcher.runtime import transport as transport_module
from sd_webui_all_in_one_hotpatcher.runtime.client import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.protocol import RuntimeProtocolError, encode_message
from sd_webui_all_in_one_hotpatcher.runtime.transport import JsonlTcpTransport
from sd_webui_all_in_one_hotpatcher.services import PatchService, ServiceControlChannel


class _ScriptedReader:
    def __init__(self, items=(), *, close_error=None):
        self.items = list(items)
        self.close_error = close_error
        self.close_calls = 0
        self.closed = False

    def readline(self):
        if not self.items:
            return b""
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def close(self):
        self.close_calls += 1
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class _FakeSocket:
    def __init__(
        self,
        reader,
        *,
        timeout=5.0,
        fail_send_calls=(),
        send_errors=None,
        shutdown_error=None,
        close_error=None,
    ):
        self.reader = reader
        self.timeout = timeout
        self.timeout_history = []
        self.fail_send_calls = set(fail_send_calls)
        self.send_errors = dict(send_errors or {})
        self.shutdown_error = shutdown_error
        self.close_error = close_error
        self.send_attempts = []
        self.makefile_timeouts = []
        self.shutdown_calls = 0
        self.close_calls = 0
        self.closed = False
        self.send_timeouts = []

    def settimeout(self, value):
        self.timeout = value
        self.timeout_history.append(value)

    def gettimeout(self):
        return self.timeout

    def makefile(self, mode):
        assert mode == "rb"
        self.makefile_timeouts.append(self.timeout)
        return self.reader

    def sendall(self, data):
        self.send_attempts.append(data)
        self.send_timeouts.append(self.timeout)
        error = self.send_errors.get(len(self.send_attempts))
        if error is not None:
            raise error
        if len(self.send_attempts) in self.fail_send_calls:
            raise BrokenPipeError("scripted send failure")

    def shutdown(self, how):
        assert how == socket.SHUT_RDWR
        self.shutdown_calls += 1
        if self.shutdown_error is not None:
            raise self.shutdown_error

    def close(self):
        self.close_calls += 1
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class _ResponseReader(_ScriptedReader):
    def __init__(self, sock):
        super().__init__()
        self.sock = sock

    def readline(self):
        request = json.loads(self.sock.send_attempts[-1])
        return encode_message({"id": request["id"], "ok": True, "payload": {"value": 7}})


class _StaticService:
    def handle_request_json(self, request, *, runtime_client):
        return {"ok": True, "payload": {"type": request["type"]}}


class _FailingService:
    def handle_request_json(self, request, *, runtime_client):
        raise ValueError("scripted handler failure")


def _wait_for_thread(channel):
    channel.thread.join(timeout=2)
    assert not channel.thread.is_alive()


class _FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_jsonl_connect_separates_connect_and_operation_timeouts(monkeypatch):
    reader = _ScriptedReader()
    sock = _FakeSocket(reader, timeout=0.05)
    observed = {}

    def create_connection(address, *, timeout):
        observed.update(address=address, timeout=timeout)
        return sock

    monkeypatch.setattr(socket, "create_connection", create_connection)

    transport = JsonlTcpTransport.connect(
        "127.0.0.1",
        8123,
        timeout=0.5,
        connect_timeout=0.05,
        default_request_timeout=0.1,
        event_write_timeout=0.2,
    )
    try:
        assert observed == {"address": ("127.0.0.1", 8123), "timeout": 0.05}
        assert transport.connect_timeout == 0.05
        assert transport.default_request_timeout == 0.1
        assert transport.event_write_timeout == 0.2
        assert sock.timeout_history == [None, 0.2, None]
        assert sock.makefile_timeouts == [None]
        assert sock.send_timeouts == [0.2]
        assert sock.gettimeout() is None
    finally:
        transport.close()


def test_compatibility_timeout_seeds_all_operation_policies(monkeypatch):
    reader = _ScriptedReader()
    sock = _FakeSocket(reader, timeout=0.07)
    monkeypatch.setattr(socket, "create_connection", lambda address, *, timeout: sock)

    transport = JsonlTcpTransport.connect("127.0.0.1", 8123, timeout=0.07)
    try:
        assert transport.connect_timeout == 0.07
        assert transport.default_request_timeout == 0.07
        assert transport.event_write_timeout == 0.07
        assert sock.send_timeouts == [0.07]
        assert sock.gettimeout() is None
    finally:
        transport.close()


def test_connect_from_env_allows_each_compatibility_timeout_to_be_overridden(monkeypatch):
    observed = {}
    sentinel = object()

    def connect(cls, host, port, **kwargs):
        observed.update(host=host, port=port, **kwargs)
        return sentinel

    monkeypatch.setattr(RuntimeClient, "connect", classmethod(connect))
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", "127.0.0.1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", "8123")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN", "secret")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT", "0.5")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONNECT_TIMEOUT", "0.1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REQUEST_TIMEOUT", "0.2")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_EVENT_WRITE_TIMEOUT", "0.3")

    assert RuntimeClient.connect_from_env(required=True) is sentinel
    assert observed == {
        "host": "127.0.0.1",
        "port": 8123,
        "token": "secret",
        "timeout": 0.5,
        "connect_timeout": 0.1,
        "default_request_timeout": 0.2,
        "event_write_timeout": 0.3,
    }


def test_request_without_explicit_timeout_uses_finite_default_and_restores_blocking(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)
    sock = _FakeSocket(None, timeout=None)
    reader = _ResponseReader(sock)
    sock.reader = reader
    transport = JsonlTcpTransport(
        sock,
        host="127.0.0.1",
        port=8123,
        default_request_timeout=0.2,
    )

    assert transport.request("echo") == {"value": 7}
    assert sock.send_timeouts == [0.2]
    assert sock.timeout_history == [0.2, 0.2, None]
    assert sock.gettimeout() is None
    assert transport.closed is False
    transport.close()


def test_explicit_request_timeout_overrides_default_for_one_operation(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)
    sock = _FakeSocket(None, timeout=None)
    sock.reader = _ResponseReader(sock)
    transport = JsonlTcpTransport(
        sock,
        host="127.0.0.1",
        port=8123,
        default_request_timeout=0.2,
    )

    assert transport.request("explicit", timeout=0.03) == {"value": 7}
    assert transport.request("default") == {"value": 7}
    assert sock.send_timeouts == [0.03, 0.2]
    assert transport.default_request_timeout == 0.2
    assert sock.gettimeout() is None
    transport.close()


def test_request_protocol_error_restores_timeout_without_invalidating_reader(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)
    reader = _ScriptedReader([b'{"id":"wrong","ok":true,"payload":{}}\n', b"not-json\n"])
    sock = _FakeSocket(reader, timeout=None)
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    with pytest.raises(RuntimeProtocolError):
        transport.request("echo", timeout=0.05)

    assert sock.timeout_history == [0.05, 0.05, 0.05, None]
    assert transport.closed is False
    assert reader.close_calls == 0
    transport.close()


def test_concurrent_event_waits_for_request_timeout_scope():
    request_reading = threading.Event()
    release_response = threading.Event()

    class BlockingResponseReader(_ScriptedReader):
        def __init__(self, sock):
            super().__init__()
            self.sock = sock

        def readline(self):
            request_reading.set()
            assert release_response.wait(timeout=1)
            request = json.loads(self.sock.send_attempts[0])
            return encode_message({"id": request["id"], "ok": True, "payload": {}})

    sock = _FakeSocket(None, timeout=None)
    reader = BlockingResponseReader(sock)
    sock.reader = reader
    transport = JsonlTcpTransport(
        sock,
        host="127.0.0.1",
        port=8123,
        event_write_timeout=0.2,
    )
    request_result = []
    event_finished = threading.Event()

    request_thread = threading.Thread(
        target=lambda: request_result.append(transport.request("slow", timeout=0.5)),
    )
    request_thread.start()
    assert request_reading.wait(timeout=1)

    event_thread = threading.Thread(
        target=lambda: (transport.event("progress.update", {"value": 1}), event_finished.set()),
    )
    event_thread.start()
    assert event_finished.wait(timeout=0.03) is False
    assert len(sock.send_attempts) == 1

    release_response.set()
    request_thread.join(timeout=1)
    event_thread.join(timeout=1)
    assert not request_thread.is_alive()
    assert not event_thread.is_alive()
    assert request_result == [{}]
    assert event_finished.is_set()
    assert [json.loads(item)["type"] for item in sock.send_attempts] == [
        "slow",
        "progress.update",
    ]
    assert sock.send_timeouts == [0.5, 0.2]
    transport.close()


def test_timed_out_buffered_reader_is_invalidated_after_timeout_restoration(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)
    reader = _ScriptedReader([socket.timeout("scripted request timeout")])
    sock = _FakeSocket(reader, timeout=None)
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    with pytest.raises(socket.timeout, match="scripted request timeout"):
        transport.request("slow", timeout=0.05)

    assert sock.timeout_history == [0.05, 0.05, None]
    assert transport.closed is True
    assert reader.close_calls == 1
    assert sock.close_calls == 1
    with pytest.raises(RuntimeProtocolError, match="closed"):
        transport.send_raw({"type": "event"})


def test_request_deadline_is_shared_across_write_and_nonmatching_frames(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)

    class AdvancingReader(_ScriptedReader):
        def __init__(self, sock):
            super().__init__()
            self.sock = sock
            self.read_count = 0

        def readline(self):
            self.read_count += 1
            clock.advance(0.03 if self.read_count == 1 else 0.01)
            request = json.loads(self.sock.send_attempts[0])
            response_id = "other" if self.read_count == 1 else request["id"]
            return encode_message({"id": response_id, "ok": True, "payload": {"value": 9}})

    sock = _FakeSocket(None, timeout=None)
    sock.reader = AdvancingReader(sock)
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    assert transport.request("bounded", timeout=0.05) == {"value": 9}
    assert sock.timeout_history[:2] == [0.05, 0.05]
    assert sock.timeout_history[2] == pytest.approx(0.02)
    assert sock.timeout_history[-1] is None
    transport.close()


def test_drip_fed_partial_frame_cannot_renew_request_deadline(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)

    class DripReader(_ScriptedReader):
        def __init__(self):
            super().__init__()
            self.read_calls = 0

        def read1(self, size):
            assert size == transport_module.READ_CHUNK_BYTES
            self.read_calls += 1
            clock.advance(0.02)
            return b"x"

    reader = DripReader()
    sock = _FakeSocket(reader, timeout=None)
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    with pytest.raises(socket.timeout, match="Runtime request timed out"):
        transport.request("drip", timeout=0.05)

    assert reader.read_calls == 3
    assert sock.timeout_history[:4] == pytest.approx([0.05, 0.05, 0.03, 0.01])
    assert sock.timeout_history[-1] is None
    assert transport.closed is True


def test_frame_completed_after_request_deadline_is_not_returned(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)

    class LateFrameReader(_ScriptedReader):
        def __init__(self, sock):
            super().__init__()
            self.sock = sock
            self.read_calls = 0

        def read1(self, _size):
            self.read_calls += 1
            clock.advance(0.03)
            if self.read_calls == 1:
                return b'{"id":'
            request = json.loads(self.sock.send_attempts[0])
            response = encode_message({"id": request["id"], "ok": True, "payload": {}})
            return response[len(b'{"id":') :]

    sock = _FakeSocket(None, timeout=None)
    reader = LateFrameReader(sock)
    sock.reader = reader
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    with pytest.raises(socket.timeout, match="Runtime request timed out"):
        transport.request("late-frame", timeout=0.05)

    assert reader.read_calls == 2
    assert transport.closed is True


def test_request_write_consumes_the_total_deadline_and_invalidates(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)

    class SlowWriteSocket(_FakeSocket):
        def sendall(self, data):
            super().sendall(data)
            clock.advance(0.06)

    reader = _ScriptedReader([b"unused\n"])
    sock = SlowWriteSocket(reader, timeout=None)
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    with pytest.raises(socket.timeout, match="Runtime request timed out"):
        transport.request("slow-write", timeout=0.05)

    assert reader.items == [b"unused\n"]
    assert transport.closed is True


def test_blocked_event_write_uses_finite_deadline_and_invalidates_transport():
    reader = _ScriptedReader()
    sock = _FakeSocket(
        reader,
        timeout=None,
        send_errors={1: socket.timeout("scripted event write timeout")},
    )
    transport = JsonlTcpTransport(
        sock,
        host="127.0.0.1",
        port=8123,
        event_write_timeout=0.07,
    )

    with pytest.raises(socket.timeout, match="scripted event write timeout"):
        transport.event("progress.update", {"value": 1})

    assert sock.send_timeouts == [0.07]
    assert sock.timeout_history == [0.07, None]
    assert transport.closed is True


def test_timeout_cleanup_failure_does_not_replace_primary_write_timeout():
    class RestoreFailingSocket(_FakeSocket):
        def settimeout(self, value):
            if value is None and self.send_attempts:
                raise OSError("scripted timeout restoration failure")
            super().settimeout(value)

    sock = RestoreFailingSocket(
        _ScriptedReader(close_error=OSError("scripted reader close failure")),
        timeout=None,
        send_errors={1: socket.timeout("primary write timeout")},
        close_error=OSError("scripted socket close failure"),
    )
    transport = JsonlTcpTransport(
        sock,
        host="127.0.0.1",
        port=8123,
        event_write_timeout=0.07,
    )

    with pytest.raises(socket.timeout, match="primary write timeout"):
        transport.event("progress.update")

    assert transport.closed is True


def test_emit_event_reports_failure_without_raising(monkeypatch):
    captured = []
    monkeypatch.setattr(runtime_client_module, "capture_exception", lambda: captured.append(True))
    sock = _FakeSocket(
        _ScriptedReader(),
        timeout=None,
        send_errors={1: socket.timeout("scripted best-effort timeout")},
    )
    client = RuntimeClient(
        JsonlTcpTransport(
            sock,
            host="127.0.0.1",
            port=8123,
            event_write_timeout=0.04,
        )
    )

    assert client.emit_event("browser.open", {"url": "http://127.0.0.1:7860"}) is False
    assert captured == [True]
    assert client.transport.closed is True


def test_get_config_uses_default_deadline_on_nonresponsive_connected_host(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(transport_module.time, "monotonic", clock)
    reader = _ScriptedReader([socket.timeout("scripted non-responsive host")])
    sock = _FakeSocket(reader, timeout=None)
    client = RuntimeClient(
        JsonlTcpTransport(
            sock,
            host="127.0.0.1",
            port=8123,
            default_request_timeout=0.06,
        )
    )

    with pytest.raises(socket.timeout, match="scripted non-responsive host"):
        client.get_config()

    assert sock.send_timeouts == [0.06]
    assert client.transport.closed is True


def _make_channel(
    monkeypatch,
    sock,
    *,
    service=None,
    timeout=0.05,
    connect_timeout=None,
    response_write_timeout=None,
):
    observed = {}

    def create_connection(address, *, timeout):
        observed.update(address=address, timeout=timeout)
        return sock

    monkeypatch.setattr(socket, "create_connection", create_connection)
    client = cast(RuntimeClient, SimpleNamespace(host="127.0.0.1", port=8123, token="secret"))
    channel = ServiceControlChannel(
        client,
        cast(PatchService, service or _StaticService()),
        timeout=timeout,
        connect_timeout=connect_timeout,
        response_write_timeout=response_write_timeout,
    )
    assert observed == {
        "address": ("127.0.0.1", 8123),
        "timeout": timeout if connect_timeout is None else connect_timeout,
    }
    assert sock.timeout_history == [None]
    assert sock.makefile_timeouts == [None]
    return channel


def test_services_read_failure_is_terminal_without_second_write(monkeypatch):
    reader = _ScriptedReader([ConnectionResetError("scripted read reset")])
    sock = _FakeSocket(reader)
    channel = _make_channel(monkeypatch, sock).start()
    _wait_for_thread(channel)

    assert channel.closed is True
    assert channel.reader is reader
    assert channel.sock is sock
    assert reader.closed is True
    assert sock.closed is True
    assert channel.terminal_failure == {"stage": "read", "message": "scripted read reset"}
    assert len(sock.send_attempts) == 1  # channel.open only

    close_counts = (reader.close_calls, sock.close_calls, sock.shutdown_calls)
    channel.close()
    channel.close()
    assert (reader.close_calls, sock.close_calls, sock.shutdown_calls) == close_counts


def test_services_response_send_failure_is_terminal_and_contained(monkeypatch):
    request = encode_message({"id": "svc-1", "type": "services.defaults.get", "payload": {}})
    reader = _ScriptedReader([request])
    sock = _FakeSocket(reader, fail_send_calls={2})
    channel = _make_channel(monkeypatch, sock).start()
    _wait_for_thread(channel)

    assert channel.closed is True
    assert channel.terminal_failure == {"stage": "response", "message": "scripted send failure"}
    assert len(sock.send_attempts) == 2  # no attempted error write after the failed response
    assert reader.close_calls == 1
    assert sock.close_calls == 1


def test_services_response_write_has_deadline_but_idle_reader_is_blocking(monkeypatch):
    request = encode_message({"id": "svc-1", "type": "services.defaults.get", "payload": {}})
    reader = _ScriptedReader([request])
    sock = _FakeSocket(
        reader,
        timeout=1.0,
        send_errors={2: socket.timeout("scripted services write timeout")},
    )
    channel = _make_channel(
        monkeypatch,
        sock,
        connect_timeout=0.03,
        response_write_timeout=0.07,
    ).start()
    _wait_for_thread(channel)

    assert sock.makefile_timeouts == [None]
    assert sock.send_timeouts == [0.07, 0.07]
    assert sock.timeout_history == [None, 0.07, None, 0.07, None]
    assert channel.closed is True
    assert channel.terminal_failure == {
        "stage": "response",
        "message": "scripted services write timeout",
    }


@pytest.mark.parametrize(
    ("reader", "service", "expected_stage"),
    [
        (_ScriptedReader([b"not-json\n"]), _StaticService(), "decode"),
        (
            _ScriptedReader([encode_message({"id": "svc-1", "type": "services.defaults.get", "payload": {}})]),
            _FailingService(),
            "handler",
        ),
    ],
)
def test_services_recoverable_failures_are_diagnosed_and_answered(monkeypatch, reader, service, expected_stage):
    sock = _FakeSocket(reader)
    channel = _make_channel(monkeypatch, sock, service=service).start()
    _wait_for_thread(channel)

    assert any(item["stage"] == expected_stage for item in channel.diagnostics)
    assert len(sock.send_attempts) == 2
    response = json.loads(sock.send_attempts[1])
    assert response["ok"] is False
    assert response["error"]["code"] == "request_failed"


def test_services_connect_and_close_failures_have_distinct_diagnostics(monkeypatch, caplog):
    def fail_connection(address, *, timeout):
        raise ConnectionRefusedError("scripted connect failure")

    monkeypatch.setattr(socket, "create_connection", fail_connection)
    client = cast(RuntimeClient, SimpleNamespace(host="127.0.0.1", port=8123, token=""))
    with caplog.at_level(logging.WARNING), pytest.raises(ConnectionRefusedError):
        ServiceControlChannel(client, cast(PatchService, _StaticService()))
    assert "services control channel connect failure: scripted connect failure" in caplog.text

    reader = _ScriptedReader(close_error=OSError("scripted reader close failure"))
    sock = _FakeSocket(
        reader,
        shutdown_error=OSError(errno.EIO, "scripted shutdown failure"),
        close_error=OSError("scripted socket close failure"),
    )
    channel = _make_channel(monkeypatch, sock)
    channel.close()
    first_diagnostics = list(channel.diagnostics)
    channel.close()

    close_messages = [item["message"] for item in channel.diagnostics if item["stage"] == "close"]
    assert len(close_messages) == 3
    assert any("shutdown failure" in message for message in close_messages)
    assert any("reader close failure" in message for message in close_messages)
    assert any("socket close failure" in message for message in close_messages)
    assert channel.diagnostics == first_diagnostics


class _IdleLegacyHost:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.host, self.port = self.listener.getsockname()
        self.stop_event = threading.Event()
        self.service_open = threading.Event()
        self.send_service_request = threading.Event()
        self.service_response = threading.Event()
        self.connections = []
        self.threads = []
        self.errors = []
        self.thread = threading.Thread(target=self._accept, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                pass
        except OSError:
            pass
        for conn in self.connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        self.listener.close()
        self.thread.join(timeout=2)
        for thread in self.threads:
            thread.join(timeout=2)

    def _accept(self):
        while not self.stop_event.is_set():
            try:
                conn, _ = self.listener.accept()
            except OSError:
                return
            self.connections.append(conn)
            thread = threading.Thread(target=self._handle, args=(conn,), daemon=True)
            self.threads.append(thread)
            thread.start()

    def _handle(self, conn):
        try:
            reader = conn.makefile("rb")
            first_line = reader.readline()
            if not first_line:
                return
            first = json.loads(first_line)
            if first.get("type") == "hello":
                request = json.loads(reader.readline())
                time.sleep(0.08)
                conn.sendall(encode_message({"id": request["id"], "ok": True, "payload": {"idle": True}}))
                return
            if first.get("type") == "channel.open":
                self.service_open.set()
                if not self.send_service_request.wait(timeout=7):
                    return
                conn.sendall(encode_message({"id": "svc-idle", "type": "services.defaults.get", "payload": {}}))
                response = json.loads(reader.readline())
                if response.get("id") == "svc-idle" and response.get("ok") is True:
                    self.service_response.set()
        except Exception as exc:  # pragma: no cover - asserted through errors
            if not self.stop_event.is_set():
                self.errors.append(exc)


def test_legacy_runtime_and_services_remain_usable_beyond_connect_deadline():
    with _IdleLegacyHost() as host:
        client = RuntimeClient.connect(
            host.host,
            host.port,
            timeout=0.05,
            # 服务端会在响应前等待 0.08 秒，仍可证明运行时请求没有继承
            # 0.05 秒的建连截止时间。请求自身留出充足的 CI 调度余量。
            default_request_timeout=1.0,
        )
        channel = ServiceControlChannel(client, cast(PatchService, _StaticService()), timeout=0.05).start()
        try:
            assert client.transport.sock.gettimeout() is None
            assert channel.sock is not None
            assert channel.sock.gettimeout() is None
            assert host.service_open.wait(timeout=1)

            # 一次真实耐久测试覆盖历史遗留的五秒套接字超时；其余超时测试使用
            # 确定性的替身。
            time.sleep(5.1)
            host.send_service_request.set()
            assert host.service_response.wait(timeout=1)
            assert client.request("idle.echo") == {"idle": True}
            assert channel.closed is False
            assert host.errors == []
        finally:
            channel.close()
            client.close()
