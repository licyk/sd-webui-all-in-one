"""ComfyUI extension management facade."""

from sd_webui_all_in_one.base_manager.comfyui_base.extensions.catalog import (
    ComfyUiCustomNodeInfo,
    ComfyUiCustomNodeInfoList,
    COMFYUI_CUSTOM_NODES_INFO_DICT,
    COMFYUI_CUSTOM_NODE_LIST_PATH,
    COMFYUI_CUSTOM_NODE_INDEX_URL,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.index import (
    fetch_comfyui_extension_index,
    install_comfyui_extension_index_item,
    switch_comfyui_registry_extension_version,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.install import (
    install_comfyui_custom_node,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.local import (
    set_comfyui_custom_node_list_mirror,
    ComfyUiLocalExtensionInfo,
    ComfyUiLocalExtensionInfoList,
    resolve_comfyui_custom_node_path,
    get_comfyui_custom_node_enabled,
    list_comfyui_custom_nodes,
    set_comfyui_custom_node_status,
    update_comfyui_custom_nodes,
    collect_comfyui_extensions,
    check_comfyui_custom_node_dependencies,
    uninstall_comfyui_custom_node,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.manager import (
    ComfyUiExtensionManager,
)

__all__ = [
    "ComfyUiCustomNodeInfo",
    "ComfyUiCustomNodeInfoList",
    "COMFYUI_CUSTOM_NODES_INFO_DICT",
    "COMFYUI_CUSTOM_NODE_LIST_PATH",
    "COMFYUI_CUSTOM_NODE_INDEX_URL",
    "fetch_comfyui_extension_index",
    "install_comfyui_extension_index_item",
    "switch_comfyui_registry_extension_version",
    "install_comfyui_custom_node",
    "set_comfyui_custom_node_list_mirror",
    "ComfyUiLocalExtensionInfo",
    "ComfyUiLocalExtensionInfoList",
    "resolve_comfyui_custom_node_path",
    "get_comfyui_custom_node_enabled",
    "list_comfyui_custom_nodes",
    "set_comfyui_custom_node_status",
    "update_comfyui_custom_nodes",
    "collect_comfyui_extensions",
    "check_comfyui_custom_node_dependencies",
    "uninstall_comfyui_custom_node",
    "ComfyUiExtensionManager",
]
