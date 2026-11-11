"""Hotpatcher runtime TCP host and retained event state."""

from __future__ import annotations

import copy
import ipaddress
import json
import queue
import socket
import socketserver
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from sd_webui_all_in_one.base_manager.hotpatcher_manager.config import DEFAULT_RUNTIME_HOST, DEFAULT_RUNTIME_PORT, get_hotpatcher_default_config, logger
from sd_webui_all_in_one.base_manager.hotpatcher_manager.host_control import CONNECTION_UPDATE_COMMAND, RuntimeControlMixin
from sd_webui_all_in_one.base_manager.hotpatcher_manager.protocol import RemoteServiceError, RuntimeBrowserEvent, RuntimeLogEntry, RuntimeMessage, RuntimeServiceChannel

CONTROL_PROBE_TIMEOUT = 5.0
"""``hotpatch.capabilities`` 能力探测的默认超时时间 (秒)"""

REBIND_TIMEOUT = 30.0
"""监听地址切换时等待补丁进程新 services 通道的默认时间窗口 (秒), 与补丁进程的待切换超时一致"""

_MAIN_CONNECTION_RETENTION = 32
_WILDCARD_HOSTS = frozenset({"", "0.0.0.0", "::", "[::]"})
_CAPABILITY_CONTROL = "control"
_CAPABILITY_LEGACY = "legacy"
_CAPABILITY_UNKNOWN = "unknown"
# 补丁进程以这些错误码拒绝 connection.update 时, 说明它无法执行切换, 而不是切换失败。
_UNSUPPORTED_UPDATE_CODES = frozenset({"forbidden", "unsupported_transport", "unknown_request"})


class _RuntimeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@dataclass
class _MainConnection:
    """一条补丁进程主连接的诊断记录; ``hello`` 中的 version 与 features 只用于诊断, 不参与任何判断。"""

    connection_id: int
    address: tuple[str, int] | None
    listener: tuple[str, int]
    message_type: str
    version: Any
    features: list[str]
    server: Any = field(repr=False)
    token: str = field(repr=False)
    connected_at: float = field(default_factory=time.time)
    closed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.connection_id,
            "address": list(self.address) if self.address is not None else None,
            "listener": list(self.listener),
            "type": self.message_type,
            "version": self.version,
            "features": list(self.features),
            "connected_at": self.connected_at,
            "closed_at": self.closed_at,
            "connected": self.closed_at is None,
        }


@dataclass
class _RebindTarget:
    """进行中的监听切换: 只有到达 ``server`` 且使用 ``token`` 的连接才算作补丁进程的新连接。"""

    server: Any
    thread: threading.Thread | None
    token: str
    channel: RuntimeServiceChannel | None = None
    main_closed: bool = False
    sockets: list[Any] = field(default_factory=list)


def _is_loopback_host(host: str) -> bool:
    name = host.strip()
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    name = name.rstrip(".").lower()
    if name == "localhost":
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def _connect_host(bind_host: str) -> str:
    # 监听通配地址时, 让补丁进程连接本机回环地址。
    return DEFAULT_RUNTIME_HOST if bind_host.strip() in _WILDCARD_HOSTS else bind_host


def _close_socket(sock: Any) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


