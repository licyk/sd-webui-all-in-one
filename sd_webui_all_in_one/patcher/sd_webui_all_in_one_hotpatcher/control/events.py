"""补丁事件环形缓冲区与可选的运行时事件转发。

``PatchEventLog`` 保存最近 ``capacity`` 条事件 (默认 1000), 每条事件有单调递增的游标 (从 0 开始)、
``time.time()`` 时间戳、类型和载荷。``read(since_cursor, limit)`` 的返回结构与宿主 ``read_logs`` 一致:
``events``、``start_cursor``、``next_cursor``、``truncated`` (``since_cursor`` 早于最旧的保留事件时为 True),
另有 ``has_more`` 表示是否还有更新的事件未返回 (受 ``limit`` 或字节预算限制)。

开销约定: ``record`` 只在内部叶子锁内分配游标并把 ``(cursor, timestamp, type, payload)`` 元组追加到
``deque``, 不获取 ``control_lock``、不做 JSON 序列化。载荷由调用方新建, 记录后不应再修改;
JSON 安全化、敏感字段脱敏 (``redact_mapping``) 和长度限制在读取或转发时惰性完成。热路径可以传入惰性载荷 ``(builder, *args)`` 元组,
读取、转发或跟踪时才调用 ``builder(*args)`` 构造字典。

转发: 启用后 (配置 ``control.forward_events``, 默认关闭), ``patch.failed``、``set.*``、``feature.*`` 和
``connection.changed`` 事件以 ``hotpatch.event`` 类型通过 ``state.bootstrap_runtime_client`` 发送。
转发在释放内部锁之后进行, 尽力而为且从不抛出异常, 并受每秒条数上限约束, 以保护桌面代理普通事件
240 条的准入额度。
"""

from __future__ import annotations

import enum
import json
import math
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from itertools import islice
from typing import TYPE_CHECKING, Any, TypeAlias

from ..state import get_default_state
from .trace import redact_mapping

if TYPE_CHECKING:
    from ..state import HotpatcherState

__all__ = [
    "DEFAULT_EVENT_CAPACITY",
    "DEFAULT_FORWARD_RATE",
    "DEFAULT_READ_LIMIT",
    "DEFAULT_READ_MAX_BYTES",
    "EVENT_TYPES",
    "EventPayload",
    "FORWARD_EVENT_TYPE",
    "MAX_EVENT_BYTES",
    "MAX_FORWARD_PAYLOAD_BYTES",
    "MAX_READ_LIMIT",
    "PatchEventLog",
    "get_event_log",
    "is_forwarded_event",
    "json_safe",
    "read_events",
    "record_event",
    "resolve_payload",
    "set_event_forwarding",
]

DEFAULT_EVENT_CAPACITY = 1000
"""事件环形缓冲区默认容量"""

DEFAULT_READ_LIMIT = 200
"""``read`` 默认返回的最大事件数"""

MAX_READ_LIMIT = 1000
"""``read`` 单次返回的事件数上限"""

DEFAULT_READ_MAX_BYTES = 48 * 1024
"""``read`` 返回事件列表的默认 JSON 字节预算, 保证单个命令结果低于桌面代理 64 KiB 上限"""

MAX_EVENT_BYTES = 8 * 1024
"""单条事件 JSON 安全化后的字节上限, 超出时载荷被替换为摘要"""

MAX_FORWARD_PAYLOAD_BYTES = 12 * 1024
"""转发事件载荷的字节上限, 低于桌面代理单条事件 16 KiB 上限"""

DEFAULT_FORWARD_RATE = 10
"""每秒最多转发的事件数"""

FORWARD_EVENT_TYPE = "hotpatch.event"
"""转发到运行时通道时使用的事件类型"""

