"""ComfyUI extension management facade."""

from sd_webui_all_in_one.base_manager.comfyui_base.extensions.catalog import (
    ComfyUiCustomNodeInfo as ComfyUiCustomNodeInfo,
    ComfyUiCustomNodeInfoList as ComfyUiCustomNodeInfoList,
    COMFYUI_CUSTOM_NODES_INFO_DICT as COMFYUI_CUSTOM_NODES_INFO_DICT,
    COMFYUI_CUSTOM_NODE_LIST_PATH as COMFYUI_CUSTOM_NODE_LIST_PATH,
    COMFYUI_CUSTOM_NODE_INDEX_URL as COMFYUI_CUSTOM_NODE_INDEX_URL,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.index import (
    fetch_comfyui_extension_index as fetch_comfyui_extension_index,
    install_comfyui_extension_index_item as install_comfyui_extension_index_item,
    switch_comfyui_registry_extension_version as switch_comfyui_registry_extension_version,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.install import (
    install_comfyui_custom_node as install_comfyui_custom_node,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.local import (
    set_comfyui_custom_node_list_mirror as set_comfyui_custom_node_list_mirror,
    ComfyUiLocalExtensionInfo as ComfyUiLocalExtensionInfo,
    ComfyUiLocalExtensionInfoList as ComfyUiLocalExtensionInfoList,
    resolve_comfyui_custom_node_path as resolve_comfyui_custom_node_path,
    get_comfyui_custom_node_enabled as get_comfyui_custom_node_enabled,
    list_comfyui_custom_nodes as list_comfyui_custom_nodes,
    set_comfyui_custom_node_status as set_comfyui_custom_node_status,
    update_comfyui_custom_nodes as update_comfyui_custom_nodes,
    collect_comfyui_extensions as collect_comfyui_extensions,
    check_comfyui_custom_node_dependencies as check_comfyui_custom_node_dependencies,
    uninstall_comfyui_custom_node as uninstall_comfyui_custom_node,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.manager import (
    ComfyUiExtensionManager as ComfyUiExtensionManager,
)

__all__ = [name for name in globals() if not name.startswith("_")]
