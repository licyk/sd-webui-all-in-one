"""Hotpatcher 服务控制通道与启动引导测试"""

import json
import socket
import threading

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env
from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message
from sd_webui_all_in_one_hotpatcher.services import (
    clear_current_config,
    handle_request_json,
    install_service_control_channel,
)
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess


@pytest.fixture(autouse=True)
def clean_service_state():
    clear_current_config()
    uninstall_error_capture()
    uninstall_log_capture()
    uninstall_import_hook()
    uninstall_stack_shadower()
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()
    yield
    clear_current_config()
    uninstall_error_capture()
    uninstall_log_capture()
    uninstall_import_hook()
    uninstall_stack_shadower()
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()


class ServicesHost:
    def __init__(self):
        self.messages = []
        self.responses = []
        self.response_ready = threading.Event()
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
            first_line = file.readline()
            if not first_line:
                return
            first_message = json.loads(first_line.decode("utf-8"))
            self.messages.append(first_message)
            if first_message.get("type") != "channel.open":
                return
            conn.sendall(
                encode_message(
                    {
                        "id": "svc-1",
                        "type": "services.defaults.get",
                        "payload": {},
                    }
                )
            )
            response_line = file.readline()
            if not response_line:
                return
            self.responses.append(json.loads(response_line.decode("utf-8")))
            self.response_ready.set()


def test_service_control_channel_handles_host_request():
    with ServicesHost() as host:
        with RuntimeClient.connect(host.host, host.port, token="svc-token") as client:
            channel = install_service_control_channel(client)
            assert host.response_ready.wait(timeout=2)
            channel.close()

        assert any(message.get("type") == "channel.open" and message.get("channel") == "services" for message in host.messages)
        response = host.responses[0]
        assert response["id"] == "svc-1"
        assert response["ok"] is True
        assert "config" in response["payload"]


def test_bootstrap_applies_services_config_and_opens_control_channel(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser

    browser_calls = []
    monkeypatch.setattr(
        browser,
        "patch_webbrowser",
        lambda client, *, mode, state: browser_calls.append((client, mode, state)),
    )
    with ServicesHost() as host:
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", host.host)
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(host.port))
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
        monkeypatch.setenv(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
            '{"services":{"apply_on_bootstrap":true},"core":{"import_hook":{"enabled":true}},"runtime":{"browser":{"enabled":true,"mode":"host"}}}',
        )
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES", "1")

        state = configure_from_env()
        try:
            assert state.service_apply_result is not None
            assert "core.import_hook" in state.service_apply_result["applied"]
            assert "runtime.browser" in state.service_apply_result["applied"]
            assert browser_calls and browser_calls[0][0] is state.runtime_client
            assert browser_calls[0][1] == "host"
            assert state.service_control_channel is not None
            assert host.response_ready.wait(timeout=2)
        finally:
            if state.service_control_channel is not None:
                state.service_control_channel.close()
            if state.runtime_client is not None:
                state.runtime_client.close()


def test_bootstrap_records_loaded_config_without_apply(monkeypatch):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        '{"services":{"apply_on_bootstrap":false},"runtime":{"errors":{"enabled":false,"asyncio":false}}}',
    )

    state = configure_from_env()
    current = handle_request_json({"type": "services.config.current", "payload": {}})

    assert state.service_apply_result is None
    assert current["ok"] is True
    assert current["payload"]["config"]["services"]["apply_on_bootstrap"] is False
    assert current["payload"]["config"]["runtime"]["errors"]["asyncio"] is False


def test_bootstrap_browser_interception_ignores_disabled_general_apply_toggle(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser

    calls = []
    monkeypatch.setattr(
        browser,
        "patch_webbrowser",
        lambda client, *, mode, state: calls.append((client, mode, state)),
    )
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        '{"services":{"apply_on_bootstrap":false},"runtime":{"browser":{"enabled":true,"mode":"suppress"}}}',
    )
    state = configure_from_env()
    assert state.service_apply_result is not None
    assert "runtime.browser" in state.service_apply_result["applied"]
    assert calls and calls[0][1] == "suppress"
