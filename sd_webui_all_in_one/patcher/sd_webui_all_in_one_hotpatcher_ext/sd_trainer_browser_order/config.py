"""SD Trainer 浏览器打开顺序补丁配置入口"""

from __future__ import annotations

from typing import Any

from .patches import patch_sd_trainer_browser_order
from .replay import DEFAULT_MONITOR_DELAY


def apply_from_config(config: dict[str, Any] | None) -> None:
    """根据扩展配置注册 SD Trainer 浏览器打开顺序补丁。

    Args:
        config (dict[str, Any] | None):
            扩展配置。
    """

    if config and config.get("enabled"):
        patch_sd_trainer_browser_order(_coerce_delay(config.get("monitor_delay", DEFAULT_MONITOR_DELAY)))


def _coerce_delay(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return DEFAULT_MONITOR_DELAY
