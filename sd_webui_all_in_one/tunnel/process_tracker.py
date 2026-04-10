"""进程追踪器"""

from typing import TYPE_CHECKING

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger

if TYPE_CHECKING:
    from sd_webui_all_in_one.tunnel.base import BaseTunnel


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class ProcessTracker:
    """进程追踪器

    管理所有启动的内网穿透进程, 提供统一的停止接口。
    """

    def __init__(
        self,
    ) -> None:
        """初始化进程追踪器"""
        self._tunnels: list["BaseTunnel"] = []

    def register(self, tunnel: "BaseTunnel") -> None:
        """注册一个隧道

        Args:
            tunnel (BaseTunnel):
                要注册的隧道实例
        """
        self._tunnels.append(tunnel)
        logger.debug("注册隧道: %s", tunnel.__class__.__name__)

    def stop_all(
        self,
    ) -> None:
        """停止所有隧道

        遍历所有已注册的隧道并停止它们。即使某个隧道停止失败, 
        也会继续尝试停止其他隧道。
        """
        if not self._tunnels:
            logger.debug("没有需要停止的隧道")
            return

        logger.info("正在停止所有内网穿透进程 (共 %d 个)", len(self._tunnels))
        failed_count = 0

        for tunnel in self._tunnels:
            try:
                tunnel.stop()
            except Exception as e:
                failed_count += 1
                logger.error("停止 %s 隧道失败: %s", tunnel.__class__.__name__, e)

        self._tunnels.clear()

        if failed_count > 0:
            logger.warning("停止隧道完成, 但有 %d 个隧道停止失败", failed_count)
        else:
            logger.info("所有内网穿透进程已停止")

    def get_running_tunnels(
        self,
    ) -> list["BaseTunnel"]:
        """获取所有运行中的隧道

        Returns:
            list[BaseTunnel]: 运行中的隧道列表
        """
        return [t for t in self._tunnels if t.is_running]

    def __len__(
        self,
    ) -> int:
        """返回已注册的隧道数量

        Returns:
            int: 隧道数量
        """
        return len(self._tunnels)
