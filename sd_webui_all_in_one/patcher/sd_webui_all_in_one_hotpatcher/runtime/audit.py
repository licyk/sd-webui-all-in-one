"""Python audit hook 上报工具"""

from __future__ import annotations

import base64
import sys
import types
from typing import Any

from .client import RuntimeClient


def install_audit_hook(client: RuntimeClient, filters: set[str] | list[str] | tuple[str, ...]) -> None:
    """
    安装 Python audit hook

    Args:
        client (RuntimeClient):
            发送 audit 事件的运行时客户端
        filters (set[str] | list[str] | tuple[str, ...]):
            允许上报的 audit 事件名集合
    """

    filter_set = set(filters)

    def audit_hook(event: str, args: tuple[Any, ...]) -> None:
        if event not in filter_set:
            return
        client.event(
            "audit.event",
            {
                "event": event,
                "args": [_json_safe(arg) for arg in args],
            },
        )

    sys.addaudithook(audit_hook)


def extract_strings(code_obj: types.CodeType) -> list[str]:
    """
    提取 code object 中的字符串常量

    Args:
        code_obj (types.CodeType):
            需要扫描的 code object

    Returns:
        list[str]:
            去重排序后的字符串常量列表
    """

    strings: set[str] = set()
    stack = [code_obj]
    while stack:
        code = stack.pop()
        for const in code.co_consts:
            if isinstance(const, str):
                strings.add(const)
            elif isinstance(const, types.CodeType):
                stack.append(const)
    return sorted(strings)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"type": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, types.CodeType):
        return {
            "type": "code",
            "name": value.co_name,
            "filename": value.co_filename,
            "strings": extract_strings(value),
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return {"type": type(value).__name__, "repr": repr(value)}
