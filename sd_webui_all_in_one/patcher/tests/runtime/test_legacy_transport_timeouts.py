"""Hotpatcher 旧版 JSONL 传输超时测试"""

import json
import socket
import threading

import pytest
from legacy_transport_test_helpers import FakeSocket, ScriptedReader

from sd_webui_all_in_one_hotpatcher.runtime import client as runtime_client_module
from sd_webui_all_in_one_hotpatcher.runtime import transport as transport_module
from sd_webui_all_in_one_hotpatcher.runtime.client import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.protocol import RuntimeProtocolError, encode_message
from sd_webui_all_in_one_hotpatcher.runtime.transport import JsonlTcpTransport


class _ResponseReader(ScriptedReader):
    def __init__(self, sock):
        super().__init__()
        self.sock = sock

    def readline(self):
        request = json.loads(self.sock.send_attempts[-1])
        return encode_message({"id": request["id"], "ok": True, "payload": {"value": 7}})


class _FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_jsonl_connect_separates_connect_and_operation_timeouts(monkeypatch):
    reader = ScriptedReader()
    sock = FakeSocket(reader, timeout=0.05)
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
    reader = ScriptedReader()
    sock = FakeSocket(reader, timeout=0.07)
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
    sock = FakeSocket(None, timeout=None)
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
    sock = FakeSocket(None, timeout=None)
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
    reader = ScriptedReader([b'{"id":"wrong","ok":true,"payload":{}}\n', b"not-json\n"])
    sock = FakeSocket(reader, timeout=None)
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

    class BlockingResponseReader(ScriptedReader):
        def __init__(self, sock):
            super().__init__()
            self.sock = sock

        def readline(self):
            request_reading.set()
            assert release_response.wait(timeout=1)
            request = json.loads(self.sock.send_attempts[0])
            return encode_message({"id": request["id"], "ok": True, "payload": {}})

    sock = FakeSocket(None, timeout=None)
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
    reader = ScriptedReader([socket.timeout("scripted request timeout")])
    sock = FakeSocket(reader, timeout=None)
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

    class AdvancingReader(ScriptedReader):
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

    sock = FakeSocket(None, timeout=None)
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

    class DripReader(ScriptedReader):
        def __init__(self):
            super().__init__()
            self.read_calls = 0

        def read1(self, size):
            assert size == transport_module.READ_CHUNK_BYTES
            self.read_calls += 1
            clock.advance(0.02)
            return b"x"

    reader = DripReader()
    sock = FakeSocket(reader, timeout=None)
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

    class LateFrameReader(ScriptedReader):
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

    sock = FakeSocket(None, timeout=None)
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

    class SlowWriteSocket(FakeSocket):
        def sendall(self, data):
            super().sendall(data)
            clock.advance(0.06)

    reader = ScriptedReader([b"unused\n"])
    sock = SlowWriteSocket(reader, timeout=None)
    transport = JsonlTcpTransport(sock, host="127.0.0.1", port=8123)

    with pytest.raises(socket.timeout, match="Runtime request timed out"):
        transport.request("slow-write", timeout=0.05)

    assert reader.items == [b"unused\n"]
    assert transport.closed is True


def test_blocked_event_write_uses_finite_deadline_and_invalidates_transport():
    reader = ScriptedReader()
    sock = FakeSocket(
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
    class RestoreFailingSocket(FakeSocket):
        def settimeout(self, value):
            if value is None and self.send_attempts:
                raise OSError("scripted timeout restoration failure")
            super().settimeout(value)

    sock = RestoreFailingSocket(
        ScriptedReader(close_error=OSError("scripted reader close failure")),
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
    sock = FakeSocket(
        ScriptedReader(),
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
    reader = ScriptedReader([socket.timeout("scripted non-responsive host")])
    sock = FakeSocket(reader, timeout=None)
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
