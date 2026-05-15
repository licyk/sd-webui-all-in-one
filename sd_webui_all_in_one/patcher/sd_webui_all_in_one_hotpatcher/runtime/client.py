"""运行时客户端"""

from __future__ import annotations

import os
from typing import Any

from ..exceptions import capture_exception
from .transport import JsonlTcpTransport

DEFAULT_FEATURES = ["config", "progress", "browser", "fileops", "faults", "audit", "logs", "services"]


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
        timeout: float = 5.0,
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
                连接和请求默认超时时间
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

        host = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST")
        port = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT")
        token = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN", "")
        timeout = float(os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT", "5"))

        if not host or not port:
            if required:
                raise RuntimeError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST and SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT are required")
            return None

        try:
            return cls.connect(host, int(port), token=token, timeout=timeout)
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
                本次请求的超时时间

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

        try:
            self.transport.event(message_type, payload)
        except Exception:
            capture_exception()

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
