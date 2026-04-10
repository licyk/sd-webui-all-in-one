"""内网穿透管理器"""

from pathlib import Path
from typing import Any, Callable, Optional

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.logger import get_logger
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
from sd_webui_all_in_one.tunnel.types import TunnelUrl


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class TunnelManager:
    """内网穿透管理器
    
    支持多种内网穿透服务，并提供上下文管理器接口用于自动资源清理。
    
    使用示例:
        ```python
        # 推荐用法：使用上下文管理器
        with TunnelManager(workspace=Path("/workspace"), port=7860) as manager:
            tunnel_url = manager.start_tunnel(use_cloudflare=True)
            print(f"访问地址: {tunnel_url}")
        # 退出时自动停止所有内网穿透
        
        # 手动管理
        manager = TunnelManager(workspace=Path("/workspace"), port=7860)
        try:
            tunnel_url = manager.start_tunnel(use_cloudflare=True)
            print(f"访问地址: {tunnel_url}")
        finally:
            manager.stop_all()
        ```
    
    Attributes:
        workspace (Path):
            工作区路径
        port (int):
            要进行端口映射的端口
    """

    def __init__(self, workspace: Path, port: int) -> None:
        """初始化内网穿透管理器
        
        Args:
            workspace (Path):
                工作区路径
            port (int):
                要进行端口映射的端口
        """
        self.workspace = workspace
        self.port = port
        self._tracker = ProcessTracker()
        self._tunnel_url: Optional[TunnelUrl] = None

    def __enter__(self) -> "TunnelManager":
        """进入上下文管理器
        
        Returns:
            TunnelManager: 管理器实例
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """退出上下文管理器，自动清理所有资源
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪
            
        Returns:
            bool: 总是返回 False，不抑制异常
        """
        self.stop_all()
        return False

    def start_tunnel(
        self,
        use_ngrok: bool | None = False,
        ngrok_token: str | None = None,
        use_cloudflare: bool | None = False,
        use_remote_moe: bool | None = False,
        use_localhost_run: bool | None = False,
        use_gradio: bool | None = False,
        use_pinggy_io: bool | None = False,
        use_zrok: bool | None = False,
        zrok_token: str | None = None,
        check: bool | None = True,
    ) -> TunnelUrl:
        """启动内网穿透
        
        Args:
            use_ngrok (bool | None):
                启用 Ngrok 内网穿透
            ngrok_token (str | None):
                Ngrok 账号 Token
            use_cloudflare (bool | None):
                启用 CloudFlare 内网穿透
            use_remote_moe (bool | None):
                启用 remote.moe 内网穿透
            use_localhost_run (bool | None):
                使用 localhost.run 内网穿透
            use_gradio (bool | None):
                使用 Gradio 内网穿透
            use_pinggy_io (bool | None):
                使用 pinggy.io 内网穿透
            use_zrok (bool | None):
                使用 Zrok 内网穿透
            zrok_token (str | None):
                Zrok 账号 Token
            check (bool | None):
                检查内网穿透是否启动成功
                
        Returns:
            TunnelUrl: 内网穿透地址字典
            
        Raises:
            AggregateError:
                当 check=True 且启动内网穿透发生错误时
        """
        tunnel_url: TunnelUrl = {"local_url": f"http://127.0.0.1:{self.port}"}
        errors: list[Exception] = []

        # 定义任务列表：(是否启用, 键名, 隧道类, 参数)
        tasks: list[tuple[bool, str, Callable, list[Any]]] = [
            (use_cloudflare, "cloudflare", CloudflareTunnel, [self.port, self.workspace]),
            (use_ngrok, "ngrok", NgrokTunnel, [self.port, self.workspace, ngrok_token] if ngrok_token else None),
            (use_remote_moe, "remote_moe", RemoteMoeTunnel, [self.port, self.workspace]),
            (use_localhost_run, "localhost_run", LocalhostRunTunnel, [self.port, self.workspace]),
            (use_gradio, "gradio", GradioTunnel, [self.port, self.workspace]),
            (use_pinggy_io, "pinggy_io", PinggyIoTunnel, [self.port, self.workspace]),
            (use_zrok, "zrok", ZrokTunnel, [self.port, self.workspace, zrok_token] if zrok_token else None),
        ]

        # 启动各个隧道
        for enabled, key, tunnel_class, args in tasks:
            if not enabled or args is None:
                continue

            try:
                # 创建隧道实例
                tunnel = tunnel_class(*args)
                # 注册到追踪器
                self._tracker.register(tunnel)
                # 启动隧道
                url = tunnel.start()
                tunnel_url[key] = url
            except Exception as e:
                logger.error("启动 %s 内网穿透失败: %s", key, e)
                if check:
                    errors.append(e)

        # 保存结果
        self._tunnel_url = tunnel_url

        # 如果有错误且需要检查，抛出聚合异常
        if errors:
            raise AggregateError(f"内网穿透启动部分失败，共 {len(errors)} 个错误。", errors)

        return tunnel_url

    def stop_all(self) -> None:
        """停止所有内网穿透
        
        终止所有已启动的内网穿透进程。
        """
        self._tracker.stop_all()

    @property
    def tunnel_url(self) -> Optional[TunnelUrl]:
        """获取内网穿透地址
        
        Returns:
            Optional[TunnelUrl]: 内网穿透地址字典，如果未启动则返回 None
        """
        return self._tunnel_url

    @property
    def running_tunnels_count(self) -> int:
        """获取运行中的隧道数量
        
        Returns:
            int: 运行中的隧道数量
        """
        return len(self._tracker.get_running_tunnels())
