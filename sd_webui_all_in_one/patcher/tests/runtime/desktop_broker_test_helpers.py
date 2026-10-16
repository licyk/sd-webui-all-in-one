"""桌面端代理测试辅助工具"""

from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import (
    BROKER_URL_ENV,
    PROTOCOL_VERSION_ENV,
    RUNTIME_IDENTITY_ENV,
    SESSION_ID_ENV,
    SESSION_TOKEN_ENV,
    DesktopBrokerClient,
    DesktopBrokerSettings,
)
from sd_webui_all_in_one_hotpatcher.runtime.transport_mode import TRANSPORT_MODE_ENV


def make_desktop_env(**updates):
    values = {
        TRANSPORT_MODE_ENV: "desktop_broker",
        BROKER_URL_ENV: "http://127.0.0.1:43123",
        SESSION_ID_ENV: "session-1",
        SESSION_TOKEN_ENV: "unpredictable-token",
        RUNTIME_IDENTITY_ENV: "runtime-1",
        PROTOCOL_VERSION_ENV: "2",
    }
    values.update(updates)
    return values


class ScriptedRequester:
    def __init__(self, scripts=None):
        self.scripts = {path: list(items) for path, items in (scripts or {}).items()}
        self.calls = []
        self.acknowledged_diagnostic_sequence = 0

    def request(self, method, path, *, body=None, query=None, timeout):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "body": body,
                "query": query,
                "timeout": timeout,
            }
        )
        items = self.scripts.setdefault(path, [])
        if items:
            value = items.pop(0)
            if isinstance(value, BaseException):
                raise value
            if callable(value):
                return value(self.calls[-1])
            return value
        if path == "/v1/runtime/connect":
            return {
                "status": "connected",
                "acknowledgedSequence": 0,
                "acknowledgedDiagnosticSequence": self.acknowledged_diagnostic_sequence,
            }
        if path == "/v1/runtime/events":
            assert body is not None
            events = body["events"]
            return {"acknowledgedSequence": events[-1]["sequence"]}
        if path == "/v1/runtime/commands":
            return {"commands": []}
        if path == "/v1/runtime/results":
            assert body is not None
            return {"acceptedCommandIds": [item["commandId"] for item in body["results"]]}
        if path == "/v1/runtime/heartbeat":
            assert body is not None
            diagnostics = body["diagnostics"]
            start = body["diagnosticsStartSequence"]
            if body["diagnosticsTruncated"] and start > self.acknowledged_diagnostic_sequence + 1:
                self.acknowledged_diagnostic_sequence = start - 1
            for diagnostic in diagnostics:
                if diagnostic["sequence"] != self.acknowledged_diagnostic_sequence + 1:
                    break
                self.acknowledged_diagnostic_sequence = diagnostic["sequence"]
            return {
                "status": "connected",
                "acknowledgedSequence": body["lastAcknowledgedSequence"],
                "acknowledgedDiagnosticSequence": self.acknowledged_diagnostic_sequence,
            }
        return {}


def make_client(requester=None, **kwargs):
    return DesktopBrokerClient(
        DesktopBrokerSettings.from_env(make_desktop_env()),
        requester=requester or ScriptedRequester(),
        **kwargs,
    )
