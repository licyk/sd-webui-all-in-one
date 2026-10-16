"""Hotpatcher 运行时宿主测试"""

import json
import socket
import threading
import time

from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    HotpatcherRuntimeHost,
    RemoteServiceError,
    RuntimeLogEntry,
    RuntimeServiceChannel,
    wait_for_runtime_log,
    wait_for_service_channel,
)


def _send_json_line(file, message):
    file.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
    file.flush()


def _read_json_line(file):
    return json.loads(file.readline().decode("utf-8"))


class _RecordingWriter:
    def __init__(self):
        self.data = bytearray()
        self.written = threading.Event()

    def write(self, data):
        self.data.extend(data)
        self.written.set()

    def flush(self):
        pass


def test_runtime_log_cursor_is_monotonic_bounded_and_reports_truncation():
    host = HotpatcherRuntimeHost(port=0)
    host._log_retention = 2
    host._record_log(RuntimeLogEntry("log.record", {"level": "INFO", "message": "one"}))
    host._record_log(RuntimeLogEntry("log.stream", {"source": "stdout", "text": "two"}))

    first = host.read_logs(since_cursor=0, limit=1)
    assert [entry["sequence"] for entry in first["logs"]] == [0]
    assert first["next_cursor"] == 1
    assert first["truncated"] is False

    host._record_log(RuntimeLogEntry("log.dropped", {"count": 1}))
    retained = host.read_logs(since_cursor=0, limit=10)
    assert [entry["sequence"] for entry in retained["logs"]] == [1, 2]
    assert retained["start_cursor"] == 1
    assert retained["next_cursor"] == 3
    assert retained["truncated"] is True


def test_runtime_browser_events_are_typed_bounded_and_cursor_based():
    host = HotpatcherRuntimeHost(port=0)
    host._browser_retention = 2
    host._record_message({"type": "browser.open", "payload": {"url": "http://localhost:1"}}, None)
    host._record_message({"type": "browser.open", "payload": {"url": "http://localhost:2"}}, None)

    first = host.read_browser_events(since_cursor=0, limit=1)
    assert first["events"][0]["sequence"] == 0
    assert first["events"][0]["url"] == "http://localhost:1"
    assert isinstance(first["events"][0]["created"], float)
    assert first["next_cursor"] == 1
    assert first["truncated"] is False

    host._record_message({"type": "browser.open", "payload": {"url": "http://localhost:3"}}, None)
    host._record_message({"type": "browser.open", "payload": {"url": 42}}, None)
    retained = host.read_browser_events(since_cursor=0, limit=200)
    assert [event["sequence"] for event in retained["events"]] == [1, 2]
    assert retained["start_cursor"] == 1
    assert retained["next_cursor"] == 3
    assert retained["truncated"] is True
    assert len(host.messages) == 4
    assert host.browser_diagnostics == ["rejected malformed browser.open runtime event"]


def test_runtime_restart_resets_browser_stream_and_identity():
    host = HotpatcherRuntimeHost(port=0)
    host.start()
    first_identity = host.runtime_identity
    host._record_message({"type": "browser.open", "payload": {"url": "http://localhost:1"}}, None)
    host.stop()
    host.start()
    try:
        assert host.runtime_identity != first_identity
        assert host.read_browser_events() == {
            "runtime_identity": host.runtime_identity,
            "events": [],
            "start_cursor": 0,
            "next_cursor": 0,
            "truncated": False,
        }
    finally:
        host.stop()


