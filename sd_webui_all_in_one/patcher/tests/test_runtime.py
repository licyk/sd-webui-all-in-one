import json
import logging
import socket
import subprocess
import sys
import threading
import time

import pytest

from sd_webui_all_in_one_hotpatcher.runtime import FileOperation, ManagedBrowser, Progress, ProgressManager, RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.config import load_config
from sd_webui_all_in_one_hotpatcher.runtime.errors import install_exception_reporter, uninstall_exception_reporter
from sd_webui_all_in_one_hotpatcher.runtime.faults import install_faulthandler
from sd_webui_all_in_one_hotpatcher.runtime.logs import install_log_capture, uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message
from sd_webui_all_in_one_hotpatcher.runtime.audit import install_audit_hook
from sd_webui_all_in_one_hotpatcher.runtime.fileops import UserCanceledException
from sd_webui_all_in_one_hotpatcher.exceptions import capture_exception


@pytest.fixture(autouse=True)
def clean_exception_reporter():
    uninstall_exception_reporter()
    uninstall_log_capture()
    yield
    uninstall_log_capture()
    uninstall_exception_reporter()


class JsonlHost:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.messages = []
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self.host, self.port = self._sock.getsockname()
        self._sock.listen()

    def __enter__(self):
        self._thread.start()
        self._ready.wait(timeout=2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop.set()
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                pass
        except Exception:
            pass
        self._thread.join(timeout=2)
        self._sock.close()

    def _run(self):
        self._ready.set()
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        with conn:
            file = conn.makefile("rb")
            for line in file:
                message = json.loads(line.decode("utf-8"))
                self.messages.append(message)
                if message.get("type") == "channel.open":
                    return
                message_id = message.get("id")
                if message_id is None:
                    continue
                response = self.responses.get(message.get("type"), {"ok": True, "payload": {}})
                response = dict(response)
                response["id"] = message_id
                conn.sendall(encode_message(response))

    def wait_for(self, predicate, timeout=2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if any(predicate(message) for message in self.messages):
                return True
            time.sleep(0.01)
        return False


def test_tcp_jsonl_handshake_request_and_event():
    with JsonlHost({"echo": {"ok": True, "payload": {"value": 7}}}) as host:
        with RuntimeClient.connect(host.host, host.port, token="secret") as client:
            assert client.request("echo") == {"value": 7}
            client.event("progress.update", {"id": 1})

        assert host.messages[0]["type"] == "hello"
        assert host.messages[0]["token"] == "secret"
        assert any(message.get("type") == "echo" for message in host.messages)
        assert any(message.get("type") == "progress.update" for message in host.messages)


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON", '{"mode":"env"}')

    assert load_config() == {"mode": "env"}


def test_load_config_from_file(tmp_path, monkeypatch):
    config_file = tmp_path / "hotpatcher-config.json"
    config_file.write_text(json.dumps({"mode": "file", "enabled": True}), encoding="utf-8")

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "file")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE", str(config_file))

    assert load_config() == {"mode": "file", "enabled": True}


def test_load_config_auto_prefers_env_json_then_file(tmp_path, monkeypatch):
    config_file = tmp_path / "hotpatcher-config.json"
    config_file.write_text(json.dumps({"mode": "auto-file"}), encoding="utf-8")

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE", str(config_file))
    assert load_config(source="auto") == {"mode": "auto-file"}

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON", '{"mode":"auto-env"}')
    assert load_config(source="auto") == {"mode": "auto-env"}


def test_load_config_from_remote_and_auto(monkeypatch):
    with JsonlHost({"config.get": {"ok": True, "payload": {"config": {"mode": "remote"}}}}) as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            assert load_config(client=client, source="remote") == {"mode": "remote"}

    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON", '{"mode":"auto-env"}')
    assert load_config(source="auto") == {"mode": "auto-env"}


def test_runtime_progress_browser_and_file_operation_events():
    responses = {
        "file.operation.begin": {"ok": True, "payload": {}},
        "file.delete": {"ok": True, "payload": {}},
        "file.operation.perform": {"ok": True, "payload": {}},
        "file.operation.end": {"ok": True, "payload": {}},
    }
    with JsonlHost(responses) as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            Progress.manager = ProgressManager(client)
            with Progress("work", 2) as progress:
                progress.value = 1
                progress.right = "1/2"
            Progress.manager = None

            ManagedBrowser(client).open("https://example.com")

            with FileOperation(client) as fileop:
                fileop.delete("/tmp/example")
                fileop.perform()

        types = [message.get("type") for message in host.messages]
        assert "progress.create" in types
        assert "progress.update" in types
        assert "progress.remove" in types
        assert "browser.open" in types
        assert "file.delete" in types
        assert "file.operation.perform" in types


def test_file_operation_cancelled_maps_to_user_cancelled():
    responses = {
        "file.operation.begin": {"ok": True, "payload": {}},
        "file.delete": {"ok": False, "error": {"code": "cancelled", "message": "user cancelled"}},
        "file.operation.end": {"ok": True, "payload": {}},
    }
    with JsonlHost(responses) as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            with pytest.raises(UserCanceledException):
                with FileOperation(client) as fileop:
                    fileop.delete("/tmp/example")


def test_fault_channel_opens_raw_channel():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port, token="fault-token") as client:
            channel = install_faulthandler(client, enable=False)
            channel.close()

        assert host.wait_for(
            lambda message: message.get("type") == "channel.open"
            and message.get("channel") == "fault"
            and message.get("token") == "fault-token"
        )


