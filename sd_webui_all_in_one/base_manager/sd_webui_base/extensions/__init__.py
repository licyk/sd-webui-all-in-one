"""SD WebUI extension management facade."""

from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.catalog import (
    SDWebUiExtensionInfo,
    SDWebUiExtensionInfoList,
    SD_WEBUI_EXTENSION_INFO_DICT,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.index import (
    fetch_sd_webui_extension_index,
    install_sd_webui_extension_index_item,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.service import (
    set_sd_webui_extension_download_list_mirror,
    install_sd_webui_extension,
    SDWebUiLocalExtensionInfo,
    SDWebUiLocalExtensionInfoList,
    set_sd_webui_extensions_status,
    list_sd_webui_extensions,
    update_sd_webui_extensions,
    uninstall_sd_webui_extension,
)

__all__ = [
    "SDWebUiExtensionInfo",
    "SDWebUiExtensionInfoList",
    "SD_WEBUI_EXTENSION_INFO_DICT",
    "fetch_sd_webui_extension_index",
    "install_sd_webui_extension_index_item",
    "set_sd_webui_extension_download_list_mirror",
    "install_sd_webui_extension",
    "SDWebUiLocalExtensionInfo",
    "SDWebUiLocalExtensionInfoList",
    "set_sd_webui_extensions_status",
    "list_sd_webui_extensions",
    "update_sd_webui_extensions",
    "uninstall_sd_webui_extension",
]
