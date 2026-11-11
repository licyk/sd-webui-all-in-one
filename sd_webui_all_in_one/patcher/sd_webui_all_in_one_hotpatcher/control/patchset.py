"""补丁集: 加载与卸载的基本单元。

``PatchSet`` 拥有一个 ``PatchJournal`` 和一组 ``PatchHandle``。所有修改与 disposer 都写入
同一个 LIFO 日志, 关闭补丁集时按生效的相反顺序撤销, 单个条目失败不会中断其他条目。

``PatchContext`` 是补丁作者拿到的对象, 提供可撤销的基础操作。补丁集处于激活状态
(``with patch_set:``、``patch_set.run(setup)`` 或 ``context.activate()``) 时,
``current_patch_context()`` 返回它的上下文, 后续阶段据此把 ``Monkey.patch_*`` 注册归属到该补丁集。

事务模式 (默认) 下, ``with`` 块或 ``run`` 回调抛出异常会撤销本补丁集的全部修改,
状态固定为 ``failed`` 并继续抛出原异常; 正常退出时修改保持生效, 直到 ``close()`` / ``unload()``。
"""

from __future__ import annotations

import contextlib
import contextvars
import enum
import os
import threading
import time
from collections.abc import Callable, Generator, MutableMapping
from dataclasses import dataclass, field
from types import ModuleType, TracebackType
from typing import TYPE_CHECKING, Any

from ..state import HotpatcherState, get_default_state
from .handles import (
    PatchHandle,
    PatchOutcome,
    PatchStatus,
    allocate_patch_id,
    create_patch_handle,
    register_patch_handle,
    unregister_patch_handle,
)
from . import operations
from .journal import NOTSET, JournalUndoReport, PatchJournal
from .targets import describe_target

if TYPE_CHECKING:
    from ..hook import Monkey

__all__ = [
    "PatchContext",
    "PatchSet",
    "PatchSetClosedError",
    "PatchSetReport",
    "PatchSetStatus",
    "collect_operations",
    "current_patch_context",
    "get_patch_set",
    "list_patch_sets",
    "register_patch_set",
    "remove_patch_set",
]

_CURRENT_PATCH_CONTEXT: contextvars.ContextVar[PatchContext | None] = contextvars.ContextVar(
    "sd_webui_all_in_one_hotpatcher_current_patch_context",
    default=None,
)

_OPERATION_COLLECTOR: contextvars.ContextVar[list[PatchHandle] | None] = contextvars.ContextVar(
    "sd_webui_all_in_one_hotpatcher_operation_collector",
    default=None,
)

# 同一句柄有多个撤销结果时取优先级最高的状态。
_UNDO_STATUS_PRIORITY = {
    PatchStatus.DEREGISTERED: 1,
    PatchStatus.REVERTED: 2,
    PatchStatus.REQUIRES_RESTART: 3,
    PatchStatus.FAILED: 4,
}


class PatchSetStatus(str, enum.Enum):
    """
    补丁集状态。

    Attributes:
        OPEN: 可继续添加补丁。
        CLOSED: 已关闭, 修改已撤销。
        FAILED: 事务失败或被标记为失败, 修改已撤销; 该状态不会再变化。
    """

    OPEN = "open"
    CLOSED = "closed"
    FAILED = "failed"


class PatchSetClosedError(RuntimeError):
    """向已关闭的补丁集添加补丁时抛出。"""