def test_audit_hook_sends_filtered_event():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_audit_hook(client, ["sd_webui_all_in_one_hotpatcher.test_event"])
            import sys

            sys.audit("sd_webui_all_in_one_hotpatcher.test_event", "payload")

        assert host.wait_for(lambda message: message.get("type") == "audit.event")


def test_exception_reporter_sends_explicit_exception(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_exception_reporter(client)
            exc = ValueError("bad value")
            capture_exception(exc)

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["type"] == "builtins.ValueError"
        assert payload["name"] == "ValueError"
        assert payload["message"] == "bad value"
        assert "ValueError: bad value" in payload["traceback"]
        assert payload["process"]["pid"]

    captured = capsys.readouterr()
    assert "ValueError: bad value" in captured.err


def test_exception_reporter_sends_current_exception_from_except_block():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_exception_reporter(client)
            try:
                raise RuntimeError("from except")
            except RuntimeError:
                capture_exception()

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["type"] == "builtins.RuntimeError"
        assert payload["message"] == "from except"
        assert any(frame["function"] == "test_exception_reporter_sends_current_exception_from_except_block" for frame in payload["frames"])


def test_log_capture_sends_logging_records_and_filters_defaults():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, streams=(), subprocess_mode="0")
            logging.getLogger("app.test").warning("hello %s", "world")
            logging.getLogger("sd_webui_all_in_one_hotpatcher.noise").warning("hidden")

            assert host.wait_for(lambda message: message.get("type") == "log.record")
            uninstall_log_capture()

        records = [message for message in host.messages if message.get("type") == "log.record"]
        assert len(records) == 1
        payload = records[0]["payload"]
        assert payload["logger"] == "app.test"
        assert payload["level"] == "WARNING"
        assert payload["message"] == "hello world"
        assert payload["process"]


def test_log_capture_tees_stdout_and_stderr(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=("stdout", "stderr"), subprocess_mode="0")
            print("stream hello")
            sys.stderr.write("stream bad\n")

            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["stream"] == "stdout"
                and "stream hello" in message["payload"]["text"]
            )
            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["stream"] == "stderr"
                and "stream bad" in message["payload"]["text"]
            )
            uninstall_log_capture()

    captured = capsys.readouterr()
    assert "stream hello" in captured.out
    assert "stream bad" in captured.err


