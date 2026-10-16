"""Hotpatcher 运行时已捕获异常追踪测试"""

import sys
import threading
import time

import pytest
from runtime_test_helpers import JsonlHost, locals_for_function

from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.errors import (
    CaughtExceptionTracer,
    configure_error_capture_from_env,
    install_error_capture,
    uninstall_error_capture,
    uninstall_exception_reporter,
)
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture


def _coverage_tracing_active():
    tracer = sys.gettrace()
    return tracer is not None and tracer.__class__.__module__.startswith("coverage")


def coverage_trace_conflict(test_func):
    test_func = pytest.mark.coverage_trace_conflict(test_func)
    return pytest.mark.skipif(
        _coverage_tracing_active(),
        reason="coverage installs sys.settrace and conflicts with caught-exception tracing tests",
    )(test_func)


@pytest.fixture(autouse=True)
def clean_exception_reporter():
    uninstall_error_capture()
    uninstall_exception_reporter()
    uninstall_log_capture()
    yield
    uninstall_log_capture()
    uninstall_error_capture()
    uninstall_exception_reporter()


def _caught_exception_function(message="caught"):
    visible_local = "visible value"  # noqa: F841
    try:
        raise ValueError(message)
    except ValueError:
        return "handled"


@coverage_trace_conflict
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
        assert locals_for_function(payload, "_caught_exception_function")["visible_local"]["repr"] == "'visible value'"


@coverage_trace_conflict
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


@coverage_trace_conflict
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


@coverage_trace_conflict
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


@coverage_trace_conflict
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


@coverage_trace_conflict
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


@coverage_trace_conflict
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
