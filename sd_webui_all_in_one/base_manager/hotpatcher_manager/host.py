"""Hotpatcher runtime TCP host and retained event state."""

from __future__ import annotations

import copy
import json
import queue
import socketserver
import threading
import time
import uuid
from typing import Any, Callable

from .config import DEFAULT_RUNTIME_HOST, DEFAULT_RUNTIME_PORT, get_hotpatcher_default_config, logger
from .protocol import RemoteServiceError, RuntimeBrowserEvent, RuntimeLogEntry, RuntimeMessage, RuntimeServiceChannel


class _RuntimeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class HotpatcherRuntimeHost:
    """
    hotpatcher runtime 宿主。

    该对象监听 TCP JSONL 端口, 接收补丁进程主动连接、配置请求、日志事件和
    services 控制通道。

    Attributes:
        host (str):
            runtime host 监听地址。
        port (int):
            runtime host 监听端口。
        token (str):
            连接 token。
        messages (list[RuntimeMessage]):
            已接收的 runtime 原始消息。
        log_entries (list[RuntimeLogEntry]):
            已接收的 runtime 日志事件。
        log_queue (queue.Queue[RuntimeLogEntry]):
            供 GUI / CLI 消费的日志队列。
    """

    def __init__(
        self,
        host: str = DEFAULT_RUNTIME_HOST,
        port: int = DEFAULT_RUNTIME_PORT,
        *,
        token: str = "",
        get_config: Callable[[], dict[str, Any]] | None = None,
        on_message: Callable[[RuntimeMessage], None] | None = None,
        on_log: Callable[[RuntimeLogEntry], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        confirm_file_operation: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.token = token
        self.get_config = get_config or get_hotpatcher_default_config
        self.on_message = on_message
        self.on_log = on_log
        self.on_status = on_status
        self.confirm_file_operation = confirm_file_operation
        self.messages: list[RuntimeMessage] = []
        self.log_entries: list[RuntimeLogEntry] = []
        self.browser_events: list[RuntimeBrowserEvent] = []
        self.browser_diagnostics: list[str] = []
        self.log_queue: queue.Queue[RuntimeLogEntry] = queue.Queue()
        self._lock = threading.Lock()
        self._server: _RuntimeServer | None = None
        self._thread: threading.Thread | None = None
        self._service_channel: RuntimeServiceChannel | None = None
        self._next_log_sequence = 0
        self._log_retention = 2000
        self._next_browser_sequence = 0
        self._browser_retention = 256
        self.runtime_identity = uuid.uuid4().hex

    @property
    def server_address(self) -> tuple[str, int]:
        """
        获取实际监听地址

        Returns:
            tuple[str, int]:
                runtime host 实际监听的 host 和 port。
        """

        if self._server is None:
            return (self.host, self.port)
        host, port = self._server.server_address[:2]
        return (str(host), int(port))

    @property
    def service_channel_available(self) -> bool:
        """
        判断是否已连接远端 services 控制通道

        Returns:
            bool:
                services 控制通道可用时返回 True。
        """

        channel = self._service_channel
        return channel is not None and not channel.closed

    @property
    def browser_next_cursor(self) -> int:
        """返回用于启动基线的下一个单调递增浏览器序号。

        Returns:
            int: 下一个浏览器事件游标。
        """

        with self._lock:
            return self._next_browser_sequence

    def start(self) -> "HotpatcherRuntimeHost":
        """
        启动 runtime host

        Returns:
            HotpatcherRuntimeHost:
                当前 runtime host 实例。
        """

        if self._server is not None:
            return self

        logger.info("启动 hotpatcher runtime host, host: %s, port: %s", self.host, self.port)
        with self._lock:
            self.browser_events.clear()
            self.browser_diagnostics.clear()
            self._next_browser_sequence = 0
            self.runtime_identity = uuid.uuid4().hex

        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:  # noqa: D401
                outer._handle_client(self)

        self._server = _RuntimeServer((self.host, self.port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="sd-webui-all-in-one-hotpatcher-runtime-host",
            daemon=True,
        )
        self._thread.start()
        self._emit_status(f"runtime host listening on {self.server_address[0]}:{self.server_address[1]}")
        return self

    def stop(self) -> None:
        """
        停止 runtime host

        会关闭当前 services channel、停止 TCP server 并等待后台线程退出。
        """

        if self._service_channel is not None:
            self._service_channel.close()
            self._service_channel = None
        server = self._server
        self._server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("hotpatcher runtime host 已停止")
        self._emit_status("runtime host stopped")

    def request_services(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        向已连接补丁进程的 services channel 发送请求

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
                services channel 未连接或请求失败时抛出。
        """

        channel = self._service_channel
        if channel is None or channel.closed:
            logger.warning("services channel 未连接, 无法发送请求 %s", message_type)
            raise RemoteServiceError("channel_unavailable", "services channel is not connected")
        return channel.request(message_type, payload, timeout=timeout)

    def apply_remote_config(
        self,
        config: dict[str, Any],
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        通过 services channel 应用远端配置

        Args:
            config (dict[str, Any]):
                要应用到远端进程的 hotpatcher 配置。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                远端 services.apply_config 的结果。

        Raises:
            RemoteServiceError:
                services channel 未连接或请求失败时抛出。
        """

        logger.debug("通过 services channel 应用远端 hotpatcher 配置")
        payload = self.request_services(
            "services.config.apply",
            {"config": config},
            timeout=timeout,
        )
        result = payload.get("result", {})
        logger.debug("远端配置应用结果: %s", list(result.keys()))
        return result if isinstance(result, dict) else {}

    def close(self) -> None:
        """
        关闭 runtime host

        该方法等价于调用 ``stop()``。
        """

        self.stop()

    def __enter__(self) -> "HotpatcherRuntimeHost":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def _handle_client(self, handler: socketserver.StreamRequestHandler) -> None:
        address = self._client_address(handler)
        first_line = handler.rfile.readline()
        if not first_line:
            return
        try:
            first_message = self._decode(first_line)
        except Exception as exc:
            logger.warning("来自 %s 的非法 runtime 消息: %s", address, exc)
            self._emit_status(f"invalid runtime message from {address}: {exc}")
            return

        if not self._check_token(first_message):
            logger.warning("来自 %s 的 runtime token 校验失败", address)
            self._emit_status(f"runtime token rejected from {address}")
            return

        logger.debug("收到来自 %s 的首条 runtime 消息, type: %s", address, first_message.get("type"))
        self._record_message(first_message, address)
        if first_message.get("type") == "channel.open":
            self._handle_channel(handler, first_message, address)
            return

        for raw_line in handler.rfile:
            try:
                message = self._decode(raw_line)
            except Exception as exc:
                logger.warning("来自 %s 的非法 runtime 消息: %s", address, exc)
                self._emit_status(f"invalid runtime message from {address}: {exc}")
                continue
            self._record_message(message, address)
            self._handle_main_message(handler, message)

    def _handle_channel(
        self,
        handler: socketserver.StreamRequestHandler,
        message: dict[str, Any],
        address: tuple[str, int] | None,
    ) -> None:
        channel_name = message.get("channel")
        if channel_name == "services":
            channel = RuntimeServiceChannel(handler.wfile, on_close=self._remove_service_channel)
            self._service_channel = channel
            logger.info("services channel 已连接, 来源: %s", address)
            self._emit_status(f"services channel connected from {address}")
            try:
                for raw_line in handler.rfile:
                    try:
                        incoming = self._decode(raw_line)
                    except Exception as exc:
                        logger.warning("来自 %s 的非法 services 消息: %s", address, exc)
                        self._emit_status(f"invalid services message from {address}: {exc}")
                        continue
                    self._record_message(incoming, address)
                    channel.handle_message(incoming)
            finally:
                channel.close()
                logger.info("services channel 已断开, 来源: %s", address)
                self._emit_status("services channel disconnected")
            return

        if channel_name == "fault":
            logger.debug("fault channel 已连接, 来源: %s", address)
            self._emit_status(f"fault channel connected from {address}")
            for raw_line in handler.rfile:
                payload = {"stream": "fault", "text": raw_line.decode("utf-8", errors="replace"), "source": "fault"}
                self._record_log(RuntimeLogEntry("log.stream", payload))

    def _handle_main_message(
        self,
        handler: socketserver.StreamRequestHandler,
        message: dict[str, Any],
    ) -> None:
        message_type = str(message.get("type", ""))
        message_id = message.get("id")
        logger.debug("处理 runtime 消息, id: %s, type: %s", message_id, message_type)
        if message_type.startswith("log."):
            self._record_log(RuntimeLogEntry(message_type, dict(message.get("payload", {}) if isinstance(message.get("payload"), dict) else {})))

        if message_id is None:
            return

        if message_type == "config.get":
            logger.debug("响应 config.get 请求, id: %s", message_id)
            self._send_response(handler, message_id, {"config": self._safe_config()})
            return

        if message_type.startswith("file."):
            if self.confirm_file_operation is not None and self.confirm_file_operation(message_type, self._payload(message)):
                logger.debug("响应 file 请求 %s, id: %s, 已接受", message_type, message_id)
                self._send_response(handler, message_id, {"accepted": True})
            else:
                logger.warning("file 操作 %s (id: %s) 被拒绝", message_type, message_id)
                self._send_error(handler, message_id, "cancelled", "file operation cancelled")
            return

        self._send_response(handler, message_id, {"accepted": True})

    def _record_message(self, message: dict[str, Any], address: tuple[str, int] | None) -> None:
        entry = RuntimeMessage(copy.deepcopy(message), address=address)
        with self._lock:
            self.messages.append(entry)
        if message.get("type") == "browser.open":
            payload = message.get("payload")
            url = payload.get("url") if isinstance(payload, dict) else None
            if isinstance(url, str):
                self._record_browser_event(url)
            else:
                diagnostic = "rejected malformed browser.open runtime event"
                logger.warning("拒绝格式错误的 browser.open 消息, 来源: %s", address)
                with self._lock:
                    self.browser_diagnostics.append(diagnostic)
                    del self.browser_diagnostics[:-100]
                self._emit_status(diagnostic)
        if self.on_message is not None:
            self.on_message(entry)

    def _record_browser_event(self, url: str) -> None:
        with self._lock:
            event = RuntimeBrowserEvent(
                sequence=self._next_browser_sequence,
                url=url,
            )
            self._next_browser_sequence += 1
            self.browser_events.append(event)
            overflow = len(self.browser_events) - self._browser_retention
            if overflow > 0:
                del self.browser_events[:overflow]
        logger.debug("记录浏览器事件, sequence: %s, url: %s", event.sequence, url)

    def read_browser_events(self, since_cursor: int = 0, limit: int = 100) -> dict[str, Any]:
        """读取已校验浏览器事件的有界单调切片。

        Args:
            since_cursor (int): 起始游标。
            limit (int): 最多返回的事件数量。

        Returns:
            dict[str, Any]: 浏览器事件切片及游标信息。
        """

        bounded_limit = max(1, min(int(limit), 200))
        requested = max(0, int(since_cursor))
        with self._lock:
            first_cursor = self.browser_events[0].sequence if self.browser_events else self._next_browser_sequence
            start_cursor = max(requested, first_cursor)
            selected = [event for event in self.browser_events if event.sequence >= start_cursor][:bounded_limit]
            next_cursor = selected[-1].sequence + 1 if selected else start_cursor
            logger.debug("读取浏览器事件, since_cursor: %s, limit: %s, 返回 %s 条", requested, bounded_limit, len(selected))
            return {
                "runtime_identity": self.runtime_identity,
                "events": [
                    {
                        "sequence": event.sequence,
                        "url": event.url,
                        "created": event.created,
                    }
                    for event in selected
                ],
                "start_cursor": start_cursor,
                "next_cursor": next_cursor,
                "truncated": requested < first_cursor,
            }

    def _record_log(self, entry: RuntimeLogEntry) -> None:
        with self._lock:
            entry.sequence = self._next_log_sequence
            self._next_log_sequence += 1
            self.log_entries.append(entry)
            overflow = len(self.log_entries) - self._log_retention
            if overflow > 0:
                del self.log_entries[:overflow]
        self.log_queue.put(entry)
        if self.on_log is not None:
            self.on_log(entry)

    def read_logs(self, since_cursor: int = 0, limit: int = 200) -> dict[str, Any]:
        """读取已保留运行时日志的有界单调切片。

        Args:
            since_cursor (int): 起始游标。
            limit (int): 最多返回的日志数量。

        Returns:
            dict[str, Any]: 运行时日志切片及游标信息。
        """

        bounded_limit = max(1, min(int(limit), 1000))
        requested = max(0, int(since_cursor))
        with self._lock:
            first_cursor = self.log_entries[0].sequence if self.log_entries else self._next_log_sequence
            start_cursor = max(requested, first_cursor)
            selected = [item for item in self.log_entries if item.sequence >= start_cursor][:bounded_limit]
            next_cursor = selected[-1].sequence + 1 if selected else start_cursor
            logger.debug("读取 runtime 日志, since_cursor: %s, limit: %s, 返回 %s 条", requested, bounded_limit, len(selected))
            return {
                "logs": [
                    {
                        "sequence": item.sequence,
                        "message_type": item.message_type,
                        "payload": item.payload,
                        "created": item.created,
                        "line": item.format_line(),
                    }
                    for item in selected
                ],
                "start_cursor": start_cursor,
                "next_cursor": next_cursor,
                "truncated": requested < first_cursor,
            }

    def _safe_config(self) -> dict[str, Any]:
        try:
            config = self.get_config()
        except Exception:
            logger.exception("获取 hotpatcher 配置失败, 返回空配置")
            config = {}
        return config if isinstance(config, dict) else {}

    def _remove_service_channel(self, channel: RuntimeServiceChannel) -> None:
        if self._service_channel is channel:
            logger.debug("移除已断开的 services channel")
            self._service_channel = None

    def _check_token(self, message: dict[str, Any]) -> bool:
        if not self.token:
            return True
        return str(message.get("token", "")) == self.token

    def _emit_status(self, message: str) -> None:
        if self.on_status is not None:
            self.on_status(message)

    @staticmethod
    def _client_address(handler: socketserver.StreamRequestHandler) -> tuple[str, int] | None:
        address = getattr(handler, "client_address", None)
        if isinstance(address, tuple) and len(address) >= 2:
            return (str(address[0]), int(address[1]))
        return None

    @staticmethod
    def _payload(message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", {})
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _decode(line: bytes) -> dict[str, Any]:
        message = json.loads(line.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("runtime message must be an object")
        return message

    @staticmethod
    def _send_response(
        handler: socketserver.StreamRequestHandler,
        message_id: Any,
        payload: dict[str, Any],
    ) -> None:
        HotpatcherRuntimeHost._send(handler, {"id": message_id, "ok": True, "payload": payload})

    @staticmethod
    def _send_error(
        handler: socketserver.StreamRequestHandler,
        message_id: Any,
        code: str,
        message: str,
    ) -> None:
        HotpatcherRuntimeHost._send(handler, {"id": message_id, "ok": False, "error": {"code": code, "message": message}})

    @staticmethod
    def _send(handler: socketserver.StreamRequestHandler, message: dict[str, Any]) -> None:
        data = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        handler.wfile.write(data)
        handler.wfile.flush()


def wait_for_runtime_log(
    host: HotpatcherRuntimeHost,
    predicate: Callable[[RuntimeLogEntry], bool],
    timeout: float = 2.0,
) -> RuntimeLogEntry | None:
    """
    等待符合条件的 runtime 日志

    Args:
        host (HotpatcherRuntimeHost):
            runtime host 实例。
        predicate (Callable[[RuntimeLogEntry], bool]):
            日志匹配函数。
        timeout (float):
            等待超时时间。

    Returns:
        RuntimeLogEntry | None:
            匹配到的日志事件。超时时返回 None。
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        with host._lock:  # pylint: disable=protected-access
            for entry in host.log_entries:
                if predicate(entry):
                    logger.debug("等待到符合条件的 runtime 日志")
                    return entry
        time.sleep(0.02)
    logger.debug("等待 runtime 日志超时")
    return None


def wait_for_service_channel(host: HotpatcherRuntimeHost, timeout: float = 2.0) -> bool:
    """
    等待 services channel 连接

    Args:
        host (HotpatcherRuntimeHost):
            runtime host 实例。
        timeout (float):
            等待超时时间。

    Returns:
        bool:
            services channel 在超时前连接时返回 True。
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        if host.service_channel_available:
            logger.debug("services channel 已连接")
            return True
        time.sleep(0.02)
    logger.debug("等待 services channel 连接超时")
    return False