class HotpatcherRuntimeHost(RuntimeControlMixin):
    """
    hotpatcher runtime 宿主。

    该对象监听 TCP JSONL 端口, 接收补丁进程主动连接、配置请求、日志事件和
    services 控制通道。新版补丁进程还能通过 services 通道执行 ``hotpatch.*`` 控制命令
    (``request_control`` 及其便捷方法), 旧版补丁进程只支持 ``request_services``。

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
        auto_probe (bool):
            是否在每条新 services 通道建立时于后台线程探测 ``hotpatch.capabilities``。关闭时 (默认) 在第一次
            需要能力信息时 (``get_capabilities``、``request_control``、``rebind``) 才探测, 不会向通道写入额外请求。
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
        auto_probe: bool = False,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.token = token
        self.get_config = get_config or get_hotpatcher_default_config
        self.on_message = on_message
        self.on_log = on_log
        self.on_status = on_status
        self.confirm_file_operation = confirm_file_operation
        self.auto_probe = auto_probe
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
        # 连接状态 (services 通道、主连接、监听切换) 使用独立的条件变量; 持有期间不做任何网络 I/O,
        # 也不会与记录日志 / 消息使用的 ``_lock`` 嵌套。
        self._state = threading.Condition()
        self._live_channels: list[RuntimeServiceChannel] = []
        self._main_connections: dict[int, _MainConnection] = {}
        self._next_connection_id = 0
        self._transition_tokens: tuple[str, ...] = ()
        self._rebind_target: _RebindTarget | None = None
        self._rebind_lock = threading.Lock()

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
    def capability_status(self) -> str:
        """
        获取当前 services 通道对端的控制能力状态, 只读取缓存, 不会阻塞。

        Returns:
            str:
                ``disconnected`` (没有 services 通道)、``unknown`` (尚未探测或探测失败)、``control`` 或 ``legacy``。
        """

        channel = self._service_channel
        if channel is None or channel.closed:
            return "disconnected"
        return channel.capability_status

    @property
    def control_available(self) -> bool:
        """
        判断当前 services 通道对端是否已确认支持 ``hotpatch.*`` 控制命令, 只读取缓存, 不会阻塞。

        Returns:
            bool:
                能力探测已确认支持控制命令时返回 True。
        """

        return self.capability_status == _CAPABILITY_CONTROL

    @property
    def client_capabilities(self) -> dict[str, Any] | None:
        """
        获取缓存的对端能力, 只读取缓存, 不会阻塞。

        Returns:
            dict[str, Any] | None:
                支持控制命令时为 ``hotpatch.capabilities`` 结果的副本; 旧版对端为 ``{"legacy": True}``;
                未连接或尚未探测时为 None。
        """

        channel = self._service_channel
        if channel is None or channel.closed:
            return None
        if channel.capability_status == _CAPABILITY_LEGACY:
            return {"legacy": True}
        if channel.capability_status == _CAPABILITY_CONTROL and channel.capabilities is not None:
            return copy.deepcopy(channel.capabilities)
        return None

    @property
    def main_connections(self) -> list[dict[str, Any]]:
        """
        获取最近的补丁进程主连接诊断记录 (包含已断开的连接, 最多保留 32 条已断开记录)。

        Returns:
            list[dict[str, Any]]:
                按连接顺序排列的记录, 包含 ``hello`` 中的 ``version`` 与 ``features``, 不包含 token。
        """

        with self._state:
            return [record.to_dict() for record in self._main_connections.values()]

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

        self._server, self._thread = self._listen(self.host, self.port)
        self._warn_if_exposed(self.host, self.token)
        self._emit_status(f"runtime host listening on {self.server_address[0]}:{self.server_address[1]}")
        return self

    def stop(self) -> None:
        """
        停止 runtime host

        会关闭所有 services channel、停止 TCP server (包括进行中的监听切换创建的新监听) 并等待后台线程退出。
        """

        with self._state:
            channels = list(self._live_channels)
            if self._service_channel is not None and self._service_channel not in channels:
                channels.append(self._service_channel)
            target = self._rebind_target
            self._rebind_target = None
            self._transition_tokens = ()
            self._state.notify_all()
        for channel in channels:
            channel.close()
        self._service_channel = None
        if target is not None and target.server is not self._server:
            self._shutdown_listener(target.server, target.thread)
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        self._shutdown_listener(server, thread)
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

    # -- 控制命令 -------------------------------------------------------------

    def get_capabilities(self, *, timeout: float = CONTROL_PROBE_TIMEOUT) -> dict[str, Any]:
        """
        获取当前补丁进程的控制能力, 尚未探测时在调用线程中探测并缓存。

        Args:
            timeout (float):
                探测的超时时间。

        Returns:
            dict[str, Any]:
                ``hotpatch.capabilities`` 结果的副本。

        Raises:
            RemoteServiceError:
                未连接 (``channel_unavailable``)、对端为旧版 (``unsupported``) 或探测失败时抛出。
        """

        _channel, capabilities = self._ensure_control(timeout)
        return copy.deepcopy(capabilities)

    def request_control(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        向补丁进程发送 ``hotpatch.*`` 控制命令并等待结果。

        Args:
            message_type (str):
                控制命令名, 必须出现在能力探测结果的 ``commands`` 或 ``aliases`` 中。
            payload (dict[str, Any] | None):
                命令载荷。
            timeout (float):
                等待响应的超时时间, 尚未探测能力时也用于探测 (最多 ``CONTROL_PROBE_TIMEOUT``)。

        Returns:
            dict[str, Any]:
                命令结果载荷。

        Raises:
            RemoteServiceError:
                未连接、对端为旧版或不提供该命令 (``unsupported``)、请求超时或补丁进程返回错误时抛出,
                ``code`` 为补丁进程的错误码 (例如 ``invalid_payload``、``forbidden``、``not_found``、``busy``)。
        """

        channel, capabilities = self._ensure_control(min(timeout, CONTROL_PROBE_TIMEOUT))
        commands = capabilities.get("commands")
        aliases = capabilities.get("aliases")
        known = message_type in commands if isinstance(commands, list) else False
        if not known and isinstance(aliases, dict):
            known = message_type in aliases
        if not known:
            logger.warning("补丁进程不提供控制命令 %s", message_type)
            raise RemoteServiceError("unsupported", f"connected hotpatcher runtime does not offer {message_type}")
        logger.debug("发送控制命令 %s", message_type)
        return channel.request(message_type, payload or {}, timeout=timeout)

    # -- 监听切换 -------------------------------------------------------------

    def rebind(
        self,
        host: str | None = None,
        port: int | None = None,
        token: str | None = None,
        *,
        timeout: float = REBIND_TIMEOUT,
    ) -> dict[str, Any]:
        """
        修改本宿主的监听地址、端口或 token, 并让已连接的补丁进程跟随切换 (先建后拆)。

        流程: 在新地址上启动第二个监听 (只改 token 时复用当前监听), 在切换窗口内同时接受新旧 token; 补丁进程支持
        ``hotpatch.connection.update`` 时通过当前 services 通道发送该命令; 在 ``timeout`` 内等待补丁进程在新监听上
        以新 token 打开 services 通道并关闭旧通道; 成功后停止旧监听并丢弃旧 token。超时或失败时关闭新监听
        (以及新监听上已建立的连接), 旧监听与旧 token 保持不变。

        没有补丁进程连接时只移动监听: 启动新监听、停止旧监听, 报告 ``switched`` 且 ``child`` 为 None。宿主未启动时
        只更新地址与 token 属性。

        Args:
            host (str | None):
                新监听地址, None 时保持不变。监听通配地址时补丁进程会被要求连接 ``127.0.0.1``;
                非回环地址需要补丁进程的启动环境设置 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ALLOW_NON_LOOPBACK=1``。
            port (int | None):
                新监听端口, None 时保持不变, 0 表示由系统分配。
            token (str | None):
                新 token, None 时保持不变。
            timeout (float):
                等待补丁进程完成切换的时间窗口。

        Returns:
            dict[str, Any]:
                ``status`` 为 ``switched``、``rolled_back`` (附 ``stage`` 与 ``error``) 或 ``unsupported``
                (附 ``reason``), 以及 ``address`` (当前监听地址) 与 ``previous_address``。

        Raises:
            ValueError:
                没有任何参数变化时抛出。
            RemoteServiceError:
                已有监听切换正在进行时抛出 (``busy``)。
        """

        if not self._rebind_lock.acquire(blocking=False):
            raise RemoteServiceError("busy", "a runtime host rebind is already in progress")
        try:
            return self._rebind(host, port, token, float(timeout))
        finally:
            self._rebind_lock.release()

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

        record = self._register_main_connection(handler, first_message, address)
        try:
            for raw_line in handler.rfile:
                try:
                    message = self._decode(raw_line)
                except Exception as exc:
                    logger.warning("来自 %s 的非法 runtime 消息: %s", address, exc)
                    self._emit_status(f"invalid runtime message from {address}: {exc}")
                    continue
                self._record_message(message, address)
                self._handle_main_message(handler, message)
        finally:
            self._close_main_connection(record)

    def _handle_channel(
        self,
        handler: socketserver.StreamRequestHandler,
        message: dict[str, Any],
        address: tuple[str, int] | None,
    ) -> None:
        channel_name = message.get("channel")
        if channel_name == "services":
            channel = RuntimeServiceChannel(handler.wfile, on_close=self._remove_service_channel)
            self._add_service_channel(channel, handler, message)
            logger.info("services channel 已连接, 来源: %s", address)
            self._emit_status(f"services channel connected from {address}")
            if self.auto_probe:
                threading.Thread(
                    target=self._probe_capabilities,
                    args=(channel, CONTROL_PROBE_TIMEOUT),
                    name="sd-webui-all-in-one-hotpatcher-capability-probe",
                    daemon=True,
                ).start()
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
                if self.service_channel_available:
                    # 监听切换期间旧通道晚于新通道关闭, 状态栏应反映仍然可用的通道。
                    self._emit_status(f"services channel from {address} closed; another services channel is connected")
                else:
                    self._emit_status("services channel disconnected")
            return

        if channel_name == "fault":
            logger.debug("fault channel 已连接, 来源: %s", address)
            self._emit_status(f"fault channel connected from {address}")
            self._track_target_socket(handler, message)
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
        # 按对象身份移除: 监听切换时新通道先到、旧通道后关, 旧通道关闭不能清掉新通道;
        # 新通道先关 (补丁进程在 fault / rebind 阶段回滚) 时回退到仍然存活的较早通道。
        with self._state:
            if channel in self._live_channels:
                self._live_channels.remove(channel)
            if self._service_channel is channel:
                logger.debug("移除已断开的 services channel")
                self._service_channel = next((item for item in reversed(self._live_channels) if not item.closed), None)
            self._state.notify_all()

    def _check_token(self, message: dict[str, Any]) -> bool:
        # 监听切换窗口内同时接受旧 token (self.token) 与新 token; 任一为空表示不校验, 与原有行为一致。
        accepted = (self.token, *self._transition_tokens)
        if not all(accepted):
            return True
        return str(message.get("token", "")) in accepted

    def _listen(self, host: str, port: int) -> tuple[_RuntimeServer, threading.Thread]:
        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:  # noqa: D401
                outer._handle_client(self)

        server = _RuntimeServer((host, port), Handler)
        thread = threading.Thread(
            target=server.serve_forever,
            name="sd-webui-all-in-one-hotpatcher-runtime-host",
            daemon=True,
        )
        thread.start()
        return server, thread

    @staticmethod
    def _shutdown_listener(server: Any, thread: threading.Thread | None) -> None:
        # 只关闭监听套接字; 已建立的连接由各自的处理线程在对端关闭时结束。
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2)

    @staticmethod
    def _warn_if_exposed(host: str, token: str) -> None:
        if not token and not _is_loopback_host(host):
            logger.warning("runtime host 监听非回环地址 %s 且未设置 token, 任何能访问该地址的进程都可以连接并控制补丁进程", host)

    def _add_service_channel(self, channel: RuntimeServiceChannel, handler: socketserver.StreamRequestHandler, message: dict[str, Any]) -> None:
        server = getattr(handler, "server", None)
        token = str(message.get("token", ""))
        with self._state:
            self._live_channels.append(channel)
            self._service_channel = channel
            target = self._rebind_target
            if target is not None and target.channel is None and server is target.server and token == target.token:
                target.channel = channel
                target.sockets.append(handler.connection)
            self._state.notify_all()

    def _track_target_socket(self, handler: socketserver.StreamRequestHandler, message: dict[str, Any]) -> None:
        server = getattr(handler, "server", None)
        with self._state:
            target = self._rebind_target
            if target is not None and server is target.server and str(message.get("token", "")) == target.token:
                target.sockets.append(handler.connection)

    def _register_main_connection(self, handler: socketserver.StreamRequestHandler, message: dict[str, Any], address: tuple[str, int] | None) -> _MainConnection:
        server = getattr(handler, "server", None)
        listener = getattr(server, "server_address", ("", 0))
        features = message.get("features")
        token = str(message.get("token", ""))
        with self._state:
            self._next_connection_id += 1
            record = _MainConnection(
                connection_id=self._next_connection_id,
                address=address,
                listener=(str(listener[0]), int(listener[1])),
                message_type=str(message.get("type", "")),
                version=message.get("version"),
                features=[str(item) for item in features] if isinstance(features, list) else [],
                server=server,
                token=token,
            )
            self._main_connections[record.connection_id] = record
            target = self._rebind_target
            if target is not None and server is target.server and token == target.token:
                target.sockets.append(handler.connection)
        if record.message_type == "hello":
            logger.debug("补丁进程主连接 hello, 来源: %s, version: %s, features: %s", address, record.version, record.features)
        return record

    def _close_main_connection(self, record: _MainConnection) -> None:
        with self._state:
            record.closed_at = time.time()
            target = self._rebind_target
            if target is not None and target.channel is None and self._matches_target(record, target):
                # 补丁进程在切换前回滚时会关闭新主连接, 且不会打开新 services 通道。只有最后一条匹配的主连接关闭才算
                # 回滚, 容忍 ``connection.test`` 等短暂连接 (hello 后立即关闭)。
                if not any(item.closed_at is None and self._matches_target(item, target) for item in self._main_connections.values()):
                    target.main_closed = True
            closed = [key for key, item in self._main_connections.items() if item.closed_at is not None]
            for key in closed[:-_MAIN_CONNECTION_RETENTION]:
                del self._main_connections[key]
            self._state.notify_all()

    @staticmethod
    def _matches_target(record: _MainConnection, target: _RebindTarget) -> bool:
        return record.message_type == "hello" and record.server is target.server and record.token == target.token

    def _probe_capabilities(self, channel: RuntimeServiceChannel, timeout: float) -> None:
        if not channel.probe_lock.acquire(timeout=max(timeout, 0.0)):
            return
        try:
            if channel.closed or channel.capability_status != _CAPABILITY_UNKNOWN:
                return
            try:
                payload = channel.request("hotpatch.capabilities", {}, timeout=timeout)
            except RemoteServiceError as exc:
                if exc.code != "unknown_request":
                    logger.debug("hotpatcher 控制能力探测失败, 稍后重试: %s", exc)
                    return
                channel.capability_status = _CAPABILITY_LEGACY
                logger.info("补丁进程不支持控制命令 (旧版), 只能使用 services.* 请求")
                message = "legacy hotpatcher runtime: control commands unavailable"
            else:
                if not isinstance(payload.get("commands"), list):
                    logger.warning("hotpatcher 控制能力探测结果格式错误, 忽略")
                    return
                channel.capabilities = payload
                channel.capability_status = _CAPABILITY_CONTROL
                logger.debug("补丁进程支持控制命令, control_version: %s", payload.get("control_version"))
                message = f"hotpatcher runtime control available (control_version {payload.get('control_version')})"
        finally:
            channel.probe_lock.release()
        if self._service_channel is channel:
            self._emit_status(message)

    def _ensure_control(self, timeout: float) -> tuple[RuntimeServiceChannel, dict[str, Any]]:
        channel = self._service_channel
        if channel is None or channel.closed:
            logger.warning("services channel 未连接, 无法发送控制命令")
            raise RemoteServiceError("channel_unavailable", "services channel is not connected")
        if channel.capability_status == _CAPABILITY_UNKNOWN:
            self._probe_capabilities(channel, timeout)
        if channel.capability_status == _CAPABILITY_LEGACY:
            raise RemoteServiceError("unsupported", "connected hotpatcher runtime is a legacy peer without control commands; use request_services() for services.* requests")
        capabilities = channel.capabilities
        if channel.capability_status != _CAPABILITY_CONTROL or capabilities is None:
            raise RemoteServiceError("probe_failed", "could not determine the capabilities of the connected hotpatcher runtime")
        return channel, capabilities

    def _rebind(self, host: str | None, port: int | None, token: str | None, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + max(timeout, 0.0)
        old_server = self._server
        old_thread = self._thread
        previous = self.server_address
        old_token = self.token
        new_host = self.host if host is None else str(host)
        new_port = previous[1] if port is None else int(port)
        new_token = old_token if token is None else str(token)
        token_changed = new_token != old_token
        same_listener = new_host == self.host and new_port == previous[1]
        if same_listener and not token_changed:
            raise ValueError("no runtime host connection parameters to change")

        if old_server is None:
            self.host, self.port, self.token = new_host, new_port, new_token
            logger.info("runtime host 未启动, 仅更新监听参数: %s:%s", new_host, new_port)
            return {"status": "switched", "child": None, "listening": False, "address": [new_host, new_port], "previous_address": list(previous), "token_changed": token_changed}

        channel = self._service_channel
        if channel is None or channel.closed:
            return self._move_listener(new_host, new_port, new_token, same_listener=same_listener, previous=previous)

        def report(status: str, **extra: Any) -> dict[str, Any]:
            result = {"status": status, "address": list(self.server_address), "previous_address": list(previous), **extra}
            if status != "switched":
                logger.warning("runtime host 监听切换未完成: %s", {key: value for key, value in result.items() if key != "address"})
            return result

        if channel.capability_status == _CAPABILITY_UNKNOWN:
            self._probe_capabilities(channel, min(max(deadline - time.monotonic(), 0.0), CONTROL_PROBE_TIMEOUT))
        capabilities = channel.capabilities or {}
        if channel.capability_status == _CAPABILITY_LEGACY:
            return report("unsupported", reason="legacy_runtime", message="the connected hotpatcher runtime does not support control commands")
        if channel.capability_status != _CAPABILITY_CONTROL:
            return report("rolled_back", stage="probe", error={"code": "probe_failed", "message": "could not determine the capabilities of the connected hotpatcher runtime"})
        commands = capabilities.get("commands")
        if not isinstance(commands, list) or CONNECTION_UPDATE_COMMAND not in commands:
            return report("unsupported", reason="command_unavailable", message=f"the connected hotpatcher runtime does not offer {CONNECTION_UPDATE_COMMAND}")
        if not old_token:
            return report(
                "unsupported",
                reason="token_required",
                message=f"{CONNECTION_UPDATE_COMMAND} requires a non-empty runtime token; start the host and the runtime with a token",
            )

        if same_listener:
            target_server: Any = old_server
            target_thread: threading.Thread | None = None
        else:
            try:
                target_server, target_thread = self._listen(new_host, new_port)
            except OSError as exc:
                return report("rolled_back", stage="listen", error={"code": "listen_failed", "message": str(exc)})
        bound_port = int(target_server.server_address[1])
        target = _RebindTarget(server=target_server, thread=target_thread, token=new_token)
        with self._state:
            self._rebind_target = target
            self._transition_tokens = (new_token,) if token_changed else ()

        payload: dict[str, Any] = {"port": bound_port}
        if _connect_host(new_host) != _connect_host(self.host):
            payload["host"] = _connect_host(new_host)
        if token_changed:
            payload["token"] = new_token
        logger.info("请求补丁进程切换到 %s:%s", payload.get("host", _connect_host(self.host)), bound_port)
        try:
            response = channel.request(CONNECTION_UPDATE_COMMAND, payload, timeout=max(deadline - time.monotonic(), 0.1))
        except RemoteServiceError as exc:
            self._abort_rebind(target, same_listener=same_listener)
            error = {"code": exc.code, "message": exc.message}
            if exc.code in _UNSUPPORTED_UPDATE_CODES:
                return report("unsupported", reason=exc.code, message=exc.message, error=error)
            return report("rolled_back", stage="update", error=error)

        outcome = self._wait_for_switch(target, channel, deadline)
        if outcome != "switched":
            self._abort_rebind(target, same_listener=same_listener)
            messages = {
                "child_rollback": "the hotpatcher runtime rolled back the connection switch",
                "timeout": "timed out waiting for the hotpatcher runtime to open a services channel on the new listener",
                "stopped": "the runtime host was stopped during the rebind",
            }
            return report("rolled_back", stage="wait", error={"code": outcome, "message": messages[outcome]}, response=response)

        with self._state:
            self.token = new_token
            self._transition_tokens = ()
            if self._rebind_target is target:
                self._rebind_target = None
        if not same_listener:
            self._server, self._thread = target_server, target_thread
            self._shutdown_listener(old_server, old_thread)
        self.host = new_host
        self.port = bound_port
        self._warn_if_exposed(new_host, new_token)
        address = self.server_address
        logger.info("runtime host 已切换到 %s:%s, 补丁进程已跟随切换", address[0], address[1])
        self._emit_status(f"runtime host listening on {address[0]}:{address[1]}; services channel connected")
        new_channel = target.channel
        child = {
            "capability_status": new_channel.capability_status if new_channel is not None else _CAPABILITY_UNKNOWN,
            "control_version": capabilities.get("control_version"),
        }
        return report("switched", child=child, token_changed=token_changed, response=response)

    def _move_listener(self, new_host: str, new_port: int, new_token: str, *, same_listener: bool, previous: tuple[str, int]) -> dict[str, Any]:
        if not same_listener:
            try:
                server, thread = self._listen(new_host, new_port)
            except OSError as exc:
                logger.warning("runtime host 无法监听 %s:%s: %s", new_host, new_port, exc)
                return {"status": "rolled_back", "stage": "listen", "error": {"code": "listen_failed", "message": str(exc)}, "address": list(previous), "previous_address": list(previous)}
            old_server, old_thread = self._server, self._thread
            self._server, self._thread = server, thread
            self._shutdown_listener(old_server, old_thread)
        token_changed = new_token != self.token
        self.token = new_token
        self.host = new_host
        address = self.server_address
        self.port = address[1]
        self._warn_if_exposed(new_host, new_token)
        logger.info("runtime host 已切换到 %s:%s (没有补丁进程连接)", address[0], address[1])
        self._emit_status(f"runtime host listening on {address[0]}:{address[1]}")
        return {"status": "switched", "child": None, "address": list(address), "previous_address": list(previous), "token_changed": token_changed}

    def _wait_for_switch(self, target: _RebindTarget, old_channel: RuntimeServiceChannel, deadline: float) -> str:
        # 补丁进程的提交信号是旧 services 通道关闭; 新通道先关闭或新主连接在通道打开前关闭表示它已回滚。
        with self._state:
            while True:
                if self._rebind_target is not target:
                    return "stopped"
                new_channel = target.channel
                if new_channel is not None:
                    if new_channel.closed:
                        return "child_rollback"
                    if old_channel.closed:
                        return "switched"
                elif target.main_closed:
                    return "child_rollback"
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return "timeout"
                self._state.wait(remaining)

    def _abort_rebind(self, target: _RebindTarget, *, same_listener: bool) -> None:
        with self._state:
            if self._rebind_target is target:
                self._rebind_target = None
            self._transition_tokens = ()
            sockets = list(target.sockets)
            self._state.notify_all()
        # 关闭新监听上已建立的连接 (包括超时后才到达的通道), 旧通道继续服务。
        for sock in sockets:
            _close_socket(sock)
        if not same_listener:
            self._shutdown_listener(target.server, target.thread)

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
