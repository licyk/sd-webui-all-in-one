"""桌面端代理命令处理测试"""

from typing import cast

import pytest
from desktop_broker_test_helpers import ScriptedRequester, make_client

from sd_webui_all_in_one_hotpatcher import bootstrap
from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import (
    DesktopBrokerClient,
    DesktopBrokerProtocolError,
)
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState


def test_commands_are_idempotent_and_results_are_acknowledged_once():
    command = {
        "commandId": "command-1",
        "sequence": 1,
        "commandType": "config.apply",
        "payload": {"config": {"runtime": {}}},
        "createdAt": 100.0,
        "deadline": 200.0,
    }
    requester = ScriptedRequester(
        {
            "/v1/runtime/commands": [
                {"commands": [command]},
                {"commands": [command]},
            ],
            "/v1/runtime/results": [
                {"acceptedCommandIds": ["command-1"]},
                {"acceptedCommandIds": ["command-1"]},
            ],
        }
    )
    handled = []
    client = make_client(
        requester,
        command_handler=lambda kind, payload: handled.append((kind, payload)) or {"applied": True},
        wall_time=lambda: 150.0,
    )
    client._connect()
    client._poll_commands()
    client._upload_results()
    client._poll_commands()
    client._upload_results()

    assert handled == [("config.apply", {"config": {"runtime": {}}})]
    result_calls = [call for call in requester.calls if call["path"] == "/v1/runtime/results"]
    assert len(result_calls) == 2
    result = result_calls[0]["body"]["results"][0]
    assert result == {
        "commandId": "command-1",
        "ok": True,
        "payload": {"applied": True},
        "completedAt": 150.0,
    }
    assert client.status()["queuedResultCount"] == 0


def test_unknown_command_returns_deterministic_typed_error(monkeypatch):
    state = HotpatcherState()
    client = make_client(command_handler=lambda kind, payload: bootstrap._handle_desktop_command(kind, payload, state=state))
    client._accept_command(
        {
            "commandId": "unknown-1",
            "sequence": 1,
            "commandType": "file.delete",
            "payload": {},
            "createdAt": 100.0,
            "deadline": 9_999_999_999.0,
        }
    )
    result = client._results[0]
    assert result["ok"] is False
    assert result["error"] == {
        "code": "unknown_command",
        "message": "unsupported desktop broker command: file.delete",
    }


def test_expired_command_is_not_executed_and_skipped_sequences_are_supported():
    handled = []
    client = make_client(
        command_handler=lambda kind, payload: handled.append((kind, payload)) or {},
        wall_time=lambda: 50.0,
    )
    client._accept_command(
        {
            "commandId": "expired-1",
            "sequence": 1,
            "commandType": "config.apply",
            "payload": {"config": {}},
            "createdAt": 10.0,
            "deadline": 20.0,
        }
    )
    assert handled == []
    assert client._results[0]["error"]["code"] == "command_expired"

    client._accept_command(
        {
            "commandId": "after-expired-3",
            "sequence": 3,
            "commandType": "config.apply",
            "payload": {"config": {}},
            "createdAt": 30.0,
            "deadline": 60.0,
        }
    )
    assert handled == [("config.apply", {"config": {}})]

    with pytest.raises(DesktopBrokerProtocolError, match="must advance beyond 3, received 2"):
        client._accept_command(
            {
                "commandId": "stale-2",
                "sequence": 2,
                "commandType": "config.apply",
                "payload": {"config": {}},
                "createdAt": 30.0,
                "deadline": 60.0,
            }
        )


def test_config_apply_command_uses_existing_service_with_selected_sink(monkeypatch):
    from sd_webui_all_in_one_hotpatcher import services

    state = HotpatcherState()
    sink = cast(DesktopBrokerClient, object())
    state.bootstrap_runtime_client = sink
    calls = []
    monkeypatch.setattr(
        services,
        "apply_config",
        lambda config, *, runtime_client, state: calls.append((config, runtime_client, state)) or {"applied": ["runtime.browser"], "warnings": [], "errors": []},
    )

    response = bootstrap._handle_desktop_command(
        "config.apply",
        {"config": {"runtime": {"browser": {"enabled": True, "mode": "host"}}}},
        state=state,
    )
    assert response["applyResult"]["applied"] == ["runtime.browser"]
    assert calls[0][1] is sink
    assert calls[0][2] is state
