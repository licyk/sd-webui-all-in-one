"""Public facade for the mizuoto_tts_webui product manager."""

from sd_webui_all_in_one.base_manager.mizuoto_tts_webui_base.catalog import (
    MIZUOTO_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_mizuoto_tts_webui_launch_argument_catalog,
    MIZUOTO_TTS_WEBUI_REPO,
)
from sd_webui_all_in_one.base_manager.mizuoto_tts_webui_base.gui import (
    launch_mizuoto_tts_webui_version_gui,
    launch_mizuoto_tts_webui_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.mizuoto_tts_webui_base.lifecycle import (
    install_mizuoto_tts_webui,
    update_mizuoto_tts_webui,
    check_mizuoto_tts_webui_env,
)
from sd_webui_all_in_one.base_manager.mizuoto_tts_webui_base.reporting import (
    check_mizuoto_tts_webui_updates,
    get_mizuoto_tts_webui_snapshot,
    get_mizuoto_tts_webui_environment_info,
)
from sd_webui_all_in_one.base_manager.mizuoto_tts_webui_base.runtime import (
    prepare_mizuoto_tts_webui_launch,
    launch_mizuoto_tts_webui,
)
from sd_webui_all_in_one.base_manager.mizuoto_tts_webui_base.shared import (
    logger,
)

__all__ = [
    "MIZUOTO_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY",
    "get_mizuoto_tts_webui_launch_argument_catalog",
    "MIZUOTO_TTS_WEBUI_REPO",
    "launch_mizuoto_tts_webui_version_gui",
    "launch_mizuoto_tts_webui_snapshot_gui",
    "install_mizuoto_tts_webui",
    "update_mizuoto_tts_webui",
    "check_mizuoto_tts_webui_env",
    "check_mizuoto_tts_webui_updates",
    "get_mizuoto_tts_webui_snapshot",
    "get_mizuoto_tts_webui_environment_info",
    "prepare_mizuoto_tts_webui_launch",
    "launch_mizuoto_tts_webui",
    "logger",
]
