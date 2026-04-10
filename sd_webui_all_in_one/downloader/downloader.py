"""下载器"""

import shutil
from pathlib import Path

from sd_webui_all_in_one.downloader.aria2_downloader import aria2
from sd_webui_all_in_one.downloader.requests_downloader import download_file_from_url
from sd_webui_all_in_one.downloader.urllib_downloader import download_file_from_url_urllib
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.downloader.types import DownloadToolType
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
    RETRY_TIMES,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


@retryable(
    times=RETRY_TIMES,
    describe="执行下载器",
    catch_exceptions=(IOError, RuntimeError, ValueError),
    raise_exception=(RuntimeError),
    retry_on_none=False,
)
def download_executer(
    url: str,
    path: Path,
    save_name: str | None,
    tool: DownloadToolType,
    progress: bool,
) -> Path:
    """底层下载执行器

    Args:
        url (str):
            下载链接
        path (Path):
            保存路径
        save_name (str | None):
            保存名称
        tool (DownloadToolType):
            工具名称
        progress (bool):
            是否显示进度

    Returns:
        Path:
            成功返回路径
    """
    if tool == "aria2":
        return aria2(url=url, path=path, save_name=save_name, progress=progress)
    elif tool == "requests":
        return download_file_from_url(url=url, save_path=path, file_name=save_name, progress=progress)
    elif tool == "urllib":
        return download_file_from_url_urllib(url=url, save_path=path, file_name=save_name, progress=progress)
    return None


def download_file(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    tool: DownloadToolType | None = "aria2",
    progress: bool | None = True,
) -> Path:
    """下载文件工具

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            文件下载路径
        save_name (str | None):
            文件保存名称
        tool (DownloadToolType | None):
            下载工具
        progress (bool | None):
            是否启用下载进度条

    Returns:
        Path: 保存的文件路径
    """
    path.mkdir(parents=True, exist_ok=True)

    selected_tool = str(tool)
    if selected_tool == "aria2" and shutil.which("aria2c") is None:
        logger.warning("未安装 Aria2, 将切换到 requests 进行下载")
        selected_tool = "requests"

    try:
        if selected_tool == "requests":
            import requests

            _ = requests
    except ImportError:
        logger.warning("未安装 requests, 将切换到 urllib 进行下载")
        selected_tool = "urllib"

    return download_executer(url=url, path=path, save_name=save_name, tool=selected_tool, progress=progress)
