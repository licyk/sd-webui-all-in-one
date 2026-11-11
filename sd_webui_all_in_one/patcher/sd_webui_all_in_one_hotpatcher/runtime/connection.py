"""旧版运行时连接参数与连接管理器。

``RuntimeConnectionSettings`` 是旧版 TCP JSONL 连接参数的不可变记录: ``from_env`` 读取与
``RuntimeClient.connect_from_env`` 完全相同的环境变量 (默认值与优先级一致), ``merged`` 生成经过校验的新参数,
``redacted`` 生成脱敏后的可序列化视图。

``ConnectionManager`` 管理一个 ``RuntimeClient`` 的连接 (每个状态对象一个, 见 ``get_connection_manager``):

- ``update`` 采用先建后拆 (make-before-break): 校验 → 建立新主连接并发送 hello (失败时不做任何修改) →
  返回成功并把切换交给 ``defer`` (旧版通道的 ``after_send``, 即响应写出之后) → 切换时依次打开新的 services 通道、
  在新 fault 通道上重新启用 faulthandler、``client.rebind``; 任一步失败则回滚到旧连接并关闭新套接字,
  成功后关闭旧 services 通道与旧主连接;
- ``test`` 只建立连接并发送 hello, 随即关闭, 不切换;
- 可选自动重连 (``reconnect=True``, 默认关闭): 主连接写入失败或 services 通道读到 EOF 时, 后台守护线程按指数退避
  (``reconnect_initial`` 到 ``reconnect_max``) 重新连接同一目标, 断开期间的事件尽力丢弃并计数, 重连后重新打开
  services 与 fault 通道并发送 ``log.dropped`` 诊断事件。

锁约定: 管理器内部锁是叶子锁, 只保护内存字段; 建连、发送、关闭套接字等 I/O 一律在锁外执行。
"""

from __future__ import annotations

import faulthandler
import ipaddress
import math
import os
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, cast

from ..state import HotpatcherState, get_default_state
from .protocol import RuntimeTransportError
from .transport import DEFAULT_CONNECT_TIMEOUT, DEFAULT_EVENT_WRITE_TIMEOUT, DEFAULT_REQUEST_TIMEOUT, JsonlTcpTransport

if TYPE_CHECKING:
    from ..services import ServiceControlChannel
    from .client import RuntimeClient
    from .faults import FaultChannel

__all__ = [
    "ALLOW_NON_LOOPBACK_ENV",
    "COMPATIBILITY_TIMEOUT_ENV",
    "CONNECTION_FIELDS",
    "CONNECT_TIMEOUT_ENV",
    "DEFAULT_RECONNECT_INITIAL",
    "DEFAULT_RECONNECT_MAX",
    "EVENT_WRITE_TIMEOUT_ENV",
    "HOST_ENV",
    "PENDING_SWITCH_TIMEOUT",
    "PORT_ENV",
    "RECONNECT_ENV",
    "REQUEST_TIMEOUT_ENV",
    "TOKEN_ENV",
    "ConnectionBusyError",
    "ConnectionFailedError",
    "ConnectionManager",
    "RuntimeConnectionSettings",
    "connect_transport",
    "get_connection_manager",
    "is_loopback_host",
    "read_connection_env",
]

HOST_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST"
"""宿主地址环境变量"""

PORT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"
"""宿主端口环境变量"""

TOKEN_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"
"""握手 token 环境变量"""

CONNECT_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONNECT_TIMEOUT"
"""建连超时环境变量, 未设置时使用兼容超时"""

REQUEST_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REQUEST_TIMEOUT"
"""默认请求超时环境变量, 未设置时使用兼容超时"""

EVENT_WRITE_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_EVENT_WRITE_TIMEOUT"
"""事件写入超时环境变量, 未设置时使用兼容超时"""

COMPATIBILITY_TIMEOUT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT"
"""兼容超时环境变量, 同时作为三个细分超时的默认值"""

RECONNECT_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RECONNECT"
"""值为 ``1`` 时启用自动重连"""

ALLOW_NON_LOOPBACK_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ALLOW_NON_LOOPBACK"
"""值为 ``1`` 时允许 ``merged`` 切换到非回环地址"""

DEFAULT_RECONNECT_INITIAL = 0.1
"""自动重连的初始退避秒数"""

DEFAULT_RECONNECT_MAX = 5.0
"""自动重连的最大退避秒数"""

PENDING_SWITCH_TIMEOUT = 30.0
"""已建立但尚未切换的新连接的最长保留秒数; 响应写出失败导致切换回调被丢弃时, 下一次操作会清理过期的新连接"""

