"""Product-specific version GUI helpers."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from sd_webui_all_in_one.base_manager.base import get_repo_name_from_url
from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionIndexItem,
)
from sd_webui_all_in_one.file_manager import move_files

COMFYUI_CUSTOM_NODE_INDEX_URL = "https://raw.githubusercontent.com/Comfy-Org/ComfyUI-Manager/refs/heads/main/custom-node-list.json"


def _comfyui_custom_node_enabled(name: str, _path: Path) -> bool:
    return not name.endswith(".disabled")


def _set_comfyui_custom_node_enabled(
    custom_nodes_path: Path,
    name: str,
    enabled: bool,
) -> None:
    name = name.removesuffix(".disabled")
    enabled_path = custom_nodes_path / name
    disabled_path = custom_nodes_path / f"{name}.disabled"
    if enabled:
        if disabled_path.exists() and not enabled_path.exists():
            move_files(disabled_path, enabled_path)
    else:
        if enabled_path.exists() and not disabled_path.exists():
            move_files(enabled_path, disabled_path)


def _download_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or get_repo_name_from_url(url)


def _format_index_tags(item: ExtensionIndexItem) -> str:
    values: list[str] = []
    for tag in item.tags:
        if item.source_type == "comfy-registry" and tag == "Comfy Registry":
            continue
        if tag not in values:
            values.append(tag)
    if item.author and item.author not in values:
        values.append(item.author)
    return ", ".join(values) or "-"
