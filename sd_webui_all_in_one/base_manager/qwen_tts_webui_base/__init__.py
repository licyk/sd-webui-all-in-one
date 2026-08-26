"""Public facade for the qwen_tts_webui product manager."""

from sd_webui_all_in_one.base_manager.qwen_tts_webui_base.catalog import (
    QWEN_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
    get_qwen_tts_webui_launch_argument_catalog,
    QWEN_TTS_WEBUI_PRESET_HF_PATH,
    QWEN_TTS_WEBUI_PRESET_MS_PATH,
    QWEN_TTS_WEBUI_REPO,
)
from sd_webui_all_in_one.base_manager.qwen_tts_webui_base.gui import (
    launch_qwen_tts_webui_version_gui,
    launch_qwen_tts_webui_snapshot_gui,
)
from sd_webui_all_in_one.base_manager.qwen_tts_webui_base.lifecycle import (
    install_qwen_tts_webui_config,
    install_qwen_tts_webui,
    update_qwen_tts_webui,
    check_qwen_tts_webui_env,
)
from sd_webui_all_in_one.base_manager.qwen_tts_webui_base.reporting import (
    check_qwen_tts_webui_updates,
    get_qwen_tts_webui_snapshot,
    get_qwen_tts_webui_environment_info,
)
from sd_webui_all_in_one.base_manager.qwen_tts_webui_base.runtime import (
    prepare_qwen_tts_webui_launch,
    launch_qwen_tts_webui,
)
from sd_webui_all_in_one.base_manager.qwen_tts_webui_base.shared import (
    logger,
)

__all__ = [
    "QWEN_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY",
    "get_qwen_tts_webui_launch_argument_catalog",
    "QWEN_TTS_WEBUI_PRESET_HF_PATH",
    "QWEN_TTS_WEBUI_PRESET_MS_PATH",
    "QWEN_TTS_WEBUI_REPO",
    "launch_qwen_tts_webui_version_gui",
    "launch_qwen_tts_webui_snapshot_gui",
    "install_qwen_tts_webui_config",
    "install_qwen_tts_webui",
    "update_qwen_tts_webui",
    "check_qwen_tts_webui_env",
    "check_qwen_tts_webui_updates",
    "get_qwen_tts_webui_snapshot",
    "get_qwen_tts_webui_environment_info",
    "prepare_qwen_tts_webui_launch",
    "launch_qwen_tts_webui",
    "logger",
]
