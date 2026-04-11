"""localhost.run 内网穿透实现"""

import re
from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.tunnel.tunnels.ssh_base import SSHTunnel


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class LocalhostRunTunnel(SSHTunnel):
    """localhost.run 内网穿透

    使用 SSH 连接到 localhost.run 服务实现内网穿透.
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
    ) -> None:
        """初始化 localhost.run 内网穿透

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
        """
        ssh_args = ["-R", f"80:127.0.0.1:{port}", "localhost.run"]
        url_pattern = re.compile(r"(?P<url>https?://\S+\.lhr\.life)")

        super().__init__(
            port=port,
            workspace=workspace,
            ssh_args=ssh_args,
            url_pattern=url_pattern,
            line_limit=27,
        )

        logger.info("初始化 localhost.run 内网穿透")

    def start(
        self,
    ) -> str:
        """启动 localhost.run 内网穿透

        Returns:
            str: localhost.run 内网穿透生成的访问地址

        Raises:
            RuntimeError: 启动内网穿透失败时
        """
        logger.info("启动 localhost.run 内网穿透")
        return super().start()
