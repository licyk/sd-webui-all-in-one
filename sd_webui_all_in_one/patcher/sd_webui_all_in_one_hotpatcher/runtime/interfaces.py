"""由项目维护并供运行时传输共享的小型边界。"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RuntimeEventSink(Protocol):
    """非关键运行时事件目标。"""

    def emit_event(self, event_type: str, payload: dict[str, Any] | None = None, /) -> bool | None:
        """接收事件且不要求调用方处理传输 I/O。

        Args:
            event_type (str): 事件类型。
            payload (dict[str, Any] | None): 事件载荷。

        Returns:
            bool | None: 可选的发送结果。
        """


@runtime_checkable
class RuntimeTransportLifecycle(Protocol):
    """所选运行时传输实现的生命周期操作。"""

    def start(self) -> Any:
        """启动由传输管理的后台工作。

        Returns:
            Any: 启动后的传输对象或实现自定义结果。
        """

    def close(self) -> None:
        """释放传输资源。"""

    def status(self) -> dict[str, Any]:
        """返回由传输维护的状态快照。

        Returns:
            dict[str, Any]: 传输状态快照。
        """


@runtime_checkable
class RuntimeCommandHandler(Protocol):
    """在 HTTP 协议实现之外处理一条代理命令。"""

    def __call__(self, command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """返回兼容 JSON 的命令结果。"""


def emit_runtime_event(
    sink: RuntimeEventSink | Any,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> bool | None:
    """在保留旧版鸭子类型的同时通过窄边界发送事件。

    Args:
        sink (RuntimeEventSink | Any): 运行时事件目标。
        event_type (str): 事件类型。
        payload (dict[str, Any] | None): 事件载荷。

    Returns:
        bool | None: 可选的发送结果。
    """

    emitter = getattr(sink, "emit_event", None)
    if emitter is not None:
        return emitter(event_type, payload)
    # RuntimeClient.event() 早于此边界存在，并且仍是公共 API。
    legacy_emitter = getattr(sink, "event", None)
    if legacy_emitter is not None:
        return legacy_emitter(event_type, payload)
    # 一些既有采集测试和嵌入方只在轻量客户端外观上公开形似
    # JsonlTcpTransport 的成员。
    return sink.transport.event(event_type, payload)


__all__ = [
    "RuntimeCommandHandler",
    "RuntimeEventSink",
    "RuntimeTransportLifecycle",
    "emit_runtime_event",
]