EVENT_TYPES: tuple[str, ...] = (
    "patch.registered",
    "patch.applied",
    "patch.noop",
    "patch.failed",
    "patch.skipped",
    "patch.reverted",
    "import.intercepted",
    "import.skipped",
    "set.loaded",
    "set.unloaded",
    "set.reloaded",
    "set.rolled_back",
    "set.updated",
    "set.failed",
    "set.watch_reload",
    "set.watch_failed",
    "feature.enabled",
    "feature.disabled",
    "feature.updated",
    "connection.changed",
    "debug.strict.changed",
    "debug.trace.changed",
    "debug.forwarding.changed",
)
"""已知事件类型"""

EventPayload: TypeAlias = "dict[str, Any] | tuple[Any, ...] | None"
"""事件载荷: 字典、None 或惰性载荷 ``(builder, *args)``"""

MAX_EVENT_STRING_CHARS = 1000
MAX_EVENT_LIST_ITEMS = 32
MAX_EVENT_DEPTH = 5

_TRACE_TAG_BY_PREFIX = {
    "patch": "patch",
    "import": "import",
    "set": "set",
    "feature": "feature",
    "connection": "conn",
    "debug": "control",
}


def is_forwarded_event(event_type: str) -> bool:
    """
    判断事件类型是否会在启用转发时发送到运行时通道。

    Args:
        event_type (str):
            事件类型。

    Returns:
        bool:
            ``patch.failed``、``set.*``、``feature.*``、``connection.changed`` 返回 True。
    """

    return event_type == "patch.failed" or event_type == "connection.changed" or event_type.startswith(("set.", "feature."))


def json_safe(
    value: Any,
    *,
    max_string: int = MAX_EVENT_STRING_CHARS,
    max_items: int = MAX_EVENT_LIST_ITEMS,
    max_depth: int = MAX_EVENT_DEPTH,
) -> Any:
    """
    把任意值转换为有界的 JSON 安全值。

    Args:
        value (Any):
            任意值。
        max_string (int):
            字符串最大字符数, 超出部分以 ``...`` 截断。
        max_items (int):
            列表和映射的最大条目数, 超出时列表追加 ``{"truncated": N}``, 映射追加 ``truncated_items`` 键。
        max_depth (int):
            最大嵌套深度, 更深的值转为截断后的字符串。

    Returns:
        Any:
            只含 ``dict``/``list``/``str``/``int``/``float``/``bool``/None 的值; 非有限浮点数转为字符串,
            其他对象转为 ``repr`` 字符串。
    """

    return _json_safe(value, max_string, max_items, max_depth, 0)


def _json_safe(value: Any, max_string: int, max_items: int, max_depth: int, depth: int) -> Any:
    if isinstance(value, enum.Enum):
        value = value.value
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, str):
        text = str(value)
        return text if len(text) <= max_string else text[: max(0, max_string - 3)] + "..."
    if depth >= max_depth:
        return _bounded_repr(value, max_string)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                result["truncated_items"] = len(value) - max_items
                break
            result[key if isinstance(key, str) else str(key)] = _json_safe(item, max_string, max_items, max_depth, depth + 1)
        return result
    if isinstance(value, (list, tuple, set, frozenset, deque)):
        items = list(value) if not isinstance(value, (list, tuple)) else value
        bounded = [_json_safe(item, max_string, max_items, max_depth, depth + 1) for item in islice(items, max_items)]
        if len(items) > max_items:
            bounded.append({"truncated": len(items) - max_items})
        return bounded
    return _bounded_repr(value, max_string)


def _bounded_repr(value: Any, limit: int) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<{type(value).__name__}>"
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."


def _encoded_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8"))


