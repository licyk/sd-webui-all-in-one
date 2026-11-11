"""运行时客户端"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any

from ..exceptions import capture_exception
from .connection import (
    COMPATIBILITY_TIMEOUT_ENV,
    CONNECT_TIMEOUT_ENV,
    EVENT_WRITE_TIMEOUT_ENV,
    REQUEST_TIMEOUT_ENV,
    RuntimeConnectionSettings,
    read_connection_env,
)
from .protocol import RuntimeTransportError
from .transport import (
    DEFAULT_CONNECT_TIMEOUT,
    JsonlTcpTransport,
)

DEFAULT_FEATURES = ["config", "progress", "browser", "fileops", "faults", "audit", "logs", "services", "control"]

ConnectionListener = Callable[[Any, BaseException, str, Any], bool]
"""传输故障通知: ``listener(transport, error, source, origin) -> handled``。``source`` 为 ``event`` / ``request`` / ``channel``,
返回 True 表示故障已被接管 (事件计为丢弃, 不再调用 ``capture_exception``)"""

__all__ = [
    "COMPATIBILITY_TIMEOUT_ENV",
    "CONNECT_TIMEOUT_ENV",
    "DEFAULT_FEATURES",
    "EVENT_WRITE_TIMEOUT_ENV",
    "REQUEST_TIMEOUT_ENV",
    "ConnectionListener",
    "RuntimeClient",
]


class RuntimeClient:
    """
    运行时宿主通信客户端

    封装 TCP JSONL transport, 对外提供请求、事件、配置拉取和上下文管理能力。
    所有组件都持有客户端对象而不是传输对象, 因此 ``rebind`` 替换内部传输后它们无需更新。

    Attributes:
        transport (JsonlTcpTransport):
            底层 JSONL TCP 传输对象
    """

    def __init__(self, transport: JsonlTcpTransport):
        self.transport = transport
        self._transport_lock = threading.Lock()
        self._connection_listener: ConnectionListener | None = None

    def rebind(self, transport: JsonlTcpTransport) -> JsonlTcpTransport:
        """
        原子地替换底层传输, 不关闭旧传输

        已在进行中的发送继续使用其开始时读取的传输; ``host``、``port`` 和 ``token`` 随新传输变化。

        Args:
            transport (JsonlTcpTransport):
                新的已连接传输对象

        Returns:
            JsonlTcpTransport:
                被替换的旧传输对象, 由调用方负责关闭
        """

        with self._transport_lock:
            previous = self.transport
            self.transport = transport
        return previous

    @property
    def connection_listener(self) -> ConnectionListener | None:
        """
        当前传输故障通知函数

        Returns:
            ConnectionListener | None:
                由连接管理器登记的通知函数, 未登记时为 None
        """

        return getattr(self, "_connection_listener", None)

    def set_connection_listener(self, listener: ConnectionListener | None) -> ConnectionListener | None:
        """
        登记传输故障通知函数

        未登记时 (默认) 客户端行为与原来完全一致。

        Args:
            listener (ConnectionListener | None):
                通知函数, None 表示注销

        Returns:
            ConnectionListener | None:
                之前登记的通知函数
        """

        previous = getattr(self, "_connection_listener", None)
        self._connection_listener = listener
        return previous

    def report_connection_lost(self, reason: str = "connection lost", *, origin: Any = None) -> bool:
        """
        报告与宿主的连接已丢失 (例如 services 通道读到 EOF)

        Args:
            reason (str):
                原因描述
            origin (Any):
                报告来源对象, 例如 services 通道

        Returns:
            bool:
                通知函数接管时返回 True; 未登记通知函数时返回 False
        """

        return self._notify_failure(self.transport, RuntimeTransportError(reason), "channel", origin)

    def _notify_failure(self, transport: Any, error: BaseException, source: str, origin: Any = None) -> bool:
        # 未调用 __init__ 的子类或替身对象没有该属性, 视为未登记。
        listener = getattr(self, "_connection_listener", None)
        if listener is None:
            return False
        try:
            return bool(listener(transport, error, source, origin))
        except Exception:
            return False

    @property
    def host(self) -> str:
        """
        宿主地址

        Returns:
            str:
                当前连接的宿主地址
        """

        return self.transport.host

    @property
    def port(self) -> int:
        """
        宿主端口

        Returns:
            int:
                当前连接的宿主端口
        """

        return self.transport.port

    @property
    def token(self) -> str:
        """
        连接 token

        Returns:
            str:
                当前连接使用的 token
        """

        return self.transport.token

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
    ) -> "RuntimeClient":
        """
        连接运行时宿主

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
                请求未显式给出 timeout 时的默认操作超时。
            event_write_timeout (float | None):
                best-effort 事件和原始消息的写入超时。
            features (list[str] | None):
                握手时声明的能力列表

        Returns:
            RuntimeClient:
                已连接的客户端
        """

        transport = JsonlTcpTransport.connect(
            host,
            port,
            token=token,
            timeout=timeout,
            connect_timeout=connect_timeout,
            default_request_timeout=default_request_timeout,
            event_write_timeout=event_write_timeout,
            features=features or DEFAULT_FEATURES,
        )
        return cls(transport)

    @classmethod
    def connect_from_env(cls, *, required: bool = False) -> "RuntimeClient | None":
        """
        从环境变量读取连接参数并连接宿主

        Args:
            required (bool):
                缺少连接参数或连接失败时是否抛出异常

        Returns:
            RuntimeClient | None:
                已连接的客户端。未配置且 ``required`` 为 False 时返回 None。

        Raises:
            RuntimeError:
                required 为 True 且缺少 host 或 port 时抛出。
            Exception:
                required 为 True 且连接宿主失败时抛出原始异常。
        """

        # 超时解析失败与原实现一样直接抛出 (即使未配置 host/port); 端口转换与建连失败才受 ``required`` 控制。
        values = read_connection_env()
        if values is None:
            if required:
                raise RuntimeError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST and SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT are required")
            return None

        try:
            settings = RuntimeConnectionSettings.from_env_values(values)
            return cls.connect(
                settings.host,
                settings.port,
                token=settings.token,
                timeout=settings.compatibility_timeout,
                connect_timeout=settings.connect_timeout,
                default_request_timeout=settings.request_timeout,
                event_write_timeout=settings.event_write_timeout,
            )
        except Exception:
            if required:
                raise
            if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG") == "1":
                capture_exception()
            return None

    def request(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        发送需要响应的请求

        Args:
            message_type (str):
                请求类型
            payload (dict[str, Any] | None):
                请求载荷
            timeout (float | None):
                本次请求的超时时间。为 None 时使用 transport 的有限默认值。

        Returns:
            dict[str, Any]:
                宿主返回的响应载荷

        Raises:
            Exception:
                传输层抛出的异常原样重新抛出; 抛出前通知已登记的连接管理器。
        """

        transport = self.transport
        try:
            return transport.request(message_type, payload, timeout=timeout)
        except Exception as exc:
            self._notify_failure(transport, exc, "request")
            raise

    def event(self, message_type: str, payload: dict[str, Any] | None = None) -> None:
        """
        发送 best-effort 事件

        Args:
            message_type (str):
                事件类型
            payload (dict[str, Any] | None):
                事件载荷
        """

        self.emit_event(message_type, payload)

    def emit_event(self, message_type: str, payload: dict[str, Any] | None = None) -> bool:
        """实现与传输无关的尽力发送事件边界。

        Args:
            message_type (str): 事件类型。
            payload (dict[str, Any] | None): 事件载荷。

        Returns:
            bool: 事件发送成功时返回 ``True``。
        """

        transport = self.transport
        try:
            transport.event(message_type, payload)
            return True
        except Exception as exc:
            if self._notify_failure(transport, exc, "event"):
                return False
            capture_exception()
            return False

    def start(self) -> "RuntimeClient":
        """返回已由 :meth:`connect` 启动的旧版连接。

        Returns:
            RuntimeClient: 当前运行时客户端。
        """

        return self

    def status(self) -> dict[str, Any]:
        """在不改变旧版 API 的情况下返回最小生命周期快照。

        Returns:
            dict[str, Any]: 传输状态、宿主和端口信息。
        """

        return {
            "transport": "legacy",
            "status": "closed" if self.transport.closed else "connected",
            "host": self.host,
            "port": self.port,
        }

    def get_config(self) -> dict[str, Any]:
        """
        从宿主拉取配置

        Returns:
            dict[str, Any]:
                宿主返回的配置对象。响应不是对象时返回空字典。
        """

        payload = self.request("config.get")
        config = payload.get("config", payload)
        return config if isinstance(config, dict) else {}

    def close(self) -> None:
        """关闭底层 transport"""

        self.transport.close()

    def __enter__(self) -> "RuntimeClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
