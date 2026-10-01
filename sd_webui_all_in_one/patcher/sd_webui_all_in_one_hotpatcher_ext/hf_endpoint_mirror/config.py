"""Hugging Face 镜像补丁配置入口"""

from __future__ import annotations

from typing import Any

from .patches import apply_mirror


def apply_from_config(config: dict[str, Any] | None = None) -> None:
    """
    根据配置应用镜像补丁

    ``HF_ENDPOINT`` 始终是镜像源的唯一来源。配置只控制是否注册补丁。

    Args:
        config (dict[str, Any] | None):
            扩展配置。传入 ``{"enabled": False}`` 时跳过注册。
    """

    if isinstance(config, dict) and config.get("enabled") is False:
        return
    apply_mirror()
