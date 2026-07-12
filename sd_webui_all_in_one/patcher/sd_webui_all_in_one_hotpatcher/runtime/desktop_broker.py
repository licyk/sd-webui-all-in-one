"""Bounded asynchronous client for the Rust-owned desktop runtime broker."""

from __future__ import annotations

import atexit
import hashlib
import ipaddress
import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Protocol

from .interfaces import RuntimeCommandHandler

BROKER_URL_ENV = "SD_WEBUI_ALL_IN_ONE_RUNTIME_BROKER_URL"
SESSION_ID_ENV = "SD_WEBUI_ALL_IN_ONE_RUNTIME_SESSION_ID"
SESSION_TOKEN_ENV = "SD_WEBUI_ALL_IN_ONE_RUNTIME_TOKEN"
RUNTIME_IDENTITY_ENV = "SD_WEBUI_ALL_IN_ONE_RUNTIME_IDENTITY"
PROTOCOL_VERSION_ENV = "SD_WEBUI_ALL_IN_ONE_RUNTIME_PROTOCOL_VERSION"
PROTOCOL_VERSION = "1"

MAX_EVENT_COUNT = 256
BROWSER_RESERVED_EVENT_CAPACITY = 16
MAX_EVENT_PAYLOAD_BYTES = 16 * 1024
MAX_EVENT_BATCH_COUNT = 32
MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
MAX_COMMAND_RESULT_BYTES = 64 * 1024
MAX_DIAGNOSTIC_COUNT = 64
MAX_DIAGNOSTIC_MESSAGE_CHARS = 2048
MAX_RESULT_COUNT = 128
MAX_COMMAND_HISTORY = 256
MAX_COMMAND_BATCH_COUNT = 32
MAX_IDENTIFIER_CHARS = 256
MAX_SEQUENCE = (1 << 63) - 1
DEFAULT_CONNECT_TIMEOUT = 2.0
DEFAULT_REQUEST_TIMEOUT = 2.0
DEFAULT_LONG_POLL_MILLISECONDS = 100
DEFAULT_HEARTBEAT_SECONDS = 5.0
DEFAULT_FINAL_FLUSH_SECONDS = 0.5
MIN_RECONNECT_SECONDS = 0.1
MAX_RECONNECT_SECONDS = 5.0


class DesktopBrokerConfigurationError(ValueError):
    """The explicit desktop broker environment is incomplete or unsafe."""


class DesktopBrokerProtocolError(RuntimeError):
    """The broker returned a response that violates protocol version 1."""


