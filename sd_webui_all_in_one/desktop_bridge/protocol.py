"""JSON line protocol for the desktop bridge."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, TextIO

from sd_webui_all_in_one.desktop_bridge.operations import BridgeOperationError, dispatch_operation


def main(stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    """
    Run one desktop bridge request from stdin and write one JSON response line.

    Args:
        stdin (TextIO | None):
            Input stream. Defaults to ``sys.stdin``.
        stdout (TextIO | None):
            Output stream. Defaults to ``sys.stdout``.

    Returns:
        int: Process exit code. Structured operation failures still return 0 so
        Rust can parse the response body.
    """
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    response = handle_request_text(stdin.read())
    write_json_line(stdout, response)
    return 0


def handle_request_text(text: str) -> dict[str, Any]:
    """
    Parse request text and return a bridge response object.

    Args:
        text (str):
            Raw request text.

    Returns:
        dict[str, Any]: JSON-serializable response.
    """
    try:
        request = parse_request_text(text)
    except BridgeOperationError as error:
        return error_response(None, error)

    return handle_request(request)


def parse_request_text(text: str) -> dict[str, Any]:
    """
    Parse a JSON request from stdin text.

    Args:
        text (str):
            Raw stdin text.

    Returns:
        dict[str, Any]: Parsed request object.
    """
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise BridgeOperationError(
                "BRIDGE_REQUEST_INVALID_JSON",
                f"Bridge request is not valid JSON: {error}",
            ) from error
        if not isinstance(value, dict):
            raise BridgeOperationError(
                "BRIDGE_REQUEST_INVALID",
                "Bridge request must be a JSON object",
            )
        return value
    raise BridgeOperationError(
        "BRIDGE_REQUEST_EMPTY",
        "Bridge request stdin did not contain a JSON object",
    )


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatch a parsed request and wrap the result in a bridge response.

    Args:
        request (dict[str, Any]):
            Parsed request object.

    Returns:
        dict[str, Any]: Bridge response.
    """
    request_id = _request_id(request)
    try:
        operation = _operation(request)
        payload = _payload(request)
        data = dispatch_operation(operation, payload)
    except BridgeOperationError as error:
        return error_response(request_id, error)
    except Exception as error:
        return error_response(
            request_id,
            BridgeOperationError(
                "BRIDGE_INTERNAL_ERROR",
                str(error) or error.__class__.__name__,
                {"traceback": traceback.format_exc()},
            ),
        )
    return {
        "requestId": request_id,
        "ok": True,
        "data": data,
    }


def error_response(request_id: str | None, error: BridgeOperationError) -> dict[str, Any]:
    """
    Build a structured bridge error response.

    Args:
        request_id (str | None):
            Request id, when available.
        error (BridgeOperationError):
            Structured operation error.

    Returns:
        dict[str, Any]: Error response object.
    """
    body: dict[str, Any] = {
        "requestId": request_id,
        "ok": False,
        "error": {
            "code": error.code,
            "message": error.message,
        },
    }
    if error.details is not None:
        body["error"]["details"] = error.details
    return body


def write_json_line(stdout: TextIO, value: dict[str, Any]) -> None:
    stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    stdout.write("\n")
    stdout.flush()


def _request_id(request: dict[str, Any]) -> str | None:
    value = request.get("requestId", request.get("request_id"))
    if value is None:
        return None
    return str(value)


def _operation(request: dict[str, Any]) -> str:
    value = request.get("operation")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise BridgeOperationError(
        "BRIDGE_REQUEST_INVALID",
        "Bridge request field operation must be a non-empty string",
        {"field": "operation"},
    )


def _payload(request: dict[str, Any]) -> dict[str, Any]:
    value = request.get("payload", {})
    if isinstance(value, dict):
        return value
    raise BridgeOperationError(
        "BRIDGE_REQUEST_INVALID",
        "Bridge request field payload must be an object",
        {"field": "payload"},
    )
