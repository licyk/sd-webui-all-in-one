"""下载器"""

import shutil
from pathlib import Path

from sd_webui_all_in_one.downloader.aria2_downloader import aria2
from sd_webui_all_in_one.downloader.requests_downloader import download_file_from_url
from sd_webui_all_in_one.downloader.urllib_downloader import download_file_from_url_urllib
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.downloader.types import DownloadToolType
from sd_webui_all_in_one.optional_dependency import try_install_optional_dependency
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


def _is_requests_available() -> bool:
    """检查 requests 是否可以导入"""
    try:
        import requests

        _ = requests
        return True
    except ImportError:
        return False


def _install_requests() -> bool:
    """尝试安装 requests, 并确认安装后可以导入"""
    if not try_install_optional_dependency("requests"):
        return False

    if _is_requests_available():
        return True

    logger.warning("安装 requests 后仍无法导入")
    return False


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
    num_threads: int = 8,
    resume: bool = True,
    max_retries: int = 5,
    chunk_size: int | None = None,
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
        num_threads (int):
            requests 下载器的单文件 HTTP Range 下载线程数
        resume (bool):
            requests 下载器是否启用断点续传
        max_retries (int):
            requests 下载器单个分片的最大重试次数
        chunk_size (int | None):
            requests 下载器的 HTTP Range 分片大小, 为 None 或 0 时启用自适应分片

    Returns:
        Path:
            成功返回路径
    """
    if tool == "aria2":
        return aria2(url=url, path=path, save_name=save_name, progress=progress)
    elif tool == "requests":
        return download_file_from_url(
            url=url,
            save_path=path,
            file_name=save_name,
            progress=progress,
            num_threads=num_threads,
            resume=resume,
            max_retries=max_retries,
            chunk_size=chunk_size,
        )
    elif tool == "urllib":
        return download_file_from_url_urllib(url=url, save_path=path, file_name=save_name, progress=progress)
    return None


def download_file(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    tool: DownloadToolType | None = "requests",
    progress: bool = True,
    num_threads: int = 8,
    resume: bool = True,
    max_retries: int = 5,
    chunk_size: int | None = None,
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
        progress (bool):
            是否启用下载进度条
        num_threads (int):
            requests 下载器的单文件 HTTP Range 下载线程数
        resume (bool):
            requests 下载器是否启用断点续传
        max_retries (int):
            requests 下载器单个分片的最大重试次数
        chunk_size (int | None):
            requests 下载器的 HTTP Range 分片大小, 为 None 或 0 时启用自适应分片

    Returns:
        Path: 保存的文件路径
    """
    if path is None:
        path = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)

    selected_tool: DownloadToolType = tool or "requests"
    if selected_tool == "aria2" and shutil.which("aria2c") is None:
        logger.warning("未安装 Aria2, 将切换到 requests 进行下载")
        selected_tool = "requests"

    if selected_tool == "requests" and not _is_requests_available():
        logger.warning("未安装 requests, 尝试自动安装 requests")
        if not _install_requests():
            logger.warning("未安装 requests, 将切换到 urllib 进行下载")
            selected_tool = "urllib"

    return download_executer(
        url=url,
        path=path,
        save_name=save_name,
        tool=selected_tool,
        progress=bool(progress),
        num_threads=num_threads,
        resume=resume,
        max_retries=max_retries,
        chunk_size=chunk_size,
    )
