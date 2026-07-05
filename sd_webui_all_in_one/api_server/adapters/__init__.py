"""API WebUI adapter。"""

from sd_webui_all_in_one.api_server.adapters.webui import (
    WEBUI_API_ADAPTERS,
    WebUiApiAdapter,
    get_webui_adapter,
)

__all__ = [
    "WEBUI_API_ADAPTERS",
    "WebUiApiAdapter",
    "get_webui_adapter",
]
