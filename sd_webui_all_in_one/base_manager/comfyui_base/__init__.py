"""Public facade for the comfyui product manager."""

from sd_webui_all_in_one.base_manager.comfyui_base.catalog import (
    COMFYUI_REPO_URL as COMFYUI_REPO_URL,
    COMFYUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY as COMFYUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    COMFYUI_CONFIG_PATH as COMFYUI_CONFIG_PATH,
    get_comfyui_launch_argument_catalog as get_comfyui_launch_argument_catalog,
)
from sd_webui_all_in_one.base_manager.comfyui_base.extensions import (
    ComfyUiCustomNodeInfo as ComfyUiCustomNodeInfo,
    ComfyUiCustomNodeInfoList as ComfyUiCustomNodeInfoList,
    COMFYUI_CUSTOM_NODES_INFO_DICT as COMFYUI_CUSTOM_NODES_INFO_DICT,
    COMFYUI_CUSTOM_NODE_LIST_PATH as COMFYUI_CUSTOM_NODE_LIST_PATH,
    COMFYUI_CUSTOM_NODE_INDEX_URL as COMFYUI_CUSTOM_NODE_INDEX_URL,
    fetch_comfyui_extension_index as fetch_comfyui_extension_index,
    install_comfyui_extension_index_item as install_comfyui_extension_index_item,
    switch_comfyui_registry_extension_version as switch_comfyui_registry_extension_version,
    install_comfyui_custom_node as install_comfyui_custom_node,
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
    ComfyUiExtensionManager as ComfyUiExtensionManager,
)
from sd_webui_all_in_one.base_manager.comfyui_base.gui import (
    launch_comfyui_version_gui as launch_comfyui_version_gui,
    launch_comfyui_snapshot_gui as launch_comfyui_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.comfyui_base.lifecycle import (
    install_comfyui_config as install_comfyui_config,
    install_comfyui as install_comfyui,
    update_comfyui as update_comfyui,
    check_comfyui_env as check_comfyui_env,
)
from sd_webui_all_in_one.base_manager.comfyui_base.model_management import (
    install_comfyui_model_from_library as install_comfyui_model_from_library,
    install_comfyui_model_from_url as install_comfyui_model_from_url,
    list_comfyui_models as list_comfyui_models,
    uninstall_comfyui_model as uninstall_comfyui_model,
)
from sd_webui_all_in_one.base_manager.comfyui_base.reporting import (
    check_comfyui_updates as check_comfyui_updates,
    get_comfyui_snapshot as get_comfyui_snapshot,
    get_comfyui_environment_info as get_comfyui_environment_info,
)
from sd_webui_all_in_one.base_manager.comfyui_base.runtime import (
    prepare_comfyui_launch as prepare_comfyui_launch,
    launch_comfyui as launch_comfyui,
)
from sd_webui_all_in_one.base_manager.comfyui_base.shared import (
    logger as logger,
)

__all__ = [name for name in globals() if not name.startswith("_")]
