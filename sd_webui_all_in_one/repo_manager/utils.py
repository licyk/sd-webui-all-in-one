"""仓库管理通用工具函数"""

import hashlib
import inspect
from pathlib import Path
from typing import Any


def _add_revision(
    kwargs: dict[str, Any],
    revision: str | None,
) -> dict[str, Any]:
    if revision is not None:
        kwargs["revision"] = revision
    return kwargs


def _repo_path_name(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


def _normalize_path_in_repo(path_in_repo: str | None) -> str:
    if path_in_repo is None:
        return ""

    parts = []
    for part in path_in_repo.replace("\\", "/").strip("/").split("/"):
        if part in ["", "."]:
            continue
        if part == "..":
            raise ValueError("仓库路径不能包含 '..'")
        parts.append(part)
    return "/".join(parts)


def _join_repo_path(path_in_repo: str, relative_path: str) -> str:
    if not path_in_repo:
        return relative_path
    return f"{path_in_repo}/{relative_path}"


def _get_mapping_or_attr(
    value: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _get_first_mapping_or_attr(
    value: Any,
    keys: tuple[str, ...],
    default: Any = None,
) -> Any:
    missing = object()
    for key in keys:
        result = _get_mapping_or_attr(value, key, missing)
        if result is not missing:
            return result
    return default


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    attributes = getattr(value, "__dict__", None)
    if attributes is not None:
        return dict(attributes)

    slots = getattr(type(value), "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    return {slot: getattr(value, slot) for slot in slots if hasattr(value, slot)}


def _file_sha256(file_path: Path) -> str:
    hash_sha256 = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def _callable_accepts_keyword(
    func: Any,
    keyword: str,
) -> bool:
    """判断可调用对象是否接受指定关键字参数"""
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return True

    return any(parameter.name == keyword or parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
