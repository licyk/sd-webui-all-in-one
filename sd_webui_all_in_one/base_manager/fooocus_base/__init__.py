"""Public facade for the fooocus product manager."""

from sd_webui_all_in_one.base_manager.fooocus_base.catalog import (
    FOOOCUS_LAUNCH_ARGUMENT_PROVIDER_IDENTITY as FOOOCUS_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_fooocus_launch_argument_catalog as get_fooocus_launch_argument_catalog,
    FooocusBranchType as FooocusBranchType,
    FOOOCUS_BRANCH_LIST as FOOOCUS_BRANCH_LIST,
    FooocusBranchInfo as FooocusBranchInfo,
    FOOOCUS_BRANCH_INFO_DICT as FOOOCUS_BRANCH_INFO_DICT,
    get_fooocus_branch_presets as get_fooocus_branch_presets,
    FOOOCUS_PRESET_HF_PATH as FOOOCUS_PRESET_HF_PATH,
    FOOOCUS_PRESET_MS_PATH as FOOOCUS_PRESET_MS_PATH,
    display_fooocus_branch_list as display_fooocus_branch_list,
    switch_fooocus_branch as switch_fooocus_branch,
)
from sd_webui_all_in_one.base_manager.fooocus_base.gui import (
    launch_fooocus_version_gui as launch_fooocus_version_gui,
    launch_fooocus_snapshot_gui as launch_fooocus_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.fooocus_base.lifecycle import (
    FOOOCUS_TRANSLATE_ZH_PATH as FOOOCUS_TRANSLATE_ZH_PATH,
    install_fooocus_config as install_fooocus_config,
    install_fooocus as install_fooocus,
    update_fooocus as update_fooocus,
    check_fooocus_env as check_fooocus_env,
)
from sd_webui_all_in_one.base_manager.fooocus_base.model_management import (
    install_fooocus_model_from_library as install_fooocus_model_from_library,
    install_fooocus_model_from_url as install_fooocus_model_from_url,
    list_fooocus_models as list_fooocus_models,
    uninstall_fooocus_model as uninstall_fooocus_model,
)
from sd_webui_all_in_one.base_manager.fooocus_base.reporting import (
    check_fooocus_updates as check_fooocus_updates,
    get_fooocus_snapshot as get_fooocus_snapshot,
    get_fooocus_environment_info as get_fooocus_environment_info,
)
from sd_webui_all_in_one.base_manager.fooocus_base.runtime import (
    prepare_fooocus_launch as prepare_fooocus_launch,
    launch_fooocus as launch_fooocus,
)
from sd_webui_all_in_one.base_manager.fooocus_base.shared import (
    logger as logger,
)

__all__ = [name for name in globals() if not name.startswith("_")]
