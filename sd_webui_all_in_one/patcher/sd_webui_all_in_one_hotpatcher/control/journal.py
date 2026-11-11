"""可撤销补丁操作日志。

``PatchJournal`` 记录每一次已经生效的修改及其逆操作, 并以单一 LIFO 列表撤销。
语义参考 pytest ``MonkeyPatch``:

- ``NOTSET`` 表示修改前目标不存在, 撤销时删除目标。
- 类属性从原始 ``__dict__`` 读取旧值, 保留 ``staticmethod`` / ``classmethod`` / ``property`` 描述符。
- 实例属性在没有数据描述符时读取实例 ``__dict__``, 撤销时不会遗留遮蔽类属性的实例条目。

相比 pytest 的改进:

- 所有类型的条目位于同一个 LIFO 列表中, 撤销顺序与生效顺序严格相反。
- 单个条目撤销失败不会中断其他条目, 失败信息汇总在撤销报告中。
- 撤销会先弹出条目再执行, 因此 ``undo()`` 幂等, 失败条目也不会被重复执行。
"""

from __future__ import annotations

import enum
import importlib
import os
import sys
import threading
import warnings
from collections.abc import Callable, MutableMapping, MutableSequence
from dataclasses import dataclass, field
from typing import Any

from .targets import describe_target

__all__ = [
    "NOTSET",
    "JournalEntry",
    "JournalUndoReport",
    "JournalUndoResult",
    "NotSetType",
    "PatchJournal",
]

_REPR_LIMIT = 200


class NotSetType(enum.Enum):
    """表示 "修改前不存在" 的哨兵类型。"""

    NOTSET = 0

    def __repr__(self) -> str:
        """返回哨兵的可读表示。

        Returns:
            str: 固定为 ``"NOTSET"``。
        """

        return "NOTSET"


NOTSET = NotSetType.NOTSET


@dataclass(frozen=True)
class JournalEntry:
    """
    单条已生效修改及其逆操作。

    Attributes:
        kind (str):
            条目类型, 例如 ``attr``、``item``、``env``、``list``、``callback``、``disposer``。
        label (str):
            面向调试的目标描述。
        undo_fn (Callable[[], Any]):
            撤销该修改的函数。返回值会原样记录在撤销结果中。
        target (Any):
            被修改的对象。
        key (Any):
            属性名、键名或插入的值。
        old_value (Any):
            修改前的值, ``NOTSET`` 表示修改前不存在。
        handle_id (str | None):
            所属补丁句柄 ID。
    """

    kind: str
    label: str
    undo_fn: Callable[[], Any] = field(repr=False)
    target: Any = field(default=None, repr=False)
    key: Any = None
    old_value: Any = field(default=NOTSET, repr=False)
    handle_id: str | None = None

    def describe(self) -> dict[str, Any]:
        """
        生成可序列化的条目描述。

        Returns:
            dict[str, Any]:
                包含类型、标签、所属句柄和是否存在旧值的字典。
        """

        return {
            "kind": self.kind,
            "label": self.label,
            "handle_id": self.handle_id,
            "key": _bounded_repr(self.key),
            "had_previous_value": self.old_value is not NOTSET,
        }


@dataclass
class JournalUndoResult:
    """
    单条日志条目的撤销结果。

    Attributes:
        entry (JournalEntry):
            被撤销的条目。
        result (Any):
            ``undo_fn`` 的返回值。
        error (Exception | None):
            撤销失败时的异常。
    """

    entry: JournalEntry
    result: Any = None
    error: Exception | None = None

    @property
    def ok(self) -> bool:
        """
        撤销是否成功。

        Returns:
            bool:
                没有异常时返回 True。
        """

        return self.error is None


