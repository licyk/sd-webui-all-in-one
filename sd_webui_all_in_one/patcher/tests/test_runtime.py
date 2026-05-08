import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from sd_webui_all_in_one_hotpatcher.runtime import FileOperation, ManagedBrowser, Progress, ProgressManager, RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.config import load_config
from sd_webui_all_in_one_hotpatcher.runtime.errors import (
    CaughtExceptionTracer,
    format_exception_payload,
    configure_error_capture_from_env,
    install_error_capture,
    install_exception_reporter,
    uninstall_error_capture,
    uninstall_exception_reporter,
)
from sd_webui_all_in_one_hotpatcher.runtime.faults import install_faulthandler
from sd_webui_all_in_one_hotpatcher.runtime.logs import install_log_capture, uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message
from sd_webui_all_in_one_hotpatcher.runtime.audit import install_audit_hook
from sd_webui_all_in_one_hotpatcher.runtime.fileops import UserCanceledException
from sd_webui_all_in_one_hotpatcher.exceptions import capture_exception


@pytest.fixture(autouse=True)
def clean_exception_reporter():
    uninstall_error_capture()
    uninstall_exception_reporter()
    uninstall_log_capture()
    yield
    uninstall_log_capture()
    uninstall_error_capture()
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


class ForwardingStream:
    def __init__(self, original):
        self.original = original

    def write(self, text):
        return self.original.write(text)

    def flush(self):
        return self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


class BrokenFlushStream(ForwardingStream):
    def flush(self):
        raise OSError(1, "bad flush")


class BrokenWriteStream(ForwardingStream):
    def write(self, text):
        raise OSError(1, "bad write")


class BrokenLocalRepr:
    def __repr__(self):
        raise RuntimeError("repr failed")


def _raise_with_locals(message="locals"):
    visible_local = "visible value"  # noqa: F841
    password_token = "secret value"  # noqa: F841
    long_local = "x" * 600  # noqa: F841
    broken_repr = BrokenLocalRepr()  # noqa: F841
    raise RuntimeError(message)


def _locals_for_function(payload, function_name):
    frame = next(frame for frame in payload["frames"] if frame["function"] == function_name)
    return frame["locals"]


def _caught_exception_function(message="caught"):
    visible_local = "visible value"  # noqa: F841
    try:
        raise ValueError(message)
    except ValueError:
        return "handled"


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


def test_load_config_auto_does_not_use_host_without_runtime_flag(monkeypatch):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", "127.0.0.1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", "8765")

    assert load_config(source="auto") == {}


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


def test_format_exception_payload_includes_source_and_context():
    try:
        raise RuntimeError("structured")
    except RuntimeError as exc:
        payload = format_exception_payload(
            type(exc),
            exc,
            exc.__traceback__,
            source="sys.excepthook",
            context={"thread_name": "main", "object": object()},
        )

    assert payload["type"] == "builtins.RuntimeError"
    assert payload["message"] == "structured"
    assert payload["source"] == "sys.excepthook"
    assert payload["context"]["thread_name"] == "main"
    assert isinstance(payload["context"]["object"], str)
    assert any(frame["function"] == "test_format_exception_payload_includes_source_and_context" for frame in payload["frames"])
    assert all("locals" not in frame for frame in payload["frames"])


def test_format_exception_payload_includes_sanitized_locals():
    try:
        _raise_with_locals("locals payload")
    except RuntimeError as exc:
        payload = format_exception_payload(type(exc), exc, exc.__traceback__, include_locals=True)

    locals_payload = _locals_for_function(payload, "_raise_with_locals")
    assert locals_payload["visible_local"] == {
        "type": "builtins.str",
        "repr": "'visible value'",
        "truncated": False,
    }
    assert locals_payload["password_token"] == {
        "type": "builtins.str",
        "redacted": True,
        "reason": "sensitive_name",
    }
    assert locals_payload["long_local"]["type"] == "builtins.str"
    assert locals_payload["long_local"]["truncated"] is True
    assert len(locals_payload["long_local"]["repr"]) == 512
    assert locals_payload["broken_repr"]["type"].endswith(".BrokenLocalRepr")
    assert locals_payload["broken_repr"]["repr"] == "<unrepresentable BrokenLocalRepr>"
    assert "secret value" not in json.dumps(payload)


def test_exception_reporter_include_locals_sends_sanitized_locals():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_exception_reporter(client, include_locals=True)
            try:
                _raise_with_locals("reported locals")
            except RuntimeError:
                capture_exception()

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        locals_payload = _locals_for_function(event["payload"], "_raise_with_locals")
        assert locals_payload["visible_local"]["repr"] == "'visible value'"
        assert locals_payload["password_token"]["redacted"] is True


