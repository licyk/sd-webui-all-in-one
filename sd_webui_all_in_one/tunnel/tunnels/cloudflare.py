"""CloudFlare 内网穿透实现"""

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


class CloudflareTunnel(BaseTunnel):
    """CloudFlare 内网穿透

    使用 pycloudflared 库实现 CloudFlare 内网穿透. 
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
    ) -> None:
        """初始化 CloudFlare 内网穿透

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
        """
        super().__init__(port, workspace)
        self._cloudflare_tunnel = None

    def start(
        self,
    ) -> str:
        """启动 CloudFlare 内网穿透

        Returns:
            str: CloudFlare 内网穿透生成的访问地址

        Raises:
            RuntimeError: 启动 CloudFlare 内网穿透失败时
        """
        logger.info("启动 CloudFlare 内网穿透")

        # 导入或安装 pycloudflared
        try:
            from pycloudflared import try_cloudflare
        except ImportError:
            try:
                pip_install("pycloudflared")
                from pycloudflared import try_cloudflare
            except (RuntimeError, ImportError) as e:
                logger.error("安装 CloudFlare 内网穿透失败: %s", e)
                raise RuntimeError(f"安装 CloudFlare 内网穿透模块失败: {e}") from e

        try:
            self._cloudflare_tunnel = try_cloudflare(self.port)
            self._url = self._cloudflare_tunnel.tunnel
            logger.info("CloudFlare 内网穿透启动完成")
            return self._url
        except Exception as e:
            logger.error("启动 CloudFlare 内网穿透时出现了错误: %s", e)
            raise RuntimeError(f"启动 CloudFlare 内网穿透时出现了错误: {e}") from e

    def stop(
        self,
    ) -> None:
        """停止 CloudFlare 内网穿透

        终止 CloudFlare 隧道进程. 
        """
        if self._cloudflare_tunnel:
            try:
                logger.info("正在停止 CloudFlare 内网穿透")
                # pycloudflared 的 tunnel 对象有 terminate 方法
                if hasattr(self._cloudflare_tunnel, "terminate"):
                    self._cloudflare_tunnel.terminate()
                logger.info("CloudFlare 内网穿透已停止")
            except Exception as e:
                logger.error("停止 CloudFlare 内网穿透时发生错误: %s", e)

        super().stop()
