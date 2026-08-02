"""宿主通信 JSON Lines 协议工具"""

from __future__ import annotations

import json
import uuid
from typing import Any

PROTOCOL_VERSION = 1


class RuntimeProtocolError(Exception):
    """运行时协议错误"""

    pass


class RuntimeTransportError(RuntimeProtocolError):
    """运行时传输错误"""

    pass


class RuntimeRequestError(RuntimeProtocolError):
    """
    宿主请求失败错误

    Attributes:
        code (str):
            宿主返回的错误码
        message (str):
            宿主返回的错误信息
        payload (dict[str, Any]):
            原始错误对象
    """

    def __init__(self, code: str, message: str = "", payload: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"{code}: {message}" if message else code)


def make_message_id() -> str:
    """
    生成请求消息 ID

    Returns:
        str:
            十六进制 UUID 字符串
    """

    return uuid.uuid4().hex


def encode_message(message: dict[str, Any]) -> bytes:
    """
    编码 JSONL 消息

    Args:
        message (dict[str, Any]):
            消息对象

    Returns:
        bytes:
            UTF-8 编码且以换行结束的 JSONL 数据
    """

    return (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(line: bytes | str) -> dict[str, Any]:
    """
    解码 JSONL 消息

    Args:
        line (bytes | str):
            单行 JSONL 数据

    Returns:
        dict[str, Any]:
            解码后的消息对象

    Raises:
        RuntimeProtocolError:
            消息不是合法 JSON 或不是对象
    """

    if isinstance(line, bytes):
        line = line.decode("utf-8")
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise RuntimeProtocolError(f"Invalid JSONL message: {exc}") from exc
    if not isinstance(message, dict):
        raise RuntimeProtocolError("JSONL message must be an object")
    return message


def hello_message(token: str | None, features: list[str] | None = None) -> dict[str, Any]:
    """
    构造握手消息

    Args:
        token (str | None):
            宿主认证 token
        features (list[str] | None):
            客户端声明的能力列表

    Returns:
        dict[str, Any]:
            hello 消息对象
    """

    return {
        "type": "hello",
        "version": PROTOCOL_VERSION,
        "token": token or "",
        "features": features or [],
    }


def request_message(message_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    构造请求消息

    Args:
        message_type (str):
            请求类型
        payload (dict[str, Any] | None):
            请求载荷

    Returns:
        dict[str, Any]:
            带 ID 的请求消息对象
    """

    return {
        "id": make_message_id(),
        "type": message_type,
        "payload": payload or {},
    }


def event_message(message_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    构造事件消息

    Args:
        message_type (str):
            事件类型
        payload (dict[str, Any] | None):
            事件载荷

    Returns:
        dict[str, Any]:
            事件消息对象
    """

    return {
        "type": message_type,
        "payload": payload or {},
    }
