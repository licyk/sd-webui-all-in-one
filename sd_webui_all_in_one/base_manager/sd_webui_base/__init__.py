"""Public facade for the sd_webui product manager."""

from sd_webui_all_in_one.base_manager.sd_webui_base.catalog import (
    SD_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY as SD_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_sd_webui_launch_argument_catalog as get_sd_webui_launch_argument_catalog,
    SDWebUiBranchType as SDWebUiBranchType,
    SD_WEBUI_BRANCH_LIST as SD_WEBUI_BRANCH_LIST,
    SDWebUiBranchInfo as SDWebUiBranchInfo,
    SD_WEBUI_BRANCH_INFO_DICT as SD_WEBUI_BRANCH_INFO_DICT,
    get_sd_webui_branch_presets as get_sd_webui_branch_presets,
    SD_WEBUI_CONFIG_PATH as SD_WEBUI_CONFIG_PATH,
    display_sd_webui_branch_list as display_sd_webui_branch_list,
    switch_sd_webui_branch as switch_sd_webui_branch,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.extensions import (
    SDWebUiExtensionInfo as SDWebUiExtensionInfo,
    SDWebUiExtensionInfoList as SDWebUiExtensionInfoList,
    SD_WEBUI_EXTENSION_INFO_DICT as SD_WEBUI_EXTENSION_INFO_DICT,
    fetch_sd_webui_extension_index as fetch_sd_webui_extension_index,
    install_sd_webui_extension_index_item as install_sd_webui_extension_index_item,
    set_sd_webui_extension_download_list_mirror as set_sd_webui_extension_download_list_mirror,
    install_sd_webui_extension as install_sd_webui_extension,
    SDWebUiLocalExtensionInfo as SDWebUiLocalExtensionInfo,
    SDWebUiLocalExtensionInfoList as SDWebUiLocalExtensionInfoList,
    set_sd_webui_extensions_status as set_sd_webui_extensions_status,
    list_sd_webui_extensions as list_sd_webui_extensions,
    update_sd_webui_extensions as update_sd_webui_extensions,
    uninstall_sd_webui_extension as uninstall_sd_webui_extension,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.gui import (
    launch_sd_webui_version_gui as launch_sd_webui_version_gui,
    launch_sd_webui_snapshot_gui as launch_sd_webui_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.lifecycle import (
    SD_WEBUI_REPOSITORY_INFO_DICT as SD_WEBUI_REPOSITORY_INFO_DICT,
    install_sd_webui_config as install_sd_webui_config,
    install_clip_package as install_clip_package,
    install_sd_webui as install_sd_webui,
    update_sd_webui as update_sd_webui,
    check_sd_webui_env as check_sd_webui_env,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.model_management import (
    install_sd_webui_model_from_library as install_sd_webui_model_from_library,
    install_sd_webui_model_from_url as install_sd_webui_model_from_url,
    list_sd_webui_models as list_sd_webui_models,
    uninstall_sd_webui_model as uninstall_sd_webui_model,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.reporting import (
    check_sd_webui_updates as check_sd_webui_updates,
    get_sd_webui_snapshot as get_sd_webui_snapshot,
    get_sd_webui_environment_info as get_sd_webui_environment_info,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.runtime import (
    prepare_sd_webui_launch as prepare_sd_webui_launch,
    launch_sd_webui as launch_sd_webui,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.shared import (
    logger as logger,
)

__all__ = [name for name in globals() if not name.startswith("_")]
