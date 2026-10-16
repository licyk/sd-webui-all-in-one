"""Hotpatcher 运行时异常上报与错误捕获测试"""

import asyncio
import json
import sys
import threading
from types import SimpleNamespace

import pytest
from runtime_test_helpers import JsonlHost, locals_for_function

from sd_webui_all_in_one_hotpatcher.exceptions import capture_exception
from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.errors import (
    format_exception_payload,
    install_error_capture,
    install_exception_reporter,
    uninstall_error_capture,
    uninstall_exception_reporter,
)
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture


@pytest.fixture(autouse=True)
def clean_exception_reporter():
    uninstall_error_capture()
    uninstall_exception_reporter()
    uninstall_log_capture()
    yield
    uninstall_log_capture()
    uninstall_error_capture()
    uninstall_exception_reporter()


class BrokenLocalRepr:
    def __repr__(self):
        raise RuntimeError("repr failed")


def _raise_with_locals(message="locals"):
    visible_local = "visible value"  # noqa: F841
    password_token = "secret value"  # noqa: F841
    long_local = "x" * 600  # noqa: F841
    broken_repr = BrokenLocalRepr()  # noqa: F841
    raise RuntimeError(message)


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


def test_format_exception_payload_includes_bounded_locals():
    try:
        _raise_with_locals("locals payload")
    except RuntimeError as exc:
        payload = format_exception_payload(type(exc), exc, exc.__traceback__, include_locals=True)

    locals_payload = locals_for_function(payload, "_raise_with_locals")
    assert locals_payload["visible_local"] == {
        "type": "builtins.str",
        "repr": "'visible value'",
        "truncated": False,
    }
    assert locals_payload["password_token"] == {
        "type": "builtins.str",
        "repr": "'secret value'",
        "truncated": False,
    }
    assert locals_payload["long_local"]["type"] == "builtins.str"
    assert locals_payload["long_local"]["truncated"] is True
    assert len(locals_payload["long_local"]["repr"]) == 512
    assert locals_payload["broken_repr"]["type"].endswith(".BrokenLocalRepr")
    assert locals_payload["broken_repr"]["repr"] == "<unrepresentable BrokenLocalRepr>"
    assert "secret value" in json.dumps(payload)


def test_exception_reporter_include_locals_sends_bounded_locals():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_exception_reporter(client, include_locals=True)
            try:
                _raise_with_locals("reported locals")
            except RuntimeError:
                capture_exception()

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        locals_payload = locals_for_function(event["payload"], "_raise_with_locals")
        assert locals_payload["visible_local"]["repr"] == "'visible value'"
        assert locals_payload["password_token"]["repr"] == "'secret value'"


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
        assert locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

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
            threading.excepthook(args)  # ty: ignore[invalid-argument-type]

        assert host.wait_for(lambda message: message.get("type") == "error.exception")
        event = next(message for message in host.messages if message.get("type") == "error.exception")
        payload = event["payload"]
        assert payload["source"] == "threading.excepthook"
        assert payload["message"] == "from thread"
        assert payload["context"]["thread_name"] == threading.current_thread().name
        assert locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

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
        assert locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

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
        assert locals_for_function(payload, "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"

    assert calls and calls[0][1]["exception"] is exc


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
