"""Aria2 下载工具"""

import os
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sd_webui_all_in_one.downloader.aria2_server import Aria2RpcServer
from sd_webui_all_in_one.downloader.requests_downloader import (
    DEFAULT_MAX_CONNECTION_PER_SERVER,
    DEFAULT_MIN_SPLIT_SIZE,
    DEFAULT_PIECE_LENGTH,
    DEFAULT_SPLIT,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class _Aria2ServerPool:
    """
    Aria2RpcServer 共享实例池

    使用引用计数管理共享的 Aria2RpcServer 实例生命周期:
    - 首次获取时自动创建并启动服务器
    - 每次获取引用计数 +1, 每次释放引用计数 -1
    - 引用计数归零时自动关闭并清理服务器实例

    线程安全, 适用于多线程并发下载场景
    """

    def __init__(
        self,
    ) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._server: Aria2RpcServer | None = None
        self._ref_count: int = 0

    def acquire(self) -> Aria2RpcServer:
        """
        获取共享的 Aria2RpcServer 实例, 若不存在则创建并启动

        引用计数 +1, 线程安全

        Returns:
            Aria2RpcServer: 共享的服务器实例
        """
        with self._lock:
            if self._server is None:
                logger.debug("创建共享 Aria2RpcServer 实例")
                self._server = Aria2RpcServer(use_external_server=False)
                self._server.__enter__()  # pylint: disable=unnecessary-dunder-call

            self._ref_count += 1
            logger.debug("Aria2RpcServer 引用计数: %d", self._ref_count)
            return self._server

    def release(
        self,
    ) -> None:
        """
        释放对共享 Aria2RpcServer 实例的引用

        引用计数 -1, 若归零则关闭并清理实例, 线程安全
        """
        with self._lock:
            self._ref_count -= 1
            logger.debug("Aria2RpcServer 引用计数: %d", self._ref_count)

            if self._ref_count <= 0 and self._server is not None:
                logger.debug("所有下载任务已完成, 关闭共享 Aria2RpcServer 实例")
                try:
                    self._server.__exit__(None, None, None)
                except Exception as e:
                    logger.error("关闭共享 Aria2RpcServer 实例时出错: %s", e)
                finally:
                    self._server = None
                    self._ref_count = 0


_server_pool: _Aria2ServerPool = _Aria2ServerPool()
"""模块级共享服务器池"""


def aria2(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    progress: bool = True,
    split: int = DEFAULT_SPLIT,
    max_connection_per_server: int = DEFAULT_MAX_CONNECTION_PER_SERVER,
    min_split_size: int = DEFAULT_MIN_SPLIT_SIZE,
    piece_length: int = DEFAULT_PIECE_LENGTH,
    continue_download: bool = False,
    max_tries: int = 5,
) -> Path:
    """Aria2 下载工具

    多次并发调用时共享同一个 Aria2RpcServer 实例, 所有下载任务完成后自动关闭服务器

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            下载文件的路径, 为`None`时使用当前路径
        save_name (str | None):
            保存的文件名, 为`None`时使用`url`提取保存的文件名
        progress (bool):
            是否启用下载进度条
        split (int):
            aria2 单文件最大分割数
        max_connection_per_server (int):
            aria2 单服务器最大连接数
        min_split_size (int):
            aria2 最小切分大小
        piece_length (int):
            aria2 piece 大小
        continue_download (bool):
            是否启用断点续传
        max_tries (int):
            最大尝试次数

    Returns:
        Path: 下载成功时返回文件路径

    Raises:
        RuntimeError: 下载出现错误
    """
    if path is None:
        path = Path().cwd()

    path = Path(path) if not isinstance(path, Path) and path is not None else path
    if save_name is None:
        parts = urlparse(url)
        save_name = os.path.basename(parts.path)

    save_path = path / save_name
    server = _server_pool.acquire()
    try:
        logger.info("下载 %s 到 %s 中", save_name, save_path)
        options: dict[str, Any] = {
            "split": str(max(1, int(split))),
            "max-connection-per-server": str(max(1, int(max_connection_per_server))),
            "min-split-size": str(max(1, int(min_split_size))),
            "piece-length": str(max(1, int(piece_length))),
            "continue": "true" if continue_download else "false",
            "max-tries": str(max(1, int(max_tries))),
        }
        return server.download(
            url=url,
            save_path=path,
            save_name=save_name,
            options=options,
            show_progress=bool(progress),
        )
    except RuntimeError as e:
        logger.error("下载 %s 时发生错误: %s", url, e)
        raise RuntimeError(e) from e
    finally:
        _server_pool.release()
