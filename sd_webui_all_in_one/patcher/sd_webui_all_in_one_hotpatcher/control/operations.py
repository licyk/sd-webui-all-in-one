"""可撤销的实时补丁操作。

本模块是 ``PatchContext`` 全部实时操作的唯一实现, ``PatchContext`` 的方法只做参数转发。
每个操作都通过 ``PatchSet.record_operation`` 创建一个 ``PatchHandle``, 并把逆操作以该句柄 ID
写入补丁集日志, 关闭补丁集时按 LIFO 撤销。

失败语义:

- 基础操作 (``set_attr`` / ``del_attr`` / ``set_item`` / ``del_item`` / ``set_env`` / ``del_env`` /
  ``syspath_prepend``) 与 P1 保持一致: 任何失败都会把句柄标记为 ``failed`` 并抛出异常。
- 新增操作 (``wrap_callable`` / ``patch_method`` / ``set_class_attr`` / ``reload_module``) 的
  **目标解析失败** (``TargetError``: 模块不存在、属性不存在、模块尚未导入) 只把句柄标记为
  ``failed`` (结果原因 ``target_unresolved``) 并记录警告, 不抛出异常; 严格模式
  (``state.strict_mode``) 下照常抛出。补丁工厂函数等其他异常始终抛出。
- 操作中途失败时, 本句柄已写入的日志条目会立即撤销, 不会留下部分生效的修改。

蹦床 (trampoline): ``wrap_callable(..., trampoline=True)`` 在目标位置安装一个稳定的转发函数,
其当前目标可以替换。卸载只把目标换回原函数, 转发函数本身永久保留, 因此在安装之后通过
``from x import f`` 复制出去的引用会跟随包装与卸载。在安装之前复制的引用指向原函数对象本身,
只能通过 ``rebind_references=True`` 改为指向转发函数。

锁约定: ``Trampoline`` 内部锁是叶子锁, 只保护层列表, 持有时不调用补丁工厂、被包装函数或任何
其他 hotpatcher 锁。所有操作都在 ``record_operation`` 的锁外执行, ``reload_module`` 的
``importlib.reload`` 不会在持有任何 hotpatcher 锁时运行。
"""

from __future__ import annotations

import functools
import importlib
import inspect
import logging
import os
import sys
import threading
from collections.abc import Callable, MutableMapping
from types import ModuleType
from typing import TYPE_CHECKING, Any

from .handles import PatchHandle, PatchOutcome, PatchStatus
from .journal import NOTSET, JournalEntry
from .targets import TargetAttributeError, TargetError, TargetImportError, describe_target, split_target

if TYPE_CHECKING:
    from .patchset import PatchSet

__all__ = [
    "MAX_REBIND_REFERENCES",
    "TRAMPOLINE_ATTRIBUTE",
    "Trampoline",
    "del_attr",
    "del_env",
    "del_item",
    "get_trampoline",
    "patch_method",
    "reload_module",
    "set_attr",
    "set_class_attr",
    "set_env",
    "set_item",
    "syspath_prepend",
    "wrap_callable",
]

TRAMPOLINE_ATTRIBUTE = "__sd_webui_aio_trampoline__"
"""蹦床转发函数上指向其 ``Trampoline`` 状态对象的属性名"""

MAX_REBIND_REFERENCES = 1000
"""``rebind_references`` 默认最多重新绑定的引用数量"""

TARGET_UNRESOLVED_REASON = "target_unresolved"
"""目标解析失败时失败结果的 ``reason``"""

RELOAD_REASON = "stale_references_may_remain"
"""``reload_module`` 结果的 ``reason``"""

_LOGGER = logging.getLogger(__name__)
_PACKAGE_NAME = __name__.split(".", 1)[0]


# ---------------------------------------------------------------- 蹦床


class _Forwarding:
    """持有可替换 ``target`` 的转发目标基类。"""

    target: Any


class _Link(_Forwarding):
    """叠加包装时传给上层工厂的间接层, 始终转发到 "当前位于其下方" 的可调用对象。"""

    def __init__(self, target: Any) -> None:
        self.target = target
        self.function = _make_forwarder(target, self)

    def retarget(self, target: Any) -> None:
        self.target = target
        try:
            setattr(self.function, "__wrapped__", target)
        except (AttributeError, TypeError):
            pass


