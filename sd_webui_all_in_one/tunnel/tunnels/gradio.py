"""Gradio 内网穿透实现"""

import secrets
from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.tunnel.base import BaseTunnel


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class GradioTunnel(BaseTunnel):
    """Gradio 内网穿透

    使用 gradio-tunneling 库实现 Gradio 内网穿透. 
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
    ) -> None:
        """初始化 Gradio 内网穿透

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
        """
        super().__init__(port, workspace)
        self._tunnel = None  # 保存 Tunnel 对象引用

    def start(
        self,
    ) -> str:
        """启动 Gradio 内网穿透

        Returns:
            str: Gradio 内网穿透生成的访问地址

        Raises:
            RuntimeError: 启动 Gradio 内网穿透失败时
        """
        logger.info("启动 Gradio 内网穿透")

        # 导入或安装 gradio-tunneling
        try:
            from gradio_tunneling.main import Tunnel, GRADIO_API_SERVER
            import requests
        except ImportError:
            try:
                pip_install("gradio-tunneling")
                from gradio_tunneling.main import Tunnel, GRADIO_API_SERVER
                import requests
            except (RuntimeError, ImportError) as e:
                logger.error("安装 Gradio Tunneling 内网穿透时出现了错误: %s", e)
                raise RuntimeError(f"安装 Gradio Tunneling 内网穿透模块失败: {e}") from e

        try:
            # 获取服务器地址
            response = requests.get(GRADIO_API_SERVER)
            if not (response and response.status_code == 200):
                raise RuntimeError("无法从 Gradio API 服务器获取共享链接")
            payload = response.json()[0]
            remote_host, remote_port = payload["host"], int(payload["port"])

            # 创建并启动隧道
            share_token = secrets.token_urlsafe(32)
            self._tunnel = Tunnel(
                remote_host=remote_host,
                remote_port=remote_port,
                local_host="127.0.0.1",
                local_port=self.port,
                share_token=share_token,
            )
            self._url = self._tunnel.start_tunnel()
            logger.info("Gradio 内网穿透启动完成")
            return self._url
        except Exception as e:
            logger.error("启动 Gradio 内网穿透时出现错误: %s", e)
            raise RuntimeError(f"启动 Gradio 内网穿透时出现了错误: {e}") from e

    def stop(
        self,
    ) -> None:
        """停止 Gradio 内网穿透

        调用 Tunnel.kill() 方法来终止隧道进程. 
        """
        if self._tunnel:
            try:
                logger.info("正在停止 Gradio 内网穿透")
                self._tunnel.kill()
                logger.info("Gradio 内网穿透已停止")
            except Exception as e:
                logger.error("停止 Gradio 内网穿透时发生错误: %s", e)

        super().stop()
