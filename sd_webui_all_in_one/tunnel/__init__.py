"""内网穿透模块

提供多种内网穿透服务的统一接口, 支持上下文管理器。

使用示例:
    ```python
    from pathlib import Path
    from sd_webui_all_in_one.tunnel import TunnelManager

    # 推荐用法：使用上下文管理器
    with TunnelManager(workspace=Path("/workspace"), port=7860) as manager:
        tunnel_url = manager.start_tunnel(
            use_cloudflare=True,
            use_ngrok=True,
            ngrok_token="your_token"
        )
        print(f"访问地址: {tunnel_url}")
    # 退出时自动停止所有内网穿透
    ```
"""

from sd_webui_all_in_one.tunnel.manager import TunnelManager
from sd_webui_all_in_one.tunnel.types import TunnelUrl
from sd_webui_all_in_one.tunnel.base import BaseTunnel
from sd_webui_all_in_one.tunnel.process_tracker import ProcessTracker
from sd_webui_all_in_one.tunnel.tunnels import (
    CloudflareTunnel,
    GradioTunnel,
    LocalhostRunTunnel,
    NgrokTunnel,
    PinggyIoTunnel,
    RemoteMoeTunnel,
    ZrokTunnel,
)

__all__ = [
    "TunnelManager",
    "TunnelUrl",
    "BaseTunnel",
    "ProcessTracker",
    "CloudflareTunnel",
    "GradioTunnel",
    "LocalhostRunTunnel",
    "NgrokTunnel",
    "PinggyIoTunnel",
    "RemoteMoeTunnel",
    "ZrokTunnel",
]
