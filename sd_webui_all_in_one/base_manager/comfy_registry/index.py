"""Implementation grouped from the former ``comfy_registry.py`` module."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sd_webui_all_in_one.base_manager.version_manager import ExtensionIndexItem

from .client import fetch_all_comfy_registry_nodes
from .models import COMFY_REGISTRY_DEFAULT_PAGE_SIZE, COMFY_REGISTRY_UNAVAILABLE_STATUS, ComfyRegistryProgressCallback


def fetch_comfy_registry_extension_index(
    search: str | None = None,
    limit: int | None = None,
    page_size: int = COMFY_REGISTRY_DEFAULT_PAGE_SIZE,
    force_refresh: bool = False,
    progress_callback: ComfyRegistryProgressCallback | None = None,
) -> list[ExtensionIndexItem]:
    """获取 Registry 节点并转换为扩展源条目。

    Args:
        search (str | None):
            搜索关键字，未指定时返回默认列表。
        limit (int | None):
            最多返回节点数量，未指定时读取全部节点。
        page_size (int):
            Registry 分页读取的单页数量。
        force_refresh (bool):
            是否忽略内存缓存并重新请求 Registry。
        progress_callback (ComfyRegistryProgressCallback | None):
            Registry 分页加载进度回调。

    Returns:
        list[ExtensionIndexItem]:
            `ExtensionIndexItem` 列表。
    """
    from sd_webui_all_in_one.base_manager.version_manager import ExtensionIndexItem

    items: list[ExtensionIndexItem] = []
    for node in fetch_all_comfy_registry_nodes(search=search, page_size=page_size, max_items=limit, force_refresh=force_refresh, progress_callback=progress_callback):
        version = node.latest_version.version if node.latest_version else ""
        download_url = node.latest_version.download_url if node.latest_version else ""
        dependencies = tuple(node.latest_version.dependencies) if node.latest_version else ()
        installable = bool(version)
        install_status = "可安装" if installable else COMFY_REGISTRY_UNAVAILABLE_STATUS
        items.append(
            ExtensionIndexItem(
                name=node.name,
                url=node.repository or download_url or node.id,
                description=node.description,
                tags=(*node.tags, "Comfy Registry"),
                install_type="comfy-registry",
                files=(),
                reference=node.repository,
                source_type="comfy-registry",
                registry_id=node.id,
                registry_version=version,
                repository=node.repository,
                download_url=download_url,
                dependencies=dependencies,
                author=node.author,
                installable=installable,
                install_status=install_status,
            )
        )
    return items
