"""补丁句柄、状态与结果记录。

每个补丁注册或实时修改都对应一个 ``PatchHandle``。句柄 ID 由
``HotpatcherState.patch_id_counter`` 在 ``control_lock`` 下分配, 句柄注册表位于
``HotpatcherState.patch_handles``。锁只保护计数器和注册表字典, 不会在调用用户代码时持有。
"""

from __future__ import annotations

import enum
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..state import get_default_state

if TYPE_CHECKING:
    from ..state import HotpatcherState

__all__ = [
    "MAX_ERROR_MESSAGE_CHARS",
    "MAX_HANDLE_OUTCOMES",
    "MAX_TRACEBACK_CHARS",
    "PatchHandle",
    "PatchOutcome",
    "PatchOutcomeKind",
    "PatchStatus",
    "allocate_patch_id",
    "create_patch_handle",
    "get_patch_handle",
    "list_patch_handles",
    "register_patch_handle",
    "unregister_patch_handle",
]

MAX_HANDLE_OUTCOMES = 20
MAX_TRACEBACK_CHARS = 8000
MAX_ERROR_MESSAGE_CHARS = 1000


class PatchStatus(str, enum.Enum):
    """
    补丁句柄状态。

    Attributes:
        REGISTERED: 已登记但尚未生效, 例如目标模块尚未导入的 import 阶段补丁。
        APPLIED: 已生效。
        REVERTED: 已完全撤销。
        DEREGISTERED: 生效前已从补丁计划中移除。
        FAILED: 应用或撤销失败。
        REQUIRES_RESTART: 已从计划中移除, 但已执行的效果只能通过重启进程消除。
    """

    REGISTERED = "registered"
    APPLIED = "applied"
    REVERTED = "reverted"
    DEREGISTERED = "deregistered"
    FAILED = "failed"
    REQUIRES_RESTART = "requires_restart"