CONNECTION_FIELDS: tuple[str, ...] = (
    "host",
    "port",
    "token",
    "connect_timeout",
    "request_timeout",
    "event_write_timeout",
    "reconnect",
    "reconnect_initial",
    "reconnect_max",
    "allow_non_loopback",
)
"""``RuntimeConnectionSettings.merged`` 接受的字段"""

MAX_HOST_CHARS = 253
"""主机名最大长度"""

MAX_TOKEN_CHARS = 4096
"""token 最大长度"""

DIAGNOSTIC_LIMIT = 50
"""连接管理器保留的诊断条数"""

_TIMEOUT_FIELDS = ("connect_timeout", "request_timeout", "event_write_timeout", "reconnect_initial", "reconnect_max")
_BOOL_FIELDS = ("reconnect", "allow_non_loopback")
_REDACTED = "***"


class ConnectionFailedError(RuntimeError):
    """建立新连接或发送 hello 失败, 连接状态没有任何变化。"""


class ConnectionBusyError(RuntimeError):
    """已有连接切换或重连正在进行。"""


def read_connection_env(environ: Mapping[str, str] | None = None) -> dict[str, Any] | None:
    """
    读取旧版连接环境变量, 只做 ``float`` 解析, 不做范围校验。

    与 ``RuntimeClient.connect_from_env`` 原有的读取顺序一致: 先解析兼容超时与三个细分超时 (解析失败直接抛出
    ``ValueError``, 即使未配置 host/port), 再检查 host 与 port。端口保持原始字符串, 由调用方转换。

    Args:
        environ (Mapping[str, str] | None):
            环境变量映射。为 None 时使用 ``os.environ``。

    Returns:
        dict[str, Any] | None:
            ``host``、``port`` (字符串)、``token``、``compatibility_timeout``、``connect_timeout``、``request_timeout``、
            ``event_write_timeout``、``reconnect``、``allow_non_loopback``; host 或 port 缺失或为空时返回 None。

    Raises:
        ValueError:
            超时环境变量不是合法浮点数时抛出。
    """

    source = os.environ if environ is None else environ
    host = source.get(HOST_ENV)
    port = source.get(PORT_ENV)
    token = source.get(TOKEN_ENV, "")
    compatibility_timeout = float(source.get(COMPATIBILITY_TIMEOUT_ENV, str(DEFAULT_CONNECT_TIMEOUT)))
    connect_timeout = float(source.get(CONNECT_TIMEOUT_ENV, str(compatibility_timeout)))
    request_timeout = float(source.get(REQUEST_TIMEOUT_ENV, str(compatibility_timeout)))
    event_write_timeout = float(source.get(EVENT_WRITE_TIMEOUT_ENV, str(compatibility_timeout)))
    if not host or not port:
        return None
    return {
        "host": host,
        "port": port,
        "token": token,
        "compatibility_timeout": compatibility_timeout,
        "connect_timeout": connect_timeout,
        "request_timeout": request_timeout,
        "event_write_timeout": event_write_timeout,
        "reconnect": source.get(RECONNECT_ENV) == "1",
        "allow_non_loopback": source.get(ALLOW_NON_LOOPBACK_ENV) == "1",
    }


def is_loopback_host(host: Any) -> bool:
    """
    判断主机是否为回环地址, 不做 DNS 解析。

    ``localhost`` 视为回环; IP 字面量 (可带方括号) 按 ``127.0.0.0/8`` 与 ``::1`` (含映射到 IPv4 回环的 IPv6 地址)
    判断; 其他主机名一律视为非回环。

    Args:
        host (Any):
            主机地址。

    Returns:
        bool:
            回环地址返回 True。
    """

    if not isinstance(host, str):
        return False
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