def test_error_capture_sys_excepthook_reports_and_chains(monkeypatch):
    calls = []

    def fake_original(exc_type, exc_value, exc_tb):
        calls.append((exc_type, exc_value, exc_tb))

    monkeypatch.setattr(sys, "excepthook", fake_original)

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(client, threading_excepthook=False, unraisablehook=False, asyncio=False, include_locals=True)
            try:
                _raise_with_locals("from sys")
            except RuntimeError as exc:
                sys.excepthook(type(exc), exc, exc.__traceback__)

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["source"] == "sys.excepthook"
        assert payload["type"] == "builtins.RuntimeError"
        assert payload["message"] == "from sys"
        assert _locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

    assert len(calls) == 1
    assert calls[0][0] is RuntimeError
    assert isinstance(calls[0][1], RuntimeError)
    assert calls[0][1].args == ("from sys",)
    assert calls[0][2] is not None


def test_error_capture_threading_excepthook_reports_and_chains(monkeypatch):
    calls = []

    def fake_original(args):
        calls.append(args)

    monkeypatch.setattr(threading, "excepthook", fake_original)

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(client, sys_excepthook=False, unraisablehook=False, asyncio=False, include_locals=True)
            try:
                _raise_with_locals("from thread")
            except RuntimeError as caught:
                exc = caught
            args = SimpleNamespace(
                exc_type=type(exc),
                exc_value=exc,
                exc_traceback=exc.__traceback__,
                thread=threading.current_thread(),
            )
            threading.excepthook(args)

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["source"] == "threading.excepthook"
        assert payload["message"] == "from thread"
        assert payload["context"]["thread_name"] == threading.current_thread().name
        assert _locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

    assert calls and calls[0].exc_value is exc


def test_error_capture_unraisablehook_reports_and_chains(monkeypatch):
    calls = []

    def fake_original(args):
        calls.append(args)

    monkeypatch.setattr(sys, "unraisablehook", fake_original)

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(client, sys_excepthook=False, threading_excepthook=False, asyncio=False, include_locals=True)
            try:
                _raise_with_locals("from unraisable")
            except RuntimeError as caught:
                exc = caught
            args = SimpleNamespace(
                exc_type=type(exc),
                exc_value=exc,
                exc_traceback=exc.__traceback__,
                err_msg="ignored in callback",
                object="callback-object",
            )
            sys.unraisablehook(args)

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["source"] == "sys.unraisablehook"
        assert payload["message"] == "from unraisable"
        assert payload["context"]["err_msg"] == "ignored in callback"
        assert payload["context"]["object"] == "'callback-object'"
        assert _locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

    assert calls and calls[0].exc_value is exc


def test_error_capture_asyncio_exception_handler_reports_and_chains(monkeypatch):
    calls = []

    def fake_original(loop, context):
        calls.append((loop, context))

    monkeypatch.setattr(asyncio.BaseEventLoop, "call_exception_handler", fake_original)

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(client, sys_excepthook=False, threading_excepthook=False, unraisablehook=False, include_locals=True)
            loop = asyncio.new_event_loop()
            try:
                try:
                    _raise_with_locals("from asyncio")
                except RuntimeError as caught:
                    exc = caught
                loop.call_exception_handler({"message": "async context", "exception": exc})
            finally:
                loop.close()

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["source"] == "asyncio"
        assert payload["message"] == "from asyncio"
        assert payload["context"]["message"] == "async context"
        assert _locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

    assert calls and calls[0][1]["exception"] is exc


def test_caught_exception_tracer_reports_handled_exception():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(
                client,
                sys_excepthook=False,
                threading_excepthook=False,
                unraisablehook=False,
                asyncio=False,
                include_locals=True,
                caught_exceptions_enabled=True,
                caught_exceptions_threading=False,
                caught_exception_module_prefixes=(__name__,),
            )
            assert _caught_exception_function("caught by except") == "handled"

        assert host.wait_for(lambda message: message.get("type") == "error.caught_exception")
        event = next(message for message in host.messages if message.get("type") == "error.caught_exception")
        payload = event["payload"]
        assert payload["source"] == "sys.settrace"
        assert payload["type"] == "builtins.ValueError"
        assert payload["message"] == "caught by except"
        assert payload["context"]["caught"] is True
        assert payload["context"]["module"] == __name__
        assert payload["context"]["function"] == "_caught_exception_function"
        assert payload["context"]["thread_name"] == threading.current_thread().name
        assert _locals_for_function(payload, "_caught_exception_function")["visible_local"]["repr"] == "'visible value'"