class _TrampolineLayer:
    __slots__ = ("handle_id", "wrapper", "link")

    def __init__(self, handle_id: str, wrapper: Any, link: _Link | None) -> None:
        self.handle_id = handle_id
        self.wrapper = wrapper
        self.link = link


class Trampoline(_Forwarding):
    """
    蹦床状态: 稳定的转发函数和按句柄叠加的包装层。

    转发函数 (``function``) 用 ``functools.update_wrapper`` 复制原函数的元数据, ``__wrapped__``
    指向原函数, 并通过 ``TRAMPOLINE_ATTRIBUTE`` 属性指回本对象。原函数是协程函数时转发函数也是协程函数;
    生成器函数按普通可调用对象转发。

    每个包装层对应一个补丁句柄。最底层的工厂收到原函数本身; 其上各层的工厂收到一个间接层,
    它总是转发到当前位于该层下方的可调用对象, 因此任意顺序卸载都能保持其余层的正确叠加。

    Attributes:
        original (Any):
            被包装的原可调用对象。
        target (Any):
            转发函数当前调用的对象, 即最上层包装或原函数。
        function (Callable[..., Any]):
            安装在目标位置的稳定转发函数。
        home (tuple[Any, str]):
            安装位置 ``(所属对象, 属性名)``。
    """

    def __init__(self, original: Any, owner: Any, name: str) -> None:
        """
        创建蹦床。不会安装到任何位置。

        Args:
            original (Any):
                被包装的原可调用对象。
            owner (Any):
                安装位置的所属对象。
            name (str):
                安装位置的属性名。

        Raises:
            TypeError:
                ``original`` 不可调用时抛出。
        """

        if not callable(original):
            raise TypeError(f"trampoline target must be callable, got {type(original).__name__}")
        self.original = original
        self.target = original
        self.home: tuple[Any, str] = (owner, name)
        self._layers: list[_TrampolineLayer] = []
        self._lock = threading.Lock()
        self.function = _make_forwarder(original, self)
        setattr(self.function, TRAMPOLINE_ATTRIBUTE, self)

    def __repr__(self) -> str:
        """
        返回调试表示。

        Returns:
            str:
                包含原函数和层数的字符串。
        """

        return f"<Trampoline original={describe_target(self.original)!r} layers={len(self.layer_ids)}>"

    @property
    def layer_ids(self) -> list[str]:
        """
        自底向上排列的包装层句柄 ID。

        Returns:
            list[str]:
                句柄 ID 列表。
        """

        with self._lock:
            return [layer.handle_id for layer in self._layers]

    @property
    def active(self) -> bool:
        """
        是否存在包装层。

        Returns:
            bool:
                存在至少一层包装时返回 True。
        """

        with self._lock:
            return bool(self._layers)

    def describe(self) -> dict[str, Any]:
        """
        生成可序列化的蹦床描述。

        Returns:
            dict[str, Any]:
                包含安装位置、原函数、是否协程函数和包装层句柄 ID 的字典。
        """

        owner, name = self.home
        return {
            "target": describe_target(owner, name),
            "original": describe_target(self.original),
            "coroutine": inspect.iscoroutinefunction(self.function),
            "layers": self.layer_ids,
        }

    def _owns_slot(self, owner: Any, name: str) -> bool:
        return self.home[0] is owner and self.home[1] == name

    def _prepare(self) -> tuple[Any, _Link | None]:
        with self._lock:
            if not self._layers:
                return self.original, None
            below = self._layers[-1].wrapper
        link = _Link(below)
        return link.function, link

    def _push(self, handle_id: str, wrapper: Any, link: _Link | None) -> _TrampolineLayer:
        layer = _TrampolineLayer(handle_id, wrapper, link)
        with self._lock:
            if link is not None:
                # 工厂执行期间下方的层可能已被卸载: 重新指向当前最上层。
                link.retarget(self._layers[-1].wrapper if self._layers else self.original)
            self._layers.append(layer)
            self.target = wrapper
        return layer

    def _remove(self, layer: _TrampolineLayer) -> bool:
        with self._lock:
            for index, candidate in enumerate(self._layers):
                if candidate is layer:
                    break
            else:
                return False
            del self._layers[index]
            if index < len(self._layers):
                above = self._layers[index]
                if above.link is not None:
                    above.link.retarget(self._layers[index - 1].wrapper if index > 0 else self.original)
            self.target = self._layers[-1].wrapper if self._layers else self.original
        return True


