"""集中管理热补丁运行时传输选择。"""

from __future__ import annotations

import os
from collections.abc import Mapping
from enum import Enum

TRANSPORT_MODE_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRANSPORT_MODE"


class TransportMode(str, Enum):
    """支持的运行时传输实现。"""

    LEGACY = "legacy"
    DESKTOP_BROKER = "desktop_broker"


def resolve_transport_mode(environ: Mapping[str, str] | None = None) -> TransportMode:
    """解析配置的传输模式且不接受别名。

    缺失或完全为空的值保留旧版 TCP JSONL 默认值。值区分大小写且不规范化
    空白，避免部署错误静默选择另一种传输。

    Args:
        environ (Mapping[str, str] | None): 可选环境变量映射。

    Returns:
        TransportMode: 解析后的传输模式。

    Raises:
        ValueError: 配置的传输模式无效时抛出。
    """

    source = os.environ if environ is None else environ
    value = source.get(TRANSPORT_MODE_ENV)
    if value is None or value == "":
        return TransportMode.LEGACY
    try:
        return TransportMode(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {TRANSPORT_MODE_ENV} value {value!r}; supported values: legacy, desktop_broker") from exc


__all__ = ["TRANSPORT_MODE_ENV", "TransportMode", "resolve_transport_mode"]