def test_caught_exception_tracer_filters_modules():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(
                client,
                sys_excepthook=False,
                threading_excepthook=False,
                unraisablehook=False,
                asyncio=False,
                caught_exceptions_enabled=True,
                caught_exceptions_threading=False,
                caught_exception_module_prefixes=("not_this_module",),
            )
            _caught_exception_function("filtered by include")

        assert not host.wait_for(lambda message: message.get("type") == "error.caught_exception", timeout=0.2)

    uninstall_error_capture()
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(
                client,
                sys_excepthook=False,
                threading_excepthook=False,
                unraisablehook=False,
                asyncio=False,
                caught_exceptions_enabled=True,
                caught_exceptions_threading=False,
                caught_exception_module_prefixes=(__name__,),
                caught_exception_exclude_module_prefixes=(__name__,),
            )
            _caught_exception_function("filtered by exclude")

        assert not host.wait_for(lambda message: message.get("type") == "error.caught_exception", timeout=0.2)


def test_caught_exception_tracer_rate_limits_events():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(
                client,
                sys_excepthook=False,
                threading_excepthook=False,
                unraisablehook=False,
                asyncio=False,
                caught_exceptions_enabled=True,
                caught_exceptions_threading=False,
                caught_exception_module_prefixes=(__name__,),
                caught_exception_max_events_per_second=1,
            )
            _caught_exception_function("first")
            _caught_exception_function("second")

        assert host.wait_for(lambda message: message.get("type") == "error.caught_exception")
        time.sleep(0.05)
        events = [message for message in host.messages if message.get("type") == "error.caught_exception"]
        assert len(events) == 1
        assert events[0]["payload"]["message"] == "first"


def test_caught_exception_tracer_rejects_existing_trace(monkeypatch):
    def existing_trace(frame, event, arg):
        return existing_trace

    monkeypatch.setattr(sys, "excepthook", lambda *args: None)
    sys.settrace(existing_trace)
    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                with pytest.raises(RuntimeError, match="another sys trace function"):
                    install_error_capture(
                        client,
                        sys_excepthook=False,
                        threading_excepthook=False,
                        unraisablehook=False,
                        asyncio=False,
                        caught_exceptions_enabled=True,
                        caught_exceptions_threading=False,
                    )
        assert sys.gettrace() is existing_trace
    finally:
        sys.settrace(None)


def test_caught_exception_tracer_restores_trace_functions():
    assert sys.gettrace() is None
    original_threading_trace = threading.gettrace() if hasattr(threading, "gettrace") else None

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_error_capture(
                client,
                sys_excepthook=False,
                threading_excepthook=False,
                unraisablehook=False,
                asyncio=False,
                caught_exceptions_enabled=True,
                caught_exceptions_threading=True,
                caught_exception_module_prefixes=(__name__,),
            )
            assert isinstance(capture.caught_exception_tracer, CaughtExceptionTracer)
            assert sys.gettrace() is not None
            if hasattr(threading, "gettrace"):
                assert threading.gettrace() is sys.gettrace()
            uninstall_error_capture()

    assert sys.gettrace() is None
    if hasattr(threading, "gettrace"):
        assert threading.gettrace() is original_threading_trace


def test_configure_error_capture_from_env_enables_caught_tracer(monkeypatch):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_EXCEPTIONS", "1")
            monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_MODULE_PREFIXES", __name__)
            monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_EXCLUDE_PREFIXES", "")
            monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_MAX_EVENTS_PER_SECOND", "3")
            capture = configure_error_capture_from_env(
                client,
                {"runtime": {"errors": {"enabled": True}}},
            )
            assert capture is not None
            assert capture.caught_exception_tracer is not None
            assert capture.caught_exception_tracer.module_prefixes == (__name__,)
            assert capture.caught_exception_tracer.exclude_module_prefixes == ()
            assert capture.caught_exception_tracer.max_events_per_second == 3

    uninstall_error_capture()


def test_configure_error_capture_from_env_ignores_caught_when_errors_disabled(monkeypatch):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_CAUGHT_EXCEPTIONS", "1")
            capture = configure_error_capture_from_env(
                client,
                {"runtime": {"errors": {"enabled": False, "caught_exceptions": {"enabled": True}}}},
            )

    assert capture is None
    assert sys.gettrace() is None


