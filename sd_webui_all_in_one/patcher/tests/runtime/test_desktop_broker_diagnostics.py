"""桌面端代理心跳与诊断信息测试"""

import json

import pytest
from desktop_broker_test_helpers import ScriptedRequester, make_client

from sd_webui_all_in_one_hotpatcher.runtime import desktop_broker as desktop_broker_module
from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import (
    MAX_DIAGNOSTIC_BATCH_BYTES,
    MAX_DIAGNOSTIC_BATCH_COUNT,
    MAX_DIAGNOSTIC_COUNT,
    MAX_DIAGNOSTIC_HISTORY_BYTES,
    MAX_DIAGNOSTIC_MESSAGE_BYTES,
    DesktopBrokerHttpError,
    DesktopBrokerProtocolError,
)


def test_heartbeat_reports_bounded_local_diagnostics():
    requester = ScriptedRequester()
    client = make_client(requester, event_capacity=2, monotonic=lambda: 10.0, wall_time=lambda: 20.0)
    client.emit_event("first", {})
    client.emit_event("overflow", {})
    client._connect()
    client._heartbeat()

    heartbeat = next(call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat")
    assert heartbeat["body"]["lastAcknowledgedSequence"] == 0
    assert heartbeat["body"]["queuedEventCount"] == 1
    assert heartbeat["body"]["activeDiagnostic"] is None
    assert heartbeat["body"]["diagnosticsStartSequence"] == 1
    assert heartbeat["body"]["diagnosticsTruncated"] is False
    assert heartbeat["body"]["diagnostics"][-1]["sequence"] == 1
    assert heartbeat["body"]["diagnostics"][-1]["code"] == "ordinary_event_capacity_exhausted"
    assert len(heartbeat["body"]["diagnostics"]) <= 8


def test_winerror_failure_episode_is_active_and_reconnect_retains_history():
    client = make_client(wall_time=lambda: 100.0)
    client._connect()
    message = "[WinError 10053] software caused connection abort"

    client._handle_transport_failure("connection_failed", message, retryable=True)
    client._handle_transport_failure("connection_failed", message, retryable=True)

    status = client.status()
    assert status["status"] == "reconnecting"
    assert status["activeDiagnostic"] == {
        "sequence": 1,
        "code": "connection_failed",
        "message": message,
        "createdAt": 100.0,
        "occurrences": 2,
    }
    assert status["unacknowledgedDiagnostics"] == [status["activeDiagnostic"]]
    assert status["acknowledgedDiagnosticSequence"] == 0
    assert status["diagnosticsStartSequence"] == 1
    assert status["diagnosticsTruncated"] is False

    client._connect()
    recovered = client.status()
    assert recovered["status"] == "connected"
    assert recovered["activeDiagnostic"] is None
    assert recovered["unacknowledgedDiagnostics"][0]["message"] == message

    client._handle_transport_failure("connection_failed", "later outage", retryable=True)
    later = client.status()
    assert later["activeDiagnostic"]["sequence"] == 2
    assert [item["sequence"] for item in later["unacknowledgedDiagnostics"]] == [1, 2]


def test_connect_consumes_diagnostic_acknowledgement_and_clears_active_error():
    requester = ScriptedRequester(
        {
            "/v1/runtime/connect": [
                {"status": "connected", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 0},
                {"status": "reconnecting", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 1},
            ]
        }
    )
    client = make_client(requester)
    client._connect()
    client._handle_transport_failure("connection_failed", "temporary outage", retryable=True)

    client._connect()

    status = client.status()
    assert status["activeDiagnostic"] is None
    assert status["unacknowledgedDiagnostics"] == []
    assert status["acknowledgedDiagnosticSequence"] == 1
    assert status["diagnosticsStartSequence"] == 2


def test_heartbeat_acknowledges_history_once_and_subsequent_success_sends_none():
    requester = ScriptedRequester()
    client = make_client(requester)
    client._record_diagnostic("local_warning", "record once")
    client._connect()

    client._heartbeat()
    client._heartbeat()

    heartbeat_calls = [call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat"]
    assert [item["sequence"] for item in heartbeat_calls[0]["body"]["diagnostics"]] == [1]
    assert heartbeat_calls[1]["body"]["diagnostics"] == []
    assert heartbeat_calls[1]["body"]["diagnosticsStartSequence"] == 2
    status = client.status()
    assert status["unacknowledgedDiagnostics"] == []
    assert status["acknowledgedDiagnosticSequence"] == 1


def test_lost_heartbeat_response_replays_sequence_with_max_occurrences():
    requester = ScriptedRequester(
        {
            "/v1/runtime/heartbeat": [
                DesktopBrokerHttpError("connection_failed", "lost heartbeat response"),
                {"status": "connected", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 1},
            ]
        }
    )
    client = make_client(requester, wall_time=lambda: 200.0)
    client._connect()
    message = "[WinError 10053] software caused connection abort"
    client._handle_transport_failure("connection_failed", message, retryable=True)

    with pytest.raises(DesktopBrokerHttpError, match="lost heartbeat response"):
        client._heartbeat()
    client._handle_transport_failure("connection_failed", message, retryable=True)
    client._heartbeat()

    heartbeat_calls = [call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat"]
    assert heartbeat_calls[0]["body"]["diagnostics"][0]["sequence"] == 1
    assert heartbeat_calls[0]["body"]["diagnostics"][0]["occurrences"] == 1
    assert heartbeat_calls[1]["body"]["diagnostics"][0]["sequence"] == 1
    assert heartbeat_calls[1]["body"]["diagnostics"][0]["occurrences"] == 2
    assert client.status()["unacknowledgedDiagnostics"] == []
    assert client.status()["activeDiagnostic"]["occurrences"] == 2


def test_active_failure_heartbeat_accepts_degraded_broker_response():
    requester = ScriptedRequester({"/v1/runtime/heartbeat": [{"status": "degraded", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 1}]})
    client = make_client(requester)
    client._connect()
    client._handle_transport_failure("connection_failed", "still unresolved", retryable=True)

    client._heartbeat()

    assert client.status()["activeDiagnostic"]["message"] == "still unresolved"
    assert client.status()["unacknowledgedDiagnostics"] == []
    assert client.status()["acknowledgedDiagnosticSequence"] == 1


def test_diagnostic_gap_acknowledgement_keeps_unacknowledged_prefix():
    requester = ScriptedRequester({"/v1/runtime/heartbeat": [{"status": "connected", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 0}]})
    client = make_client(requester)
    client._record_diagnostic("first", "must remain pending")
    client._connect()

    client._heartbeat()

    assert [item["sequence"] for item in client.status()["unacknowledgedDiagnostics"]] == [1]
    assert client.status()["acknowledgedDiagnosticSequence"] == 0


def test_heartbeat_rejects_diagnostic_acknowledgement_beyond_sent_batch():
    requester = ScriptedRequester(
        {
            "/v1/runtime/heartbeat": [
                {
                    "status": "connected",
                    "acknowledgedSequence": 0,
                    "acknowledgedDiagnosticSequence": MAX_DIAGNOSTIC_BATCH_COUNT + 1,
                }
            ]
        }
    )
    client = make_client(requester)
    for index in range(MAX_DIAGNOSTIC_BATCH_COUNT + 2):
        client._record_diagnostic(f"diagnostic_{index}", f"message {index}")
    client._connect()

    with pytest.raises(DesktopBrokerProtocolError, match="exceeds the uploaded heartbeat batch"):
        client._heartbeat()

    heartbeat = next(call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat")
    assert [item["sequence"] for item in heartbeat["body"]["diagnostics"]] == list(range(1, MAX_DIAGNOSTIC_BATCH_COUNT + 1))
    assert [item["sequence"] for item in client.status()["unacknowledgedDiagnostics"]] == list(range(1, MAX_DIAGNOSTIC_BATCH_COUNT + 3))
    assert client.status()["acknowledgedDiagnosticSequence"] == 0


def test_diagnostic_history_truncation_retains_valid_sequence_metadata():
    requester = ScriptedRequester()
    client = make_client(requester, wall_time=lambda: 300.0)
    for index in range(MAX_DIAGNOSTIC_COUNT + 3):
        client._record_diagnostic(f"diagnostic_{index}", f"message {index}")

    status = client.status()
    assert status["unacknowledgedDiagnosticCount"] == MAX_DIAGNOSTIC_COUNT
    assert status["unacknowledgedDiagnosticBytes"] <= MAX_DIAGNOSTIC_HISTORY_BYTES
    assert status["diagnosticsStartSequence"] == 4
    assert status["diagnosticsTruncated"] is True
    assert [item["sequence"] for item in status["unacknowledgedDiagnostics"][:2]] == [4, 5]

    client._connect()
    client._heartbeat()
    heartbeat = next(call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat")
    assert heartbeat["body"]["diagnosticsStartSequence"] == 4
    assert heartbeat["body"]["diagnosticsTruncated"] is True
    assert [item["sequence"] for item in heartbeat["body"]["diagnostics"]] == list(range(4, 12))
    assert client.status()["acknowledgedDiagnosticSequence"] == 11
    assert client.status()["diagnosticsStartSequence"] == 12


def test_diagnostic_message_and_heartbeat_batch_have_encoded_byte_bounds(monkeypatch):
    message = "\N{SNOWMAN}" * MAX_DIAGNOSTIC_MESSAGE_BYTES
    message_client = make_client()
    message_client._record_diagnostic("unicode", message)
    bounded_message = message_client.status()["unacknowledgedDiagnostics"][0]["message"]
    assert len(bounded_message.encode("utf-8")) <= MAX_DIAGNOSTIC_MESSAGE_BYTES

    monkeypatch.setattr(desktop_broker_module, "MAX_DIAGNOSTIC_BATCH_BYTES", 400)
    requester = ScriptedRequester()
    client = make_client(requester)
    client._record_diagnostic("first", "x" * 200)
    client._record_diagnostic("second", "y" * 200)
    client._connect()

    client._heartbeat()

    heartbeat = next(call for call in requester.calls if call["path"] == "/v1/runtime/heartbeat")
    diagnostics = heartbeat["body"]["diagnostics"]
    assert len(diagnostics) == 1
    encoded = json.dumps({"diagnostics": diagnostics}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(encoded) <= desktop_broker_module.MAX_DIAGNOSTIC_BATCH_BYTES
    assert desktop_broker_module.MAX_DIAGNOSTIC_BATCH_BYTES < MAX_DIAGNOSTIC_BATCH_BYTES


def test_heartbeat_and_command_poll_recover_after_transient_failure():
    requester = ScriptedRequester(
        {
            "/v1/runtime/connect": [
                {"status": "connected", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 0},
                {"status": "reconnecting", "acknowledgedSequence": 0, "acknowledgedDiagnosticSequence": 0},
            ],
            "/v1/runtime/commands": [
                DesktopBrokerHttpError("connection_failed", "poll outage"),
                {"commands": []},
            ],
        }
    )
    client = make_client(requester)
    client._connect()
    client._heartbeat()
    with pytest.raises(DesktopBrokerHttpError) as error:
        client._poll_commands()
    client._handle_transport_failure(error.value.code, str(error.value), retryable=True)
    assert client.status()["status"] == "reconnecting"

    client._connect()
    client._heartbeat()
    client._poll_commands()
    assert client.status()["status"] == "connected"
    assert client.status()["lastHeartbeatAt"] is not None
