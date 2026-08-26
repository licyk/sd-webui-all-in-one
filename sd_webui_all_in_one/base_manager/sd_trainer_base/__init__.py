"""Public facade for the sd_trainer product manager."""

from sd_webui_all_in_one.base_manager.sd_trainer_base.catalog import (
    SD_TRAINER_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    KOHYA_GUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_sd_trainer_launch_argument_catalog,
    SDTrainerBranchType,
    SD_TRAINER_BRANCH_LIST,
    SDTrainerBranchInfo,
    SD_TRAINER_BRANCH_INFO_DICT,
    get_sd_trainer_branch_presets,
    display_sd_trainer_branch_list,
    switch_sd_trainer_branch,
)
from sd_webui_all_in_one.base_manager.sd_trainer_base.gui import (
    launch_sd_trainer_version_gui,
    launch_sd_trainer_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.sd_trainer_base.lifecycle import (
    install_sd_trainer,
    update_sd_trainer,
    check_sd_trainer_env,
)
from sd_webui_all_in_one.base_manager.sd_trainer_base.model_management import (
    install_sd_trainer_model_from_library,
    install_sd_trainer_model_from_url,
    list_sd_trainer_models,
    uninstall_sd_trainer_model,
)
from sd_webui_all_in_one.base_manager.sd_trainer_base.reporting import (
    check_sd_trainer_updates,
    get_sd_trainer_snapshot,
    get_sd_trainer_environment_info,
)
from sd_webui_all_in_one.base_manager.sd_trainer_base.runtime import (
    prepare_sd_trainer_launch,
    launch_sd_trainer,
)
from sd_webui_all_in_one.base_manager.sd_trainer_base.shared import (
    logger,
)

__all__ = [
    "SD_TRAINER_LAUNCH_ARGUMENT_PROVIDER_IDENTITY",
    "KOHYA_GUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY",
    "get_sd_trainer_launch_argument_catalog",
    "SDTrainerBranchType",
    "SD_TRAINER_BRANCH_LIST",
    "SDTrainerBranchInfo",
    "SD_TRAINER_BRANCH_INFO_DICT",
    "get_sd_trainer_branch_presets",
    "display_sd_trainer_branch_list",
    "switch_sd_trainer_branch",
    "launch_sd_trainer_version_gui",
    "launch_sd_trainer_snapshot_gui",
    "install_sd_trainer",
    "update_sd_trainer",
    "check_sd_trainer_env",
    "install_sd_trainer_model_from_library",
    "install_sd_trainer_model_from_url",
    "list_sd_trainer_models",
    "uninstall_sd_trainer_model",
    "check_sd_trainer_updates",
    "get_sd_trainer_snapshot",
    "get_sd_trainer_environment_info",
    "prepare_sd_trainer_launch",
    "launch_sd_trainer",
    "logger",
]