@dataclass(frozen=True)
class RuntimeConnectionSettings:
    """
    旧版运行时连接参数。

    ``token`` 不出现在 ``repr`` 中; 需要展示时使用 ``redacted()``。

    Attributes:
        host (str):
            宿主地址。
        port (int):
            宿主端口。
        token (str):
            握手 token, 空字符串表示未设置。
        connect_timeout (float):
            TCP 建连超时秒数。
        request_timeout (float):
            未显式指定时的请求超时秒数。
        event_write_timeout (float):
            尽力发送事件的写入超时秒数。
        reconnect (bool):
            主连接断开后是否自动重连, 默认关闭。
        reconnect_initial (float):
            自动重连的初始退避秒数。
        reconnect_max (float):
            自动重连的最大退避秒数。
        allow_non_loopback (bool):
            ``merged`` 是否允许切换到非回环地址; 远程命令永远不能开启。
        compatibility_timeout (float):
            ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT`` 兼容超时, 只用于 ``connect_from_env`` 保持原有调用参数。
    """

    host: str
    port: int
    token: str = field(default="", repr=False)
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT
    event_write_timeout: float = DEFAULT_EVENT_WRITE_TIMEOUT
    reconnect: bool = False
    reconnect_initial: float = DEFAULT_RECONNECT_INITIAL
    reconnect_max: float = DEFAULT_RECONNECT_MAX
    allow_non_loopback: bool = False
    compatibility_timeout: float = DEFAULT_CONNECT_TIMEOUT

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> RuntimeConnectionSettings | None:
        """
        从环境变量读取连接参数, 默认值与优先级与 ``RuntimeClient.connect_from_env`` 一致。

        只做类型转换, 不做范围或回环校验: 启动环境由宿主提供, 其目标与原有行为一样直接使用。

        Args:
            environ (Mapping[str, str] | None):
                环境变量映射。为 None 时使用 ``os.environ``。

        Returns:
            RuntimeConnectionSettings | None:
                连接参数; host 或 port 缺失时返回 None。

        Raises:
            ValueError:
                超时不是合法浮点数或端口不是合法整数时抛出。
        """

        values = read_connection_env(environ)
        if values is None:
            return None
        return cls.from_env_values(values)

    @classmethod
    def from_env_values(cls, values: Mapping[str, Any]) -> RuntimeConnectionSettings:
        """
        由 ``read_connection_env`` 的结果构造连接参数。

        Args:
            values (Mapping[str, Any]):
                ``read_connection_env`` 返回的映射。

        Returns:
            RuntimeConnectionSettings:
                连接参数。

        Raises:
            ValueError:
                端口不是合法整数时抛出。
        """

        return cls(
            host=values["host"],
            port=int(values["port"]),
            token=values["token"],
            connect_timeout=values["connect_timeout"],
            request_timeout=values["request_timeout"],
            event_write_timeout=values["event_write_timeout"],
            reconnect=bool(values.get("reconnect", False)),
            allow_non_loopback=bool(values.get("allow_non_loopback", False)),
            compatibility_timeout=values["compatibility_timeout"],
        )

    @classmethod
    def from_transport(cls, transport: Any, environ: Mapping[str, str] | None = None) -> RuntimeConnectionSettings:
        """
        由已连接的传输对象推导连接参数, ``reconnect`` 与 ``allow_non_loopback`` 取自环境变量。

        Args:
            transport (Any):
                ``JsonlTcpTransport`` 或具有相同属性的对象。
            environ (Mapping[str, str] | None):
                环境变量映射。为 None 时使用 ``os.environ``。

        Returns:
            RuntimeConnectionSettings:
                连接参数。
        """

        source = os.environ if environ is None else environ
        connect_timeout = float(getattr(transport, "connect_timeout", DEFAULT_CONNECT_TIMEOUT))
        return cls(
            host=str(transport.host),
            port=int(transport.port),
            token=str(getattr(transport, "token", "") or ""),
            connect_timeout=connect_timeout,
            request_timeout=float(getattr(transport, "default_request_timeout", DEFAULT_REQUEST_TIMEOUT)),
            event_write_timeout=float(getattr(transport, "event_write_timeout", DEFAULT_EVENT_WRITE_TIMEOUT)),
            reconnect=source.get(RECONNECT_ENV) == "1",
            allow_non_loopback=source.get(ALLOW_NON_LOOPBACK_ENV) == "1",
            compatibility_timeout=connect_timeout,
        )

    def merged(self, changes: Mapping[str, Any]) -> RuntimeConnectionSettings:
        """
        合并修改并校验, 返回新参数。

        校验规则: 只接受 ``CONNECTION_FIELDS`` 中的字段; host 为非空且不含空白的字符串; port 为 1-65535 的整数
        (不接受 bool); 各超时与退避为有限正数, 且 ``reconnect_max`` 不小于 ``reconnect_initial``; token 为字符串;
        ``reconnect`` 与 ``allow_non_loopback`` 为 bool。host 改变时, 新地址必须是回环地址 (``localhost``、
        ``127.0.0.0/8``、``::1``, 不做 DNS), 除非合并后的 ``allow_non_loopback`` 为 True。

        Args:
            changes (Mapping[str, Any]):
                要修改的字段。

        Returns:
            RuntimeConnectionSettings:
                新参数。

        Raises:
            ValueError:
                字段未知或取值非法时抛出, 信息中不包含 token。
        """

        if not isinstance(changes, Mapping):
            raise ValueError("connection changes must be a mapping")
        unknown = sorted(str(key) for key in changes if key not in CONNECTION_FIELDS)
        if unknown:
            raise ValueError(f"unknown connection fields: {', '.join(unknown)}")
        values: dict[str, Any] = {}
        for key, value in changes.items():
            if key == "host":
                values[key] = _validated_host(value)
            elif key == "port":
                if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
                    raise ValueError(f"port must be an integer between 1 and 65535, got {value!r}")
                values[key] = value
            elif key == "token":
                if not isinstance(value, str):
                    raise ValueError("token must be a string")
                if len(value) > MAX_TOKEN_CHARS:
                    raise ValueError(f"token exceeds {MAX_TOKEN_CHARS} characters")
                values[key] = value
            elif key in _TIMEOUT_FIELDS:
                values[key] = _positive_finite(key, value)
            elif key in _BOOL_FIELDS:
                if not isinstance(value, bool):
                    raise ValueError(f"{key} must be a bool, got {type(value).__name__}")
                values[key] = value
        result = replace(self, **values)
        if result.reconnect_max < result.reconnect_initial:
            raise ValueError("reconnect_max must not be smaller than reconnect_initial")
        if result.host != self.host and not result.allow_non_loopback and not is_loopback_host(result.host):
            raise ValueError(f"host {result.host!r} is not a loopback address; non-loopback hosts must be allowed in-process with allow_non_loopback")
        return result

    def redacted(self) -> dict[str, Any]:
        """
        生成脱敏后的可序列化视图。

        Returns:
            dict[str, Any]:
                全部连接字段 (不含兼容超时); ``token`` 已设置时为 ``***``, 未设置时为空字符串, 另有 ``token_set``。
        """

        return {
            "host": self.host,
            "port": self.port,
            "token": _REDACTED if self.token else "",
            "token_set": bool(self.token),
            "connect_timeout": self.connect_timeout,
            "request_timeout": self.request_timeout,
            "event_write_timeout": self.event_write_timeout,
            "reconnect": self.reconnect,
            "reconnect_initial": self.reconnect_initial,
            "reconnect_max": self.reconnect_max,
            "allow_non_loopback": self.allow_non_loopback,
        }