def test_log_capture_safe_subprocess_captures_explicit_pipe():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="safe")
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('safe out'); print('safe err', file=sys.stderr)",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.stdout.strip() == "safe out"
            assert result.stderr.strip() == "safe err"
            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["source"] == "subprocess"
                and message["payload"]["stream"] == "stdout"
                and "safe out" in message["payload"]["text"]
            )
            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["source"] == "subprocess"
                and message["payload"]["stream"] == "stderr"
                and "safe err" in message["payload"]["text"]
            )
            uninstall_log_capture()


def test_log_capture_safe_subprocess_does_not_force_inherited_output():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="safe")
            subprocess.run(
                [sys.executable, "-c", "print('safe inherit')"],
                check=True,
            )
            assert not host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["source"] == "subprocess"
                and "safe inherit" in message["payload"]["text"],
                timeout=0.3,
            )
            uninstall_log_capture()


def test_log_capture_force_subprocess_captures_and_writes_back(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="force")
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('force out'); print('force err', file=sys.stderr)",
                ],
                text=True,
                check=True,
            )

            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["source"] == "subprocess"
                and message["payload"]["stream"] == "stdout"
                and "force out" in message["payload"]["text"]
            )
            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["source"] == "subprocess"
                and message["payload"]["stream"] == "stderr"
                and "force err" in message["payload"]["text"]
            )
            uninstall_log_capture()

    captured = capsys.readouterr()
    assert "force out" in captured.out
    assert "force err" in captured.err


def test_log_capture_bounded_and_raw_policy(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(
                client,
                capture_logging=False,
                streams=("stdout",),
                subprocess_mode="0",
                policy="bounded",
                max_chars=5,
            )
            print("abcdef")

            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["text"] == "abcde"
                and message["payload"].get("truncated") is True
            )
            uninstall_log_capture()

    capsys.readouterr()

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(
                client,
                capture_logging=False,
                streams=("stdout",),
                subprocess_mode="0",
                policy="raw",
                max_chars=5,
            )
            print("abcdef")

            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["text"] == "abcdef"
                and "truncated" not in message["payload"]
            )
            uninstall_log_capture()


def test_log_capture_reports_dropped_messages_when_queue_full():
    class BlockingTransport:
        def __init__(self):
            self.events = []
            self.first_send = threading.Event()
            self.release = threading.Event()
            self._blocked = False

        def event(self, message_type, payload):
            self.events.append({"type": message_type, "payload": payload})
            if message_type == "log.stream" and not self._blocked:
                self._blocked = True
                self.first_send.set()
                self.release.wait(timeout=2)

    class BlockingClient:
        def __init__(self):
            self.transport = BlockingTransport()

    client = BlockingClient()
    capture = install_log_capture(
        client,
        capture_logging=False,
        streams=(),
        subprocess_mode="0",
        queue_size=1,
    )
    capture.submit("log.stream", {"text": "first"})
    assert client.transport.first_send.wait(timeout=2)
    capture.submit("log.stream", {"text": "second"})
    capture.submit("log.stream", {"text": "third"})
    client.transport.release.set()

    deadline = time.time() + 2
    while time.time() < deadline:
        if any(event["type"] == "log.dropped" for event in client.transport.events):
            break
        time.sleep(0.01)

    uninstall_log_capture()
    dropped = [event for event in client.transport.events if event["type"] == "log.dropped"]
    assert dropped
    assert dropped[0]["payload"]["count"] >= 1


def test_bootstrap_installs_log_capture_from_env(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

    with JsonlHost() as host:
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", host.host)
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(host.port))
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON", "{}")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS", "1")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_STREAMS", "none")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS", "0")

        state = configure_from_env()
        assert state.log_capture is not None
        logging.getLogger("bootstrap.logs").warning("from bootstrap")

        assert host.wait_for(
            lambda message: message.get("type") == "log.record"
            and message["payload"]["message"] == "from bootstrap"
        )
        uninstall_log_capture()
        state.runtime_client.close()