@dataclass
class PatchSetReport:
    """
    补丁集关闭报告。

    Attributes:
        set_id (str):
            补丁集 ID。
        name (str):
            补丁集名称。
        status (PatchSetStatus):
            关闭后的补丁集状态。
        handles (list[dict[str, Any]]):
            每个句柄的 ``id``、``kind``、``target``、``status``。
        errors (list[dict[str, Any]]):
            撤销失败的条目, 包含 ``handle_id``、``label``、``error_type``、``error_message``。
        exceptions (list[Exception]):
            撤销失败的原始异常, 与 ``errors`` 顺序一致。
    """

    set_id: str
    name: str
    status: PatchSetStatus
    handles: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    exceptions: list[Exception] = field(default_factory=list, repr=False, compare=False)

    @property
    def ok(self) -> bool:
        """
        撤销是否全部成功。

        Returns:
            bool:
                没有撤销错误时返回 True。
        """

        return not self.errors

    def raise_first_error(self) -> None:
        """
        存在撤销失败时重新抛出第一个异常。

        Raises:
            Exception:
                第一个撤销失败的原始异常。
        """

        if self.exceptions:
            raise self.exceptions[0]

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的报告。

        Returns:
            dict[str, Any]:
                报告字段字典, 不含原始异常对象。
        """

        return {
            "set_id": self.set_id,
            "name": self.name,
            "status": self.status.value,
            "ok": self.ok,
            "handles": [dict(item) for item in self.handles],
            "errors": [dict(item) for item in self.errors],
        }


def current_patch_context() -> PatchContext | None:
    """
    返回当前激活的补丁上下文。

    Returns:
        PatchContext | None:
            当前线程/上下文中最内层激活的补丁上下文, 没有时为 None。
    """

    return _CURRENT_PATCH_CONTEXT.get()


@contextlib.contextmanager
def collect_operations() -> Generator[list[PatchHandle], None, None]:
    """
    收集 ``with`` 块内当前线程/上下文创建的实时操作句柄。

    ``record_operation`` 和 ``add_disposer`` 创建的句柄 (不论属于哪个补丁集) 会追加到产出的列表中;
    import 阶段补丁通过 ``adopt_handle`` 归属的句柄不会被收集。嵌套使用时只有最内层收集器生效。
    ``hook.Monkey`` 用它判断模块级补丁函数是否只通过可撤销操作修改了模块。

    Yields:
        list[PatchHandle]:
            按创建顺序排列的句柄列表, 块结束后仍可读取。
    """

    collected: list[PatchHandle] = []
    token = _OPERATION_COLLECTOR.set(collected)
    try:
        yield collected
    finally:
        _OPERATION_COLLECTOR.reset(token)


class PatchSet:
    """
    可整体卸载的一组补丁。

    Attributes:
        id (str):
            进程内唯一 ID, 形如 ``set_1``, 是合法 Python 标识符。
        name (str):
            补丁集名称, 未指定时等于 ``id``。
        state (HotpatcherState):
            所属状态对象。
        journal (PatchJournal):
            本补丁集的修改日志。
        transactional (bool):
            是否在激活块抛出异常时撤销全部修改。
        created (float):
            创建时间, ``time.time()`` 秒。
        error (PatchOutcome | None):
            失败原因。
        context (PatchContext):
            提供给补丁作者的上下文。
    """

    def __init__(
        self,
        name: str | None = None,
        *,
        transactional: bool = True,
        config: dict[str, Any] | None = None,
        state: HotpatcherState | None = None,
    ) -> None:
        """
        创建补丁集, 不会自动注册到状态。

        Args:
            name (str | None):
                补丁集名称。为 None 时使用自动分配的 ID。
            transactional (bool):
                是否在激活块抛出异常时撤销全部修改。
            config (dict[str, Any] | None):
                传给补丁作者的配置, 可通过 ``context.config`` 读取。
            state (HotpatcherState | None):
                可选状态对象。为 None 时使用默认状态。

        Raises:
            ValueError:
                ``name`` 为空字符串时抛出。
        """

        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError(f"patch set name must be a non-empty string, got {name!r}")
        self.state = state or get_default_state()
        self.id = allocate_patch_id("set", state=self.state)
        self.name = name if name is not None else self.id
        self.journal = PatchJournal()
        self.transactional = transactional
        self.created = time.time()
        self.error: PatchOutcome | None = None
        self._status = PatchSetStatus.OPEN
        self._closed = False
        self._report: PatchSetReport | None = None
        self._handles: dict[str, PatchHandle] = {}
        self._lock = threading.RLock()
        self._activation = threading.local()
        self.context = PatchContext(self, config=config)

    def __repr__(self) -> str:
        """
        返回调试表示。

        Returns:
            str:
                包含 ID、名称和状态的字符串。
        """

        return f"<PatchSet id={self.id!r} name={self.name!r} status={self._status.value!r}>"

    @property
    def status(self) -> PatchSetStatus:
        """
        当前状态。

        Returns:
            PatchSetStatus:
                补丁集状态。
        """

        return self._status

    @property
    def closed(self) -> bool:
        """
        是否已开始或完成关闭。

        Returns:
            bool:
                调用过 ``close()`` 后返回 True。
        """

        return self._closed

    @property
    def handles(self) -> list[PatchHandle]:
        """
        本补丁集句柄快照, 按创建顺序排列。

        Returns:
            list[PatchHandle]:
                句柄列表。
        """

        with self._lock:
            return list(self._handles.values())

    def get_handle(self, handle_id: str) -> PatchHandle | None:
        """
        按 ID 查询本补丁集的句柄。

        Args:
            handle_id (str):
                句柄 ID。

        Returns:
            PatchHandle | None:
                句柄, 不属于本补丁集时为 None。
        """

        with self._lock:
            return self._handles.get(handle_id)

    def record_operation(
        self,
        kind: str,
        target: str,
        action: Callable[[str], Any],
        *,
        stage: str | None = None,
        failure_reason: Callable[[BaseException], str | None] | None = None,
    ) -> PatchHandle:
        """
        创建句柄并执行一次可撤销操作。

        ``action`` 接收句柄 ID, 应通过 ``self.journal`` 写入带该 ID 的条目。返回 None 时
        记录 ``noop`` 结果, 返回 ``PatchOutcome`` 时原样记录该结果, 否则记录 ``applied``。
        ``action`` 在锁外执行。

        Args:
            kind (str):
                句柄类型。
            target (str):
                目标描述。
            action (Callable[[str], Any]):
                执行修改并写日志的函数。
            stage (str | None):
                import 补丁阶段。
            failure_reason (Callable[[BaseException], str | None] | None):
                ``action`` 抛出异常时计算失败结果 ``reason`` 的函数。

        Returns:
            PatchHandle:
                状态为 ``applied`` 的句柄。

        Raises:
            PatchSetClosedError:
                补丁集已关闭时抛出; 若关闭发生在操作执行期间, 本次修改会先被撤销。
            Exception:
                ``action`` 抛出的原异常, 此时句柄状态为 ``failed``。
        """

        handle = self._new_handle(kind, target, stage=stage)
        try:
            result = action(handle.id)
        except BaseException as exc:
            handle.status = PatchStatus.FAILED
            handle.record_outcome(PatchOutcome.failed(exc, reason=failure_reason(exc) if failure_reason is not None else None))
            raise
        handle.status = PatchStatus.APPLIED
        if isinstance(result, PatchOutcome):
            handle.record_outcome(result)
        else:
            handle.record_outcome(PatchOutcome.noop() if result is None else PatchOutcome.applied())
        with self._lock:
            closed_meanwhile = self._closed
        if closed_meanwhile:
            report = self.journal.undo(handle_id=handle.id)
            handle.status = PatchStatus.REVERTED if report.ok else PatchStatus.FAILED
            raise PatchSetClosedError(f"patch set {self.name!r} was closed while {kind} {target!r} was being applied; the change was reverted")
        return handle

    def adopt_handle(self, handle: PatchHandle, undo: Callable[[], Any] | None = None) -> PatchHandle:
        """
        把外部创建的句柄归属到本补丁集, 并可登记其逆操作。

        供 import 阶段补丁等由其他模块创建句柄的场景使用。``undo`` 可返回
        ``PatchStatus`` (例如 ``deregistered`` / ``requires_restart``) 作为关闭后的句柄状态。

        Args:
            handle (PatchHandle):
                外部句柄。
            undo (Callable[[], Any] | None):
                关闭补丁集时调用的逆操作。

        Returns:
            PatchHandle:
                同一个句柄对象, ``owner`` 已设置为本补丁集 ID。

        Raises:
            PatchSetClosedError:
                补丁集已关闭时抛出。
        """

        with self._lock:
            self._ensure_open(f"adopt handle {handle.id!r}")
            handle.owner = self.id
            self._handles[handle.id] = handle
            register_patch_handle(handle, state=self.state)
            if undo is not None:
                self.journal.record_callback(undo, handle.target, kind=handle.kind, handle_id=handle.id)
        return handle

    def add_disposer(self, disposer: Callable[[], Any], label: str | None = None) -> PatchHandle:
        """
        登记关闭时调用的清理函数。

        清理函数与其他修改位于同一个 LIFO 日志中。补丁集已关闭时立即执行清理函数。

        Args:
            disposer (Callable[[], Any]):
                清理函数。可返回 ``PatchStatus`` 作为关闭后的句柄状态。
            label (str | None):
                面向调试的描述。为 None 时使用函数名。

        Returns:
            PatchHandle:
                清理函数对应的句柄。

        Raises:
            TypeError:
                ``disposer`` 不可调用时抛出。
            Exception:
                补丁集已关闭且清理函数立即执行失败时抛出原异常。
        """

        if not callable(disposer):
            raise TypeError(f"disposer must be callable, got {type(disposer).__name__}")
        target = label or describe_target(disposer)
        with self._lock:
            closed = self._closed
            # 锁顺序固定为 PatchSet._lock -> control_lock; 两者内都不执行用户代码。
            handle = create_patch_handle("disposer", target, owner=self.id, status=PatchStatus.APPLIED, register=not closed, state=self.state)
            self._handles[handle.id] = handle
            if not closed:
                # 在锁内写日志: close() 只能在此之前或之后翻转关闭标记, 清理函数不会丢失也不会执行两次。
                self.journal.record_callback(disposer, target, kind="disposer", handle_id=handle.id)
                handle.record_outcome(PatchOutcome.applied())
        _collect_operation(handle)
        if not closed:
            return handle
        try:
            result = disposer()
        except BaseException as exc:
            handle.status = PatchStatus.FAILED
            handle.record_outcome(PatchOutcome.failed(exc, reason="disposer_failed"))
            raise
        handle.status = _coerce_undo_status(result)
        return handle

    def run(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        在激活本补丁集的情况下调用 ``callback(context, *args, **kwargs)``。

        事务模式下回调抛出异常会撤销本补丁集全部修改并标记为 ``failed``。

        Args:
            callback (Callable[..., Any]):
                接收 ``PatchContext`` 的函数, 例如补丁模块的 ``setup``。
            *args (Any):
                额外位置参数。
            **kwargs (Any):
                额外关键字参数。

        Returns:
            Any:
                回调返回值。
        """

        with self as context:
            return callback(context, *args, **kwargs)

    def fail(self, error: BaseException) -> PatchSetReport:
        """
        把补丁集标记为失败并撤销全部修改。``failed`` 状态不会再变化。

        Args:
            error (BaseException):
                失败原因。

        Returns:
            PatchSetReport:
                关闭报告。
        """

        with self._lock:
            self._status = PatchSetStatus.FAILED
            self.error = PatchOutcome.failed(error, reason="patch_set_failed")
            report = self._report
        if report is not None:
            report.status = PatchSetStatus.FAILED
            return report
        return self.close()

    def close(self) -> PatchSetReport:
        """
        按 LIFO 顺序撤销全部修改并返回逐句柄报告。

        幂等: 再次调用返回同一份报告。关闭进行中被其他线程调用时返回当前快照。
        关闭后本补丁集的句柄会从 ``state.patch_handles`` 移除, 仍可通过 ``handles`` 和报告查看。
        撤销被 ``KeyboardInterrupt`` 等非 ``Exception`` 异常打断时, 补丁集恢复为未关闭,
        再次调用会继续撤销剩余条目。

        Returns:
            PatchSetReport:
                关闭报告。

        Raises:
            BaseException:
                撤销函数抛出非 ``Exception`` 异常时原样抛出。
        """

        with self._lock:
            if self._closed:
                return self._report or self._build_report(JournalUndoReport())
            self._closed = True
        try:
            undo_report = self.journal.undo()
        except BaseException:
            # 日志已把未执行的条目放回; 重新打开关闭标记, 让后续 close() 继续撤销剩余条目。
            with self._lock:
                self._closed = False
            raise
        statuses: dict[str, PatchStatus] = {}
        with self._lock:
            for result in undo_report.results:
                handle_id = result.entry.handle_id
                if handle_id is None:
                    continue
                handle = self._handles.get(handle_id)
                if result.error is not None:
                    status = PatchStatus.FAILED
                    if handle is not None:
                        handle.record_outcome(PatchOutcome.failed(result.error, reason="undo_failed"))
                else:
                    status = _coerce_undo_status(result.result)
                previous = statuses.get(handle_id)
                if previous is None or _UNDO_STATUS_PRIORITY[status] > _UNDO_STATUS_PRIORITY[previous]:
                    statuses[handle_id] = status
            for handle in self._handles.values():
                if handle.status is PatchStatus.FAILED:
                    continue
                if handle.id in statuses:
                    handle.status = statuses[handle.id]
                elif handle.status is PatchStatus.APPLIED:
                    handle.status = PatchStatus.REVERTED
                elif handle.status is PatchStatus.REGISTERED:
                    handle.status = PatchStatus.DEREGISTERED
            if self._status is PatchSetStatus.OPEN:
                self._status = PatchSetStatus.CLOSED
            handle_ids = list(self._handles)
            report = self._build_report(undo_report)
            self._report = report
        for handle_id in handle_ids:
            unregister_patch_handle(handle_id, state=self.state)
        return report

    def unload(self) -> PatchSetReport:
        """
        卸载补丁集, 等同于 ``close()``。

        Returns:
            PatchSetReport:
                关闭报告。
        """

        return self.close()

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的补丁集描述。

        Returns:
            dict[str, Any]:
                包含 ID、名称、状态、句柄和日志条目的字典。
        """

        with self._lock:
            handles = list(self._handles.values())
            status = self._status
            error = self.error
        return {
            "id": self.id,
            "name": self.name,
            "status": status.value,
            "transactional": self.transactional,
            "created": self.created,
            "error": error.to_dict() if error is not None else None,
            "handles": [handle.to_dict() for handle in handles],
            "journal": self.journal.entries(),
        }

    def __enter__(self) -> PatchContext:
        """
        激活补丁集。

        Returns:
            PatchContext:
                本补丁集的上下文。
        """

        tokens = self._activation_tokens()
        tokens.append(_CURRENT_PATCH_CONTEXT.set(self.context))
        return self.context

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """
        取消激活; 事务模式下发生异常时撤销全部修改。异常不会被吞掉。

        Args:
            exc_type (type[BaseException] | None):
                异常类型。
            exc (BaseException | None):
                异常对象。
            tb (TracebackType | None):
                traceback。
        """

        tokens = self._activation_tokens()
        if tokens:
            _CURRENT_PATCH_CONTEXT.reset(tokens.pop())
        if exc is not None and self.transactional:
            self.fail(exc)

    def _activation_tokens(self) -> list[contextvars.Token[PatchContext | None]]:
        tokens = getattr(self._activation, "tokens", None)
        if tokens is None:
            tokens = []
            self._activation.tokens = tokens
        return tokens

    def _ensure_open(self, action: str) -> None:
        if self._closed:
            raise PatchSetClosedError(f"cannot {action}: patch set {self.name!r} is {self._status.value}")

    def _new_handle(self, kind: str, target: str, *, stage: str | None) -> PatchHandle:
        with self._lock:
            self._ensure_open(f"apply {kind} {target!r}")
            handle = create_patch_handle(kind, target, owner=self.id, stage=stage, state=self.state)
            self._handles[handle.id] = handle
        _collect_operation(handle)
        return handle

    def _build_report(self, undo_report: JournalUndoReport) -> PatchSetReport:
        with self._lock:
            handles = list(self._handles.values())
            status = self._status
        report = PatchSetReport(
            set_id=self.id,
            name=self.name,
            status=status,
            handles=[{"id": handle.id, "kind": handle.kind, "target": handle.target, "status": handle.status.value} for handle in handles],
        )
        for result in undo_report.results:
            if result.error is None:
                continue
            report.errors.append(
                {
                    "handle_id": result.entry.handle_id,
                    "label": result.entry.label,
                    "error_type": type(result.error).__name__,
                    "error_message": str(result.error),
                }
            )
            report.exceptions.append(result.error)
        return report


class PatchContext:
    """
    补丁作者使用的上下文。

    每个方法都会创建一个 ``PatchHandle`` 并把逆操作写入所属补丁集的日志。

    Attributes:
        patch_set (PatchSet):
            所属补丁集。
        config (dict[str, Any]):
            补丁配置。
    """

    def __init__(self, patch_set: PatchSet, *, config: dict[str, Any] | None = None) -> None:
        """
        创建上下文。通常由 ``PatchSet`` 创建。

        Args:
            patch_set (PatchSet):
                所属补丁集。
            config (dict[str, Any] | None):
                补丁配置。
        """

        self.patch_set = patch_set
        self.config: dict[str, Any] = dict(config or {})

    def __repr__(self) -> str:
        """
        返回调试表示。

        Returns:
            str:
                包含所属补丁集 ID 和名称的字符串。
        """

        return f"<PatchContext set={self.patch_set.id!r} name={self.patch_set.name!r}>"

    @property
    def id(self) -> str:
        """
        所属补丁集 ID。

        Returns:
            str:
                补丁集 ID。
        """

        return self.patch_set.id

    @property
    def name(self) -> str:
        """
        所属补丁集名称。

        Returns:
            str:
                补丁集名称。
        """

        return self.patch_set.name

    @property
    def state(self) -> HotpatcherState:
        """
        所属状态对象。

        Returns:
            HotpatcherState:
                状态对象。
        """

        return self.patch_set.state

    @property
    def journal(self) -> PatchJournal:
        """
        所属补丁集的修改日志。

        Returns:
            PatchJournal:
                修改日志。
        """

        return self.patch_set.journal

    @contextlib.contextmanager
    def activate(self) -> Generator[PatchContext, None, None]:
        """
        在 ``with`` 块内把本上下文设为 ``current_patch_context()``。

        只切换上下文变量, 不会在异常时撤销修改。

        Yields:
            PatchContext:
                本上下文。
        """

        token = _CURRENT_PATCH_CONTEXT.set(self)
        try:
            yield self
        finally:
            _CURRENT_PATCH_CONTEXT.reset(token)

    @contextlib.contextmanager
    def module(self, name: str, *, apply_if_loaded: bool = False) -> Generator[Monkey, None, None]:
        """
        在激活本上下文的情况下获取模块的 import 阶段补丁计划。

        ``with`` 块内的 ``patch_*`` 注册归属到本补丁集, 卸载补丁集时撤销框架写入或从计划中注销,
        规则见 ``Monkey.remove``。注册表使用本补丁集状态的 ``monkey_zoo``。

        Args:
            name (str):
                目标模块名。
            apply_if_loaded (bool):
                为 True 且目标模块已导入时, 退出时把新增条目的执行后阶段追溯应用到该模块。

        Yields:
            Monkey:
                目标模块的补丁计划。
        """

        from ..hook import _state_monkey_zoo

        zoo = _state_monkey_zoo(self.state)
        with self.activate(), zoo(name, apply_if_loaded=apply_if_loaded) as monkey:
            yield monkey

    def set_attr(
        self,
        target: Any,
        name: Any,
        value: Any = NOTSET,
        *,
        raising: bool = True,
        rebind_references: bool = False,
        rebind_limit: int = operations.MAX_REBIND_REFERENCES,
    ) -> PatchHandle:
        """
        设置属性。

        支持 ``set_attr(obj, "name", value)`` 和 ``set_attr("pkg.mod:Obj.name", value)`` 两种写法。

        Args:
            target (Any):
                模块、类、实例, 或目标路径字符串。
            name (Any):
                属性名; 使用目标路径写法时为新值。
            value (Any):
                新值; 使用目标路径写法时省略。
            raising (bool):
                属性不存在时是否抛出 ``AttributeError``。
            rebind_references (bool):
                旧值是可调用对象时, 是否把其他模块命名空间中对旧值的同一对象引用也改为新值,
                每个重新绑定位置单独写日志, 位置列表记录在结果的 ``detail`` 中。
            rebind_limit (int):
                最多重新绑定的引用数量, 超出时结果 ``detail["truncated"]`` 为 True。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.set_attr(self.patch_set, target, name, value, raising=raising, rebind_references=rebind_references, rebind_limit=rebind_limit)

    def del_attr(self, target: Any, name: Any = NOTSET, *, raising: bool = True) -> PatchHandle:
        """
        删除属性。

        支持 ``del_attr(obj, "name")`` 和 ``del_attr("pkg.mod:Obj.name")`` 两种写法。

        Args:
            target (Any):
                模块、类、实例, 或目标路径字符串。
            name (Any):
                属性名; 使用目标路径写法时省略。
            raising (bool):
                属性不存在时是否抛出 ``AttributeError``。为 False 且属性不存在时记录 ``noop``。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.del_attr(self.patch_set, target, name, raising=raising)

    def set_item(self, mapping: MutableMapping[Any, Any], key: Any, value: Any) -> PatchHandle:
        """
        设置映射条目。

        Args:
            mapping (MutableMapping[Any, Any]):
                目标映射。
            key (Any):
                键。
            value (Any):
                新值。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.set_item(self.patch_set, mapping, key, value)

    def del_item(self, mapping: MutableMapping[Any, Any], key: Any, *, raising: bool = True) -> PatchHandle:
        """
        删除映射条目。

        Args:
            mapping (MutableMapping[Any, Any]):
                目标映射。
            key (Any):
                键。
            raising (bool):
                键不存在时是否抛出 ``KeyError``。为 False 且键不存在时记录 ``noop``。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.del_item(self.patch_set, mapping, key, raising=raising)

    def set_env(self, name: str, value: str, *, prepend: str | None = None) -> PatchHandle:
        """
        设置环境变量, 语义与 pytest ``setenv`` 一致。

        Args:
            name (str):
                环境变量名。
            value (str):
                新值。
            prepend (str | None):
                非空且变量已存在时, 新值为 ``value + prepend + 原值``。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.set_env(self.patch_set, name, value, prepend=prepend)

    def del_env(self, name: str, *, raising: bool = True) -> PatchHandle:
        """
        删除环境变量。

        Args:
            name (str):
                环境变量名。
            raising (bool):
                变量不存在时是否抛出 ``KeyError``。为 False 且变量不存在时记录 ``noop``。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.del_env(self.patch_set, name, raising=raising)

    def syspath_prepend(self, path: str | os.PathLike[str]) -> PatchHandle:
        """
        把路径插入 ``sys.path`` 最前面, 撤销时按值移除。

        Args:
            path (str | os.PathLike[str]):
                要插入的路径。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.syspath_prepend(self.patch_set, path)

    def wrap(
        self,
        target: Any,
        factory: Callable[[Any], Any],
        *,
        trampoline: bool = False,
        rebind_references: bool = False,
        rebind_limit: int = operations.MAX_REBIND_REFERENCES,
    ) -> PatchHandle:
        """
        用 ``factory(original) -> replacement`` 包装可调用对象。

        ``trampoline=True`` 时在目标位置安装稳定的转发函数, 卸载只把转发目标换回原函数;
        同一位置的多次蹦床包装会叠加并可按任意顺序卸载。目标所属对象是类时保留描述符类型,
        规则同 ``patch_method``。目标解析失败时句柄为 ``failed`` 且不抛出 (严格模式下抛出)。

        Args:
            target (Any):
                目标路径字符串 ``"pkg.mod:Obj.attr"``, 或 ``(所属对象, 属性名)``。
            factory (Callable[[Any], Any]):
                接收原可调用对象并返回替换对象的工厂, 返回 None 时记录 ``noop``。
            trampoline (bool):
                是否使用蹦床。
            rebind_references (bool):
                是否把其他模块命名空间中对原可调用对象的同一对象引用改为新对象
                (蹦床模式下为转发函数), 位置列表记录在结果的 ``detail`` 中。
            rebind_limit (int):
                最多重新绑定的引用数量。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.wrap_callable(self.patch_set, target, factory, trampoline=trampoline, rebind_references=rebind_references, rebind_limit=rebind_limit)

    def patch_method(self, target: Any, factory: Callable[[Any], Any], *, trampoline: bool = False) -> PatchHandle:
        """
        包装类成员并保留描述符类型。

        普通函数、``staticmethod``、``classmethod`` 把底层函数交给工厂, ``property`` 把 ``fget``
        交给工厂 (工厂返回 ``property`` 时直接使用)。非蹦床模式撤销时恢复原描述符对象本身。

        Args:
            target (Any):
                目标路径字符串 ``"pkg.mod:Cls.meth"``, 或 ``(类, 成员名)``。
            factory (Callable[[Any], Any]):
                接收原函数并返回替换函数的工厂。
            trampoline (bool):
                是否使用蹦床。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.patch_method(self.patch_set, target, factory, trampoline=trampoline)

    def set_class_attr(self, target: Any, name: Any, value: Any = NOTSET, *, raising: bool = True) -> PatchHandle:
        """
        设置类属性, 旧值从类的原始 ``__dict__`` 读取, 撤销时恢复原描述符对象。

        支持 ``set_class_attr(Cls, "name", value)`` 和 ``set_class_attr("pkg.mod:Cls.name", value)``。

        Args:
            target (Any):
                类, 或目标路径字符串。
            name (Any):
                属性名; 使用目标路径写法时为新值。
            value (Any):
                新值; 使用目标路径写法时省略。
            raising (bool):
                属性 (含继承属性) 不存在时是否视为目标解析失败。

        Returns:
            PatchHandle:
                操作句柄。
        """

        return operations.set_class_attr(self.patch_set, target, name, value, raising=raising)

    def reload_module(self, name: str | ModuleType) -> PatchHandle:
        """
        在当前补丁计划下重新执行已导入的模块 (显式启用, 不可撤销)。

        Args:
            name (str | ModuleType):
                模块名或模块对象。

        Returns:
            PatchHandle:
                状态为 ``requires_restart`` 的句柄, 结果说明其他位置可能仍持有旧引用。
        """

        return operations.reload_module(self.patch_set, name)

    def add_disposer(self, disposer: Callable[[], Any], label: str | None = None) -> PatchHandle:
        """
        登记关闭时调用的清理函数。补丁集已关闭时立即执行。

        Args:
            disposer (Callable[[], Any]):
                清理函数。
            label (str | None):
                面向调试的描述。

        Returns:
            PatchHandle:
                清理函数对应的句柄。
        """

        return self.patch_set.add_disposer(disposer, label)


