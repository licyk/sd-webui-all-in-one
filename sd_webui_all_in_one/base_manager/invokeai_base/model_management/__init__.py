"""InvokeAI model management facade."""

from sd_webui_all_in_one.base_manager.invokeai_base.model_management.importers import (
    import_model_to_invokeai,
    install_invokeai_model_from_library,
    install_invokeai_model_from_url,
    install_invokeai_model_from_source,
)
from sd_webui_all_in_one.base_manager.invokeai_base.model_management.registry import (
    InvokeAILocalModelInfo,
    InvokeAILocalModelInfoList,
    get_invokeai_model_list,
    list_invokeai_models,
    uninstall_model_from_invokeai,
    uninstall_invokeai_model,
)

__all__ = [
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
]