def _validated_host(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("host must be a non-empty string")
    host = value.strip()
    if len(host) > MAX_HOST_CHARS or any(char.isspace() for char in host):
        raise ValueError(f"host must not contain whitespace or exceed {MAX_HOST_CHARS} characters")
    return host


def _positive_finite(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {value!r}")
    return number


def connect_transport(settings: RuntimeConnectionSettings, features: list[str] | None = None) -> JsonlTcpTransport:
    """
    按连接参数建立新的主连接并发送 hello。

    Args:
        settings (RuntimeConnectionSettings):
            连接参数。
        features (list[str] | None):
            hello 声明的能力列表。为 None 时使用 ``RuntimeClient`` 的默认能力列表。

    Returns:
        JsonlTcpTransport:
            已发送 hello 的传输对象。
    """

    if features is None:
        from .client import DEFAULT_FEATURES

        features = list(DEFAULT_FEATURES)
    return JsonlTcpTransport.connect(
        settings.host,
        settings.port,
        token=settings.token,
        timeout=settings.connect_timeout,
        connect_timeout=settings.connect_timeout,
        default_request_timeout=settings.request_timeout,
        event_write_timeout=settings.event_write_timeout,
        features=features,
    )


def _open_services_channel(manager: ConnectionManager, settings: RuntimeConnectionSettings, previous: ServiceControlChannel) -> ServiceControlChannel:
    from ..services import ServiceControlChannel

    channel = ServiceControlChannel(
        manager.client,
        previous.service,
        connect_timeout=previous.connect_timeout,
        response_write_timeout=previous.response_write_timeout,
        endpoint=(settings.host, settings.port, settings.token),
    )
    return channel.start()


def _open_fault_channel(manager: ConnectionManager, settings: RuntimeConnectionSettings, previous: FaultChannel) -> FaultChannel:
    from .faults import open_fault_channel

    return open_fault_channel(
        settings.host,
        settings.port,
        settings.token,
        timeout=previous.timeout,
        all_threads=previous.all_threads,
        enable=previous.enabled,
        client=manager.client,
    )


@dataclass
class _PendingSwitch:
    """已建立新主连接、等待切换的记录。"""

    settings: RuntimeConnectionSettings
    transport: Any
    created: float


ServicesOpener = Callable[["ConnectionManager", RuntimeConnectionSettings, "ServiceControlChannel"], "ServiceControlChannel"]
"""打开新 services 通道的函数: ``opener(manager, settings, previous_channel) -> channel``"""

FaultOpener = Callable[["ConnectionManager", RuntimeConnectionSettings, "FaultChannel"], "FaultChannel"]
"""打开新 fault 通道的函数: ``opener(manager, settings, previous_channel) -> channel``"""


class ConnectionManager:
    """
    单个旧版 ``RuntimeClient`` 的连接管理器。

    Attributes:
        client (RuntimeClient):
            被管理的运行时客户端, 切换只替换其内部传输, 所有持有该客户端的组件保持有效。
        state (HotpatcherState):
            所属状态对象, 用于查找 services 通道 (``bootstrap_service_control_channel``) 与 fault 通道
            (``fault_channel``), 以及记录事件和跟踪。
        diagnostics (list[dict[str, Any]]):
            最近的连接诊断 (最多 ``DIAGNOSTIC_LIMIT`` 条), 不包含 token。
    """

    def __init__(
        self,
        client: RuntimeClient,
        *,
        state: HotpatcherState | None = None,
        settings: RuntimeConnectionSettings | None = None,
        connector: Callable[[RuntimeConnectionSettings], Any] | None = None,
        services_opener: ServicesOpener | None = None,
        fault_opener: FaultOpener | None = None,
        sleep: Callable[[float], Any] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """
        创建连接管理器; 需调用 ``attach`` 才会接收客户端的断线通知。

        Args:
            client (RuntimeClient):
                已连接的旧版运行时客户端。
            state (HotpatcherState | None):
                所属状态对象。为 None 时使用默认状态。
            settings (RuntimeConnectionSettings | None):
                当前连接参数。为 None 时由客户端的传输推导。
            connector (Callable[[RuntimeConnectionSettings], Any] | None):
                建立主连接并发送 hello 的函数, 默认 ``connect_transport``。
            services_opener (ServicesOpener | None):
                打开新 services 通道的函数, 主要用于测试。
            fault_opener (FaultOpener | None):
                打开新 fault 通道的函数, 主要用于测试。
            sleep (Callable[[float], Any] | None):
                重连退避等待函数, 默认是可被 ``close`` 打断的等待。
            clock (Callable[[], float] | None):
                单调时钟, 默认 ``time.monotonic``。
        """

        self.client = client
        self.state = state or get_default_state()
        self._settings = settings if settings is not None else RuntimeConnectionSettings.from_transport(client.transport)
        self._connector = connector or connect_transport
        self._services_opener: ServicesOpener = services_opener or _open_services_channel
        self._fault_opener: FaultOpener = fault_opener or _open_fault_channel
        self._stop = threading.Event()
        self._sleep = sleep or self._stop.wait
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._status = "disconnected" if getattr(client.transport, "closed", False) else "connected"
        self._busy = False
        self._pending: _PendingSwitch | None = None
        self._closed = False
        self._attached = False
        self._reconnect_thread: threading.Thread | None = None
        self._dropped_pending = 0
        self._dropped_total = 0
        self._reconnect_attempts = 0
        self._reconnects = 0
        self._switches = 0
        self._last_error: str | None = None
        self._last_change: dict[str, Any] | None = None
        self.diagnostics: list[dict[str, Any]] = []

    # -- 生命周期 -----------------------------------------------------------

    def attach(self) -> ConnectionManager:
        """
        在客户端上登记断线通知。未启用重连时通知被忽略, 客户端行为不变。

        Returns:
            ConnectionManager:
                当前管理器。
        """

        self.client.set_connection_listener(self._on_transport_failure)
        self._attached = True
        return self

    def close(self) -> None:
        """停止重连线程、注销断线通知并关闭尚未切换的新连接; 不关闭当前连接。"""

        with self._lock:
            self._closed = True
            # 重连中关闭时停止重连并报告 closed; 已连接时当前连接保持可用, 状态不变。
            if self._status != "connected":
                self._status = "closed"
            pending = self._pending
            self._pending = None
            thread = self._reconnect_thread
        self._stop.set()
        if self._attached and self.client.connection_listener == self._on_transport_failure:
            self.client.set_connection_listener(None)
        self._attached = False
        if pending is not None:
            _close_quietly(pending.transport)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)

    @property
    def settings(self) -> RuntimeConnectionSettings:
        """
        当前连接参数。

        Returns:
            RuntimeConnectionSettings:
                最近一次成功切换后的参数。
        """

        with self._lock:
            return self._settings

    # -- 查询 ---------------------------------------------------------------

    def get(self) -> dict[str, Any]:
        """
        生成连接快照, token 已脱敏。

        Returns:
            dict[str, Any]:
                ``settings`` (含 ``transport: "legacy"`` 与 ``editable: True``)、``state`` (``connected`` /
                ``reconnecting`` / ``closed``)、``connected``、``dropped_events`` (断开期间丢弃的事件总数)、
                ``reconnect_attempts``、``reconnects``、``switches``、``pending_switch``、``last_error``、
                ``last_change`` 与 ``diagnostics``。
        """

        transport_closed = bool(getattr(self.client.transport, "closed", False))
        with self._lock:
            settings = self._settings
            status = self._status
            snapshot = {
                "state": status,
                "connected": status == "connected" and not transport_closed,
                "dropped_events": self._dropped_total,
                "reconnect_attempts": self._reconnect_attempts,
                "reconnects": self._reconnects,
                "switches": self._switches,
                "pending_switch": self._pending is not None,
                "last_error": self._last_error,
                "last_change": dict(self._last_change) if self._last_change is not None else None,
                "diagnostics": [dict(item) for item in self.diagnostics[-10:]],
            }
        return {"settings": {"transport": "legacy", "editable": True, **settings.redacted()}, **snapshot}

    # -- 测试与更新 ----------------------------------------------------------

    def test(self, changes: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """
        按合并后的参数建立连接并发送 hello, 随即关闭; 不切换。

        Args:
            changes (Mapping[str, Any] | None):
                要测试的参数修改。

        Returns:
            dict[str, Any]:
                ``ok``、脱敏后的 ``settings`` 与 ``elapsed_ms``。

        Raises:
            ValueError:
                参数校验失败时抛出。
            ConnectionFailedError:
                建连或 hello 失败时抛出。
        """

        self._discard_stale_pending()
        settings = self.settings.merged(changes or {})
        started = self._clock()
        self._trace("connection test", settings.redacted())
        try:
            transport = self._connector(settings)
        except Exception as exc:
            message = _error_text(exc)
            self._trace("connection test failed", {"error": message})
            raise ConnectionFailedError(f"connection test to {settings.host}:{settings.port} failed: {message}") from exc
        _close_quietly(transport)
        return {"ok": True, "settings": settings.redacted(), "elapsed_ms": round((self._clock() - started) * 1000, 3)}

    def update(self, changes: Mapping[str, Any], *, defer: Callable[[Callable[[], Any]], Any] | None = None) -> dict[str, Any]:
        """
        先建后拆地切换连接参数。

        先校验并建立新主连接 (发送 hello); 失败时抛出 ``ConnectionFailedError`` 且不做任何修改。成功后把切换交给
        ``defer`` (例如 ``ctx.after_send.append``, 在响应写出后执行); ``defer`` 为 None 时立即切换。

        Args:
            changes (Mapping[str, Any]):
                要修改的参数。
            defer (Callable[[Callable[[], Any]], Any] | None):
                登记切换回调的函数。

        Returns:
            dict[str, Any]:
                延迟切换时为 ``{"status": "scheduled", "settings": ...}``; 立即切换时为切换报告,
                ``status`` 为 ``switched`` 或 ``rolled_back``。

        Raises:
            ValueError:
                参数校验失败时抛出。
            ConnectionBusyError:
                已有切换或重连安装正在进行时抛出。
            ConnectionFailedError:
                建立新连接失败时抛出。
            RuntimeError:
                管理器已关闭时抛出。
        """

        settings = self.settings.merged(changes)
        self._acquire_busy()
        self._trace("connection update connect", settings.redacted())
        try:
            transport = self._connector(settings)
        except Exception as exc:
            self._release_busy(None)
            message = _error_text(exc)
            self._diagnostic("connect", message)
            self._trace("connection update connect failed", {"error": message})
            raise ConnectionFailedError(f"connecting to {settings.host}:{settings.port} failed: {message}") from exc
        pending = _PendingSwitch(settings=settings, transport=transport, created=self._clock())
        with self._lock:
            self._pending = pending

        def switch() -> dict[str, Any]:
            return self._run_pending(pending)

        if defer is None:
            return switch()
        defer(switch)
        return {"status": "scheduled", "settings": settings.redacted()}

    def _acquire_busy(self) -> None:
        stale: _PendingSwitch | None = None
        with self._lock:
            if self._closed:
                raise RuntimeError("connection manager is closed")
            if self._busy:
                pending = self._pending
                if pending is None or self._clock() - pending.created <= PENDING_SWITCH_TIMEOUT:
                    raise ConnectionBusyError("a connection switch or reconnect is already in progress")
                # 切换回调被丢弃 (例如响应写出失败) 的过期新连接, 由本次操作接管忙标记。
                stale = pending
                self._pending = None
            self._busy = True
        if stale is not None:
            _close_quietly(stale.transport)
            self._diagnostic("pending", "discarded a stale pending connection switch")

    def _release_busy(self, pending: _PendingSwitch | None) -> None:
        with self._lock:
            if pending is None or self._pending is pending:
                self._pending = None
                self._busy = False

    def _discard_stale_pending(self) -> None:
        with self._lock:
            pending = self._pending
            if pending is None or self._clock() - pending.created <= PENDING_SWITCH_TIMEOUT:
                return
            self._pending = None
            self._busy = False
        _close_quietly(pending.transport)
        self._diagnostic("pending", "discarded a stale pending connection switch")

    def _run_pending(self, pending: _PendingSwitch) -> dict[str, Any]:
        with self._lock:
            current = self._pending is pending and not self._closed
        if not current:
            _close_quietly(pending.transport)
            return {"status": "discarded"}
        try:
            return self._install(pending.settings, pending.transport, reason="update")
        finally:
            self._release_busy(pending)

    # -- 切换 ---------------------------------------------------------------

    def _managed_services_channel(self) -> Any:
        channel = self.state.bootstrap_service_control_channel
        if channel is not None and getattr(channel, "client", None) is self.client:
            return channel
        return None

    def _managed_fault_channel(self) -> Any:
        channel = getattr(self.state, "fault_channel", None)
        if channel is not None and getattr(channel, "client", None) is self.client and not getattr(channel, "closed", False):
            return channel
        return None

    def _install(self, settings: RuntimeConnectionSettings, transport: Any, *, reason: str) -> dict[str, Any]:
        """依次打开新 services 通道、新 fault 通道并重新绑定客户端; 失败时回滚。"""

        client = self.client
        old_transport = client.transport
        old_channel = self._managed_services_channel()
        old_fault = self._managed_fault_channel()
        new_channel: Any = None
        new_fault: Any = None
        rebound = False
        stage = "services"
        self._trace("connection switch", {"reason": reason, "services": old_channel is not None, "fault": old_fault is not None, **settings.redacted()})
        try:
            if old_channel is not None:
                new_channel = self._services_opener(self, settings, old_channel)
            stage = "fault"
            if old_fault is not None:
                new_fault = self._fault_opener(self, settings, old_fault)
            stage = "rebind"
            client.rebind(transport)
            rebound = True
        except Exception as exc:
            message = _error_text(exc)
            if rebound:
                client.rebind(old_transport)
            if new_fault is not None:
                if getattr(old_fault, "enabled", False):
                    _reenable_faulthandler(old_fault)
                new_fault.enabled = False
            # 先记录诊断与事件再关闭新套接字, 宿主观察到关闭时状态已经可查询。
            self._diagnostic(stage, message)
            report = {"status": "rolled_back", "reason": reason, "stage": stage, "error": message}
            with self._lock:
                self._last_error = message
                self._last_change = {"status": "rolled_back", "reason": reason, "stage": stage}
            self._record("connection.changed", dict(report))
            _close_quietly(new_fault)
            _close_quietly(new_channel)
            _close_quietly(transport)
            return report

        if old_channel is not None and self.state.bootstrap_service_control_channel is old_channel:
            self.state.bootstrap_service_control_channel = new_channel
        if old_fault is not None:
            # 所有权已转移到新通道: 关闭旧通道时不能禁用刚在新文件上启用的 faulthandler。
            old_fault.enabled = False
            if getattr(self.state, "fault_channel", None) is old_fault:
                self.state.fault_channel = new_fault
        with self._lock:
            self._settings = settings
            if self._status != "closed":
                self._status = "connected"
            if reason == "update":
                self._switches += 1
            else:
                self._reconnects += 1
            self._last_change = {"status": "switched" if reason == "update" else "reconnected", "reason": reason}
        report = {"status": "switched", "reason": reason, "settings": settings.redacted()}
        if reason == "update":
            # 重连成功由重连循环记录 ``reconnected``。
            self._record("connection.changed", dict(report))
        # 旧 services 通道可能正是承载本次命令的通道, 此时运行在其读取线程上; close 不会 join 当前线程。
        _close_quietly(old_channel)
        _close_quietly(old_fault)
        _close_quietly(old_transport)
        return report

    # -- 自动重连 -------------------------------------------------------------

    def _on_transport_failure(self, transport: Any, error: BaseException, source: str, origin: Any = None) -> bool:
        """处理客户端报告的传输故障; 返回 True 表示已接管 (事件计为丢弃, 不再调用 ``capture_exception``)。"""

        if not isinstance(error, (OSError, RuntimeTransportError)):
            return False
        if source == "channel" and origin is not None and origin is not self.state.bootstrap_service_control_channel:
            return False
        start = False
        with self._lock:
            if self._closed or not self._settings.reconnect:
                return False
            if source == "event":
                self._dropped_pending += 1
                self._dropped_total += 1
            if self._status == "connected" and transport is self.client.transport:
                self._status = "reconnecting"
                self._last_error = _error_text(error)
                self._last_change = {"status": "disconnected", "reason": source}
                start = True
        if start:
            _close_quietly(transport)
            self._diagnostic("disconnected", f"{source}: {_error_text(error)}")
            self._record("connection.changed", {"status": "disconnected", "reason": source, "error": _error_text(error)})
            self._start_reconnect_thread()
        return True

    def _start_reconnect_thread(self) -> None:
        thread = threading.Thread(target=self._reconnect_loop, name="sd_webui_all_in_one_hotpatcher-reconnect", daemon=True)
        with self._lock:
            if self._closed or (self._reconnect_thread is not None and self._reconnect_thread.is_alive()):
                return
            # 在锁内启动: 发布到 ``_reconnect_thread`` 的线程总是已启动, ``close`` 可以 join, 并发的故障通知也不会再启动第二个线程。
            # ``start`` 只等待线程完成引导 (目标函数随后才获取本锁), 不做 I/O。
            self._reconnect_thread = thread
            thread.start()

    def _reconnect_loop(self) -> None:
        delay: float | None = None
        while True:
            # 响应写出失败时切换回调会被丢弃, 留下忙标记; 过期后由重连循环清理, 否则重连会永远让路。
            self._discard_stale_pending()
            with self._lock:
                if self._closed or self._status != "reconnecting":
                    return
                settings = self._settings
                self._reconnect_attempts += 1
                attempt = self._reconnect_attempts
            if delay is None:
                delay = settings.reconnect_initial
            self._trace("connection reconnect attempt", {"attempt": attempt, "host": settings.host, "port": settings.port})
            try:
                transport = self._connector(settings)
            except Exception as exc:
                with self._lock:
                    self._last_error = _error_text(exc)
                self._sleep(delay)
                delay = min(delay * 2, settings.reconnect_max)
                continue
            with self._lock:
                proceed = not self._closed and self._status == "reconnecting" and not self._busy
                if proceed:
                    self._busy = True
            if not proceed:
                # 已关闭、已被 update 切换, 或 update 正在进行: 放弃本次连接, 由循环开头决定是否继续。
                _close_quietly(transport)
                with self._lock:
                    done = self._closed or self._status != "reconnecting"
                if done:
                    return
                self._sleep(delay)
                delay = min(delay * 2, settings.reconnect_max)
                continue
            try:
                report = self._install(settings, transport, reason="reconnect")
            finally:
                self._release_busy(None)
            if report["status"] != "switched":
                self._sleep(delay)
                delay = min(delay * 2, settings.reconnect_max)
                continue
            with self._lock:
                dropped = self._dropped_pending
                self._dropped_pending = 0
            self._record("connection.changed", {"status": "reconnected", "attempts": attempt, "dropped_events": dropped, "settings": settings.redacted()})
            if dropped:
                self.client.emit_event("log.dropped", {"count": dropped, "reason": "disconnected"})
            return

    # -- 诊断 ---------------------------------------------------------------

    def _diagnostic(self, stage: str, message: str) -> None:
        with self._lock:
            self.diagnostics.append({"stage": stage, "message": message, "at": time.time()})
            del self.diagnostics[:-DIAGNOSTIC_LIMIT]

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            from ..control.events import record_event

            record_event(event_type, payload, state=self.state, tag="conn")
        except Exception:
            return

    def _trace(self, message: str, fields: Mapping[str, Any] | None = None) -> None:
        tracer = self.state.tracer
        if tracer is None or not tracer.active:
            return
        try:
            tracer.trace("conn", message, fields)
        except Exception:
            return


def _error_text(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"[:500]


def _close_quietly(resource: Any) -> None:
    if resource is None:
        return
    try:
        resource.close()
    except Exception:
        pass


def _reenable_faulthandler(channel: Any) -> None:
    try:
        faulthandler.enable(file=channel.file, all_threads=bool(getattr(channel, "all_threads", False)))
    except Exception:
        pass


def get_connection_manager(state: HotpatcherState | None = None, *, create: bool = True) -> ConnectionManager | None:
    """
    获取状态对象当前旧版运行时客户端的连接管理器, 首次访问时创建并登记断线通知。

    只有支持 ``rebind`` 的客户端 (``RuntimeClient``) 才有管理器; 桌面代理客户端、未连接或其他替身对象返回 None。
    ``bootstrap_runtime_client`` 换成另一个客户端时, 旧管理器会被关闭并为新客户端创建管理器。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        create (bool):
            不存在时是否创建。

    Returns:
        ConnectionManager | None:
            连接管理器。
    """

    active_state = state or get_default_state()
    client = active_state.bootstrap_runtime_client
    if client is None or not callable(getattr(client, "rebind", None)) or not callable(getattr(client, "set_connection_listener", None)):
        return None
    manager = active_state.connection_manager
    if manager is not None and manager.client is client:
        return manager
    if not create:
        return None
    created = ConnectionManager(cast("RuntimeClient", client), state=active_state)
    with active_state.control_lock:
        existing = active_state.connection_manager
        if existing is not None and existing.client is client:
            return existing
        active_state.connection_manager = created
    if existing is not None:
        existing.close()
    return created.attach()
