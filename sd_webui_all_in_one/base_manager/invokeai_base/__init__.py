"""Public facade for the invokeai product manager."""

from sd_webui_all_in_one.base_manager.invokeai_base.catalog import (
    INVOKEAI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_invokeai_launch_argument_catalog,
)
from sd_webui_all_in_one.base_manager.invokeai_base.components import (
    get_pytorch_mirror_type_for_ivnokeai,
    get_pytorch_for_invokeai,
    get_xformers_for_invokeai,
    sync_invokeai_component,
    install_invokeai_component,
    install_pypatchmatch,
    reinstall_invokeai_pytorch,
)
from sd_webui_all_in_one.base_manager.invokeai_base.extensions import (
    install_invokeai_custom_nodes,
    install_invokeai_extension_index_item,
    set_invokeai_custom_nodes_status,
    InvokeAILocalExtensionInfo,
    InvokeAILocalExtensionInfoList,
    list_invokeai_custom_nodes,
    update_invokeai_custom_nodes,
    uninstall_invokeai_custom_node,
)
from sd_webui_all_in_one.base_manager.invokeai_base.gui import (
    launch_invokeai_version_gui,
    launch_invokeai_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.invokeai_base.lifecycle import (
    INVOKEAI_RUNNER_SCRIPT,
    get_invokeai_require_torch_version,
    init_invokeai_default_config,
    install_invokeai,
    update_invokeai,
    check_invokeai_env,
)
from sd_webui_all_in_one.base_manager.invokeai_base.model_management import (
    import_model_to_invokeai,
    install_invokeai_model_from_library,
    install_invokeai_model_from_url,
    install_invokeai_model_from_source,
    InvokeAILocalModelInfo,
    InvokeAILocalModelInfoList,
    get_invokeai_model_list,
    list_invokeai_models,
    uninstall_model_from_invokeai,
    uninstall_invokeai_model,
)
from sd_webui_all_in_one.base_manager.invokeai_base.reporting import (
    check_invokeai_updates,
    get_invokeai_snapshot,
    get_invokeai_environment_info,
)
from sd_webui_all_in_one.base_manager.invokeai_base.runtime import (
    prepare_invokeai_launch,
    launch_invokeai,
)
from sd_webui_all_in_one.base_manager.invokeai_base.shared import (
    logger,
)

__all__ = [
    "INVOKEAI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY",
    "get_invokeai_launch_argument_catalog",
    "get_pytorch_mirror_type_for_ivnokeai",
    "get_pytorch_for_invokeai",
    "get_xformers_for_invokeai",
    "sync_invokeai_component",
    "install_invokeai_component",
    "install_pypatchmatch",
    "reinstall_invokeai_pytorch",
    "install_invokeai_custom_nodes",
    "install_invokeai_extension_index_item",
    "set_invokeai_custom_nodes_status",
    "InvokeAILocalExtensionInfo",
    "InvokeAILocalExtensionInfoList",
    "list_invokeai_custom_nodes",
    "update_invokeai_custom_nodes",
    "uninstall_invokeai_custom_node",
    "launch_invokeai_version_gui",
    "launch_invokeai_snapshot_gui",
    "INVOKEAI_RUNNER_SCRIPT",
    "get_invokeai_require_torch_version",
    "init_invokeai_default_config",
    "install_invokeai",
    "update_invokeai",
    "check_invokeai_env",
    "import_model_to_invokeai",
    "install_invokeai_model_from_library",
    "install_invokeai_model_from_url",
    "install_invokeai_model_from_source",
    "InvokeAILocalModelInfo",
    "InvokeAILocalModelInfoList",
    "get_invokeai_model_list",
    "list_invokeai_models",
    "uninstall_model_from_invokeai",
    "uninstall_invokeai_model",
    "check_invokeai_updates",
    "get_invokeai_snapshot",
    "get_invokeai_environment_info",
    "prepare_invokeai_launch",
    "launch_invokeai",
    "logger",
]
