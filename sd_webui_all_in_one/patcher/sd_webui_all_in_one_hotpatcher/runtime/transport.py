"""同步 TCP JSONL 传输层"""

from __future__ import annotations

import socket
import threading
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

    def __init__(self, sock: socket.socket, *, host: str, port: int, token: str = ""):
        self.sock = sock
        self.host = host
        self.port = port
        self.token = token
        self._reader = sock.makefile("rb")
        self._write_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self.closed = False

    @classmethod
    def connect(
        cls,
        host: str,
        port: int,
        *,
        token: str = "",
        timeout: float = 5.0,
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
                连接超时时间
            features (list[str] | None):
                客户端能力列表

        Returns:
            JsonlTcpTransport:
                已完成握手发送的传输对象
        """

        sock = socket.create_connection((host, port), timeout=timeout)
        transport = cls(sock, host=host, port=port, token=token)
        transport.send_raw(hello_message(token, features))
        return transport

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

        if self.closed:
            raise RuntimeTransportError("Transport is closed")
        data = encode_message(message)
        with self._write_lock:
            self.sock.sendall(data)

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
                本次请求超时时间

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

        with self._request_lock:
            old_timeout = self.sock.gettimeout()
            if timeout is not None:
                self.sock.settimeout(timeout)
            try:
                self.send_raw(message)
                while True:
                    line = self._reader.readline()
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
            finally:
                if timeout is not None:
                    self.sock.settimeout(old_timeout)

    def close(self) -> None:
        """关闭 socket 和 reader"""

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
