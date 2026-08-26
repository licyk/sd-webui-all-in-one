"""Comfy Registry service facade."""

from sd_webui_all_in_one.base_manager.comfy_registry.client import (
    logger as logger,
    clear_comfy_registry_cache as clear_comfy_registry_cache,
    fetch_comfy_registry_nodes as fetch_comfy_registry_nodes,
    fetch_all_comfy_registry_nodes as fetch_all_comfy_registry_nodes,
    fetch_comfy_registry_versions as fetch_comfy_registry_versions,
    fetch_comfy_registry_install_info as fetch_comfy_registry_install_info,
)
from sd_webui_all_in_one.base_manager.comfy_registry.index import (
    fetch_comfy_registry_extension_index as fetch_comfy_registry_extension_index,
)
from sd_webui_all_in_one.base_manager.comfy_registry.install import (
    install_comfy_registry_node as install_comfy_registry_node,
    switch_comfy_registry_node_version as switch_comfy_registry_node_version,
)
from sd_webui_all_in_one.base_manager.comfy_registry.local import (
    read_comfy_registry_info as read_comfy_registry_info,
    read_comfy_registry_nightly_id as read_comfy_registry_nightly_id,
)
from sd_webui_all_in_one.base_manager.comfy_registry.models import (
    COMFY_REGISTRY_BASE_URL as COMFY_REGISTRY_BASE_URL,
    COMFY_REGISTRY_ACTIVE_VERSION_STATUSES as COMFY_REGISTRY_ACTIVE_VERSION_STATUSES,
    COMFY_REGISTRY_UNAVAILABLE_STATUS as COMFY_REGISTRY_UNAVAILABLE_STATUS,
    COMFY_REGISTRY_DEFAULT_PAGE_SIZE as COMFY_REGISTRY_DEFAULT_PAGE_SIZE,
    COMFY_REGISTRY_CACHE_TTL_SECONDS as COMFY_REGISTRY_CACHE_TTL_SECONDS,
    ComfyRegistryProgressCallback as ComfyRegistryProgressCallback,
    ComfyRegistryInstallUnavailableError as ComfyRegistryInstallUnavailableError,
    ComfyRegistryNodeVersion as ComfyRegistryNodeVersion,
    ComfyRegistryNode as ComfyRegistryNode,
    ComfyRegistryLocalInfo as ComfyRegistryLocalInfo,
)

__all__ = [name for name in globals() if not name.startswith("_")]
