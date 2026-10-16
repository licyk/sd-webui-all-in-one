"""Hotpatcher 旧版服务通道测试"""

import errno
import json
import logging
import socket
import threading
import time
from types import SimpleNamespace
from typing import cast

import pytest
from legacy_transport_test_helpers import FakeSocket, ScriptedReader

from sd_webui_all_in_one_hotpatcher.runtime.client import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message
from sd_webui_all_in_one_hotpatcher.services import PatchService, ServiceControlChannel


class _StaticService:
    def handle_request_json(self, request, *, runtime_client):
        return {"ok": True, "payload": {"type": request["type"]}}


class _FailingService:
    def handle_request_json(self, request, *, runtime_client):
        raise ValueError("scripted handler failure")


def _wait_for_thread(channel):
    channel.thread.join(timeout=2)
    assert not channel.thread.is_alive()


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
    reader = ScriptedReader([ConnectionResetError("scripted read reset")])
    sock = FakeSocket(reader)
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
    reader = ScriptedReader([request])
    sock = FakeSocket(reader, fail_send_calls={2})
    channel = _make_channel(monkeypatch, sock).start()
    _wait_for_thread(channel)

    assert channel.closed is True
    assert channel.terminal_failure == {"stage": "response", "message": "scripted send failure"}
    assert len(sock.send_attempts) == 2  # no attempted error write after the failed response
    assert reader.close_calls == 1
    assert sock.close_calls == 1


def test_services_response_write_has_deadline_but_idle_reader_is_blocking(monkeypatch):
    request = encode_message({"id": "svc-1", "type": "services.defaults.get", "payload": {}})
    reader = ScriptedReader([request])
    sock = FakeSocket(
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
        (ScriptedReader([b"not-json\n"]), _StaticService(), "decode"),
        (
            ScriptedReader([encode_message({"id": "svc-1", "type": "services.defaults.get", "payload": {}})]),
            _FailingService(),
            "handler",
        ),
    ],
)
def test_services_recoverable_failures_are_diagnosed_and_answered(monkeypatch, reader, service, expected_stage):
    sock = FakeSocket(reader)
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

    reader = ScriptedReader(close_error=OSError("scripted reader close failure"))
    sock = FakeSocket(
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