class PatchEventLog:
    """
    有界补丁事件环形缓冲区。

    Attributes:
        capacity (int):
            保留的最大事件数。
    """

    def __init__(
        self,
        capacity: int = DEFAULT_EVENT_CAPACITY,
        *,
        sink: Callable[[], Any] | None = None,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        forward_rate: int = DEFAULT_FORWARD_RATE,
    ) -> None:
        """
        创建事件缓冲区。

        Args:
            capacity (int):
                保留的最大事件数, 必须为正整数。
            sink (Callable[[], Any] | None):
                返回当前运行时事件目标 (例如 ``RuntimeClient``) 的函数, 转发时调用; 返回 None 时不转发。
            clock (Callable[[], float]):
                事件时间戳来源。
            monotonic (Callable[[], float]):
                转发限速使用的单调时钟。
            forward_rate (int):
                每秒最多转发的事件数, 必须为正整数。

        Raises:
            ValueError:
                ``capacity`` 或 ``forward_rate`` 不是正整数时抛出。
        """

        self.capacity = _positive_int(capacity, "capacity")
        self._events: deque[tuple[int, float, str, EventPayload]] = deque(maxlen=self.capacity)
        self._next_cursor = 0
        self._lock = threading.Lock()
        self._clock = clock
        self._monotonic = monotonic
        self._sink = sink
        self._forward_enabled = False
        self._forward_rate = _positive_int(forward_rate, "forward_rate")
        self._window_start = -math.inf
        self._window_count = 0
        self._forwarded = 0
        self._rate_limited = 0
        self._forward_failed = 0
        self._guard = threading.local()

    @property
    def forward_enabled(self) -> bool:
        """
        是否启用转发。

        Returns:
            bool:
                启用时返回 True。
        """

        return self._forward_enabled

    @property
    def forward_rate(self) -> int:
        """
        每秒最多转发的事件数。

        Returns:
            int:
                速率上限。
        """

        return self._forward_rate

    def configure_forwarding(self, enabled: bool, *, max_per_second: int | None = None, sink: Callable[[], Any] | None = None) -> None:
        """
        修改转发设置。

        Args:
            enabled (bool):
                是否启用转发。
            max_per_second (int | None):
                新的每秒上限。为 None 时保持不变。
            sink (Callable[[], Any] | None):
                新的事件目标函数。为 None 时保持不变。

        Raises:
            ValueError:
                ``max_per_second`` 不是正整数时抛出。
        """

        rate = None if max_per_second is None else _positive_int(max_per_second, "max_per_second")
        with self._lock:
            self._forward_enabled = bool(enabled)
            if rate is not None:
                self._forward_rate = rate
            if sink is not None:
                self._sink = sink

    def record(self, event_type: str, payload: EventPayload = None) -> int:
        """
        追加一条事件, 需要时在锁外转发。

        Args:
            event_type (str):
                事件类型, 见 ``EVENT_TYPES``。
            payload (EventPayload):
                调用方新建的载荷字典, 或惰性载荷 ``(builder, *args)``; 记录后不应再修改。

        Returns:
            int:
                事件游标。
        """

        timestamp = self._clock()
        forward = False
        with self._lock:
            cursor = self._next_cursor
            self._next_cursor = cursor + 1
            self._events.append((cursor, timestamp, event_type, payload))
            if self._forward_enabled and is_forwarded_event(event_type):
                forward = self._admit_locked()
        if forward:
            self._forward(cursor, timestamp, event_type, payload)
        return cursor

    def read(self, since_cursor: int = 0, limit: int = DEFAULT_READ_LIMIT, *, max_bytes: int = DEFAULT_READ_MAX_BYTES) -> dict[str, Any]:
        """
        读取有界的单调事件切片。

        Args:
            since_cursor (int):
                起始游标, 小于 0 视为 0。
            limit (int):
                最多返回的事件数, 限制在 1 到 ``MAX_READ_LIMIT`` 之间。
            max_bytes (int):
                返回事件的 JSON 字节预算, 至少返回一条事件。

        Returns:
            dict[str, Any]:
                ``events`` (每项含 ``cursor``、``timestamp``、``type``、``payload``)、``start_cursor``、
                ``next_cursor``、``truncated``、``has_more``。
        """

        bounded_limit = max(1, min(int(limit), MAX_READ_LIMIT))
        requested = max(0, int(since_cursor))
        budget = max(1, int(max_bytes))
        with self._lock:
            first_cursor = self._events[0][0] if self._events else self._next_cursor
            latest_cursor = self._next_cursor
            start_cursor = max(requested, first_cursor)
            offset = min(start_cursor - first_cursor, len(self._events))
            selected = list(islice(self._events, offset, offset + bounded_limit))
        events: list[dict[str, Any]] = []
        used = 0
        for raw in selected:
            item = _materialize(raw)
            size = _encoded_size(item)
            if events and used + size > budget:
                break
            events.append(item)
            used += size
        next_cursor = events[-1]["cursor"] + 1 if events else start_cursor
        return {
            "events": events,
            "start_cursor": start_cursor,
            "next_cursor": next_cursor,
            "truncated": requested < first_cursor,
            "has_more": next_cursor < latest_cursor,
        }

    def stats(self) -> dict[str, Any]:
        """
        返回缓冲区与转发统计。

        Returns:
            dict[str, Any]:
                ``capacity``、``count``、``first_cursor``、``next_cursor``、``dropped`` (已被淘汰的事件数) 与
                ``forward`` (``enabled``、``max_per_second``、``forwarded``、``rate_limited``、``failed``)。
        """

        with self._lock:
            count = len(self._events)
            first_cursor = self._events[0][0] if self._events else self._next_cursor
            return {
                "capacity": self.capacity,
                "count": count,
                "first_cursor": first_cursor,
                "next_cursor": self._next_cursor,
                "dropped": first_cursor,
                "forward": {
                    "enabled": self._forward_enabled,
                    "max_per_second": self._forward_rate,
                    "forwarded": self._forwarded,
                    "rate_limited": self._rate_limited,
                    "failed": self._forward_failed,
                },
            }

    def clear(self) -> None:
        """清空已保留事件, 游标继续递增 (之后用旧游标读取会得到 ``truncated``)。"""

        with self._lock:
            self._events.clear()

    def _admit_locked(self) -> bool:
        now = self._monotonic()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._window_count = 0
        if self._window_count >= self._forward_rate:
            self._rate_limited += 1
            return False
        self._window_count += 1
        return True

    def _forward(self, cursor: int, timestamp: float, event_type: str, payload: EventPayload) -> None:
        if getattr(self._guard, "active", False):
            return
        self._guard.active = True
        ok = False
        try:
            sink_getter = self._sink
            sink = sink_getter() if sink_getter is not None else None
            if sink is not None:
                body = {"cursor": cursor, "timestamp": timestamp, "type": event_type, "payload": _bounded_payload(payload, MAX_FORWARD_PAYLOAD_BYTES)}
                from ..runtime.interfaces import emit_runtime_event

                ok = emit_runtime_event(sink, FORWARD_EVENT_TYPE, body) is not False
        except Exception:
            ok = False
        finally:
            self._guard.active = False
        with self._lock:
            if ok:
                self._forwarded += 1
            else:
                self._forward_failed += 1


