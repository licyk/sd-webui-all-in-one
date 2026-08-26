"""Comfy Registry service facade."""

from sd_webui_all_in_one.base_manager.comfy_registry.client import (
    logger,
    clear_comfy_registry_cache,
    fetch_comfy_registry_nodes,
    fetch_all_comfy_registry_nodes,
    fetch_comfy_registry_versions,
    fetch_comfy_registry_install_info,
)
from sd_webui_all_in_one.base_manager.comfy_registry.index import (
    fetch_comfy_registry_extension_index,
)
from sd_webui_all_in_one.base_manager.comfy_registry.install import (
    install_comfy_registry_node,
    switch_comfy_registry_node_version,
)
from sd_webui_all_in_one.base_manager.comfy_registry.local import (
    read_comfy_registry_info,
    read_comfy_registry_nightly_id,
)
from sd_webui_all_in_one.base_manager.comfy_registry.models import (
    COMFY_REGISTRY_BASE_URL,
    COMFY_REGISTRY_ACTIVE_VERSION_STATUSES,
    COMFY_REGISTRY_UNAVAILABLE_STATUS,
    COMFY_REGISTRY_DEFAULT_PAGE_SIZE,
    COMFY_REGISTRY_CACHE_TTL_SECONDS,
    ComfyRegistryProgressCallback,
    ComfyRegistryInstallUnavailableError,
    ComfyRegistryNodeVersion,
    ComfyRegistryNode,
    ComfyRegistryLocalInfo,
)

__all__ = [
    "logger",
    "clear_comfy_registry_cache",
    "fetch_comfy_registry_nodes",
    "fetch_all_comfy_registry_nodes",
    "fetch_comfy_registry_versions",
    "fetch_comfy_registry_install_info",
    "fetch_comfy_registry_extension_index",
    "install_comfy_registry_node",
    "switch_comfy_registry_node_version",
    "read_comfy_registry_info",
    "read_comfy_registry_nightly_id",
    "COMFY_REGISTRY_BASE_URL",
    "COMFY_REGISTRY_ACTIVE_VERSION_STATUSES",
    "COMFY_REGISTRY_UNAVAILABLE_STATUS",
    "COMFY_REGISTRY_DEFAULT_PAGE_SIZE",
    "COMFY_REGISTRY_CACHE_TTL_SECONDS",
    "ComfyRegistryProgressCallback",
    "ComfyRegistryInstallUnavailableError",
    "ComfyRegistryNodeVersion",
    "ComfyRegistryNode",
    "ComfyRegistryLocalInfo",
]