def register_patch_set(patch_set: PatchSet, *, state: HotpatcherState | None = None) -> PatchSet:
    """
    把补丁集写入 ``state.patch_sets``。

    Args:
        patch_set (PatchSet):
            补丁集。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用补丁集自身的状态。

    Returns:
        PatchSet:
            同一个补丁集对象。

    Raises:
        ValueError:
            状态对象与补丁集不一致, 或已注册同 ID / 同名称的其他补丁集时抛出。
    """

    active_state = state or patch_set.state
    if active_state is not patch_set.state:
        raise ValueError(f"patch set {patch_set.id!r} belongs to a different HotpatcherState")
    with active_state.control_lock:
        for existing in active_state.patch_sets.values():
            if existing is patch_set:
                return patch_set
            if existing.id == patch_set.id:
                raise ValueError(f"patch set id {patch_set.id!r} is already registered")
            if existing.name == patch_set.name:
                raise ValueError(f"patch set name {patch_set.name!r} is already registered as {existing.id!r}")
        active_state.patch_sets[patch_set.id] = patch_set
    return patch_set


def get_patch_set(key: str, *, state: HotpatcherState | None = None) -> PatchSet | None:
    """
    按 ID 或名称查询已注册补丁集, ID 优先。

    Args:
        key (str):
            补丁集 ID 或名称。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchSet | None:
            补丁集, 不存在时为 None。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        found = active_state.patch_sets.get(key)
        if found is not None:
            return found
        for patch_set in active_state.patch_sets.values():
            if patch_set.name == key:
                return patch_set
    return None


def list_patch_sets(*, state: HotpatcherState | None = None) -> list[PatchSet]:
    """
    列出已注册补丁集快照, 按注册顺序排列。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        list[PatchSet]:
            补丁集列表。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        return list(active_state.patch_sets.values())