def get_trampoline(obj: Any) -> Trampoline | None:
    """
    返回对象对应的蹦床状态。

    Args:
        obj (Any):
            转发函数, 或包装转发函数的 ``staticmethod`` / ``classmethod`` / ``property``。

    Returns:
        Trampoline | None:
            蹦床状态; 对象不是蹦床转发函数时为 None。
    """

    if isinstance(obj, (staticmethod, classmethod)):
        obj = obj.__func__
    elif isinstance(obj, property):
        obj = obj.fget
    state = getattr(obj, TRAMPOLINE_ATTRIBUTE, None)
    # functools.wraps(trampoline) 会把标记属性复制到用户包装函数上, 需要核对身份。
    if isinstance(state, Trampoline) and state.function is obj:
        return state
    return None


def _make_forwarder(template: Any, holder: _Forwarding) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(template):

        async def forward_async(*args: Any, **kwargs: Any) -> Any:
            return await holder.target(*args, **kwargs)

        forwarder: Callable[..., Any] = forward_async
    else:

        def forward(*args: Any, **kwargs: Any) -> Any:
            return holder.target(*args, **kwargs)

        forwarder = forward
    functools.update_wrapper(forwarder, template)
    # 模板若是其他蹦床, 不继承它的标记属性。
    forwarder.__dict__.pop(TRAMPOLINE_ATTRIBUTE, None)
    return forwarder


# ---------------------------------------------------------------- 通用执行路径


def _run_operation(
    patch_set: PatchSet,
    kind: str,
    label: str,
    resolve: Callable[[], Any],
    apply: Callable[[str, Any], Any],
    *,
    tolerant: bool,
) -> PatchHandle:
    # resolve 在 action 内执行, 只有它抛出的 TargetError 才算解析失败;
    # apply 失败时撤销本句柄已写入的条目, 再交给 record_operation 标记 failed。
    marker: dict[str, Any] = {}

    def action(handle_id: str) -> Any:
        marker["handle_id"] = handle_id
        try:
            resolved = resolve()
        except TargetError as exc:
            marker["unresolved"] = exc
            raise
        try:
            return apply(handle_id, resolved)
        except BaseException:
            patch_set.journal.undo(handle_id=handle_id)
            raise

    def failure_reason(exc: BaseException) -> str | None:
        return TARGET_UNRESOLVED_REASON if exc is marker.get("unresolved") else None

    try:
        return patch_set.record_operation(kind, label, action, failure_reason=failure_reason)
    except TargetError as exc:
        if not tolerant or exc is not marker.get("unresolved") or patch_set.state.strict_mode:
            raise
        handle = patch_set.get_handle(marker["handle_id"])
        if handle is None:
            raise
        _LOGGER.warning("Hotpatcher %s %r skipped: target could not be resolved: %s", kind, label, exc)
        return handle


def _unresolved(error_type: type[TargetError], message: str, target: str, **kwargs: Any) -> TargetError:
    error = error_type(message, **kwargs)
    error.target = target
    return error


def _member_label(target: Any, name: Any) -> tuple[Any, str | None, str]:
    if (name is None or name is NOTSET) and isinstance(target, tuple):
        if len(target) != 2:
            raise TypeError(f"target pair must be (owner, name), got {len(target)} items")
        target, name = target
    if name is None or name is NOTSET:
        if not isinstance(target, str):
            raise TypeError("pass a target path string 'pkg.mod:Obj.attr' or an (owner, name) pair")
        return target, None, target
    if not isinstance(name, str):
        raise TypeError(f"attribute name must be str, got {type(name).__name__}")
    return target, name, describe_target(target, name)


def _resolve_member(owner: Any, name: str | None, label: str) -> tuple[Any, str]:
    if name is None:
        return split_target(label, raising=True)
    if getattr(owner, name, NOTSET) is NOTSET:
        raise _unresolved(TargetAttributeError, f"{describe_target(owner)} has no attribute {name!r}", label)
    return owner, name


