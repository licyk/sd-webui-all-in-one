"""API WebUI adapter。"""

from sd_webui_all_in_one.api_server.adapters.hotpatcher import HOTPATCHER_API_ADAPTER, HotpatcherApiAdapter
from sd_webui_all_in_one.api_server.adapters.library_operations import (
    install_model_from_catalog,
    model_library_catalog,
    pytorch_catalog,
    reinstall_from_catalog,
    resolve_model_library_install,
    resolve_pytorch_selection,
)
from sd_webui_all_in_one.api_server.adapters.webui import (
    WEBUI_API_ADAPTERS,
    WebUiApiType,
    WebUiApiAdapter,
)

__all__ = [
    "HOTPATCHER_API_ADAPTER",
    "pytorch_catalog",
    "reinstall_from_catalog",
    "model_library_catalog",
    "install_model_from_catalog",
    "resolve_pytorch_selection",
    "resolve_model_library_install",
    "HotpatcherApiAdapter",
    "WebUiApiType",
    "WEBUI_API_ADAPTERS",
    "WebUiApiAdapter",
]