def resolve_payload(payload: EventPayload) -> dict[str, Any] | None:
    """
    把惰性载荷展开为字典。

    Args:
        payload (EventPayload):
            载荷字典、None 或惰性载荷 ``(builder, *args)``。

    Returns:
        dict[str, Any] | None:
            载荷字典; 构造函数抛出异常时返回含 ``payload_error`` 的字典。
    """

    if isinstance(payload, tuple):
        try:
            return payload[0](*payload[1:])
        except Exception as exc:
            return {"payload_error": f"{type(exc).__name__}: {exc}"}
    return payload


def _materialize(raw: tuple[int, float, str, EventPayload]) -> dict[str, Any]:
    cursor, timestamp, event_type, payload = raw
    return {"cursor": cursor, "timestamp": timestamp, "type": event_type, "payload": _bounded_payload(payload, MAX_EVENT_BYTES)}


def _bounded_payload(payload: EventPayload, limit: int) -> dict[str, Any]:
    resolved = resolve_payload(payload)
    safe = json_safe(redact_mapping(resolved)) if resolved is not None else {}
    if not isinstance(safe, dict):
        safe = {"value": safe}
    if _encoded_size(safe) <= limit:
        return safe
    # 字段级截断后仍然过大: 保留标量字段, 丢弃嵌套结构。
    compact = {key: value for key, value in safe.items() if not isinstance(value, (dict, list))}
    compact["truncated"] = True
    if _encoded_size(compact) <= limit:
        return compact
    return {"truncated": True, "keys": sorted(safe)[:MAX_EVENT_LIST_ITEMS]}


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return value