def _normalize_attr_call(method: str, target: Any, name: Any, value: Any) -> tuple[Any, str | None, Any, str]:
    if value is NOTSET:
        if not isinstance(target, str):
            raise TypeError(f"use {method}(target, name, value) or {method}('pkg.mod:attr', value) with a target path string")
        return target, None, name, target
    if not isinstance(name, str):
        raise TypeError(f"attribute name must be str, got {type(name).__name__}")
    return target, name, value, describe_target(target, name)


def _resolve_owner(owner: Any, attr: str | None, label: str) -> tuple[Any, str]:
    if attr is None:
        return split_target(label)
    return owner, attr


def _no_resolution() -> None:
    return None


# ---------------------------------------------------------------- 基础操作 (P1 语义)


def set_attr(
    patch_set: PatchSet,
    target: Any,
    name: Any,
    value: Any = NOTSET,
    *,
    raising: bool = True,
    rebind_references: bool = False,
    rebind_limit: int = MAX_REBIND_REFERENCES,
) -> PatchHandle:
    """
    设置属性。

    支持 ``set_attr(ps, obj, "name", value)`` 和 ``set_attr(ps, "pkg.mod:Obj.name", value)`` 两种写法。
    类属性的旧值从原始 ``__dict__`` 读取, 撤销时恢复原描述符对象。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        target (Any):
            模块、类、实例, 或目标路径字符串。
        name (Any):
            属性名; 使用目标路径写法时为新值。
        value (Any):
            新值; 使用目标路径写法时省略。
        raising (bool):
            属性不存在时是否抛出 ``AttributeError``。
        rebind_references (bool):
            旧值是可调用对象时, 是否把其他模块命名空间中对旧值的同一对象引用也改为新值。
        rebind_limit (int):
            最多重新绑定的引用数量。

    Returns:
        PatchHandle:
            操作句柄。

    Raises:
        ValueError:
            ``rebind_limit`` 不是非负整数时抛出。
    """

    owner, attr, new_value, label = _normalize_attr_call("set_attr", target, name, value)
    _check_rebind_limit(rebind_limit)

    def apply(handle_id: str, _resolved: None) -> Any:
        resolved, attr_name = _resolve_owner(owner, attr, label)
        if not rebind_references:
            # 默认路径与 P1 完全一致, 不额外读取属性 (避免触发模块 __getattr__ 或描述符 getter)。
            return patch_set.journal.set_attr(resolved, attr_name, new_value, raising=raising, label=label, handle_id=handle_id)
        previous = getattr(resolved, attr_name, NOTSET)
        patch_set.journal.set_attr(resolved, attr_name, new_value, raising=raising, label=label, handle_id=handle_id)
        if previous is NOTSET or previous is new_value or not callable(previous):
            return PatchOutcome.applied(reason="rebind_skipped:not_callable", detail={"rebound": [], "truncated": False, "limit": rebind_limit})
        return _rebind_outcome(_rebind_references(patch_set, handle_id, previous, new_value, rebind_limit))

    return _run_operation(patch_set, "attr", label, _no_resolution, apply, tolerant=False)


def del_attr(patch_set: PatchSet, target: Any, name: Any = NOTSET, *, raising: bool = True) -> PatchHandle:
    """
    删除属性。

    支持 ``del_attr(ps, obj, "name")`` 和 ``del_attr(ps, "pkg.mod:Obj.name")`` 两种写法。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        target (Any):
            模块、类、实例, 或目标路径字符串。
        name (Any):
            属性名; 使用目标路径写法时省略。
        raising (bool):
            属性不存在时是否抛出 ``AttributeError``。为 False 且属性不存在时记录 ``noop``。

    Returns:
        PatchHandle:
            操作句柄。

    Raises:
        TypeError:
            参数组合不合法时抛出。
    """

    if name is NOTSET:
        if not isinstance(target, str):
            raise TypeError("use del_attr(target, name) or del_attr('pkg.mod:attr') with a target path string")
        owner: Any = target
        attr: str | None = None
        label = target
    else:
        if not isinstance(name, str):
            raise TypeError(f"attribute name must be str, got {type(name).__name__}")
        owner, attr, label = target, name, describe_target(target, name)

    def apply(handle_id: str, _resolved: None) -> JournalEntry | None:
        resolved, attr_name = _resolve_owner(owner, attr, label)
        return patch_set.journal.del_attr(resolved, attr_name, raising=raising, label=label, handle_id=handle_id)

    return _run_operation(patch_set, "attr", label, _no_resolution, apply, tolerant=False)