class PatchOutcomeKind(str, enum.Enum):
    """
    单次补丁执行结果类型。

    Attributes:
        APPLIED: 补丁产生了修改。
        NOOP: 补丁执行成功但没有产生修改。
        FAILED: 补丁执行抛出异常。
        SKIPPED: 补丁因条件不满足等原因未执行。
    """

    APPLIED = "applied"
    NOOP = "noop"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PatchOutcome:
    """
    单次补丁执行结果。

    Attributes:
        kind (PatchOutcomeKind):
            结果类型。
        reason (str | None):
            附加原因, 例如 ``function_missing``、``unsupported_loader``。
        error_type (str | None):
            失败时的异常类型名。
        error_message (str | None):
            失败时的异常消息, 最长 ``MAX_ERROR_MESSAGE_CHARS`` 字符。
        traceback (str | None):
            失败时的 traceback 末尾, 最长 ``MAX_TRACEBACK_CHARS`` 字符。
        timestamp (float):
            记录时间, ``time.time()`` 秒。
        detail (dict[str, Any] | None):
            可序列化的结构化附加信息, 例如 ``rebind_references`` 重新绑定的位置列表。
    """

    kind: PatchOutcomeKind
    reason: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    timestamp: float = field(default_factory=time.time)
    detail: dict[str, Any] | None = None

    @classmethod
    def applied(cls, reason: str | None = None, *, detail: dict[str, Any] | None = None) -> PatchOutcome:
        """
        创建 ``applied`` 结果。

        Args:
            reason (str | None):
                附加原因。
            detail (dict[str, Any] | None):
                结构化附加信息。

        Returns:
            PatchOutcome:
                结果对象。
        """

        return cls(kind=PatchOutcomeKind.APPLIED, reason=reason, detail=detail)

    @classmethod
    def noop(cls, reason: str | None = None) -> PatchOutcome:
        """
        创建 ``noop`` 结果。

        Args:
            reason (str | None):
                附加原因。

        Returns:
            PatchOutcome:
                结果对象。
        """

        return cls(kind=PatchOutcomeKind.NOOP, reason=reason)

    @classmethod
    def skipped(cls, reason: str) -> PatchOutcome:
        """
        创建 ``skipped`` 结果。

        Args:
            reason (str):
                跳过原因, 例如 ``condition_false``。

        Returns:
            PatchOutcome:
                结果对象。
        """

        return cls(kind=PatchOutcomeKind.SKIPPED, reason=reason)

    @classmethod
    def failed(cls, error: BaseException, reason: str | None = None) -> PatchOutcome:
        """
        根据异常创建 ``failed`` 结果, 消息和 traceback 都有长度上限。

        Args:
            error (BaseException):
                失败异常。
            reason (str | None):
                附加原因。

        Returns:
            PatchOutcome:
                结果对象。
        """

        return cls(
            kind=PatchOutcomeKind.FAILED,
            reason=reason,
            error_type=type(error).__name__,
            error_message=_bounded_head(str(error), MAX_ERROR_MESSAGE_CHARS),
            traceback=_bounded_tail("".join(traceback.format_exception(type(error), error, error.__traceback__)), MAX_TRACEBACK_CHARS),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的结果描述。

        Returns:
            dict[str, Any]:
                结果字段字典, ``kind`` 为字符串。
        """

        return {
            "kind": self.kind.value,
            "reason": self.reason,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "timestamp": self.timestamp,
            "detail": dict(self.detail) if self.detail is not None else None,
        }


@dataclass
class PatchHandle:
    """
    单个补丁的句柄。

    Attributes:
        id (str):
            全局唯一 ID, 形如 ``patch_1``。
        kind (str):
            补丁类型, 例如 ``attr``、``item``、``env``、``syspath``、``disposer``, 以及后续阶段的 import 补丁类型。
        target (str):
            面向调试的目标描述。
        owner (str | None):
            所属 ``PatchSet`` 的 ID。
        stage (str | None):
            import 补丁阶段, 实时操作为 None。
        status (PatchStatus):
            当前状态。
        outcomes (deque[PatchOutcome]):
            最近的执行结果, 最多保留 ``MAX_HANDLE_OUTCOMES`` 条。
        outcome_counts (dict[str, int]):
            各类结果的累计次数, 不受 ``outcomes`` 上限影响。
        created (float):
            创建时间, ``time.time()`` 秒。
    """

    id: str
    kind: str
    target: str
    owner: str | None = None
    stage: str | None = None
    status: PatchStatus = PatchStatus.REGISTERED
    outcomes: deque[PatchOutcome] = field(default_factory=lambda: deque(maxlen=MAX_HANDLE_OUTCOMES))
    outcome_counts: dict[str, int] = field(default_factory=dict)
    created: float = field(default_factory=time.time)

    @property
    def last_outcome(self) -> PatchOutcome | None:
        """
        最近一次执行结果。

        Returns:
            PatchOutcome | None:
                没有结果时为 None。
        """

        return self.outcomes[-1] if self.outcomes else None

    def record_outcome(self, outcome: PatchOutcome) -> None:
        """
        追加一次执行结果。

        Args:
            outcome (PatchOutcome):
                执行结果。
        """

        self.outcomes.append(outcome)
        key = outcome.kind.value
        self.outcome_counts[key] = self.outcome_counts.get(key, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的句柄描述。

        Returns:
            dict[str, Any]:
                句柄字段字典, ``status`` 为字符串, ``outcomes`` 为结果字典列表。
        """

        return {
            "id": self.id,
            "kind": self.kind,
            "target": self.target,
            "owner": self.owner,
            "stage": self.stage,
            "status": self.status.value,
            "outcomes": [outcome.to_dict() for outcome in list(self.outcomes)],
            "outcome_counts": dict(self.outcome_counts),
            "created": self.created,
        }


def allocate_patch_id(prefix: str = "patch", *, state: HotpatcherState | None = None) -> str:
    """
    分配进程内唯一的补丁 ID。

    计数器位于 ``HotpatcherState.patch_id_counter``, 在 ``control_lock`` 下递增。
    ID 形如 ``patch_1`` / ``set_2``, 只要前缀是合法标识符, ID 就是合法 Python 标识符。

    Args:
        prefix (str):
            ID 前缀。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        str:
            新 ID。

    Raises:
        ValueError:
            前缀不是合法标识符时抛出。
    """

    if not prefix.isidentifier():
        raise ValueError(f"patch id prefix must be an identifier, got {prefix!r}")
    active_state = state or get_default_state()
    with active_state.control_lock:
        active_state.patch_id_counter += 1
        number = active_state.patch_id_counter
    return f"{prefix}_{number}"


def create_patch_handle(
    kind: str,
    target: str,
    *,
    owner: str | None = None,
    stage: str | None = None,
    status: PatchStatus = PatchStatus.REGISTERED,
    register: bool = True,
    state: HotpatcherState | None = None,
) -> PatchHandle:
    """
    分配 ID 并创建补丁句柄。

    Args:
        kind (str):
            补丁类型。
        target (str):
            目标描述。
        owner (str | None):
            所属 ``PatchSet`` 的 ID。
        stage (str | None):
            import 补丁阶段。
        status (PatchStatus):
            初始状态。
        register (bool):
            是否写入 ``state.patch_handles``。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchHandle:
            新句柄。
    """

    active_state = state or get_default_state()
    handle = PatchHandle(id=allocate_patch_id("patch", state=active_state), kind=kind, target=target, owner=owner, stage=stage, status=status)
    if register:
        register_patch_handle(handle, state=active_state)
    return handle


def register_patch_handle(handle: PatchHandle, *, state: HotpatcherState | None = None) -> None:
    """
    把句柄写入状态注册表。

    Args:
        handle (PatchHandle):
            要注册的句柄。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Raises:
        ValueError:
            已存在同 ID 的其他句柄时抛出。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        existing = active_state.patch_handles.get(handle.id)
        if existing is not None and existing is not handle:
            raise ValueError(f"patch handle {handle.id!r} is already registered")
        active_state.patch_handles[handle.id] = handle


def unregister_patch_handle(handle_id: str, *, state: HotpatcherState | None = None) -> PatchHandle | None:
    """
    从状态注册表移除句柄。

    Args:
        handle_id (str):
            句柄 ID。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchHandle | None:
            被移除的句柄, 不存在时为 None。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        return active_state.patch_handles.pop(handle_id, None)


def get_patch_handle(handle_id: str, *, state: HotpatcherState | None = None) -> PatchHandle | None:
    """
    按 ID 查询已注册句柄。

    Args:
        handle_id (str):
            句柄 ID。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchHandle | None:
            句柄, 不存在时为 None。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        return active_state.patch_handles.get(handle_id)


def list_patch_handles(*, owner: str | None = None, state: HotpatcherState | None = None) -> list[PatchHandle]:
    """
    列出已注册句柄的快照, 按注册顺序排列。

    Args:
        owner (str | None):
            只列出属于该 ``PatchSet`` ID 的句柄。为 None 时列出全部。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        list[PatchHandle]:
            句柄列表。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        handles = list(active_state.patch_handles.values())
    return [handle for handle in handles if owner is None or handle.owner == owner]


def _bounded_head(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _bounded_tail(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    marker = "...(truncated)...\n"
    return marker + text[-(limit - len(marker)) :]
