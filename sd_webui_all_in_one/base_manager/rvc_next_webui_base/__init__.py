"""Public facade for the rvc_next_webui product manager."""

from sd_webui_all_in_one.base_manager.rvc_next_webui_base.catalog import (
    RVC_NEXT_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_rvc_next_webui_launch_argument_catalog,
    RVC_NEXT_WEBUI_REPO,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.gui import (
    launch_rvc_next_webui_version_gui,
    launch_rvc_next_webui_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.lifecycle import (
    install_rvc_next_webui,
    update_rvc_next_webui,
    check_rvc_next_webui_env,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.reporting import (
    check_rvc_next_webui_updates,
    get_rvc_next_webui_snapshot,
    get_rvc_next_webui_environment_info,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.runtime import (
    prepare_rvc_next_webui_launch,
    launch_rvc_next_webui,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.shared import (
    logger,
)

__all__ = [
    "RVC_NEXT_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY",
    "get_rvc_next_webui_launch_argument_catalog",
    "RVC_NEXT_WEBUI_REPO",
    "launch_rvc_next_webui_version_gui",
    "launch_rvc_next_webui_snapshot_gui",
    "install_rvc_next_webui",
    "update_rvc_next_webui",
    "check_rvc_next_webui_env",
    "check_rvc_next_webui_updates",
    "get_rvc_next_webui_snapshot",
    "get_rvc_next_webui_environment_info",
    "prepare_rvc_next_webui_launch",
    "launch_rvc_next_webui",
    "logger",
]