def test_runtime_host_serves_config_and_records_logs():
    with HotpatcherRuntimeHost(port=0, get_config=lambda: {"answer": 42}) as host:
        with socket.create_connection(host.server_address, timeout=2) as sock, sock.makefile("rwb") as file:
            _send_json_line(file, {"type": "hello", "version": 1, "features": ["config", "logs"]})
            _send_json_line(file, {"id": "cfg", "type": "config.get", "payload": {}})
            response = _read_json_line(file)
            assert response == {"id": "cfg", "ok": True, "payload": {"config": {"answer": 42}}}

            _send_json_line(
                file,
                {
                    "type": "log.record",
                    "payload": {
                        "logger": "demo",
                        "level": "WARNING",
                        "message": "hello",
                    },
                },
            )
            entry = wait_for_runtime_log(host, lambda item: item.payload.get("message") == "hello")
            assert entry is not None
            assert entry.format_line() == "[WARNING] demo: hello"

            _send_json_line(file, {"id": "file-1", "type": "file.delete", "payload": {"path": "/tmp/demo"}})
            rejection = _read_json_line(file)
            assert rejection["id"] == "file-1"
            assert rejection["ok"] is False
            assert rejection["error"]["code"] == "cancelled"


def test_runtime_client_optional_connection_failure_is_quiet(monkeypatch, capsys):
    from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", "127.0.0.1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(port))
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT", "0.1")

    assert RuntimeClient.connect_from_env(required=False) is None
    assert "ConnectionRefusedError" not in capsys.readouterr().err

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG", "1")
    assert RuntimeClient.connect_from_env(required=False) is None
    debug_err = capsys.readouterr().err
    assert "Traceback" in debug_err
    assert "ConnectionRefusedError" in debug_err or "TimeoutError" in debug_err


def test_runtime_host_services_channel_roundtrip():
    with HotpatcherRuntimeHost(port=0) as host:
        with socket.create_connection(host.server_address, timeout=2) as sock, sock.makefile("rwb") as file:
            _send_json_line(file, {"type": "channel.open", "channel": "services", "token": ""})
            assert wait_for_service_channel(host)

            result = {}
            error = {}

            def _request():
                try:
                    result["value"] = host.request_services("services.config.apply", {"config": {"core": {}}}, timeout=5)
                except Exception as exc:  # pragma: no cover - makes thread assertion readable
                    error["value"] = exc

            thread = threading.Thread(target=_request)
            thread.start()
            request = _read_json_line(file)
            assert request["type"] == "services.config.apply"
            assert request["payload"] == {"config": {"core": {}}}
            _send_json_line(file, {"id": request["id"], "ok": True, "payload": {"result": {"applied": ["core.import_hook"]}}})
            thread.join(timeout=5)

            assert not thread.is_alive()
            assert error == {}
            assert result["value"] == {"result": {"applied": ["core.import_hook"]}}


def test_runtime_service_channel_close_wakes_pending_request():
    writer = _RecordingWriter()
    channel = RuntimeServiceChannel(writer)
    error = {}

    def _request():
        try:
            channel.request("services.config.apply", timeout=30)
        except RemoteServiceError as exc:
            error["value"] = exc

    thread = threading.Thread(target=_request)
    thread.start()
    assert writer.written.wait(timeout=1)

    channel.close()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert error["value"].code == "channel_closed"


def test_runtime_host_keeps_browser_retention_after_services_disconnect():
    with HotpatcherRuntimeHost(port=0) as host:
        with socket.create_connection(host.server_address, timeout=2) as services_sock, services_sock.makefile("rwb") as services_file:
            _send_json_line(
                services_file,
                {"type": "channel.open", "channel": "services", "token": ""},
            )
            assert wait_for_service_channel(host)

        deadline = time.time() + 2
        while host.service_channel_available and time.time() < deadline:
            time.sleep(0.01)
        assert host.service_channel_available is False

        with socket.create_connection(host.server_address, timeout=2) as runtime_sock, runtime_sock.makefile("rwb") as runtime_file:
            _send_json_line(runtime_file, {"type": "hello", "version": 1})
            _send_json_line(
                runtime_file,
                {
                    "type": "browser.open",
                    "payload": {"url": "http://localhost:8188"},
                },
            )

        deadline = time.time() + 2
        while not host.browser_events and time.time() < deadline:
            time.sleep(0.01)
        assert [event.url for event in host.browser_events] == ["http://localhost:8188"]
