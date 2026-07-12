"""同步 TCP JSONL 传输层"""

from __future__ import annotations

import math
import socket
import threading
import time
from typing import Any

from .protocol import (
    RuntimeProtocolError,
    RuntimeRequestError,
    RuntimeTransportError,
    decode_message,
    encode_message,
    event_message,
    hello_message,
    request_message,
)

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_REQUEST_TIMEOUT = 5.0
DEFAULT_EVENT_WRITE_TIMEOUT = 5.0
READ_CHUNK_BYTES = 64 * 1024


def _finite_timeout(name: str, value: float) -> float:
    """Return a positive finite socket operation timeout."""

    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return timeout


class JsonlTcpTransport:
    """
    同步 TCP JSONL 传输对象

    负责 socket 读写、hello 握手、请求响应匹配和 best-effort 事件发送。

    Attributes:
        sock (socket.socket):
            已连接的 socket
        host (str):
            宿主地址
        port (int):
            宿主端口
        token (str):
            握手 token
        closed (bool):
            传输是否已关闭
    """

    def __init__(
        self,
        sock: socket.socket,
        *,
        host: str,
        port: int,
        token: str = "",
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        default_request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        event_write_timeout: float = DEFAULT_EVENT_WRITE_TIMEOUT,
    ):
        self.sock = sock
        self.host = host
        self.port = port
        self.token = token
        self.connect_timeout = _finite_timeout("connect_timeout", connect_timeout)
        self.default_request_timeout = _finite_timeout(
            "default_request_timeout",
            default_request_timeout,
        )
        self.event_write_timeout = _finite_timeout("event_write_timeout", event_write_timeout)
        self._reader = sock.makefile("rb")
        self._read_buffer = bytearray()
        self._write_lock = threading.Lock()
        # The socket timeout is process-object state. Hold this reentrant lock
        # for the complete request timeout scope and for every standalone send
        # so an event cannot inherit a temporary request deadline.
        self._request_lock = threading.RLock()
        self._close_lock = threading.Lock()
        self.closed = False

    @classmethod
    def connect(
        cls,
        host: str,
        port: int,
        *,
        token: str = "",
        timeout: float = DEFAULT_CONNECT_TIMEOUT,
        connect_timeout: float | None = None,
        default_request_timeout: float | None = None,
        event_write_timeout: float | None = None,
        features: list[str] | None = None,
    ) -> "JsonlTcpTransport":
        """
        建立 TCP 连接并发送 hello 消息

        Args:
            host (str):
                宿主地址
            port (int):
                宿主端口
            token (str):
                握手 token
            timeout (float):
                兼容超时设置。未单独指定时，同时作为建连、默认请求和事件写入超时。
            connect_timeout (float | None):
                TCP 连接建立超时。为 None 时使用 ``timeout``。
            default_request_timeout (float | None):
                未显式指定单次 deadline 时的请求超时。为 None 时使用 ``timeout``。
            event_write_timeout (float | None):
                best-effort 事件和原始消息的写入超时。为 None 时使用 ``timeout``。
            features (list[str] | None):
                客户端能力列表

        Returns:
            JsonlTcpTransport:
                已完成握手发送的传输对象
        """

        compatibility_timeout = _finite_timeout("timeout", timeout)
        resolved_connect_timeout = compatibility_timeout if connect_timeout is None else _finite_timeout("connect_timeout", connect_timeout)
        resolved_request_timeout = compatibility_timeout if default_request_timeout is None else _finite_timeout("default_request_timeout", default_request_timeout)
        resolved_event_timeout = compatibility_timeout if event_write_timeout is None else _finite_timeout("event_write_timeout", event_write_timeout)

        sock = socket.create_connection((host, port), timeout=resolved_connect_timeout)
        transport: JsonlTcpTransport | None = None
        try:
            # ``create_connection`` leaves its establishment deadline on the
            # socket. Runtime connections are blocking while idle; each
            # request or write applies its own bounded operation deadline.
            sock.settimeout(None)
            transport = cls(
                sock,
                host=host,
                port=port,
                token=token,
                connect_timeout=resolved_connect_timeout,
                default_request_timeout=resolved_request_timeout,
                event_write_timeout=resolved_event_timeout,
            )
            # The initial hello is a write operation, not part of TCP
            # establishment.  It uses the same bounded policy as other raw
            # best-effort writes while idle mode remains blocking.
            transport.send_raw(hello_message(token, features))
            return transport
        except Exception:
            if transport is not None:
                try:
                    transport.close()
                except Exception:
                    pass
            else:
                try:
                    sock.close()
                except Exception:
                    pass
            raise

    def send_raw(self, message: dict[str, Any]) -> None:
        """
        发送原始消息对象

        Args:
            message (dict[str, Any]):
                待发送的消息对象

        Raises:
            RuntimeTransportError:
                传输已经关闭
        """

        with self._request_lock:
            self._send_raw_locked(encode_message(message), self.event_write_timeout)

    def event(self, message_type: str, payload: dict[str, Any] | None = None) -> None:
        """
        发送事件消息

        Args:
            message_type (str):
                事件类型
            payload (dict[str, Any] | None):
                事件载荷
        """

        self.send_raw(event_message(message_type, payload))

    def request(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        发送请求并等待匹配响应

        Args:
            message_type (str):
                请求类型
            payload (dict[str, Any] | None):
                请求载荷
            timeout (float | None):
                本次请求的临时超时时间。为 None 时使用有限的
                ``default_request_timeout``。请求结束后恢复先前的 socket 模式。

        Returns:
            dict[str, Any]:
                响应载荷

        Raises:
            RuntimeTransportError:
                宿主断开连接
            RuntimeProtocolError:
                响应格式非法
            RuntimeRequestError:
                宿主返回失败响应
        """

        message = request_message(message_type, payload)
        message_id = message["id"]
        operation_timeout = self.default_request_timeout if timeout is None else _finite_timeout("timeout", timeout)

        with self._request_lock:
            if self.closed:
                raise RuntimeTransportError("Transport is closed")
            old_timeout = self.sock.gettimeout()
            transport_timed_out = False
            request_error: BaseException | None = None
            deadline = time.monotonic() + operation_timeout
            try:
                # CPython's sendall timeout is a total write budget. The
                # monotonic deadline then carries the unused portion into all
                # response reads, including frames for other request IDs.
                self.sock.settimeout(operation_timeout)
                # One deadline covers both the complete request write and the
                # response read.  Do not call ``send_raw`` here because its
                # standalone write policy is intentionally separate.
                self._send_bytes_locked(encode_message(message))
                while True:
                    try:
                        line = self._readline_before_deadline_locked(deadline)
                    except (TimeoutError, socket.timeout):
                        # A buffered socket reader cannot be used reliably
                        # after a timeout (CPython reports "cannot read from
                        # timed out object" on subsequent reads).  The stream
                        # may also be positioned in the middle of a JSON line,
                        # so recreating the file object is not protocol-safe.
                        transport_timed_out = True
                        raise
                    if not line:
                        raise RuntimeTransportError("Host closed the connection")
                    response = decode_message(line)
                    if response.get("id") != message_id:
                        continue
                    if response.get("ok") is True:
                        payload_value = response.get("payload", {})
                        if not isinstance(payload_value, dict):
                            raise RuntimeProtocolError("Response payload must be an object")
                        return payload_value
                    error = response.get("error", {})
                    if not isinstance(error, dict):
                        error = {}
                    raise RuntimeRequestError(
                        str(error.get("code", "request_failed")),
                        str(error.get("message", "")),
                        error,
                    )
            except (TimeoutError, socket.timeout) as exc:
                # A timed-out write may be partial too, so either read or write
                # timeout makes the JSONL stream unsafe for another request.
                transport_timed_out = True
                request_error = exc
                raise
            except BaseException as exc:
                request_error = exc
                raise
            finally:
                try:
                    self.sock.settimeout(old_timeout)
                except Exception:
                    # Failure to restore the prior mode also makes this
                    # connection unsuitable for reuse.  Preserve an active
                    # request error instead of masking it with cleanup.
                    self._invalidate()
                    if request_error is None:
                        raise
                if transport_timed_out:
                    self._invalidate()

    def _readline_before_deadline_locked(self, deadline: float) -> bytes:
        """Read one JSONL frame without letting partial input renew the deadline."""

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("Runtime request timed out")

            newline = self._read_buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self._read_buffer[: newline + 1])
                del self._read_buffer[: newline + 1]
                return line

            self.sock.settimeout(remaining)
            read1 = getattr(self._reader, "read1", None)
            if read1 is not None:
                # BufferedReader.read1() performs at most one raw read. This
                # lets the loop recompute the absolute budget after every
                # partial chunk instead of granting readline() a fresh socket
                # inactivity timeout for each internal recv().
                chunk = read1(READ_CHUNK_BYTES)
            else:
                # Deterministic legacy socket fakes expose only readline(). A
                # real socket.makefile("rb") reader is a BufferedReader and
                # therefore always follows the deadline-aware read1 path.
                chunk = self._reader.readline()

            if chunk:
                self._read_buffer.extend(chunk)
                continue

            # EOF may arrive exactly as the operation budget expires. Preserve
            # deadline precedence instead of returning late buffered data.
            if deadline - time.monotonic() <= 0:
                raise socket.timeout("Runtime request timed out")
            if self._read_buffer:
                line = bytes(self._read_buffer)
                self._read_buffer.clear()
                return line
            return b""

    def _send_raw_locked(self, data: bytes, timeout: float) -> None:
        """Send one raw frame with a temporary deadline under the operation lock."""

        if self.closed:
            raise RuntimeTransportError("Transport is closed")
        old_timeout = self.sock.gettimeout()
        operation_error: BaseException | None = None
        transport_timed_out = False
        try:
            self.sock.settimeout(timeout)
            self._send_bytes_locked(data)
        except (TimeoutError, socket.timeout) as exc:
            transport_timed_out = True
            operation_error = exc
            raise
        except BaseException as exc:
            operation_error = exc
            raise
        finally:
            try:
                self.sock.settimeout(old_timeout)
            except Exception:
                self._invalidate()
                if operation_error is None:
                    raise
            if transport_timed_out:
                # A timed-out send may have placed only part of the JSONL
                # frame on the wire, so the stream cannot be reused.
                self._invalidate()

    def _send_bytes_locked(self, data: bytes) -> None:
        """Write encoded bytes while the caller owns the complete operation lock."""

        if self.closed:
            raise RuntimeTransportError("Transport is closed")
        with self._write_lock:
            self.sock.sendall(data)

    def _invalidate(self) -> None:
        """Mark the transport unusable and close poisoned stream state."""

        try:
            self.close()
        except Exception:
            # Invalidation is cleanup for an already-active transport error.
            # It must not replace that primary failure.
            pass

    def close(self) -> None:
        """关闭 socket 和 reader"""

        with self._close_lock:
            if self.closed:
                return
            self.closed = True
            try:
                self._reader.close()
            finally:
                self.sock.close()

    def __enter__(self) -> "JsonlTcpTransport":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
