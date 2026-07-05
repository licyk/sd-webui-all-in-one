"""API WebUI adapter。"""

from sd_webui_all_in_one.api_server.adapters.hotpatcher import HOTPATCHER_API_ADAPTER, HotpatcherApiAdapter
from sd_webui_all_in_one.api_server.adapters.model import MODEL_API_ADAPTER, ModelApiAdapter
from sd_webui_all_in_one.api_server.adapters.webui import (
    WEBUI_API_ADAPTERS,
    WebUiApiAdapter,
    get_webui_adapter,
)

__all__ = [
    "HOTPATCHER_API_ADAPTER",
    "MODEL_API_ADAPTER",
    "HotpatcherApiAdapter",
    "ModelApiAdapter",
    "WEBUI_API_ADAPTERS",
    "WebUiApiAdapter",
    "get_webui_adapter",
]
