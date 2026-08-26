"""Hotpatcher runtime messages and request channel."""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from sd_webui_all_in_one.base_manager.hotpatcher_manager.config import logger


@dataclass(slots=True)
class RuntimeLogEntry:
    """
    runtime 日志事件

    Attributes:
        message_type (str):
            runtime 消息类型。
        payload (dict[str, Any]):
            runtime 消息载荷。
        created (float):
            记录创建时间戳。
    """

    message_type: str
    payload: dict[str, Any]
    created: float = field(default_factory=time.time)
    sequence: int = 0

    def format_line(self) -> str:
        """
        格式化为 GUI / CLI 可读日志行

        Returns:
            str:
                可直接显示的单行日志文本。
        """

        if self.message_type == "log.record":
            level = self.payload.get("level", "LOG")
            logger_name = self.payload.get("logger", "")
            message = self.payload.get("message", "")
            return f"[{level}] {logger_name}: {message}".rstrip()
        if self.message_type == "log.stream":
            stream = self.payload.get("stream", "stream")
            source = self.payload.get("source", "stream")
            text = str(self.payload.get("text", ""))
            return f"[{source}/{stream}] {text}".rstrip()
        if self.message_type == "log.dropped":
            count = self.payload.get("count", 0)
            reason = self.payload.get("reason", "")
            return f"[dropped] {count} messages dropped: {reason}".rstrip()
        return f"[{self.message_type}] {json.dumps(self.payload, ensure_ascii=False)}"


@dataclass(slots=True)
class RuntimeMessage:
    """
    runtime 原始消息记录

    Attributes:
        message (dict[str, Any]):
            原始 runtime 消息。
        address (tuple[str, int] | None):
            客户端地址。
        created (float):
            记录创建时间戳。
    """

    message: dict[str, Any]
    address: tuple[str, int] | None = None
    created: float = field(default_factory=time.time)


@dataclass(slots=True)
class RuntimeBrowserEvent:
    """运行时主机保留的已校验浏览器请求。"""

    sequence: int
    url: str
    created: float = field(default_factory=time.time)


class RemoteServiceError(RuntimeError):
    """
    远程 services channel 请求失败

    Attributes:
        code (str):
            错误代码。
        message (str):
            错误说明。
        payload (dict[str, Any]):
            远端返回的错误载荷。
    """

    def __init__(self, code: str, message: str = "", payload: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"{code}: {message}" if message else code)


class _PendingRequest:
    def __init__(self) -> None:
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)


class RuntimeServiceChannel:
    """
    连接到远端 hotpatcher services 控制通道的宿主侧对象

    Attributes:
        writer (Any):
            services channel 的写入端。
        on_close (Callable[[RuntimeServiceChannel], None] | None):
            通道关闭时的回调函数。
        closed (bool):
            通道是否已关闭。
    """

    def __init__(
        self,
        writer: Any,
        *,
        on_close: Callable[["RuntimeServiceChannel"], None] | None = None,
    ) -> None:
        self.writer = writer
        self.on_close = on_close
        self._write_lock = threading.Lock()
        self._pending: dict[str, _PendingRequest] = {}
        self._pending_lock = threading.Lock()
        self.closed = False

    def request(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        向远端 services channel 发送请求并等待响应

        Args:
            message_type (str):
                services 请求类型。
            payload (dict[str, Any] | None):
                请求载荷。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                远端响应载荷。

        Raises:
            RemoteServiceError:
                通道关闭、请求超时或远端返回错误时抛出。
        """

        message_id = uuid.uuid4().hex
        pending = _PendingRequest()
        with self._pending_lock:
            if self.closed:
                logger.warning("services channel 已关闭, 拒绝发送请求 %s", message_type)
                raise RemoteServiceError("channel_closed", "services channel is closed")
            self._pending[message_id] = pending

        logger.debug("发送 services 请求, id: %s, type: %s, timeout: %s", message_id, message_type, timeout)
        try:
            self._send(
                {
                    "id": message_id,
                    "type": message_type,
                    "payload": payload or {},
                }
            )
            try:
                response = pending.queue.get(timeout=timeout)
            except queue.Empty as exc:
                logger.error("services 请求 %s (%s) 等待响应超时", message_type, message_id)
                raise RemoteServiceError("timeout", "services request timed out") from exc

            if response.get("ok") is True:
                response_payload = response.get("payload", {})
                logger.debug("services 请求 %s (%s) 成功", message_type, message_id)
                return response_payload if isinstance(response_payload, dict) else {}

            error = response.get("error", {})
            if not isinstance(error, dict):
                error = {}
            logger.warning("services 请求 %s (%s) 远端返回错误: %s", message_type, message_id, error.get("code", "request_failed"))
            raise RemoteServiceError(
                str(error.get("code", "request_failed")),
                str(error.get("message", "")),
                error,
            )
        finally:
            with self._pending_lock:
                self._pending.pop(message_id, None)

    def handle_message(self, message: dict[str, Any]) -> bool:
        """
        处理 services channel 输入消息

        Args:
            message (dict[str, Any]):
                远端发来的 JSON 消息。

        Returns:
            bool:
                消息匹配到等待中的请求时返回 True。
        """

        message_id = message.get("id")
        if not isinstance(message_id, str):
            return False
        with self._pending_lock:
            pending = self._pending.get(message_id)
        if pending is None:
            return False
        try:
            pending.queue.put_nowait(message)
        except queue.Full:
            return False
        logger.debug("services 通道收到匹配请求 id: %s 的响应", message_id)
        return True

    def close(self) -> None:
        """
        标记通道关闭

        关闭时会触发 ``on_close`` 回调, 用于从 runtime host 中移除当前通道。
        """

        with self._pending_lock:
            if self.closed:
                return
            logger.debug("services 通道关闭")
            self.closed = True
            pending_requests = tuple(self._pending.values())
        closed_response = {
            "ok": False,
            "error": {
                "code": "channel_closed",
                "message": "services channel is closed",
            },
        }
        for pending in pending_requests:
            try:
                pending.queue.put_nowait(closed_response)
            except queue.Full:
                pass
        if self.on_close is not None:
            self.on_close(self)

    def _send(self, message: dict[str, Any]) -> None:
        data = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._write_lock:
            self.writer.write(data)
            self.writer.flush()
