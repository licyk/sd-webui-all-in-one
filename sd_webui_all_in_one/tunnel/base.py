"""内网穿透基类"""

import subprocess
from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import Any

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class BaseTunnel(ABC):
    """内网穿透基类

    所有内网穿透实现都应该继承此类并实现 start 方法.

    Attributes:
        port (int):
            要进行端口映射的端口
        workspace (Path):
            工作区路径
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
    ) -> None:
        """初始化内网穿透基类

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
        """
        self.port = port
        self.workspace = workspace
        self._process: subprocess.Popen | None = None
        self._url: str | None = None

    @abstractmethod
    def start(
        self,
    ) -> str:
        """启动内网穿透

        Returns:
            str: 内网穿透生成的访问地址

        Raises:
            RuntimeError: 启动内网穿透失败时
        """

    def stop(
        self,
    ) -> None:
        """停止内网穿透

        终止内网穿透进程. 如果进程在 5 秒内没有终止, 则强制杀死进程.
        """
        if self._process and self._process.poll() is None:
            logger.info("正在停止 %s 内网穿透进程 (PID: %s)", self.__class__.__name__, self._process.pid)
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                    logger.info("%s 内网穿透进程已停止", self.__class__.__name__)
                except subprocess.TimeoutExpired:
                    logger.warning("%s 内网穿透进程未在 5 秒内终止, 强制杀死进程", self.__class__.__name__)
                    self._process.kill()
                    self._process.wait()
                    logger.info("%s 内网穿透进程已被强制杀死", self.__class__.__name__)
            except Exception as e:
                logger.error("停止 %s 内网穿透进程时发生错误: %s", self.__class__.__name__, e)

    @property
    def url(
        self,
    ) -> str | None:
        """获取内网穿透地址

        Returns:
            (str | None): 内网穿透地址, 如果未启动则返回 None
        """
        return self._url

    @property
    def is_running(
        self,
    ) -> bool:
        """检查进程是否运行中

        Returns:
            bool: 如果进程正在运行返回 True, 否则返回 False
        """
        return self._process is not None and self._process.poll() is None

    def __enter__(
        self,
    ) -> "BaseTunnel":
        """进入上下文管理器

        Returns:
            BaseTunnel:
                内网穿透基类实例
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """退出上下文管理器, 自动清理资源

        Args:
            exc_type (type[BaseException] | None):
                异常类型
            exc_val (BaseException | None):
                异常值
            exc_tb (Any | None):
                异常追踪信息
        """
        self.stop()
        return False
