"""内网穿透类型定义"""

from typing import TypedDict


class TunnelUrl(TypedDict, total=False):
    """内网穿透的地址"""

    local_url: str
    """被端口映射的本地访问地址"""

    cloudflare: str | None
    """CloudFlare 内网穿透地址"""

    ngrok: str | None
    """Ngrok 内网穿透地址"""

    remote_moe: str | None
    """remote.moe 内网穿透地址"""

    localhost_run: str | None
    """localhost.run 内网穿透地址"""

    gradio: str | None
    """Gradio 内网穿透地址"""

    pinggy_io: str | None
    """pinggy.io 内网穿透地址"""

    zrok: str | None
    """Zrok 内网穿透地址"""
