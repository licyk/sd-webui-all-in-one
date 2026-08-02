"""运行时客户端"""

from __future__ import annotations

import os
from typing import Any

from ..exceptions import capture_exception
from .transport import (
    DEFAULT_CONNECT_TIMEOUT,
    JsonlTcpTransport,
)

DEFAULT_FEATURES = ["config", "progress", "browser", "fileops", "faults", "audit", "logs", "services"]
CONNECT_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONNECT_TIMEOUT"
REQUEST_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REQUEST_TIMEOUT"
EVENT_WRITE_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_EVENT_WRITE_TIMEOUT"
COMPATIBILITY_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT"


class RuntimeClient:
    """
    运行时宿主通信客户端

    封装 TCP JSONL transport, 对外提供请求、事件、配置拉取和上下文管理能力。

    Attributes:
        transport (JsonlTcpTransport):
            底层 JSONL TCP 传输对象
    """

    def __init__(self, transport: JsonlTcpTransport):
        self.transport = transport

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
    ) -> RuntimeClient:
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
    def connect_from_env(cls, *, required: bool = False) -> RuntimeClient | None:
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

        host = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST")
        port = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT")
        token = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN", "")
        compatibility_timeout = float(os.getenv(COMPATIBILITY_TIMEOUT_ENV, str(DEFAULT_CONNECT_TIMEOUT)))
        connect_timeout = float(os.getenv(CONNECT_TIMEOUT_ENV, str(compatibility_timeout)))
        default_request_timeout = float(os.getenv(REQUEST_TIMEOUT_ENV, str(compatibility_timeout)))
        event_write_timeout = float(os.getenv(EVENT_WRITE_TIMEOUT_ENV, str(compatibility_timeout)))

        if not host or not port:
            if required:
                raise RuntimeError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST and SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT are required")
            return None

        try:
            return cls.connect(
                host,
                int(port),
                token=token,
                timeout=compatibility_timeout,
                connect_timeout=connect_timeout,
                default_request_timeout=default_request_timeout,
                event_write_timeout=event_write_timeout,
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
        """

        return self.transport.request(message_type, payload, timeout=timeout)

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

        try:
            self.transport.event(message_type, payload)
            return True
        except Exception:
            capture_exception()
            return False

    def start(self) -> RuntimeClient:
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

    def __enter__(self) -> RuntimeClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
