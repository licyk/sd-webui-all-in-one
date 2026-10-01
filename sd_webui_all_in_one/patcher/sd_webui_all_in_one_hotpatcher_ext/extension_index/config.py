"""扩展索引镜像补丁配置入口"""

from __future__ import annotations

from typing import Any

from .constants import A1111_EXTENSION_INDEX_AUTO, COMFYUI_MANAGER_RAW_PREFIX
from .mirror import resolve_a1111_extension_index_url
from .patches import patch_extension_index_a1111, patch_extension_index_comfyui_manager


def apply_from_config(config: dict[str, Any] | None) -> None:
    """
    根据配置应用扩展索引补丁

    支持以下配置形式:

    ``{"webui": {"enabled": true, "url": "https://mirror/index.json"}}``
        启用 A1111 扩展索引替换。

    ``{"webui": {"enabled": true, "url": "auto"}}``
        自动检测网络, 需要时使用可用 GitHub raw 镜像。

    ``{"comfyui_manager": {"enabled": true, "url": "auto"}}``
        自动检测网络, 需要时使用可用 GitHub raw 镜像。

    ``{"comfyui_manager": {"enabled": true, "url": "https://mirror/channel"}}``
        使用自定义 ComfyUI-Manager channel 前缀。

    ``{"comfyui_manager": {"enabled": true, "url": "...", "source_prefix": "..."}}``
        使用自定义前缀启用 ComfyUI-Manager 替换。未设置 ``url`` 时按 ``auto`` 处理。

    Args:
        config (dict[str, Any] | None):
            扩展配置
    """

    if not config:
        return

    webui_config = config.get("webui")
    if isinstance(webui_config, dict) and webui_config.get("enabled"):
        resolved_extension_index_url = resolve_a1111_extension_index_url(str(webui_config.get("url") or A1111_EXTENSION_INDEX_AUTO))
        if resolved_extension_index_url:
            patch_extension_index_a1111(resolved_extension_index_url)

    comfyui_config = config.get("comfyui_manager")
    if isinstance(comfyui_config, dict) and comfyui_config.get("enabled"):
        patch_extension_index_comfyui_manager(
            str(comfyui_config.get("url") or A1111_EXTENSION_INDEX_AUTO),
            source_prefix=str(comfyui_config.get("source_prefix", COMFYUI_MANAGER_RAW_PREFIX)),
        )