@dataclass
class JournalUndoReport:
    """
    一次 ``undo()`` 的汇总报告, 结果按实际执行顺序 (LIFO) 排列。

    Attributes:
        results (list[JournalUndoResult]):
            每个条目的撤销结果。
    """

    results: list[JournalUndoResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """
        是否全部撤销成功。

        Returns:
            bool:
                所有条目都成功时返回 True。
        """

        return all(result.ok for result in self.results)

    @property
    def errors(self) -> list[Exception]:
        """
        按执行顺序列出的撤销异常。

        Returns:
            list[Exception]:
                失败条目的异常列表。
        """

        return [result.error for result in self.results if result.error is not None]

    @property
    def first_error(self) -> Exception | None:
        """
        第一个撤销异常。

        Returns:
            Exception | None:
                第一个失败条目的异常, 全部成功时为 None。
        """

        errors = self.errors
        return errors[0] if errors else None

    def raise_first_error(self) -> None:
        """
        存在撤销失败时重新抛出第一个异常。

        Raises:
            Exception:
                第一个失败条目的原始异常。
        """

        error = self.first_error
        if error is not None:
            raise error

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的报告。

        Returns:
            dict[str, Any]:
                包含 ``ok``、撤销条目数和失败详情的字典。
        """

        return {
            "ok": self.ok,
            "undone": len(self.results),
            "failed": [{**result.entry.describe(), "error_type": type(result.error).__name__, "error_message": str(result.error)} for result in self.results if result.error is not None],
        }


class PatchJournal:
    """
    单一 LIFO 列表的可撤销修改日志。

    ``set_*`` / ``del_*`` / ``insert`` 系列方法先执行修改, 修改成功后才写入条目,
    因此修改失败不会留下孤立条目。``record_callback`` 只记录任意逆操作。
    内部锁仅保护条目列表, 不会在执行修改或撤销函数时持有。
    """

    def __init__(self) -> None:
        """初始化空日志。"""

        self._entries: list[JournalEntry] = []
        self._lock = threading.Lock()

    def __len__(self) -> int:
        """
        返回尚未撤销的条目数。

        Returns:
            int:
                条目数量。
        """

        with self._lock:
            return len(self._entries)

    def entries(self, *, handle_id: str | None = None) -> list[dict[str, Any]]:
        """
        列出尚未撤销的条目描述, 按记录顺序排列。

        Args:
            handle_id (str | None):
                只列出属于该句柄的条目。为 None 时列出全部。

        Returns:
            list[dict[str, Any]]:
                条目描述列表。
        """

        with self._lock:
            snapshot = list(self._entries)
        return [entry.describe() for entry in snapshot if handle_id is None or entry.handle_id == handle_id]

    def handle_ids(self) -> list[str]:
        """
        列出拥有未撤销条目的句柄 ID, 保持首次出现顺序。

        Returns:
            list[str]:
                句柄 ID 列表。
        """

        with self._lock:
            snapshot = list(self._entries)
        seen: dict[str, None] = {}
        for entry in snapshot:
            if entry.handle_id is not None:
                seen.setdefault(entry.handle_id, None)
        return list(seen)

    def record_callback(
        self,
        undo_fn: Callable[[], Any],
        label: str,
        *,
        kind: str = "callback",
        handle_id: str | None = None,
    ) -> JournalEntry:
        """
        记录一个任意逆操作。

        Args:
            undo_fn (Callable[[], Any]):
                撤销时调用的函数。返回值会记录在撤销结果中。
            label (str):
                面向调试的描述。
            kind (str):
                条目类型。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry:
                新记录的条目。

        Raises:
            TypeError:
                ``undo_fn`` 不可调用时抛出。
        """

        if not callable(undo_fn):
            raise TypeError(f"undo_fn must be callable, got {type(undo_fn).__name__}")
        return self._append(JournalEntry(kind=kind, label=label, undo_fn=undo_fn, target=undo_fn, handle_id=handle_id))

    def set_attr(
        self,
        target: Any,
        name: str,
        value: Any,
        *,
        raising: bool = True,
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry:
        """
        设置属性并记录逆操作。

        Args:
            target (Any):
                模块、类或实例。
            name (str):
                属性名。
            value (Any):
                新值。
            raising (bool):
                属性不存在时是否抛出 ``AttributeError``。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry:
                新记录的条目。

        Raises:
            TypeError:
                ``name`` 不是字符串时抛出。
            AttributeError:
                ``raising`` 为 True 且属性不存在时抛出。
        """

        if not isinstance(name, str):
            raise TypeError(f"attribute name must be str, got {type(name).__name__}")
        if raising and getattr(target, name, NOTSET) is NOTSET:
            raise AttributeError(f"{describe_target(target)} has no attribute {name!r}")
        old_value = _capture_attr(target, name)
        setattr(target, name, value)
        return self._append(
            JournalEntry(
                kind="attr",
                label=label or describe_target(target, name),
                undo_fn=_attr_restorer(target, name, old_value),
                target=target,
                key=name,
                old_value=old_value,
                handle_id=handle_id,
            )
        )

    def del_attr(
        self,
        target: Any,
        name: str,
        *,
        raising: bool = True,
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry | None:
        """
        删除属性并记录逆操作。

        Args:
            target (Any):
                模块、类或实例。
            name (str):
                属性名。
            raising (bool):
                属性不存在时是否抛出 ``AttributeError``。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry | None:
                新记录的条目。属性不存在且 ``raising`` 为 False 时返回 None。

        Raises:
            TypeError:
                ``name`` 不是字符串时抛出。
            AttributeError:
                ``raising`` 为 True 且属性不存在时抛出。
        """

        if not isinstance(name, str):
            raise TypeError(f"attribute name must be str, got {type(name).__name__}")
        if not hasattr(target, name):
            if raising:
                raise AttributeError(f"{describe_target(target)} has no attribute {name!r}")
            return None
        old_value = _capture_attr(target, name)
        delattr(target, name)
        return self._append(
            JournalEntry(
                kind="attr",
                label=label or describe_target(target, name),
                undo_fn=_attr_restorer(target, name, old_value),
                target=target,
                key=name,
                old_value=old_value,
                handle_id=handle_id,
            )
        )

    def set_item(
        self,
        mapping: MutableMapping[Any, Any],
        key: Any,
        value: Any,
        *,
        kind: str = "item",
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry:
        """
        设置映射条目并记录逆操作。

        Args:
            mapping (MutableMapping[Any, Any]):
                目标映射。
            key (Any):
                键。
            value (Any):
                新值。
            kind (str):
                条目类型。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry:
                新记录的条目。
        """

        old_value = mapping.get(key, NOTSET)
        mapping[key] = value
        return self._append(
            JournalEntry(
                kind=kind,
                label=label or _item_label(mapping, key),
                undo_fn=_item_restorer(mapping, key, old_value),
                target=mapping,
                key=key,
                old_value=old_value,
                handle_id=handle_id,
            )
        )

    def del_item(
        self,
        mapping: MutableMapping[Any, Any],
        key: Any,
        *,
        raising: bool = True,
        kind: str = "item",
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry | None:
        """
        删除映射条目并记录逆操作。

        Args:
            mapping (MutableMapping[Any, Any]):
                目标映射。
            key (Any):
                键。
            raising (bool):
                键不存在时是否抛出 ``KeyError``。
            kind (str):
                条目类型。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry | None:
                新记录的条目。键不存在且 ``raising`` 为 False 时返回 None。

        Raises:
            KeyError:
                ``raising`` 为 True 且键不存在时抛出。
        """

        if key not in mapping:
            if raising:
                raise KeyError(key)
            return None
        old_value = mapping[key]
        del mapping[key]
        return self._append(
            JournalEntry(
                kind=kind,
                label=label or _item_label(mapping, key),
                undo_fn=_item_restorer(mapping, key, old_value),
                target=mapping,
                key=key,
                old_value=old_value,
                handle_id=handle_id,
            )
        )

    def set_env(
        self,
        name: str,
        value: str,
        *,
        prepend: str | None = None,
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry:
        """
        设置环境变量并记录逆操作, 语义与 pytest ``setenv`` 一致。

        Args:
            name (str):
                环境变量名。
            value (str):
                新值。非字符串会发出警告并转换为字符串。
            prepend (str | None):
                非空且变量已存在时, 新值为 ``value + prepend + 原值``。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry:
                新记录的条目。
        """

        if not isinstance(value, str):
            warnings.warn(
                f"Value of environment variable {name} should be str, got {type(value).__name__}; converted to str implicitly",
                RuntimeWarning,
                stacklevel=2,
            )
            value = str(value)
        if prepend and name in os.environ:
            value = value + prepend + os.environ[name]
        return self.set_item(os.environ, name, value, kind="env", label=label or f"env:{name}", handle_id=handle_id)

    def del_env(
        self,
        name: str,
        *,
        raising: bool = True,
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry | None:
        """
        删除环境变量并记录逆操作。

        Args:
            name (str):
                环境变量名。
            raising (bool):
                变量不存在时是否抛出 ``KeyError``。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry | None:
                新记录的条目。变量不存在且 ``raising`` 为 False 时返回 None。
        """

        return self.del_item(os.environ, name, raising=raising, kind="env", label=label or f"env:{name}", handle_id=handle_id)

    def insert(
        self,
        sequence: MutableSequence[Any],
        index: int,
        value: Any,
        *,
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry:
        """
        向 ``sys.path`` 风格的列表插入值并记录逆操作。

        撤销时按值移除插入的元素: 优先移除同一对象, 其次移除第一个相等的元素;
        元素已不存在时视为已撤销。不会整体还原列表, 因此不会覆盖他人之后的修改。

        Args:
            sequence (MutableSequence[Any]):
                目标列表。
            index (int):
                插入位置。
            value (Any):
                插入的值。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry:
                新记录的条目。
        """

        sequence.insert(index, value)
        return self._append(
            JournalEntry(
                kind="list",
                label=label or f"{describe_target(sequence)}.insert({index}, {_bounded_repr(value)})",
                undo_fn=_list_remover(sequence, value),
                target=sequence,
                key=value,
                handle_id=handle_id,
            )
        )

    def syspath_prepend(
        self,
        path: str | os.PathLike[str],
        *,
        path_list: MutableSequence[str] | None = None,
        label: str | None = None,
        handle_id: str | None = None,
    ) -> JournalEntry:
        """
        把路径插入导入搜索路径最前面并记录逆操作。

        插入后会调用 ``importlib.invalidate_caches()``。

        Args:
            path (str | os.PathLike[str]):
                要插入的路径。
            path_list (MutableSequence[str] | None):
                目标列表。为 None 时使用 ``sys.path``。
            label (str | None):
                面向调试的描述。为 None 时自动生成。
            handle_id (str | None):
                所属补丁句柄 ID。

        Returns:
            JournalEntry:
                新记录的条目。
        """

        value = os.fspath(path)
        target_list = sys.path if path_list is None else path_list
        entry = self.insert(target_list, 0, value, label=label or f"sys.path:{value}", handle_id=handle_id)
        importlib.invalidate_caches()
        return entry

    def undo(self, *, handle_id: str | None = None) -> JournalUndoReport:
        """
        按 LIFO 顺序撤销条目。

        每个条目先从日志移除再执行, 单个条目失败不影响其他条目; 因此重复调用是幂等的,
        失败条目不会被再次执行。``KeyboardInterrupt`` 等非 ``Exception`` 异常会把尚未执行的
        条目放回日志后继续向外抛出; 被打断的条目本身视为已消费, 不会放回。

        Args:
            handle_id (str | None):
                只撤销属于该句柄的条目。为 None 时撤销全部。

        Returns:
            JournalUndoReport:
                按执行顺序排列的撤销报告。

        Raises:
            BaseException:
                撤销函数抛出非 ``Exception`` 异常 (例如 ``KeyboardInterrupt``) 时原样抛出。
        """

        with self._lock:
            if handle_id is None:
                pending = self._entries[::-1]
                self._entries.clear()
            else:
                pending = [entry for entry in reversed(self._entries) if entry.handle_id == handle_id]
                self._entries[:] = [entry for entry in self._entries if entry.handle_id != handle_id]

        report = JournalUndoReport()
        for position, entry in enumerate(pending):
            try:
                result = entry.undo_fn()
            except Exception as exc:
                report.results.append(JournalUndoResult(entry=entry, error=exc))
            except BaseException:
                self._restore_pending(pending[position + 1 :])
                raise
            else:
                report.results.append(JournalUndoResult(entry=entry, result=result))
        return report

    def _restore_pending(self, remaining_lifo: list[JournalEntry]) -> None:
        with self._lock:
            self._entries.extend(reversed(remaining_lifo))

    def _append(self, entry: JournalEntry) -> JournalEntry:
        with self._lock:
            self._entries.append(entry)
        return entry


def _is_data_descriptor(cls: type, name: str) -> bool:
    for klass in cls.__mro__:
        if name in klass.__dict__:
            descriptor_type = type(klass.__dict__[name])
            return hasattr(descriptor_type, "__set__") or hasattr(descriptor_type, "__delete__")
    return False


def _capture_attr(target: Any, name: str) -> Any:
    if isinstance(target, type):
        # 类属性读取原始 __dict__, 保留 staticmethod/classmethod/property 描述符本身。
        return target.__dict__.get(name, NOTSET)
    if not _is_data_descriptor(type(target), name):
        # 没有数据描述符时 setattr 写入实例 __dict__, 撤销也只需还原该条目,
        # 避免把继承值写回实例从而永久遮蔽类属性。
        target_dict = getattr(target, "__dict__", None)
        if isinstance(target_dict, MutableMapping):
            return target_dict.get(name, NOTSET)
    return getattr(target, name, NOTSET)


def _attr_restorer(target: Any, name: str, old_value: Any) -> Callable[[], None]:
    def restore() -> None:
        if old_value is not NOTSET:
            setattr(target, name, old_value)
            return
        if isinstance(target, type):
            if name in target.__dict__:
                delattr(target, name)
            return
        try:
            delattr(target, name)
        except AttributeError:
            # 目标已经不存在时即处于期望状态; 仍存在于实例 __dict__ 才是真正的失败。
            target_dict = getattr(target, "__dict__", None)
            if isinstance(target_dict, MutableMapping) and name in target_dict:
                raise

    return restore


def _item_restorer(mapping: MutableMapping[Any, Any], key: Any, old_value: Any) -> Callable[[], None]:
    def restore() -> None:
        if old_value is NOTSET:
            # 已被删除时即处于期望状态。
            mapping.pop(key, None)
        else:
            mapping[key] = old_value

    return restore


def _list_remover(sequence: MutableSequence[Any], value: Any) -> Callable[[], None]:
    def remove() -> None:
        for index, item in enumerate(sequence):
            if item is value:
                del sequence[index]
                return
        for index, item in enumerate(sequence):
            if item == value:
                del sequence[index]
                return

    return remove


def _item_label(mapping: Any, key: Any) -> str:
    if mapping is os.environ:
        return f"env:{key}"
    return f"{describe_target(mapping)}[{_bounded_repr(key)}]"


def _bounded_repr(value: Any) -> str:
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<unrepresentable {type(value).__name__}: {type(exc).__name__}>"
    if len(text) > _REPR_LIMIT:
        return text[: _REPR_LIMIT - 3] + "..."
    return text
