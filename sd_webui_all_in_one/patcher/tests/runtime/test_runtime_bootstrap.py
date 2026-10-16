"""Hotpatcher 运行时启动引导测试"""

import logging
import sys

import pytest
from runtime_test_helpers import JsonlHost, locals_for_function

from sd_webui_all_in_one_hotpatcher.runtime.errors import (
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

        assert host.wait_for(lambda message: message.get("type") == "log.record" and message["payload"]["message"] == "from bootstrap")
        uninstall_log_capture()
        assert state.runtime_client is not None
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

            assert host.wait_for(lambda message: message.get("type") == "error.exception" and message["payload"]["message"] == "from bootstrap error capture")
            event = next(message for message in host.messages if message.get("type") == "error.exception" and message["payload"]["message"] == "from bootstrap error capture")
            assert locals_for_function(event["payload"], "_raise_with_locals")["visible_local"]["repr"] == "'visible value'"
            assert calls and calls[0][1] is captured_exc
        finally:
            uninstall_error_capture()
            assert state.runtime_client is not None
            state.runtime_client.close()
