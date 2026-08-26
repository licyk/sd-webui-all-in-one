"""WebUI model-management facade."""

from sd_webui_all_in_one.base_manager.model_manager.files import (
    FileModelManager,
)
from sd_webui_all_in_one.base_manager.model_manager.gui import (
    launch_model_manager_gui,
    launch_sd_webui_model_manager_gui,
    launch_comfyui_model_manager_gui,
    launch_fooocus_model_manager_gui,
    launch_sd_trainer_model_manager_gui,
    launch_sd_scripts_model_manager_gui,
    launch_invokeai_model_manager_gui,
)
from sd_webui_all_in_one.base_manager.model_manager.invokeai import (
    InvokeAIModelManager,
)
from sd_webui_all_in_one.base_manager.model_manager.models import (
    logger,
    WebUiModelType,
    FileWebUiModelType,
    FILE_MODEL_ROOT_DIRS,
    WEBUI_MODEL_TITLES,
    ModelRoot,
    ModelEntry,
)

__all__ = [
    "FileModelManager",
    "launch_model_manager_gui",
    "launch_sd_webui_model_manager_gui",
    "launch_comfyui_model_manager_gui",
    "launch_fooocus_model_manager_gui",
    "launch_sd_trainer_model_manager_gui",
    "launch_sd_scripts_model_manager_gui",
    "launch_invokeai_model_manager_gui",
    "InvokeAIModelManager",
    "logger",
    "WebUiModelType",
    "FileWebUiModelType",
    "FILE_MODEL_ROOT_DIRS",
    "WEBUI_MODEL_TITLES",
    "ModelRoot",
    "ModelEntry",
]
