"""连接 Rust 所有桌面运行时代理的有界异步客户端。"""

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
PROTOCOL_VERSION = "2"

MAX_EVENT_COUNT = 256
BROWSER_RESERVED_EVENT_CAPACITY = 16
MAX_EVENT_PAYLOAD_BYTES = 16 * 1024
MAX_EVENT_BATCH_COUNT = 32
MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
MAX_COMMAND_RESULT_BYTES = 64 * 1024
MAX_DIAGNOSTIC_COUNT = 64
MAX_DIAGNOSTIC_MESSAGE_BYTES = 2048
MAX_DIAGNOSTIC_HISTORY_BYTES = 128 * 1024
MAX_DIAGNOSTIC_BATCH_COUNT = 8
MAX_DIAGNOSTIC_BATCH_BYTES = 64 * 1024
MAX_DIAGNOSTIC_CODE_BYTES = 128
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
HEARTBEAT_RESPONSE_STATUSES = {"connected", "degraded", "reconnecting", "disconnected"}


class DesktopBrokerConfigurationError(ValueError):
    """显式桌面代理环境不完整或不安全。"""


class DesktopBrokerProtocolError(RuntimeError):
    """代理返回违反第二版协议的响应。"""


class DesktopBrokerCommandError(RuntimeError):
    """代理命令产生稳定的强类型故障。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class DesktopBrokerHttpError(RuntimeError):
    """HTTP 操作失败并带有已分类的代理诊断。"""

    def __init__(self, code: str, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class DesktopTransportStatus(str, Enum):
    """独立于本地拦截状态的桌面传输健康状态。"""

    STARTING = "starting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    CLOSED = "closed"


@dataclass(frozen=True)
class DesktopBrokerSettings:
    """由 Rust 启动所有者提供并经过校验的环境。"""

    broker_url: str
    session_id: str
    session_token: str
    runtime_identity: str
    protocol_version: str = PROTOCOL_VERSION

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "DesktopBrokerSettings":
        """从环境变量创建并校验桌面代理设置。

        Args:
            environ (Mapping[str, str] | None): 可选环境变量映射。

        Returns:
            DesktopBrokerSettings: 校验后的桌面代理设置。

        Raises:
            DesktopBrokerConfigurationError: 必需设置缺失或环境不安全时抛出。
        """
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
        """构建桌面代理请求头。

        Returns:
            dict[str, str]: 身份验证与协议请求头。
        """
        return {
            "Authorization": f"Bearer {self.session_token}",
            "X-Runtime-Protocol-Version": self.protocol_version,
            "X-Runtime-Session-Id": self.session_id,
            "X-Runtime-Identity": self.runtime_identity,
        }


@dataclass(frozen=True)
class OutboundRuntimeEvent:
    """等待发送到桌面代理的运行时事件。"""

    sequence: int
    eventType: str
    payload: dict[str, Any]
    createdAt: float


@dataclass
class DesktopTransportDiagnostic:
    """桌面传输诊断记录。"""

    sequence: int
    code: str
    message: str
    createdAt: float
    occurrences: int = 1


class BrokerHttpRequester(Protocol):
    """供确定性测试注入的有界 HTTP 边界。"""

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        """发送一次代理请求并返回其 JSON 对象响应。

        Args:
            method (str): HTTP 方法。
            path (str): 请求路径。
            body (dict[str, Any] | None): 可选 JSON 请求体。
            query (dict[str, str] | None): 可选查询参数。
            timeout (float): 请求超时秒数。

        Returns:
            dict[str, Any]: JSON 对象响应。
        """


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    """在 urllib 将会话请求头复制到其他位置前拒绝重定向。"""

    def _reject(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> None:
        del req, code, msg, headers
        fp.close()
        raise DesktopBrokerHttpError(
            "redirect_rejected",
            "runtime broker redirects are not permitted by protocol version 2",
            retryable=False,
        )

    http_error_301 = _reject
    http_error_302 = _reject
    http_error_303 = _reject
    http_error_307 = _reject
    http_error_308 = _reject


class StandardLibraryBrokerHttp:
    """具有严格响应边界的短请求 HTTP 实现。"""

    def __init__(self, settings: DesktopBrokerSettings):
        self.settings = settings
        # 代理凭据绝不能跟随环境中的 HTTP(S)_PROXY 设置；校验后的目标是字面回环地址。
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
        """发送一次有界桌面代理 HTTP 请求。

        Args:
            method (str): HTTP 方法。
            path (str): 请求路径。
            body (dict[str, Any] | None): 可选 JSON 请求体。
            query (dict[str, str] | None): 可选查询参数。
            timeout (float): 请求超时秒数。

        Returns:
            dict[str, Any]: JSON 对象响应。

        Raises:
            DesktopBrokerHttpError: HTTP 请求被拒绝或连接失败时抛出。
            DesktopBrokerProtocolError: 请求或响应违反协议边界时抛出。
        """
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
    """具有有界重放和命令状态的独立桌面传输。"""

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
        self._diagnostic_history: deque[DesktopTransportDiagnostic] = deque()
        self._diagnostic_history_bytes = 0
        self._active_transport_diagnostic: DesktopTransportDiagnostic | None = None
        self._next_diagnostic_sequence = 1
        self._acknowledged_diagnostic_sequence = 0
        self._diagnostics_truncated = False
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
        """从环境变量创建桌面代理客户端。

        Args:
            environ (Mapping[str, str] | None): 可选环境变量映射。
            **kwargs (Any): 传递给客户端构造函数的参数。

        Returns:
            DesktopBrokerClient: 尚未启动的桌面代理客户端。
        """
        return cls(DesktopBrokerSettings.from_env(environ), **kwargs)

    def start(self) -> "DesktopBrokerClient":
        """启动一个守护工作线程，且不在调用线程执行网络操作。

        Returns:
            DesktopBrokerClient: 当前桌面代理客户端。

        Raises:
            RuntimeError: 客户端已经关闭时抛出。
        """

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
        """在不执行网络 I/O 或等待的情况下将事件加入队列。

        Args:
            event_type (str): 事件类型。
            payload (dict[str, Any] | None): 事件载荷。

        Returns:
            bool: 事件成功进入队列时返回 ``True``。
        """

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
        # 校验后将队列事件与调用方持有的可变字典分离，确保后台工作线程看到此处
        # 接受的精确快照。
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
        """提供与旧版 RuntimeClient 一致的兼容方法名。

        Args:
            event_type (str): 事件类型。
            payload (dict[str, Any] | None): 事件载荷。
        """

        self.emit_event(event_type, payload)

    def set_command_handler(self, handler: RuntimeCommandHandler) -> None:
        """设置运行时命令处理器。

        Args:
            handler (RuntimeCommandHandler): 新命令处理器。
        """
        with self._condition:
            self._command_handler = handler

    def status(self) -> dict[str, Any]:
        """返回桌面代理客户端状态。

        Returns:
            dict[str, Any]: 传输、队列、确认与诊断状态。
        """
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
                "activeDiagnostic": (asdict(self._active_transport_diagnostic) if self._active_transport_diagnostic is not None else None),
                "unacknowledgedDiagnostics": [asdict(item) for item in self._diagnostic_history],
                "unacknowledgedDiagnosticCount": len(self._diagnostic_history),
                "unacknowledgedDiagnosticBytes": self._diagnostic_history_bytes,
                "acknowledgedDiagnosticSequence": self._acknowledged_diagnostic_sequence,
                "diagnosticsStartSequence": self._diagnostics_start_sequence_locked(),
                "diagnosticsTruncated": self._diagnostics_truncated,
                "lastHeartbeatAt": self._last_heartbeat_at,
                "lastSuccessAt": self._last_success_at,
            }

    def close(self, *, flush_timeout: float | None = None) -> None:
        """请求关闭且等待时间不超过有界刷新截止时间。

        Args:
            flush_timeout (float | None): 最终刷新超时秒数。
        """

        timeout = self._final_flush_seconds if flush_timeout is None else max(0.0, flush_timeout)
        with self._condition:
            if self._closed:
                return
            if not self._started:
                self._closed = True
                self._closing = True
                self._status = DesktopTransportStatus.CLOSED
                if self._events or self._results or self._diagnostic_history:
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
            if self._events or self._results or self._diagnostic_history:
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
                work_pending = bool(self._events or self._results or self._diagnostic_history)
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
        """执行一次确定性协议循环，测试也会调用此方法。"""

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
            with self._condition:
                diagnostics_pending = bool(self._diagnostic_history)
            if diagnostics_pending:
                self._heartbeat()
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
        acknowledgement = _required_nonnegative_int(response, "acknowledgedSequence")
        diagnostic_acknowledgement = _required_nonnegative_int(response, "acknowledgedDiagnosticSequence")
        with self._condition:
            if self._closed:
                return
            if self._events and acknowledgement >= self._next_sequence:
                raise DesktopBrokerProtocolError("connect acknowledgement exceeds the local event sequence")
            self._discard_acknowledged_locked(acknowledgement)
            if not self._events and acknowledgement >= self._next_sequence:
                self._next_sequence = acknowledgement + 1
            self._discard_acknowledged_diagnostics_locked(diagnostic_acknowledgement)
            self._active_transport_diagnostic = None
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
            diagnostics = _bounded_diagnostic_batch(self._diagnostic_history)
            prior_diagnostic_acknowledgement = self._acknowledged_diagnostic_sequence
            body = {
                "transportStatus": self._status.value,
                "lastAcknowledgedSequence": self._acknowledged_sequence,
                "queuedEventCount": len(self._events),
                "activeDiagnostic": (asdict(self._active_transport_diagnostic) if self._active_transport_diagnostic is not None else None),
                "diagnostics": [asdict(item) for item in diagnostics],
                "diagnosticsStartSequence": self._diagnostics_start_sequence_locked(),
                "diagnosticsTruncated": self._diagnostics_truncated,
            }
        response = self._requester.request(
            "POST",
            "/v1/runtime/heartbeat",
            body=body,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        if response.get("status") not in HEARTBEAT_RESPONSE_STATUSES:
            raise DesktopBrokerProtocolError("heartbeat response status must be connected, degraded, reconnecting, or disconnected")
        acknowledgement = _required_nonnegative_int(response, "acknowledgedSequence")
        diagnostic_acknowledgement = _required_nonnegative_int(response, "acknowledgedDiagnosticSequence")
        maximum_diagnostic_acknowledgement = diagnostics[-1].sequence if diagnostics else prior_diagnostic_acknowledgement
        if diagnostic_acknowledgement > maximum_diagnostic_acknowledgement:
            raise DesktopBrokerProtocolError("diagnostic acknowledgement exceeds the uploaded heartbeat batch")
        with self._condition:
            if self._events and acknowledgement >= self._next_sequence:
                raise DesktopBrokerProtocolError("heartbeat acknowledgement exceeds the local event sequence")
            self._discard_acknowledged_locked(acknowledgement)
            if not self._events and acknowledgement >= self._next_sequence:
                self._next_sequence = acknowledgement + 1
            self._discard_acknowledged_diagnostics_locked(diagnostic_acknowledgement)
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
            normalized_code = _bounded_utf8_text(str(code), MAX_DIAGNOSTIC_CODE_BYTES)
            normalized_message = _bounded_utf8_text(str(message), MAX_DIAGNOSTIC_MESSAGE_BYTES)
            active = self._active_transport_diagnostic
            if active is not None and active.code == normalized_code and active.message == normalized_message:
                active.occurrences = min(MAX_SEQUENCE, active.occurrences + 1)
                self._enforce_diagnostic_history_bounds_locked()
            else:
                self._active_transport_diagnostic = self._record_diagnostic_locked(
                    normalized_code,
                    normalized_message,
                    coalesce=False,
                )
            if retryable:
                self._status = DesktopTransportStatus.RECONNECTING if self._ever_connected else DesktopTransportStatus.DISCONNECTED
            else:
                self._status = DesktopTransportStatus.DEGRADED

    def _record_diagnostic(self, code: str, message: str) -> None:
        with self._condition:
            self._record_diagnostic_locked(code, message)

    def _record_diagnostic_locked(
        self,
        code: str,
        message: str,
        *,
        coalesce: bool = True,
    ) -> DesktopTransportDiagnostic:
        normalized_code = _bounded_utf8_text(str(code), MAX_DIAGNOSTIC_CODE_BYTES)
        normalized_message = _bounded_utf8_text(str(message), MAX_DIAGNOSTIC_MESSAGE_BYTES)
        if coalesce and self._diagnostic_history and self._diagnostic_history[-1].code == normalized_code and self._diagnostic_history[-1].message == normalized_message:
            diagnostic = self._diagnostic_history[-1]
            diagnostic.occurrences = min(MAX_SEQUENCE, diagnostic.occurrences + 1)
            self._enforce_diagnostic_history_bounds_locked()
            return diagnostic

        if self._next_diagnostic_sequence > MAX_SEQUENCE:
            raise DesktopBrokerProtocolError("diagnostic sequence reached its protocol bound")
        created_at = self._wall_time()
        if not _is_finite_nonnegative_number(created_at):
            created_at = 0.0
        diagnostic = DesktopTransportDiagnostic(
            sequence=self._next_diagnostic_sequence,
            code=normalized_code,
            message=normalized_message,
            createdAt=created_at,
        )
        self._next_diagnostic_sequence += 1
        self._diagnostic_history.append(diagnostic)
        self._enforce_diagnostic_history_bounds_locked()
        return diagnostic

    def _enforce_diagnostic_history_bounds_locked(self) -> None:
        self._diagnostic_history_bytes = sum(_diagnostic_size(item) for item in self._diagnostic_history)
        while self._diagnostic_history and (len(self._diagnostic_history) > MAX_DIAGNOSTIC_COUNT or self._diagnostic_history_bytes > MAX_DIAGNOSTIC_HISTORY_BYTES):
            removed = self._diagnostic_history.popleft()
            self._diagnostic_history_bytes -= _diagnostic_size(removed)
            self._diagnostics_truncated = True

    def _discard_acknowledged_diagnostics_locked(self, acknowledgement: int) -> None:
        if acknowledgement < self._acknowledged_diagnostic_sequence:
            return
        if self._diagnostic_history and acknowledgement >= self._next_diagnostic_sequence:
            raise DesktopBrokerProtocolError("diagnostic acknowledgement exceeds the local diagnostic sequence")
        self._acknowledged_diagnostic_sequence = acknowledgement
        while self._diagnostic_history and self._diagnostic_history[0].sequence <= acknowledgement:
            self._diagnostic_history.popleft()
        if not self._diagnostic_history and acknowledgement >= self._next_diagnostic_sequence:
            self._next_diagnostic_sequence = acknowledgement + 1
        self._diagnostic_history_bytes = sum(_diagnostic_size(item) for item in self._diagnostic_history)

    def _diagnostics_start_sequence_locked(self) -> int:
        if self._diagnostic_history:
            return self._diagnostic_history[0].sequence
        return self._next_diagnostic_sequence


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


def _bounded_diagnostic_batch(
    diagnostics: deque[DesktopTransportDiagnostic],
) -> list[DesktopTransportDiagnostic]:
    batch: list[DesktopTransportDiagnostic] = []
    for diagnostic in list(diagnostics)[:MAX_DIAGNOSTIC_BATCH_COUNT]:
        candidate = batch + [diagnostic]
        if len(_encode_json({"diagnostics": [asdict(item) for item in candidate]})) > MAX_DIAGNOSTIC_BATCH_BYTES:
            break
        batch = candidate
    return batch


def _diagnostic_size(diagnostic: DesktopTransportDiagnostic) -> int:
    return len(_encode_json(asdict(diagnostic)))


def _bounded_utf8_text(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return encoded.decode("utf-8")
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


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
    return _bounded_utf8_text(message, MAX_DIAGNOSTIC_MESSAGE_BYTES)


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
