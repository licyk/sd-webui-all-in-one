"""CloudFlare 内网穿透实现"""

import subprocess
from pathlib import Path
from typing import Protocol, cast

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.optional_dependency import install_optional_dependency
from sd_webui_all_in_one.tunnel.base import BaseTunnel


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class _CloudflareTunnel(Protocol):
    """CloudFlare 隧道返回值协议"""

    tunnel: str
    process: subprocess.Popen


class _CloudflareClient(Protocol):
    """CloudFlare 隧道管理器协议"""

    def __call__(
        self,
        port: int | str,
        metrics_port: int | str | None = None,
        verbose: bool = True,
    ) -> _CloudflareTunnel:
        """启动指定端口的 CloudFlare 隧道"""

    def terminate(
        self,
        port: int | str,
    ) -> None:
        """停止指定端口的 CloudFlare 隧道"""


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
        self._cloudflare_client: _CloudflareClient | None = None
        self._cloudflare_tunnel: _CloudflareTunnel | None = None

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
                install_optional_dependency("pycloudflared")
                from pycloudflared import try_cloudflare
            except (RuntimeError, ImportError) as e:
                logger.error("安装 CloudFlare 内网穿透失败: %s", e)
                raise RuntimeError(f"安装 CloudFlare 内网穿透模块失败: {e}") from e

        try:
            self._cloudflare_client = cast(_CloudflareClient, try_cloudflare)
            self._cloudflare_tunnel = self._cloudflare_client(self.port)
            self._url = self._cloudflare_tunnel.tunnel
            self._process = self._cloudflare_tunnel.process
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
        if self._cloudflare_client and self._cloudflare_tunnel:
            try:
                logger.info("正在停止 CloudFlare 内网穿透")
                self._cloudflare_client.terminate(self.port)
                logger.info("CloudFlare 内网穿透已停止")
            except Exception as e:
                logger.error("停止 CloudFlare 内网穿透时发生错误: %s", e)
            finally:
                self._cloudflare_client = None
                self._cloudflare_tunnel = None

        super().stop()