def test_uninstall_error_capture_restores_hooks(monkeypatch):
    def fake_sys(exc_type, exc_value, exc_tb):
        pass

    def fake_threading(args):
        pass

    def fake_unraisable(args):
        pass

    def fake_asyncio(loop, context):
        pass

    monkeypatch.setattr(sys, "excepthook", fake_sys)
    monkeypatch.setattr(threading, "excepthook", fake_threading)
    monkeypatch.setattr(sys, "unraisablehook", fake_unraisable)
    monkeypatch.setattr(asyncio.BaseEventLoop, "call_exception_handler", fake_asyncio)

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_error_capture(client)
            assert sys.excepthook is not fake_sys
            assert threading.excepthook is not fake_threading
            assert sys.unraisablehook is not fake_unraisable
            assert asyncio.BaseEventLoop.call_exception_handler is not fake_asyncio
            uninstall_error_capture()

    assert sys.excepthook is fake_sys
    assert threading.excepthook is fake_threading
    assert sys.unraisablehook is fake_unraisable
    assert asyncio.BaseEventLoop.call_exception_handler is fake_asyncio


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


def test_log_capture_wraps_existing_stdout_hook():
    original_stdout = sys.stdout
    preexisting_hook = ForwardingStream(original_stdout)
    sys.stdout = preexisting_hook

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=("stdout",), subprocess_mode="0")
                print("cooperative stdout")

                assert host.wait_for(
                    lambda message: message.get("type") == "log.stream"
                    and message["payload"]["source"] == "stream"
                    and "cooperative stdout" in message["payload"]["text"]
                )
                uninstall_log_capture()
                assert sys.stdout is preexisting_hook
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_stream_write_error_is_best_effort():
    original_stdout = sys.stdout
    sys.stdout = BrokenWriteStream(original_stdout)

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=("stdout",), subprocess_mode="0")
                print("stream write survives")

                assert host.wait_for(
                    lambda message: message.get("type") == "log.stream"
                    and message["payload"]["source"] == "stream"
                    and "stream write survives" in message["payload"]["text"]
                )
                assert host.wait_for(
                    lambda message: message.get("type") == "log.hook_status"
                    and message["payload"]["component"] == "stream.stdout"
                    and message["payload"]["status"] == "error"
                    and "write failed" in message["payload"]["detail"]
                )
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_stream_flush_error_is_best_effort():
    original_stdout = sys.stdout
    sys.stdout = BrokenFlushStream(original_stdout)

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=("stdout",), subprocess_mode="0")
                sys.stdout.flush()

                assert host.wait_for(
                    lambda message: message.get("type") == "log.hook_status"
                    and message["payload"]["component"] == "stream.stdout"
                    and message["payload"]["status"] == "error"
                    and "flush failed" in message["payload"]["detail"]
                )
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_warns_when_stdout_hook_is_replaced():
    original_stdout = sys.stdout

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(
                    client,
                    capture_logging=False,
                    streams=("stdout",),
                    subprocess_mode="0",
                    hook_policy="warn",
                    hook_check_interval=0,
                )
                sys.stdout = ForwardingStream(original_stdout)

                assert host.wait_for(
                    lambda message: message.get("type") == "log.hook_status"
                    and message["payload"]["component"] == "stream.stdout"
                    and message["payload"]["status"] == "lost"
                )
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_reapplies_when_stdout_hook_is_replaced():
    original_stdout = sys.stdout

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(
                    client,
                    capture_logging=False,
                    streams=("stdout",),
                    subprocess_mode="0",
                    hook_policy="reapply",
                    hook_check_interval=0,
                )
                sys.stdout = ForwardingStream(original_stdout)

                assert host.wait_for(
                    lambda message: message.get("type") == "log.hook_status"
                    and message["payload"]["component"] == "stream.stdout"
                    and message["payload"]["status"] == "reapplied"
                )
                print("after stdout reapply")
                assert host.wait_for(
                    lambda message: message.get("type") == "log.stream"
                    and message["payload"]["source"] == "stream"
                    and "after stdout reapply" in message["payload"]["text"]
                )
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


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


def test_log_capture_subprocess_popen_remains_subclassable():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="force")

            class DerivedPopen(subprocess.Popen):
                pass

            assert issubclass(DerivedPopen, subprocess.Popen)
            uninstall_log_capture()