def set_item(patch_set: PatchSet, mapping: MutableMapping[Any, Any], key: Any, value: Any) -> PatchHandle:
    """
    设置映射条目。

    Args:
        patch_set (PatchSet):
            所属补丁集。
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

    label = f"{describe_target(mapping)}[{key!r}]"
    return _run_operation(
        patch_set,
        "item",
        label,
        _no_resolution,
        lambda handle_id, _resolved: patch_set.journal.set_item(mapping, key, value, label=label, handle_id=handle_id),
        tolerant=False,
    )


def del_item(patch_set: PatchSet, mapping: MutableMapping[Any, Any], key: Any, *, raising: bool = True) -> PatchHandle:
    """
    删除映射条目。

    Args:
        patch_set (PatchSet):
            所属补丁集。
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

    label = f"{describe_target(mapping)}[{key!r}]"
    return _run_operation(
        patch_set,
        "item",
        label,
        _no_resolution,
        lambda handle_id, _resolved: patch_set.journal.del_item(mapping, key, raising=raising, label=label, handle_id=handle_id),
        tolerant=False,
    )


def set_env(patch_set: PatchSet, name: str, value: str, *, prepend: str | None = None) -> PatchHandle:
    """
    设置环境变量, 语义与 pytest ``setenv`` 一致。

    Args:
        patch_set (PatchSet):
            所属补丁集。
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

    label = f"env:{name}"
    return _run_operation(
        patch_set,
        "env",
        label,
        _no_resolution,
        lambda handle_id, _resolved: patch_set.journal.set_env(name, value, prepend=prepend, label=label, handle_id=handle_id),
        tolerant=False,
    )


def del_env(patch_set: PatchSet, name: str, *, raising: bool = True) -> PatchHandle:
    """
    删除环境变量。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        name (str):
            环境变量名。
        raising (bool):
            变量不存在时是否抛出 ``KeyError``。为 False 且变量不存在时记录 ``noop``。

    Returns:
        PatchHandle:
            操作句柄。
    """

    label = f"env:{name}"
    return _run_operation(
        patch_set,
        "env",
        label,
        _no_resolution,
        lambda handle_id, _resolved: patch_set.journal.del_env(name, raising=raising, label=label, handle_id=handle_id),
        tolerant=False,
    )


def syspath_prepend(patch_set: PatchSet, path: str | os.PathLike[str]) -> PatchHandle:
    """
    把路径插入 ``sys.path`` 最前面, 撤销时按值移除。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        path (str | os.PathLike[str]):
            要插入的路径。

    Returns:
        PatchHandle:
            操作句柄。
    """

    label = f"sys.path:{os.fspath(path)}"
    return _run_operation(
        patch_set,
        "syspath",
        label,
        _no_resolution,
        lambda handle_id, _resolved: patch_set.journal.syspath_prepend(path, label=label, handle_id=handle_id),
        tolerant=False,
    )


# ---------------------------------------------------------------- 可调用对象与类成员


def wrap_callable(
    patch_set: PatchSet,
    target: Any,
    factory: Callable[[Any], Any],
    *,
    name: str | None = None,
    trampoline: bool = False,
    rebind_references: bool = False,
    rebind_limit: int = MAX_REBIND_REFERENCES,
    require_class: bool = False,
    kind: str = "wrap",
) -> PatchHandle:
    """
    用 ``factory(original) -> replacement`` 包装可调用对象。

    目标所属对象是类时按描述符规则处理: 从原始 ``__dict__`` (沿 MRO) 读取成员, ``staticmethod`` /
    ``classmethod`` 把底层函数交给工厂, ``property`` 把 ``fget`` 交给工厂 (工厂返回 ``property``
    时直接使用), 结果再包回同一种描述符。非蹦床模式撤销时恢复原描述符对象本身。

    ``trampoline=True`` 时安装稳定的转发函数 (见 ``Trampoline``), 卸载只把转发目标换回原函数,
    不移除转发函数。同一位置的多次蹦床包装会叠加, 新工厂收到当前生效的可调用对象 (最底层为原函数,
    其上为转发到下方层的间接层), 可按任意顺序卸载。

    工厂返回 None 时不做修改并记录 ``noop``。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        target (Any):
            目标路径字符串 ``"pkg.mod:Obj.attr"``, 或与 ``name`` 一起给出的所属对象。
        factory (Callable[[Any], Any]):
            接收原可调用对象并返回替换对象的工厂。
        name (str | None):
            ``target`` 为所属对象时的属性名。
        trampoline (bool):
            是否使用蹦床。
        rebind_references (bool):
            是否把其他模块命名空间中对原可调用对象的同一对象引用改为新对象 (蹦床模式下为转发函数)。
        rebind_limit (int):
            最多重新绑定的引用数量。
        require_class (bool):
            是否要求所属对象是类。
        kind (str):
            句柄类型。

    Returns:
        PatchHandle:
            操作句柄。

    Raises:
        TypeError:
            参数不合法、所属对象不是类 (``require_class``) 或蹦床目标不可调用时抛出。
        ValueError:
            ``rebind_limit`` 不是非负整数时抛出。
    """

    if not callable(factory):
        raise TypeError(f"factory must be callable, got {type(factory).__name__}")
    _check_rebind_limit(rebind_limit)
    owner_ref, attr, label = _member_label(target, name)

    def resolve() -> tuple[Any, str, str, Any, Any]:
        owner, attr_name = _resolve_member(owner_ref, attr, label)
        if require_class and not isinstance(owner, type):
            raise TypeError(f"{label!r} is not a class member: {describe_target(owner)} is not a class")
        if isinstance(owner, type):
            raw = _class_raw(owner, attr_name)
            member_kind, original = _unwrap_member(raw, label)
        else:
            raw = getattr(owner, attr_name)
            member_kind, original = "plain", raw
        return owner, attr_name, member_kind, raw, original

    def apply(handle_id: str, resolved: tuple[Any, str, str, Any, Any]) -> Any:
        owner, attr_name, member_kind, raw, original = resolved
        if trampoline:
            return _apply_trampoline(patch_set, handle_id, owner, attr_name, member_kind, raw, original, factory, rebind_references, rebind_limit, label)
        replacement = factory(original)
        if replacement is None:
            return None
        patch_set.journal.set_attr(owner, attr_name, _rewrap_member(member_kind, raw, replacement), raising=False, label=label, handle_id=handle_id)
        if not rebind_references:
            return PatchOutcome.applied()
        return _rebind_outcome(_rebind_references(patch_set, handle_id, original, replacement, rebind_limit))

    return _run_operation(patch_set, kind, label, resolve, apply, tolerant=True)


def patch_method(
    patch_set: PatchSet,
    target: Any,
    factory: Callable[[Any], Any],
    *,
    name: str | None = None,
    trampoline: bool = False,
) -> PatchHandle:
    """
    包装类成员并保留描述符类型。

    普通函数、``staticmethod``、``classmethod`` 把底层函数交给工厂, ``property`` 把 ``fget`` 交给工厂
    (工厂返回 ``property`` 时直接使用)。非蹦床模式撤销时恢复原描述符对象本身。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        target (Any):
            目标路径字符串 ``"pkg.mod:Cls.meth"``, 或与 ``name`` 一起给出的类。
        factory (Callable[[Any], Any]):
            接收原函数并返回替换函数的工厂。
        name (str | None):
            ``target`` 为类时的成员名。
        trampoline (bool):
            是否使用蹦床。

    Returns:
        PatchHandle:
            操作句柄。
    """

    return wrap_callable(patch_set, target, factory, name=name, trampoline=trampoline, require_class=True, kind="method")


def set_class_attr(patch_set: PatchSet, target: Any, name: Any, value: Any = NOTSET, *, raising: bool = True) -> PatchHandle:
    """
    设置类属性, 旧值从类的原始 ``__dict__`` 读取, 撤销时恢复原描述符对象或删除新增属性。

    支持 ``set_class_attr(ps, Cls, "name", value)`` 和 ``set_class_attr(ps, "pkg.mod:Cls.name", value)``。

    Args:
        patch_set (PatchSet):
            所属补丁集。
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

    Raises:
        TypeError:
            所属对象不是类时抛出。
    """

    owner_ref, attr, new_value, label = _normalize_attr_call("set_class_attr", target, name, value)

    def resolve() -> tuple[Any, str]:
        if attr is None:
            owner, attr_name = split_target(label, raising=raising)
        else:
            owner, attr_name = owner_ref, attr
            if raising and getattr(owner, attr_name, NOTSET) is NOTSET:
                raise _unresolved(TargetAttributeError, f"{describe_target(owner)} has no attribute {attr_name!r}", label)
        if not isinstance(owner, type):
            raise TypeError(f"set_class_attr target owner must be a class, got {describe_target(owner)}")
        return owner, attr_name

    def apply(handle_id: str, resolved: tuple[Any, str]) -> JournalEntry:
        owner, attr_name = resolved
        return patch_set.journal.set_attr(owner, attr_name, new_value, raising=False, label=label, handle_id=handle_id)

    return _run_operation(patch_set, "class_attr", label, resolve, apply, tolerant=True)


def reload_module(patch_set: PatchSet, name: str | ModuleType) -> PatchHandle:
    """
    在当前补丁计划下用 ``importlib.reload`` 重新执行已导入的模块。

    仅在显式调用时执行, 并记录警告。重新执行不可撤销: 句柄状态为 ``requires_restart``,
    结果原因为 ``stale_references_may_remain``, 因为其他模块中通过 ``from x import y`` 复制的引用、
    已创建的实例和闭包仍指向旧对象。``importlib.reload`` 不会在持有任何 hotpatcher 锁时运行。

    Args:
        patch_set (PatchSet):
            所属补丁集。
        name (str | ModuleType):
            模块名或模块对象。

    Returns:
        PatchHandle:
            状态为 ``requires_restart`` 的句柄; 模块尚未导入时为 ``failed`` (严格模式下抛出)。

    Raises:
        TypeError:
            ``name`` 不是非空字符串或模块对象时抛出。
    """

    module_name = name.__name__ if isinstance(name, ModuleType) else name
    if not isinstance(module_name, str) or not module_name:
        raise TypeError(f"module name must be a non-empty string, got {module_name!r}")
    label = module_name

    def resolve() -> ModuleType:
        module = sys.modules.get(module_name)
        if not isinstance(module, ModuleType):
            raise _unresolved(TargetImportError, f"module {module_name!r} is not imported; reload_module only reloads loaded modules", label, name=module_name)
        return module

    def apply(handle_id: str, module: ModuleType) -> PatchOutcome:
        _LOGGER.warning(
            "Hotpatcher is reloading module %r on request of patch set %r; references copied elsewhere (from-imports, instances, closures) keep the old objects",
            module_name,
            patch_set.name,
        )
        importlib.reload(module)
        patch_set.journal.record_callback(_requires_restart, f"reload:{module_name}", kind="reload", handle_id=handle_id)
        return PatchOutcome.applied(
            reason=RELOAD_REASON,
            detail={
                "module": module_name,
                "caveats": ["references copied with 'from module import name' keep the old objects", "existing instances keep their old classes", "the reload cannot be undone"],
            },
        )

    handle = _run_operation(patch_set, "reload", label, resolve, apply, tolerant=True)
    if handle.status is PatchStatus.APPLIED:
        handle.status = PatchStatus.REQUIRES_RESTART
    return handle


def _requires_restart() -> PatchStatus:
    return PatchStatus.REQUIRES_RESTART


# ---------------------------------------------------------------- 描述符与蹦床实现


def _class_raw(cls: type, name: str) -> Any:
    for klass in cls.__mro__:
        if name in klass.__dict__:
            return klass.__dict__[name]
    return getattr(cls, name)


def _unwrap_member(raw: Any, label: str) -> tuple[str, Any]:
    if isinstance(raw, staticmethod):
        return "staticmethod", raw.__func__
    if isinstance(raw, classmethod):
        return "classmethod", raw.__func__
    if isinstance(raw, property):
        if raw.fget is None:
            raise _unresolved(TargetAttributeError, f"property {label!r} has no getter to wrap", label)
        return "property", raw.fget
    return "plain", raw


def _rewrap_member(member_kind: str, raw: Any, function: Any) -> Any:
    if member_kind == "staticmethod":
        return staticmethod(function)
    if member_kind == "classmethod":
        return classmethod(function)
    if member_kind == "property":
        if isinstance(function, property):
            return function
        return raw.getter(function)
    return function


def _apply_trampoline(
    patch_set: PatchSet,
    handle_id: str,
    owner: Any,
    name: str,
    member_kind: str,
    raw: Any,
    original: Any,
    factory: Callable[[Any], Any],
    rebind_references: bool,
    rebind_limit: int,
    label: str,
) -> Any:
    existing = get_trampoline(original)
    if existing is not None and not existing._owns_slot(owner, name):
        # 其他位置的蹦床 (例如 from-import 复制过来的): 在本位置另建一层, 不修改它的位置。
        existing = None
    if existing is None:
        trampoline_state = Trampoline(original, owner, name)
        received, link = original, None
    else:
        trampoline_state = existing
        received, link = existing._prepare()
    wrapper = factory(received)
    if wrapper is None:
        return None
    if existing is None:
        # 安装本身不写日志: 转发函数永久保留, 卸载只把目标换回原函数。
        setattr(owner, name, _rewrap_member(member_kind, raw, trampoline_state.function))
    rebound: dict[str, Any] | None = None
    if rebind_references:
        # 先于包装层写日志, LIFO 撤销时先移除包装层, 再决定是否把引用恢复为原函数。
        rebound = _rebind_references(patch_set, handle_id, trampoline_state.original, trampoline_state.function, rebind_limit, trampoline_state=trampoline_state)
    layer = trampoline_state._push(handle_id, wrapper, link)

    def remove_layer() -> None:
        trampoline_state._remove(layer)

    patch_set.journal.record_callback(remove_layer, label, kind="trampoline", handle_id=handle_id)
    detail = {"trampoline": True, "layers": trampoline_state.layer_ids}
    if rebound is None:
        return PatchOutcome.applied(reason="trampoline", detail=detail)
    outcome = _rebind_outcome(rebound)
    return PatchOutcome.applied(reason=f"trampoline; {outcome.reason}", detail={**detail, **(outcome.detail or {})})


# ---------------------------------------------------------------- 引用重新绑定


def _check_rebind_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError(f"rebind_limit must be a non-negative int, got {limit!r}")


def _is_hotpatcher_module(module_name: str) -> bool:
    return module_name == _PACKAGE_NAME or module_name.startswith((f"{_PACKAGE_NAME}.", f"{_PACKAGE_NAME}_"))


def _rebind_references(
    patch_set: PatchSet,
    handle_id: str,
    original: Any,
    replacement: Any,
    limit: int,
    *,
    trampoline_state: Trampoline | None = None,
) -> dict[str, Any]:
    rebound: list[str] = []
    truncated = False
    for module_name, module in list(sys.modules.items()):
        if module is None or not isinstance(module, ModuleType) or _is_hotpatcher_module(module_name):
            continue
        namespace = getattr(module, "__dict__", None)
        if not isinstance(namespace, dict):
            continue
        try:
            items = list(namespace.items())
        except RuntimeError:
            continue
        for key, value in items:
            if value is not original:
                continue
            if len(rebound) >= limit:
                truncated = True
                break
            namespace[key] = replacement
            location = f"{module_name}.{key}"
            patch_set.journal.record_callback(
                _rebind_restorer(namespace, key, original, replacement, trampoline_state),
                location,
                kind="rebind",
                handle_id=handle_id,
            )
            rebound.append(location)
        if truncated:
            break
    return {"rebound": rebound, "truncated": truncated, "limit": limit}


def _rebind_restorer(namespace: dict[str, Any], key: str, original: Any, replacement: Any, trampoline_state: Trampoline | None) -> Callable[[], Any]:
    def restore() -> Any:
        if namespace.get(key, NOTSET) is not replacement:
            # 引用已被其他代码改写, 不覆盖, 如实报告需要重启。
            return PatchStatus.REQUIRES_RESTART
        if trampoline_state is not None and trampoline_state.active:
            # 其他包装层仍在使用该蹦床: 引用继续指向稳定的转发函数, 行为已正确。
            return None
        namespace[key] = original
        return None

    return restore


def _rebind_outcome(report: dict[str, Any]) -> PatchOutcome:
    count = len(report["rebound"])
    reason = f"rebound {count} reference(s)"
    if report["truncated"]:
        reason += f" (truncated at {report['limit']})"
    return PatchOutcome.applied(reason=reason, detail=report)