def remove_patch_set(key: str | PatchSet, *, state: HotpatcherState | None = None) -> PatchSet | None:
    """
    从 ``state.patch_sets`` 移除补丁集, 不会关闭它。

    Args:
        key (str | PatchSet):
            补丁集对象、ID 或名称。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用补丁集自身状态或默认状态。

    Returns:
        PatchSet | None:
            被移除的补丁集, 不存在时为 None。
    """

    if isinstance(key, PatchSet):
        active_state = state or key.state
        with active_state.control_lock:
            if active_state.patch_sets.get(key.id) is key:
                return active_state.patch_sets.pop(key.id)
        return None
    active_state = state or get_default_state()
    with active_state.control_lock:
        found = active_state.patch_sets.pop(key, None)
        if found is not None:
            return found
        for set_id, patch_set in list(active_state.patch_sets.items()):
            if patch_set.name == key:
                return active_state.patch_sets.pop(set_id)
    return None


def _collect_operation(handle: PatchHandle) -> None:
    collected = _OPERATION_COLLECTOR.get()
    if collected is not None:
        collected.append(handle)


def _coerce_undo_status(result: Any) -> PatchStatus:
    if isinstance(result, PatchStatus) and result in _UNDO_STATUS_PRIORITY:
        return result
    if isinstance(result, str):
        try:
            status = PatchStatus(result)
        except ValueError:
            return PatchStatus.REVERTED
        if status in _UNDO_STATUS_PRIORITY:
            return status
    return PatchStatus.REVERTED
