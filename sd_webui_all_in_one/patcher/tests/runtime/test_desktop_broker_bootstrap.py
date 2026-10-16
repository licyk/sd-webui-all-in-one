"""桌面端代理启动引导测试"""

import json
import types

import pytest
from desktop_broker_test_helpers import make_desktop_env

from sd_webui_all_in_one_hotpatcher import bootstrap
from sd_webui_all_in_one_hotpatcher.runtime import browser
from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import (
    BROKER_URL_ENV,
    PROTOCOL_VERSION_ENV,
    RUNTIME_IDENTITY_ENV,
    SESSION_ID_ENV,
    SESSION_TOKEN_ENV,
)
from sd_webui_all_in_one_hotpatcher.runtime.transport_mode import TRANSPORT_MODE_ENV
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState


def test_explicit_desktop_bootstrap_never_initializes_legacy(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import client as legacy_client
    from sd_webui_all_in_one_hotpatcher.runtime import desktop_broker

    class FakeDesktopClient:
        def __init__(self):
            self.started = False

        def start(self):
            self.started = True
            return self

        def status(self):
            return {"transport": "desktop_broker", "status": "starting"}

        def emit_event(self, *_args, **_kwargs):
            return True

    fake = FakeDesktopClient()
    monkeypatch.setattr(
        desktop_broker.DesktopBrokerClient,
        "from_env",
        lambda **_kwargs: fake,
    )
    monkeypatch.setattr(
        legacy_client.RuntimeClient,
        "connect_from_env",
        lambda **_kwargs: pytest.fail("desktop mode must not initialize legacy transport"),
    )
    for name, value in make_desktop_env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        json.dumps({"services": {"apply_on_bootstrap": False}}),
    )

    result = bootstrap.configure_from_env(state=HotpatcherState())
    assert result.transport_mode == "desktop_broker"
    assert result.runtime_client is fake
    assert fake.started is True
    assert result.service_control_channel is None


def test_explicit_legacy_bootstrap_uses_existing_runtime_client(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import client as legacy_client

    fake = types.SimpleNamespace(status=lambda: {"transport": "legacy", "status": "connected"})
    calls = []
    monkeypatch.setattr(
        legacy_client.RuntimeClient,
        "connect_from_env",
        lambda **kwargs: calls.append(kwargs) or fake,
    )
    monkeypatch.setenv(TRANSPORT_MODE_ENV, "legacy")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        json.dumps({"services": {"apply_on_bootstrap": False}}),
    )

    result = bootstrap.configure_from_env(state=HotpatcherState())
    assert calls == [{"required": False}]
    assert result.transport_mode == "legacy"
    assert result.runtime_client is fake


def test_desktop_initialization_failure_still_allows_local_suppression(monkeypatch):
    calls = []
    monkeypatch.setenv(TRANSPORT_MODE_ENV, "desktop_broker")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        json.dumps(
            {
                "services": {"apply_on_bootstrap": False},
                "runtime": {"browser": {"enabled": True, "mode": "host"}},
            }
        ),
    )
    for name in (BROKER_URL_ENV, SESSION_ID_ENV, SESSION_TOKEN_ENV, RUNTIME_IDENTITY_ENV, PROTOCOL_VERSION_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        browser,
        "patch_webbrowser",
        lambda sink, *, mode, state: calls.append((sink, mode, state)),
    )

    result = bootstrap.configure_from_env(state=HotpatcherState())
    assert result.transport_mode == "desktop_broker"
    assert result.runtime_client is None
    assert result.transport_diagnostics
    assert "desktop_broker initialization failed" in result.transport_diagnostics[0]
    assert calls and calls[0][0] is None and calls[0][1] == "host"
