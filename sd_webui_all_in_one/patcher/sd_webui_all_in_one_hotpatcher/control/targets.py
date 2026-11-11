"""补丁目标路径解析。

支持两种写法:

- 显式写法 ``"pkg.mod:Obj.attr"``: 冒号前是模块, 冒号后是属性链, 没有歧义。
- 点分写法 ``"pkg.mod.Obj.attr"``: 与 pytest ``monkeypatch`` 相同, 从第一段模块开始,
  每段先尝试 ``getattr``, 失败且当前对象是模块时再尝试导入同名子模块。

解析在调用线程中直接执行 import, 调用方不得在持有 ``control_lock`` 时调用。
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

__all__ = [
    "TargetAttributeError",
    "TargetError",
    "TargetImportError",
    "TargetSyntaxError",
    "describe_target",
    "parse_target",
    "resolve_target",
    "split_target",
]


class TargetError(Exception):
    """
    目标路径解析错误的公共基类。

    Attributes:
        target (str):
            正在解析的完整目标路径。
    """

    target: str = ""


class TargetSyntaxError(TargetError, ValueError):
    """目标路径格式错误。"""


class TargetImportError(TargetError, ImportError):
    """目标路径中的模块不存在或导入失败。"""


class TargetAttributeError(TargetError, AttributeError):
    """目标路径中的属性不存在。"""


def parse_target(path: str) -> tuple[str, tuple[str, ...], bool]:
    """
    解析目标路径字符串, 不执行导入。

    Args:
        path (str):
            ``"pkg.mod:Obj.attr"`` 或 ``"pkg.mod.Obj.attr"`` 形式的路径。

    Returns:
        tuple[str, tuple[str, ...], bool]:
            ``(模块名, 属性链, 是否为冒号写法)``。点分写法时模块名为第一段, 其余段放入属性链。

    Raises:
        TargetSyntaxError:
            路径为空、包含多个冒号或存在非法段时抛出。
    """

    if not isinstance(path, str) or not path.strip():
        raise _target_error(TargetSyntaxError, f"target must be a non-empty string, got {path!r}", path if isinstance(path, str) else repr(path))
    if path.count(":") > 1:
        raise _target_error(TargetSyntaxError, f"target {path!r} contains more than one ':'", path)
    if ":" in path:
        module_name, _, attr_path = path.partition(":")
        module_parts = module_name.split(".")
        attrs = tuple(attr_path.split(".")) if attr_path else ()
        _validate_segments(path, module_parts)
        if not attr_path:
            raise _target_error(TargetSyntaxError, f"target {path!r} has an empty attribute path after ':'", path)
        _validate_segments(path, attrs)
        return module_name, attrs, True
    parts = path.split(".")
    _validate_segments(path, parts)
    return parts[0], tuple(parts[1:]), False


def resolve_target(path: str) -> Any:
    """
    解析目标路径并返回对象。

    Args:
        path (str):
            ``"pkg.mod:Obj.attr"`` 或 ``"pkg.mod.Obj.attr"`` 形式的路径。点分写法只有一段时返回该模块。

    Returns:
        Any:
            解析得到的对象。

    Raises:
        TargetSyntaxError:
            路径格式错误时抛出。
        TargetImportError:
            模块不存在或导入失败时抛出。
        TargetAttributeError:
            属性不存在时抛出。
    """

    module_name, attrs, explicit = parse_target(path)
    return _resolve(path, module_name, attrs, explicit)


def split_target(path: str, *, raising: bool = False) -> tuple[Any, str]:
    """
    把目标路径拆分为 ``(所属对象, 属性名)``。

    冒号写法 ``"pkg.mod:Obj.attr"`` 返回 ``(Obj, "attr")``; 点分写法 ``"pkg.mod.attr"`` 返回
    ``(pkg.mod, "attr")``。

    Args:
        path (str):
            目标路径, 至少包含一个属性段。
        raising (bool):
            为 True 时要求属性当前存在。

    Returns:
        tuple[Any, str]:
            所属对象和最后一段属性名。

    Raises:
        TargetSyntaxError:
            路径格式错误或缺少属性段时抛出。
        TargetImportError:
            模块不存在或导入失败时抛出。
        TargetAttributeError:
            所属对象不存在, 或 ``raising`` 为 True 且属性不存在时抛出。
    """

    module_name, attrs, explicit = parse_target(path)
    if not attrs:
        raise _target_error(TargetSyntaxError, f"target {path!r} must name an attribute, e.g. 'pkg.mod:attr'", path)
    owner = _resolve(path, module_name, attrs[:-1], explicit)
    name = attrs[-1]
    if raising and not hasattr(owner, name):
        raise _target_error(TargetAttributeError, f"{describe_target(owner)} has no attribute {name!r} (resolving {path!r})", path)
    return owner, name


def describe_target(obj: Any, name: str | None = None) -> str:
    """
    生成面向调试的对象描述。

    Args:
        obj (Any):
            模块、类、函数或实例。
        name (str | None):
            可选属性名, 会追加为 ``.name``。

    Returns:
        str:
            模块返回模块名, 类和函数返回 ``module.qualname``, 其他实例返回 ``<Type object>``。
    """

    if isinstance(obj, ModuleType):
        text = obj.__name__
    elif isinstance(obj, type) or (callable(obj) and hasattr(obj, "__qualname__")):
        module = getattr(obj, "__module__", None)
        qualname = getattr(obj, "__qualname__", None) or getattr(obj, "__name__", type(obj).__name__)
        text = f"{module}.{qualname}" if module else str(qualname)
    else:
        text = f"<{type(obj).__qualname__} object>"
    return f"{text}.{name}" if name is not None else text


def _validate_segments(path: str, parts: tuple[str, ...] | list[str]) -> None:
    for part in parts:
        if not part.isidentifier():
            raise _target_error(TargetSyntaxError, f"target {path!r} has an invalid segment {part!r}", path)


def _resolve(path: str, module_name: str, attrs: tuple[str, ...], explicit: bool) -> Any:
    found: Any = _import_module(path, module_name)
    used = module_name
    separator = ":" if explicit else "."
    for attr in attrs:
        found = _step(path, found, attr, used)
        used = f"{used}{separator}{attr}"
        separator = "."
    return found


def _import_module(path: str, module_name: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if missing and (module_name == missing or module_name.startswith(f"{missing}.")):
            raise _target_error(TargetImportError, f"module {missing!r} not found (resolving {path!r})", path, name=module_name) from exc
        raise _target_error(TargetImportError, f"import error in {module_name!r} (resolving {path!r}): {exc}", path, name=module_name) from exc
    except ImportError as exc:
        raise _target_error(TargetImportError, f"import error in {module_name!r} (resolving {path!r}): {exc}", path, name=module_name) from exc


def _step(path: str, found: Any, attr: str, used: str) -> Any:
    try:
        return getattr(found, attr)
    except AttributeError:
        pass
    if not isinstance(found, ModuleType):
        raise _target_error(TargetAttributeError, f"{describe_target(found)} at {used!r} has no attribute {attr!r} (resolving {path!r})", path)
    submodule = f"{found.__name__}.{attr}"
    try:
        return importlib.import_module(submodule)
    except ModuleNotFoundError as exc:
        if exc.name != submodule:
            raise _target_error(TargetImportError, f"import error in {submodule!r} (resolving {path!r}): {exc}", path, name=submodule) from exc
    except ImportError as exc:
        raise _target_error(TargetImportError, f"import error in {submodule!r} (resolving {path!r}): {exc}", path, name=submodule) from exc
    raise _target_error(TargetAttributeError, f"module {used!r} has no attribute or importable submodule {attr!r} (resolving {path!r})", path)


def _target_error(error_type: type[TargetError], message: str, path: str, **kwargs: Any) -> TargetError:
    error = error_type(message, **kwargs)
    error.target = path
    return error