def test_log_capture_wraps_preexisting_subprocess_popen_hook():
    original_popen = subprocess.Popen

    class ThirdPartyPopen(original_popen):
        pass

    subprocess.Popen = ThirdPartyPopen
    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="safe")
                assert issubclass(subprocess.Popen, ThirdPartyPopen)

                result = subprocess.run(
                    [sys.executable, "-c", "print('third party popen')"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                assert result.stdout.strip() == "third party popen"
                assert host.wait_for(
                    lambda message: message.get("type") == "log.stream"
                    and message["payload"]["source"] == "subprocess"
                    and "third party popen" in message["payload"]["text"]
                )
                uninstall_log_capture()
                assert subprocess.Popen is ThirdPartyPopen
    finally:
        uninstall_log_capture()
        subprocess.Popen = original_popen


def test_log_capture_warns_when_logging_handler_is_removed():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_log_capture(
                client,
                streams=(),
                subprocess_mode="0",
                hook_policy="warn",
                hook_check_interval=0,
            )
            logging.getLogger().removeHandler(capture._root_handler)

            assert host.wait_for(
                lambda message: message.get("type") == "log.hook_status"
                and message["payload"]["component"] == "logging"
                and message["payload"]["status"] == "lost"
            )
            uninstall_log_capture()


def test_log_capture_reapplies_removed_logging_handler():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_log_capture(
                client,
                streams=(),
                subprocess_mode="0",
                hook_policy="reapply",
                hook_check_interval=0,
            )
            handler = capture._root_handler
            logging.getLogger().removeHandler(handler)

            assert host.wait_for(
                lambda message: message.get("type") == "log.hook_status"
                and message["payload"]["component"] == "logging"
                and message["payload"]["status"] == "reapplied"
            )
            assert handler in logging.getLogger().handlers

            logging.getLogger("app.logging.reapply").warning("logging after reapply")
            assert host.wait_for(
                lambda message: message.get("type") == "log.record"
                and message["payload"]["message"] == "logging after reapply"
            )
            uninstall_log_capture()


def test_log_capture_fd_force_captures_os_write():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_log_capture(
                client,
                capture_logging=False,
                streams=("stdout",),
                subprocess_mode="0",
                fd_capture="force",
            )
            fd_capture = capture._fd_captures.get("stdout")
            if fd_capture is None or fd_capture.fd is None:
                pytest.skip("fd capture is not supported in this environment")

            os.write(fd_capture.fd, b"fd force hello\n")
            assert host.wait_for(
                lambda message: message.get("type") == "log.stream"
                and message["payload"]["source"] == "fd"
                and "fd force hello" in message["payload"]["text"]
            )
            uninstall_log_capture()


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
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", host.host)
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(host.port))
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON", "{}")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS", "1")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_STREAMS", "none")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS", "0")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_POLICY", "warn")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_CHECK_INTERVAL", "2")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_FD_CAPTURE", "fallback")

        state = configure_from_env()
        assert state.log_capture is not None
        assert state.log_capture.hook_policy == "warn"
        assert state.log_capture.hook_check_interval == 2
        assert state.log_capture.fd_capture == "fallback"
        logging.getLogger("bootstrap.logs").warning("from bootstrap")

        assert host.wait_for(
            lambda message: message.get("type") == "log.record"
            and message["payload"]["message"] == "from bootstrap"
        )
        uninstall_log_capture()
        state.runtime_client.close()


def test_bootstrap_installs_error_capture_from_config(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

    calls = []

    def fake_original(exc_type, exc_value, exc_tb):
        calls.append((exc_type, exc_value, exc_tb))

    monkeypatch.setattr(sys, "excepthook", fake_original)

    with JsonlHost() as host:
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", host.host)
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(host.port))
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
        monkeypatch.setenv(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
            '{"services":{"apply_on_bootstrap":false},"runtime":{"errors":{"enabled":true,"include_locals":true}}}',
        )

        state = configure_from_env()
        try:
            assert state.error_capture is not None
            assert state.error_capture.include_locals is True
            captured_exc = None
            try:
                _raise_with_locals("from bootstrap error capture")
            except RuntimeError as exc:
                captured_exc = exc
                sys.excepthook(type(exc), exc, exc.__traceback__)

            assert host.wait_for(
                lambda message: message.get("type") == "error.exception"
                and message["payload"]["message"] == "from bootstrap error capture"
            )
            event = next(
                message
                for message in host.messages
                if message.get("type") == "error.exception"
                and message["payload"]["message"] == "from bootstrap error capture"
            )
            assert _locals_for_function(event["payload"], "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"
            assert calls and calls[0][1] is captured_exc
        finally:
            uninstall_error_capture()
            state.runtime_client.close()
