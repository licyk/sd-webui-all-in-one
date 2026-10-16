"""Hotpatcher 运行时客户端, 配置加载与事件测试"""

import json
import sys
from types import SimpleNamespace

import pytest
from runtime_test_helpers import JsonlHost

from sd_webui_all_in_one_hotpatcher.runtime import FileOperation, ManagedBrowser, Progress, ProgressManager, RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.audit import install_audit_hook
from sd_webui_all_in_one_hotpatcher.runtime.config import load_config
from sd_webui_all_in_one_hotpatcher.runtime.errors import (
    uninstall_error_capture,
    uninstall_exception_reporter,
)
from sd_webui_all_in_one_hotpatcher.runtime.faults import install_faulthandler
from sd_webui_all_in_one_hotpatcher.runtime.fileops import UserCanceledException
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState


@pytest.fixture(autouse=True)
def clean_exception_reporter():
    uninstall_error_capture()
    uninstall_exception_reporter()
    uninstall_log_capture()
    yield
    uninstall_log_capture()
    uninstall_error_capture()
    uninstall_exception_reporter()


def test_tcp_jsonl_handshake_request_and_event():
    with JsonlHost({"echo": {"ok": True, "payload": {"value": 7}}}) as host:
        with RuntimeClient.connect(host.host, host.port, token="secret") as client:
            assert client.request("echo") == {"value": 7}
            client.event("progress.update", {"id": 1})
            assert host.wait_for(lambda message: message.get("type") == "progress.update")

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


def test_webbrowser_future_import_and_fresh_passthrough(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser

    registered = {}
    monkeypatch.delitem(sys.modules, "webbrowser", raising=False)
    monkeypatch.setattr(browser, "install_import_hook", lambda **_kwargs: None)
    monkeypatch.setattr(
        browser,
        "register_hook",
        lambda module, function, hook, **_kwargs: registered.update(
            module=module,
            function=function,
            hook=hook,
        ),
    )
    events = []
    client = SimpleNamespace(event=lambda kind, payload: events.append((kind, payload)))
    state = HotpatcherState()
    browser.patch_webbrowser(client, state=state)

    module = SimpleNamespace()

    def original(*_args, **_kwargs):
        return False

    module.open = registered["hook"](original, module)
    assert registered["module"] == "webbrowser"
    assert registered["function"] == "open"
    assert module.open(url="http://localhost:7860", autoraise=False) is True
    assert events == [("browser.open", {"url": "http://localhost:7860"})]

    untouched = HotpatcherState()
    browser.patch_webbrowser(None, mode="passthrough", state=untouched)
    assert untouched.browser_patch_registered is False


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

        assert host.wait_for(lambda message: message.get("type") == "channel.open" and message.get("channel") == "fault" and message.get("token") == "fault-token")


def test_audit_hook_sends_filtered_event():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_audit_hook(client, ["sd_webui_all_in_one_hotpatcher.test_event"])
            import sys

            sys.audit("sd_webui_all_in_one_hotpatcher.test_event", "payload")

        assert host.wait_for(lambda message: message.get("type") == "audit.event")
