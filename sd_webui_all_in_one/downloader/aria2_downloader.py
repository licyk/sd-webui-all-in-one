"""Aria2 下载工具"""

import os
from pathlib import Path
from urllib.parse import urlparse

from sd_webui_all_in_one.downloader.aria2_server import Aria2RpcServer
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


def aria2(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    progress: bool | None = True,
) -> Path:
    """Aria2 下载工具

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            下载文件的路径, 为`None`时使用当前路径
        save_name (str | None):
            保存的文件名, 为`None`时使用`url`提取保存的文件名
        progress (bool | None):
            是否启用下载进度条

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
    try:
        logger.info("下载 %s 到 %s 中", os.path.basename(url), save_path)
        with Aria2RpcServer() as aria2_server:
            return aria2_server.download(
                url=url,
                save_path=path,
                show_progress=progress,
            )
    except RuntimeError as e:
        logger.error("下载 %s 时发生错误: %s", url, e)
        raise RuntimeError(e) from e
