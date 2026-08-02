"""同步 TCP JSONL 传输层"""

from __future__ import annotations

import math
import socket
import threading
import time
from typing import Any, Literal, Protocol

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


class SocketLike(Protocol):
    """JSONL 传输所需的套接字操作。"""

    def settimeout(self, value: float | None) -> None:
        """设置套接字操作超时。

        Args:
            value (float | None): 超时秒数；``None`` 表示阻塞模式。
        """
        ...

    def gettimeout(self) -> float | None:
        """获取套接字操作超时。

        Returns:
            float | None: 超时秒数或阻塞模式的 ``None``。
        """
        ...

    def makefile(self, mode: Literal["rb"]) -> Any:
        """创建套接字二进制读取器。

        Args:
            mode (Literal["rb"]): 文件模式，固定为二进制读取。

        Returns:
            Any: 套接字二进制读取器。
        """
        ...

    def sendall(self, data: bytes) -> None:
        """发送全部字节。

        Args:
            data (bytes): 待发送的数据。
        """
        ...

    def close(self) -> None:
        """关闭套接字。"""
        ...


def _finite_timeout(name: str, value: float) -> float:
    """返回正数且有限的套接字操作超时。"""

    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return timeout


class JsonlTcpTransport:
    """
    同步 TCP JSONL 传输对象

    负责套接字读写、hello 握手、请求响应匹配和尽力发送事件。

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
        sock: socket.socket | SocketLike,
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
        # 套接字超时属于进程对象状态。完整请求超时范围和每次独立发送都持有
        # 此可重入锁，避免事件继承临时请求截止时间。
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
    ) -> JsonlTcpTransport:
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

        Raises:
            Exception:
                建立连接、创建传输或发送握手失败时重新抛出原异常。
        """

        compatibility_timeout = _finite_timeout("timeout", timeout)
        resolved_connect_timeout = compatibility_timeout if connect_timeout is None else _finite_timeout("connect_timeout", connect_timeout)
        resolved_request_timeout = compatibility_timeout if default_request_timeout is None else _finite_timeout("default_request_timeout", default_request_timeout)
        resolved_event_timeout = compatibility_timeout if event_write_timeout is None else _finite_timeout("event_write_timeout", event_write_timeout)

        sock = socket.create_connection((host, port), timeout=resolved_connect_timeout)
        transport: JsonlTcpTransport | None = None
        try:
            # ``create_connection`` 会在套接字上保留建连截止时间。运行时连接在
            # 空闲时采用阻塞模式，每个请求或写入操作单独应用有界截止时间。
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
            # 初始 hello 属于写入操作，而不是 TCP 建连的一部分。它与其他原始
            # 尽力写入使用相同的有界策略，同时保持空闲模式为阻塞模式。
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
            TimeoutError:
                请求写入或读取超时时抛出。
            Exception:
                恢复套接字状态失败且没有其他活动异常时抛出。
            BaseException:
                请求期间发生无法进一步收窄的基础异常时重新抛出。
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
                # CPython 的 sendall 超时是总写入预算。单调截止时间会把未使用
                # 的预算带入所有响应读取，包括属于其他请求标识的帧。
                self.sock.settimeout(operation_timeout)
                # 一个截止时间同时覆盖完整请求写入和响应读取。此处不调用
                # ``send_raw``，因为它有意采用独立的写入策略。
                self._send_bytes_locked(encode_message(message))
                while True:
                    try:
                        line = self._readline_before_deadline_locked(deadline)
                    except TimeoutError:
                        # 缓冲套接字读取器在超时后无法可靠复用（CPython 后续读取
                        # 会报告无法从已超时对象读取）。流也可能停在 JSON 行中间，
                        # 因此重新创建文件对象不符合协议安全要求。
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
            except TimeoutError as exc:
                # 超时写入也可能只完成一部分，因此读写任一超时都会使 JSONL 流
                # 无法安全处理下一个请求。
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
                    # 无法恢复先前模式也会使连接不适合复用。保留活动请求异常，
                    # 避免清理异常将其覆盖。
                    self._invalidate()
                    if request_error is None:
                        raise
                if transport_timed_out:
                    self._invalidate()

    def _readline_before_deadline_locked(self, deadline: float) -> bytes:
        """读取一个 JSONL 帧且不允许部分输入延长截止时间。"""

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Runtime request timed out")

            newline = self._read_buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self._read_buffer[: newline + 1])
                del self._read_buffer[: newline + 1]
                return line

            self.sock.settimeout(remaining)
            read1 = getattr(self._reader, "read1", None)
            if read1 is not None:
                # BufferedReader.read1() 最多执行一次原始读取，使循环可在每个
                # 部分数据块后重新计算绝对预算，而不是让 readline() 为每次内部
                # recv() 重新获得套接字空闲超时。
                chunk = read1(READ_CHUNK_BYTES)
            else:
                # 确定性的旧版套接字替身只公开 readline()。真实的
                # socket.makefile("rb") 读取器是 BufferedReader，因此始终走
                # 感知截止时间的 read1 路径。
                chunk = self._reader.readline()

            if chunk:
                self._read_buffer.extend(chunk)
                continue

            # EOF 可能恰好在操作预算耗尽时到达。优先遵守截止时间，不返回迟到的
            # 缓冲数据。
            if deadline - time.monotonic() <= 0:
                raise TimeoutError("Runtime request timed out")
            if self._read_buffer:
                line = bytes(self._read_buffer)
                self._read_buffer.clear()
                return line
            return b""

    def _send_raw_locked(self, data: bytes, timeout: float) -> None:
        """在操作锁内使用临时截止时间发送一个原始帧。"""

        if self.closed:
            raise RuntimeTransportError("Transport is closed")
        old_timeout = self.sock.gettimeout()
        operation_error: BaseException | None = None
        transport_timed_out = False
        try:
            self.sock.settimeout(timeout)
            self._send_bytes_locked(data)
        except TimeoutError as exc:
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
                # 超时发送可能只把部分 JSONL 帧写入线路，因此该流不能复用。
                self._invalidate()

    def _send_bytes_locked(self, data: bytes) -> None:
        """在调用方持有完整操作锁时写入编码后的字节。"""

        if self.closed:
            raise RuntimeTransportError("Transport is closed")
        with self._write_lock:
            self.sock.sendall(data)

    def _invalidate(self) -> None:
        """将传输标记为不可用并关闭已损坏的流状态。"""

        try:
            self.close()
        except Exception:
            # 失效处理是对已有传输错误的清理，不能覆盖主要故障。
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

    def __enter__(self) -> JsonlTcpTransport:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