class DesktopBrokerCommandError(RuntimeError):
    """A broker command produced a stable typed failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class DesktopBrokerHttpError(RuntimeError):
    """An HTTP operation failed with a classified broker diagnostic."""

    def __init__(self, code: str, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class DesktopTransportStatus(str, Enum):
    """Desktop transport health independent from local interception state."""

    STARTING = "starting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    CLOSED = "closed"


@dataclass(frozen=True)
class DesktopBrokerSettings:
    """Validated environment supplied by the Rust launch owner."""

    broker_url: str
    session_id: str
    session_token: str
    runtime_identity: str
    protocol_version: str = PROTOCOL_VERSION

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "DesktopBrokerSettings":
        source = os.environ if environ is None else environ
        required = {
            BROKER_URL_ENV: source.get(BROKER_URL_ENV, ""),
            SESSION_ID_ENV: source.get(SESSION_ID_ENV, ""),
            SESSION_TOKEN_ENV: source.get(SESSION_TOKEN_ENV, ""),
            RUNTIME_IDENTITY_ENV: source.get(RUNTIME_IDENTITY_ENV, ""),
            PROTOCOL_VERSION_ENV: source.get(PROTOCOL_VERSION_ENV, ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise DesktopBrokerConfigurationError("desktop_broker requires environment variables: " + ", ".join(missing))
        if len(required[BROKER_URL_ENV]) > 2048:
            raise DesktopBrokerConfigurationError(f"{BROKER_URL_ENV} exceeds 2048 characters")
        version = required[PROTOCOL_VERSION_ENV]
        if version != PROTOCOL_VERSION:
            raise DesktopBrokerConfigurationError(f"Unsupported {PROTOCOL_VERSION_ENV} value {version!r}; supported value: {PROTOCOL_VERSION}")
        for name in (SESSION_ID_ENV, SESSION_TOKEN_ENV, RUNTIME_IDENTITY_ENV):
            if len(required[name]) > MAX_IDENTIFIER_CHARS:
                raise DesktopBrokerConfigurationError(f"{name} exceeds {MAX_IDENTIFIER_CHARS} characters")

        parsed = urllib.parse.urlsplit(required[BROKER_URL_ENV])
        try:
            port = parsed.port
        except ValueError as exc:
            raise DesktopBrokerConfigurationError(f"{BROKER_URL_ENV} must be an HTTP loopback origin with an explicit port") from exc
        if (
            parsed.scheme != "http"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or port is None
            or port == 0
            or not _is_loopback_hostname(parsed.hostname)
        ):
            raise DesktopBrokerConfigurationError(f"{BROKER_URL_ENV} must be an HTTP loopback origin with an explicit port")
        origin = f"http://{_format_url_host(parsed.hostname or '')}:{port}"
        return cls(
            broker_url=origin,
            session_id=required[SESSION_ID_ENV],
            session_token=required[SESSION_TOKEN_ENV],
            runtime_identity=required[RUNTIME_IDENTITY_ENV],
            protocol_version=version,
        )

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.session_token}",
            "X-Runtime-Protocol-Version": self.protocol_version,
            "X-Runtime-Session-Id": self.session_id,
            "X-Runtime-Identity": self.runtime_identity,
        }


@dataclass(frozen=True)
class OutboundRuntimeEvent:
    sequence: int
    eventType: str
    payload: dict[str, Any]
    createdAt: float


@dataclass
class DesktopTransportDiagnostic:
    code: str
    message: str
    createdAt: float
    occurrences: int = 1


class BrokerHttpRequester(Protocol):
    """Injectable bounded HTTP boundary used by deterministic tests."""

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        """Issue one broker request and return its JSON object response."""


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects before urllib can copy session headers elsewhere."""

    def _reject(self, request: Any, response: Any, code: int, message: str, headers: Any) -> None:
        del request, code, message, headers
        response.close()
        raise DesktopBrokerHttpError(
            "redirect_rejected",
            "runtime broker redirects are not permitted by protocol version 1",
            retryable=False,
        )

    http_error_301 = _reject
    http_error_302 = _reject
    http_error_303 = _reject
    http_error_307 = _reject
    http_error_308 = _reject


