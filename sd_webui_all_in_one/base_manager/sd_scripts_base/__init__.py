"""Public facade for the sd_scripts product manager."""

from sd_webui_all_in_one.base_manager.sd_scripts_base.catalog import (
    SDScriptsBranchType,
    SD_SCRIPTS_BRANCH_LIST,
    SDScriptsBranchInfo,
    SD_SCRIPTS_BRANCH_INFO_DICT,
    display_sd_scripts_branch_list,
    switch_sd_scripts_branch,
)
from sd_webui_all_in_one.base_manager.sd_scripts_base.gui import (
    launch_sd_scripts_version_gui,
    launch_sd_scripts_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.sd_scripts_base.lifecycle import (
    export_requirements_from_toml_config,
    install_sd_scripts,
    update_sd_scripts,
    check_sd_scripts_env,
)
from sd_webui_all_in_one.base_manager.sd_scripts_base.model_management import (
    install_sd_scripts_model_from_library,
    install_sd_scripts_model_from_url,
    list_sd_scripts_models,
    uninstall_sd_scripts_model,
)
from sd_webui_all_in_one.base_manager.sd_scripts_base.reporting import (
    check_sd_scripts_updates,
    get_sd_scripts_snapshot,
    get_sd_scripts_environment_info,
)
from sd_webui_all_in_one.base_manager.sd_scripts_base.shared import (
    logger,
)

__all__ = [
    "SDScriptsBranchType",
    "SD_SCRIPTS_BRANCH_LIST",
    "SDScriptsBranchInfo",
    "SD_SCRIPTS_BRANCH_INFO_DICT",
    "display_sd_scripts_branch_list",
    "switch_sd_scripts_branch",
    "launch_sd_scripts_version_gui",
    "launch_sd_scripts_snapshot_gui",
    "export_requirements_from_toml_config",
    "install_sd_scripts",
    "update_sd_scripts",
    "check_sd_scripts_env",
    "install_sd_scripts_model_from_library",
    "install_sd_scripts_model_from_url",
    "list_sd_scripts_models",
    "uninstall_sd_scripts_model",
    "check_sd_scripts_updates",
    "get_sd_scripts_snapshot",
    "get_sd_scripts_environment_info",
    "logger",
]
