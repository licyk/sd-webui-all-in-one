"""SD WebUI extension management facade."""

from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.catalog import (
    SDWebUiExtensionInfo as SDWebUiExtensionInfo,
    SDWebUiExtensionInfoList as SDWebUiExtensionInfoList,
    SD_WEBUI_EXTENSION_INFO_DICT as SD_WEBUI_EXTENSION_INFO_DICT,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.index import (
    fetch_sd_webui_extension_index as fetch_sd_webui_extension_index,
    install_sd_webui_extension_index_item as install_sd_webui_extension_index_item,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.service import (
    set_sd_webui_extension_download_list_mirror as set_sd_webui_extension_download_list_mirror,
    install_sd_webui_extension as install_sd_webui_extension,
    SDWebUiLocalExtensionInfo as SDWebUiLocalExtensionInfo,
    SDWebUiLocalExtensionInfoList as SDWebUiLocalExtensionInfoList,
    set_sd_webui_extensions_status as set_sd_webui_extensions_status,
    list_sd_webui_extensions as list_sd_webui_extensions,
    update_sd_webui_extensions as update_sd_webui_extensions,
    uninstall_sd_webui_extension as uninstall_sd_webui_extension,
)

__all__ = [name for name in globals() if not name.startswith("_")]