class StandardLibraryBrokerHttp:
    """Short-request HTTP implementation with strict response bounds."""

    def __init__(self, settings: DesktopBrokerSettings):
        self.settings = settings
        # Broker credentials must never follow ambient HTTP(S)_PROXY settings.
        # The validated destination is a literal loopback address.
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _RejectRedirectHandler(),
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        url = self.settings.broker_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        encoded: bytes | None = None
        headers = self.settings.headers()
        if body is not None:
            encoded = _encode_json(body)
            if len(encoded) > MAX_REQUEST_BYTES:
                raise DesktopBrokerProtocolError(f"broker request exceeds {MAX_REQUEST_BYTES} bytes")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=encoded, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            code = "request_rejected"
            retryable = exc.code >= 500 or exc.code in {408, 429}
            if exc.code in {401, 403}:
                code = "authentication_rejected"
                retryable = False
            elif exc.code in {409, 426}:
                code = "protocol_mismatch"
                retryable = False
            raise DesktopBrokerHttpError(
                code,
                f"broker {method} {path} returned HTTP {exc.code}",
                retryable=retryable,
            ) from exc
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise DesktopBrokerHttpError(
                "connection_failed",
                f"broker {method} {path} failed: {exc}",
            ) from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise DesktopBrokerProtocolError(f"broker response exceeds {MAX_RESPONSE_BYTES} bytes")
        if not raw:
            return {}
        try:
            decoded = _decode_json(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise DesktopBrokerProtocolError("broker response is not valid UTF-8 JSON") from exc
        if not isinstance(decoded, dict):
            raise DesktopBrokerProtocolError("broker response must be a JSON object")
        return decoded


class DesktopBrokerClient:
    """Independent desktop transport with bounded replay and command state."""

    def __init__(
        self,
        settings: DesktopBrokerSettings,
        *,
        requester: BrokerHttpRequester | None = None,
        command_handler: RuntimeCommandHandler | None = None,
        event_capacity: int = MAX_EVENT_COUNT,
        browser_reserved_capacity: int | None = None,
        final_flush_seconds: float = DEFAULT_FINAL_FLUSH_SECONDS,
        heartbeat_seconds: float = DEFAULT_HEARTBEAT_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        wall_time: Callable[[], float] = time.time,
    ) -> None:
        if not 1 <= event_capacity <= MAX_EVENT_COUNT:
            raise ValueError(f"event_capacity must be between 1 and {MAX_EVENT_COUNT}")
        if browser_reserved_capacity is None:
            browser_reserved_capacity = max(
                1,
                math.ceil(event_capacity * BROWSER_RESERVED_EVENT_CAPACITY / MAX_EVENT_COUNT),
            )
        if not 1 <= browser_reserved_capacity <= event_capacity:
            raise ValueError("browser_reserved_capacity must be between 1 and event_capacity")
        self.settings = settings
        self._requester = requester or StandardLibraryBrokerHttp(settings)
        self._command_handler = command_handler or _unavailable_command_handler
        self._event_capacity = event_capacity
        self._browser_reserved_capacity = browser_reserved_capacity
        self._ordinary_event_capacity = event_capacity - browser_reserved_capacity
        self._final_flush_seconds = max(0.0, final_flush_seconds)
        self._heartbeat_seconds = max(0.1, heartbeat_seconds)
        self._monotonic = monotonic
        self._wall_time = wall_time
        self._condition = threading.Condition(threading.RLock())
        self._events: deque[OutboundRuntimeEvent] = deque()
        self._results: deque[dict[str, Any]] = deque()
        self._queued_result_ids: set[str] = set()
        self._command_history: OrderedDict[str, tuple[int, str, dict[str, Any]]] = OrderedDict()
        self._diagnostics: deque[DesktopTransportDiagnostic] = deque(maxlen=MAX_DIAGNOSTIC_COUNT)
        self._next_sequence = 1
        self._acknowledged_sequence = 0
        self._command_sequence = 0
        self._status = DesktopTransportStatus.STARTING
        self._started = False
        self._ever_connected = False
        self._closing = False
        self._closed = False
        self._close_deadline: float | None = None
        self._last_heartbeat_at: float | None = None
        self._last_heartbeat_monotonic: float | None = None
        self._last_success_at: float | None = None
        self._reconnect_delay = MIN_RECONNECT_SECONDS
        self._thread: threading.Thread | None = None
        self._atexit_registered = False

    @classmethod
    def from_env(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> "DesktopBrokerClient":
        return cls(DesktopBrokerSettings.from_env(environ), **kwargs)

    def start(self) -> "DesktopBrokerClient":
        """Start one daemon worker; no network operation runs on this caller."""

        with self._condition:
            if self._closed:
                raise RuntimeError("desktop broker client is closed")
            if self._started:
                return self
            self._started = True
            self._thread = threading.Thread(
                target=self._run,
                name="sd-webui-aio-desktop-broker",
                daemon=True,
            )
            self._thread.start()
            if not self._atexit_registered:
                atexit.register(self.close)
                self._atexit_registered = True
        return self

    def emit_event(self, event_type: str, payload: dict[str, Any] | None = None) -> bool:
        """Enqueue one event without performing network I/O or waiting."""

        if not isinstance(event_type, str) or not event_type or len(event_type) > 128:
            self._record_diagnostic("event_rejected", "event type must contain 1 to 128 characters")
            return False
        normalized_payload = {} if payload is None else payload
        if not isinstance(normalized_payload, dict):
            self._record_diagnostic("event_rejected", "event payload must be an object")
            return False
        try:
            encoded_payload = _encode_json(normalized_payload)
            payload_size = len(encoded_payload)
        except (TypeError, ValueError):
            self._record_diagnostic("event_rejected", "event payload must be JSON serializable")
            return False
        if payload_size > MAX_EVENT_PAYLOAD_BYTES:
            self._record_diagnostic(
                "event_rejected",
                f"event payload exceeds {MAX_EVENT_PAYLOAD_BYTES} bytes",
            )
            return False
        # Detach the queued event from caller-owned mutable dictionaries after
        # validating it. The background worker must see the exact snapshot
        # that was accepted here.
        payload_snapshot = _decode_json(encoded_payload)
        broker_event_type = _broker_event_type(event_type)
        if broker_event_type != event_type:
            payload_snapshot["sourceEventType"] = event_type
            if len(_encode_json(payload_snapshot)) > MAX_EVENT_PAYLOAD_BYTES:
                self._record_diagnostic(
                    "event_rejected",
                    f"mapped event payload exceeds {MAX_EVENT_PAYLOAD_BYTES} bytes",
                )
                return False
        with self._condition:
            if self._closing or self._closed:
                self._record_diagnostic_locked("transport_closed", "event rejected after transport close")
                return False
            is_browser_event = broker_event_type == "browser.open"
            if not is_browser_event and len(self._events) >= self._ordinary_event_capacity:
                self._record_diagnostic_locked(
                    "ordinary_event_capacity_exhausted",
                    (f"ordinary event queue reached its {self._ordinary_event_capacity}-event admission limit; {self._browser_reserved_capacity} slots are reserved for browser.open"),
                )
                return False
            if is_browser_event and len(self._events) >= self._event_capacity:
                self._record_diagnostic_locked(
                    "critical_event_capacity_exhausted",
                    f"outbound event queue reached its {self._event_capacity}-event hard limit; browser.open was rejected",
                )
                return False
            if self._next_sequence > MAX_SEQUENCE:
                self._record_diagnostic_locked(
                    "sequence_exhausted",
                    "outbound event sequence reached its protocol bound",
                )
                return False
            created_at = self._wall_time()
            if not _is_finite_nonnegative_number(created_at):
                self._record_diagnostic_locked(
                    "clock_invalid",
                    "wall clock did not produce a finite non-negative timestamp",
                )
                return False
            event = OutboundRuntimeEvent(
                sequence=self._next_sequence,
                eventType=broker_event_type,
                payload=payload_snapshot,
                createdAt=created_at,
            )
            self._next_sequence += 1
            self._events.append(event)
            self._condition.notify_all()
            return True

    def event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Compatibility spelling shared with the legacy RuntimeClient."""

        self.emit_event(event_type, payload)

    def set_command_handler(self, handler: RuntimeCommandHandler) -> None:
        with self._condition:
            self._command_handler = handler

    def status(self) -> dict[str, Any]:
        with self._condition:
            return {
                "transport": "desktop_broker",
                "status": self._status.value,
                "runtimeIdentity": self.settings.runtime_identity,
                "sessionId": self.settings.session_id,
                "protocolVersion": self.settings.protocol_version,
                "queuedEventCount": len(self._events),
                "queuedResultCount": len(self._results),
                "acknowledgedSequence": self._acknowledged_sequence,
                "lastHeartbeatAt": self._last_heartbeat_at,
                "lastSuccessAt": self._last_success_at,
                "diagnostics": [asdict(item) for item in self._diagnostics],
            }

    def close(self, *, flush_timeout: float | None = None) -> None:
        """Request shutdown and wait no longer than the bounded flush deadline."""

        timeout = self._final_flush_seconds if flush_timeout is None else max(0.0, flush_timeout)
        with self._condition:
            if self._closed:
                return
            if not self._started:
                self._closed = True
                self._closing = True
                self._status = DesktopTransportStatus.CLOSED
                if self._events or self._results:
                    self._record_diagnostic_locked(
                        "final_flush_incomplete",
                        "desktop broker closed before its worker was started",
                    )
                return
            self._closing = True
            self._close_deadline = self._monotonic() + timeout
            thread = self._thread
            self._condition.notify_all()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        with self._condition:
            self._closed = True
            self._status = DesktopTransportStatus.CLOSED
            if self._events or self._results:
                self._record_diagnostic_locked(
                    "final_flush_incomplete",
                    "desktop broker final flush deadline expired with pending state",
                )
            self._condition.notify_all()
        if self._atexit_registered:
            atexit.unregister(self.close)
            self._atexit_registered = False

    def _run(self) -> None:
        while True:
            with self._condition:
                if self._closed:
                    return
                closing = self._closing
                close_deadline = self._close_deadline
                work_pending = bool(self._events or self._results)
                if closing and (not work_pending or close_deadline is None or self._monotonic() >= close_deadline):
                    self._closed = True
                    self._status = DesktopTransportStatus.CLOSED
                    return
            try:
                self._run_cycle(flushing=closing)
                self._reconnect_delay = MIN_RECONNECT_SECONDS
            except DesktopBrokerHttpError as exc:
                self._handle_transport_failure(exc.code, str(exc), retryable=exc.retryable)
            except DesktopBrokerProtocolError as exc:
                self._handle_transport_failure("protocol_mismatch", str(exc), retryable=False)
            except Exception as exc:  # defensive: the daemon must never escape noisily
                self._handle_transport_failure(
                    "client_failure",
                    f"desktop broker worker failed: {type(exc).__name__}: {exc}",
                    retryable=True,
                )

            with self._condition:
                if self._closed:
                    return
                if self._closing:
                    deadline = self._close_deadline or self._monotonic()
                    wait_for = max(0.0, min(0.02, deadline - self._monotonic()))
                elif self._status == DesktopTransportStatus.CONNECTED:
                    wait_for = 0.02 if self._events or self._results else 0.1
                else:
                    wait_for = self._reconnect_delay
                    self._reconnect_delay = min(MAX_RECONNECT_SECONDS, self._reconnect_delay * 2)
                self._condition.wait(timeout=wait_for)

    def _run_cycle(self, *, flushing: bool = False) -> None:
        """Perform one deterministic protocol cycle (also used by tests)."""

        with self._condition:
            connected = self._status == DesktopTransportStatus.CONNECTED
        if not connected:
            self._connect()
        with self._condition:
            if self._closed:
                return
        self._upload_events()
        with self._condition:
            if self._closed:
                return
        self._upload_results()
        if flushing:
            return
        now = self._monotonic()
        if self._last_heartbeat_monotonic is None or now - self._last_heartbeat_monotonic >= self._heartbeat_seconds:
            self._heartbeat()
        self._poll_commands()

    def _connect(self) -> None:
        response = self._requester.request(
            "POST",
            "/v1/runtime/connect",
            body={},
            timeout=DEFAULT_CONNECT_TIMEOUT,
        )
        if response.get("status") not in {"connected", "reconnecting"}:
            raise DesktopBrokerProtocolError("connect response status must be connected or reconnecting")
        acknowledgement = _optional_nonnegative_int(response, "acknowledgedSequence", default=0)
        with self._condition:
            if self._closed:
                return
            if self._events and acknowledgement >= self._next_sequence:
                raise DesktopBrokerProtocolError("connect acknowledgement exceeds the local event sequence")
            self._discard_acknowledged_locked(acknowledgement)
            if not self._events and acknowledgement >= self._next_sequence:
                self._next_sequence = acknowledgement + 1
            self._ever_connected = True
            self._status = DesktopTransportStatus.CONNECTED
            self._last_success_at = self._wall_time()

    def _upload_events(self) -> None:
        with self._condition:
            batch = _bounded_event_batch(self._events)
        if not batch:
            return
        response = self._requester.request(
            "POST",
            "/v1/runtime/events",
            body={"events": [asdict(item) for item in batch]},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        acknowledgement = _required_nonnegative_int(response, "acknowledgedSequence")
        if acknowledgement > batch[-1].sequence:
            raise DesktopBrokerProtocolError("event acknowledgement exceeds the uploaded batch")
        with self._condition:
            self._discard_acknowledged_locked(acknowledgement)
            self._last_success_at = self._wall_time()

    def _heartbeat(self) -> None:
        with self._condition:
            diagnostics = [asdict(item) for item in list(self._diagnostics)[-8:]]
            body = {
                "transportStatus": self._status.value,
                "lastAcknowledgedSequence": self._acknowledged_sequence,
                "queuedEventCount": len(self._events),
                "diagnostics": diagnostics,
            }
        self._requester.request(
            "POST",
            "/v1/runtime/heartbeat",
            body=body,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        with self._condition:
            self._last_heartbeat_monotonic = self._monotonic()
            self._last_heartbeat_at = self._wall_time()
            self._last_success_at = self._wall_time()

    def _poll_commands(self) -> None:
        with self._condition:
            after_sequence = self._command_sequence
            wait_ms = 0 if self._events else DEFAULT_LONG_POLL_MILLISECONDS
        response = self._requester.request(
            "GET",
            "/v1/runtime/commands",
            query={"afterSequence": str(after_sequence), "waitMs": str(wait_ms)},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        with self._condition:
            if self._closed:
                return
        commands = response.get("commands", [])
        if not isinstance(commands, list) or len(commands) > MAX_COMMAND_BATCH_COUNT:
            raise DesktopBrokerProtocolError(f"commands must be an array of at most {MAX_COMMAND_BATCH_COUNT} items")
        for command in commands:
            self._accept_command(command)
        with self._condition:
            self._last_success_at = self._wall_time()

    def _accept_command(self, command: Any) -> None:
        if not isinstance(command, dict):
            raise DesktopBrokerProtocolError("command must be an object")
        command_id = command.get("commandId")
        sequence = command.get("sequence")
        command_type = command.get("commandType")
        payload = command.get("payload", {})
        if not isinstance(command_id, str) or not command_id or len(command_id) > MAX_IDENTIFIER_CHARS:
            raise DesktopBrokerProtocolError("commandId must be a bounded non-empty string")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= MAX_SEQUENCE:
            raise DesktopBrokerProtocolError(f"command sequence must be an integer between 1 and {MAX_SEQUENCE}")
        if not isinstance(command_type, str) or not command_type or len(command_type) > 128:
            raise DesktopBrokerProtocolError("commandType must be a bounded non-empty string")
        if not isinstance(payload, dict):
            raise DesktopBrokerProtocolError("command payload must be an object")
        created_at = command.get("createdAt")
        deadline = command.get("deadline")
        if not _is_finite_nonnegative_number(created_at):
            raise DesktopBrokerProtocolError("command createdAt must be a finite non-negative number")
        if not _is_finite_nonnegative_number(deadline):
            raise DesktopBrokerProtocolError("command deadline must be a finite non-negative number")
        fingerprint = _command_fingerprint(command_type, payload)

        with self._condition:
            cached_entry = self._command_history.get(command_id)
            last_command_sequence = self._command_sequence
        if cached_entry is not None:
            cached_sequence, cached_fingerprint, cached_result = cached_entry
            if sequence != cached_sequence or fingerprint != cached_fingerprint:
                raise DesktopBrokerProtocolError(f"command ID {command_id!r} was redelivered with different content")
            self._queue_result(cached_result)
            with self._condition:
                self._command_sequence = max(self._command_sequence, sequence)
            return
        if sequence <= last_command_sequence:
            raise DesktopBrokerProtocolError(f"new command sequence must advance beyond {last_command_sequence}, received {sequence}")

        try:
            if float(deadline) < self._wall_time():
                raise DesktopBrokerCommandError(
                    "command_expired",
                    f"command {command_id!r} expired before execution",
                )
            handler_result = self._command_handler(command_type, payload)
            if not isinstance(handler_result, dict):
                raise TypeError("command handler result must be an object")
            if len(_encode_json(handler_result)) > MAX_COMMAND_RESULT_BYTES:
                raise DesktopBrokerCommandError(
                    "result_too_large",
                    f"command result exceeds {MAX_COMMAND_RESULT_BYTES} bytes",
                )
            result = {
                "commandId": command_id,
                "ok": True,
                "payload": handler_result,
                "completedAt": self._wall_time(),
            }
        except DesktopBrokerCommandError as exc:
            result = {
                "commandId": command_id,
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": _bounded_error_message(str(exc)),
                },
                "completedAt": self._wall_time(),
            }
            self._record_diagnostic(exc.code, f"command {command_id!r} was rejected: {exc}")
        except Exception as exc:
            result = {
                "commandId": command_id,
                "ok": False,
                "error": {
                    "code": "command_failed",
                    "message": _bounded_error_message(f"{type(exc).__name__}: {exc}"),
                },
                "completedAt": self._wall_time(),
            }
            self._record_diagnostic("command_failed", f"command {command_id!r} failed: {exc}")
        with self._condition:
            self._command_history[command_id] = (sequence, fingerprint, result)
            self._command_history.move_to_end(command_id)
            while len(self._command_history) > MAX_COMMAND_HISTORY:
                self._command_history.popitem(last=False)
            self._command_sequence = max(self._command_sequence, sequence)
        self._queue_result(result)

    def _queue_result(self, result: dict[str, Any]) -> None:
        command_id = str(result["commandId"])
        with self._condition:
            if command_id in self._queued_result_ids:
                return
            if len(self._results) >= MAX_RESULT_COUNT:
                self._record_diagnostic_locked(
                    "result_queue_overflow",
                    f"command result queue reached its {MAX_RESULT_COUNT}-result bound",
                )
                return
            self._results.append(result)
            self._queued_result_ids.add(command_id)

    def _upload_results(self) -> None:
        with self._condition:
            batch = _bounded_result_batch(self._results)
        if not batch:
            return
        response = self._requester.request(
            "POST",
            "/v1/runtime/results",
            body={"results": batch},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        accepted = response.get("acceptedCommandIds")
        if not isinstance(accepted, list) or any(not isinstance(item, str) for item in accepted):
            raise DesktopBrokerProtocolError("acceptedCommandIds must be an array of strings")
        accepted_ids = set(accepted)
        sent_ids = {str(item["commandId"]) for item in batch}
        if not accepted_ids.issubset(sent_ids):
            raise DesktopBrokerProtocolError("result acknowledgement contains an unknown command ID")
        with self._condition:
            self._results = deque(item for item in self._results if str(item["commandId"]) not in accepted_ids)
            self._queued_result_ids.difference_update(accepted_ids)
            self._last_success_at = self._wall_time()

    def _discard_acknowledged_locked(self, acknowledgement: int) -> None:
        if acknowledgement < self._acknowledged_sequence:
            return
        self._acknowledged_sequence = acknowledgement
        while self._events and self._events[0].sequence <= acknowledgement:
            self._events.popleft()

    def _handle_transport_failure(self, code: str, message: str, *, retryable: bool) -> None:
        with self._condition:
            if self._closed:
                return
            self._record_diagnostic_locked(code, message)
            if retryable:
                self._status = DesktopTransportStatus.RECONNECTING if self._ever_connected else DesktopTransportStatus.DISCONNECTED
            else:
                self._status = DesktopTransportStatus.DEGRADED

    def _record_diagnostic(self, code: str, message: str) -> None:
        with self._condition:
            self._record_diagnostic_locked(code, message)

    def _record_diagnostic_locked(self, code: str, message: str) -> None:
        message = message[:MAX_DIAGNOSTIC_MESSAGE_CHARS]
        if self._diagnostics and self._diagnostics[-1].code == code and self._diagnostics[-1].message == message:
            self._diagnostics[-1].occurrences += 1
            return
        self._diagnostics.append(DesktopTransportDiagnostic(code=code, message=message, createdAt=self._wall_time()))


def _bounded_event_batch(events: deque[OutboundRuntimeEvent]) -> list[OutboundRuntimeEvent]:
    batch: list[OutboundRuntimeEvent] = []
    for event in list(events)[:MAX_EVENT_BATCH_COUNT]:
        candidate = batch + [event]
        if len(_encode_json({"events": [asdict(item) for item in candidate]})) > MAX_REQUEST_BYTES:
            break
        batch = candidate
    return batch


def _bounded_result_batch(results: deque[dict[str, Any]]) -> list[dict[str, Any]]:
    batch: list[dict[str, Any]] = []
    for result in list(results)[:MAX_COMMAND_BATCH_COUNT]:
        candidate = batch + [result]
        if len(_encode_json({"results": candidate})) > MAX_REQUEST_BYTES:
            break
        batch = candidate
    return batch


def _required_nonnegative_int(response: dict[str, Any], key: str) -> int:
    if key not in response:
        raise DesktopBrokerProtocolError(f"broker response is missing {key}")
    return _optional_nonnegative_int(response, key, default=0)


def _optional_nonnegative_int(response: dict[str, Any], key: str, *, default: int) -> int:
    value = response.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= MAX_SEQUENCE:
        raise DesktopBrokerProtocolError(f"broker response {key} must be an integer between 0 and {MAX_SEQUENCE}")
    return value


def _encode_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _decode_json(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        parse_constant=_reject_json_constant,
    )


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"invalid JSON constant: {value}")


def _command_fingerprint(command_type: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        {"commandType": command_type, "payload": payload},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bounded_error_message(message: str) -> str:
    return message[:MAX_DIAGNOSTIC_MESSAGE_CHARS]


def _broker_event_type(event_type: str) -> str:
    for prefix, canonical in (
        ("log.", "runtime.log"),
        ("error.", "runtime.error"),
        ("progress.", "runtime.progress"),
    ):
        if event_type.startswith(prefix):
            return canonical
    return event_type


def _is_finite_nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) >= 0


def _is_loopback_hostname(hostname: str | None) -> bool:
    if hostname is None:
        return False
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _format_url_host(hostname: str) -> str:
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return hostname.lower()
    return f"[{address.compressed}]" if address.version == 6 else address.compressed


def _unavailable_command_handler(command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    del command_type, payload
    raise RuntimeError("desktop broker command handler is unavailable")


__all__ = [
    "BROKER_URL_ENV",
    "DesktopBrokerClient",
    "DesktopBrokerCommandError",
    "DesktopBrokerConfigurationError",
    "DesktopBrokerHttpError",
    "DesktopBrokerProtocolError",
    "DesktopBrokerSettings",
    "DesktopTransportStatus",
    "PROTOCOL_VERSION",
    "PROTOCOL_VERSION_ENV",
    "RUNTIME_IDENTITY_ENV",
    "SESSION_ID_ENV",
    "SESSION_TOKEN_ENV",
]
