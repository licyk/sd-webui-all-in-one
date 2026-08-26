"""Implementation grouped from the former ``hotpatcher_manager_gui.py`` module."""

from __future__ import annotations

import json
import tkinter as tk
from typing import Any


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name, {})
    return value if isinstance(value, dict) else {}


def _ensure_section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        value = {}
        config[name] = value
    return value


def _section_by_path(config: dict[str, Any], path: str) -> dict[str, Any]:
    current = config
    for part in path.split("."):
        current = _section(current, part)
        if not current:
            return {}
    return current


def _ensure_section_by_path(config: dict[str, Any], path: str) -> dict[str, Any]:
    current = config
    for part in path.split("."):
        current = _ensure_section(current, part)
    return current


def _value_by_path(config: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = config
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _set_value_by_path(config: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = config
    for part in parts[:-1]:
        current = _ensure_section(current, part)
    current[parts[-1]] = value


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _join_list(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return ""


def _field_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "str"


def _metadata_field_kind(metadata: dict[str, Any], default_value: Any = None) -> str:
    raw_type = str(metadata.get("type", "")).strip().lower()
    if raw_type == "choice":
        return "choice"
    if raw_type == "bool":
        return "bool"
    if raw_type == "int":
        return "int"
    if raw_type in {"list", "list[str]"} or raw_type.startswith("list["):
        return "list"
    if raw_type == "object" or "object" in raw_type:
        return "object"
    if raw_type == "str":
        return "str"
    return _field_kind(default_value)


def _value_to_text(value: Any, kind: str) -> str:
    if kind == "list":
        return _join_list(value)
    if kind in {"json", "object"}:
        if value is None:
            return ""
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return "" if value is None else str(value)


def _variable_to_value(variable: tk.Variable, kind: str, default_value: Any = None) -> Any:
    value = variable.get()
    if kind == "bool":
        return bool(value)
    if kind == "int":
        default_int = default_value if isinstance(default_value, int) and not isinstance(default_value, bool) else 0
        return _to_int(str(value), default_int)
    if kind == "list":
        return _split_list(str(value))
    if kind == "choice":
        return str(value)
    if kind in {"json", "object"}:
        text = str(value).strip()
        if not text:
            return {} if isinstance(default_value, dict) else default_value
        return json.loads(text)
    return str(value)


def _humanize_name(name: str) -> str:
    return name.replace("_", " ").replace(".", " ").title()


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        return default