def get_event_log(*, state: HotpatcherState | None = None) -> PatchEventLog:
    """
    获取状态对象的事件缓冲区, 首次访问时创建。

    事件转发目标为 ``state.bootstrap_runtime_client`` (转发时读取)。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchEventLog:
            事件缓冲区。
    """

    active_state = state or get_default_state()
    log = active_state.event_log
    if log is not None:
        return log
    with active_state.control_lock:
        if active_state.event_log is None:
            active_state.event_log = PatchEventLog(sink=lambda: active_state.bootstrap_runtime_client)
        return active_state.event_log


def record_event(event_type: str, payload: EventPayload = None, *, state: HotpatcherState | None = None, tag: str | None = None) -> int:
    """
    记录事件, 并在对应跟踪标签启用时输出跟踪消息。

    Args:
        event_type (str):
            事件类型。
        payload (EventPayload):
            调用方新建的载荷字典或惰性载荷 ``(builder, *args)``, 记录后不应再修改。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        tag (str | None):
            跟踪标签。为 None 时按事件类型前缀推导 (``patch``、``import``、``set``、``feature``、``conn``、``control``)。

    Returns:
        int:
            事件游标。
    """

    active_state = state or get_default_state()
    log = active_state.event_log
    if log is None:
        log = get_event_log(state=active_state)
    cursor = log.record(event_type, payload)
    tracer = active_state.tracer
    if tracer is not None and tracer.active:
        trace_tag = tag or _TRACE_TAG_BY_PREFIX.get(event_type.split(".", 1)[0], "control")
        if tracer.enabled_for(trace_tag):
            tracer.trace(trace_tag, event_type, resolve_payload(payload))
    return cursor


def read_events(
    since_cursor: int = 0,
    limit: int = DEFAULT_READ_LIMIT,
    *,
    max_bytes: int = DEFAULT_READ_MAX_BYTES,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    读取事件切片, 语义同 ``PatchEventLog.read``。

    Args:
        since_cursor (int):
            起始游标。
        limit (int):
            最多返回的事件数。
        max_bytes (int):
            返回事件的 JSON 字节预算。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``events``、``start_cursor``、``next_cursor``、``truncated``、``has_more``。
    """

    return get_event_log(state=state).read(since_cursor, limit, max_bytes=max_bytes)


def set_event_forwarding(enabled: bool, *, max_per_second: int | None = None, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    启用或关闭事件转发, 状态变化时记录 ``debug.forwarding.changed`` 事件。

    Args:
        enabled (bool):
            是否启用。
        max_per_second (int | None):
            新的每秒上限。为 None 时保持不变。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            转发统计, 同 ``PatchEventLog.stats()["forward"]``。
    """

    active_state = state or get_default_state()
    log = get_event_log(state=active_state)
    previous = log.forward_enabled
    log.configure_forwarding(enabled, max_per_second=max_per_second)
    if previous != log.forward_enabled:
        record_event("debug.forwarding.changed", {"enabled": log.forward_enabled, "max_per_second": log.forward_rate}, state=active_state, tag="control")
    return log.stats()["forward"]
