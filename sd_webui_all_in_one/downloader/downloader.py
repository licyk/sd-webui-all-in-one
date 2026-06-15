"""下载器"""

import shutil
from collections.abc import Sequence
from pathlib import Path

from sd_webui_all_in_one.downloader.aria2_downloader import aria2
from sd_webui_all_in_one.downloader.requests_downloader import (
    DEFAULT_MAX_CONNECTION_PER_SERVER,
    DEFAULT_MIN_SPLIT_SIZE,
    DEFAULT_PIECE_LENGTH,
    DEFAULT_SPLIT,
    download_file_from_url,
)
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
    url: str | Sequence[str],
    path: Path,
    save_name: str | None,
    tool: DownloadToolType,
    progress: bool,
    split: int = DEFAULT_SPLIT,
    max_connection_per_server: int = DEFAULT_MAX_CONNECTION_PER_SERVER,
    min_split_size: int = DEFAULT_MIN_SPLIT_SIZE,
    piece_length: int = DEFAULT_PIECE_LENGTH,
    allow_piece_length_change: bool = False,
    continue_download: bool = False,
    max_tries: int = 5,
    retry_wait: int = 0,
    conditional_get: bool = False,
    remote_time: bool = True,
) -> Path:
    """底层下载执行器

    Args:
        url (str | Sequence[str]):
            下载链接或同一文件的镜像链接列表
        path (Path):
            保存路径
        save_name (str | None):
            保存名称
        tool (DownloadToolType):
            工具名称
        progress (bool):
            是否显示进度
        split (int):
            aria2 风格的单文件最大分割数
        max_connection_per_server (int):
            aria2 风格的单服务器最大连接数
        min_split_size (int):
            aria2 风格的最小切分大小
        piece_length (int):
            aria2 风格的 piece 大小
        allow_piece_length_change (bool):
            piece_length 与已有控制文件不一致时, 是否允许转换已完成 bitfield
        continue_download (bool):
            没有匹配控制文件时, 是否从已有文件推断断点续传进度
        max_tries (int):
            requests 下载器单个分片的最大尝试次数
        retry_wait (int):
            HTTP 503 重试前等待秒数
        conditional_get (bool):
            已有本地文件时是否发送 If-Modified-Since, 远端返回 304 时复用本地文件
        remote_time (bool):
            下载完成后是否把本地文件 mtime 设置为远端 Last-Modified

    Returns:
        Path:
            成功返回路径
    """
    if tool == "aria2":
        return aria2(
            url=url,
            path=path,
            save_name=save_name,
            progress=progress,
            split=split,
            max_connection_per_server=max_connection_per_server,
            min_split_size=min_split_size,
            piece_length=piece_length,
            allow_piece_length_change=allow_piece_length_change,
            continue_download=continue_download,
            max_tries=max_tries,
            retry_wait=retry_wait,
            conditional_get=conditional_get,
            remote_time=remote_time,
        )
    elif tool == "requests":
        return download_file_from_url(
            url=url,
            save_path=path,
            file_name=save_name,
            progress=progress,
            split=split,
            max_connection_per_server=max_connection_per_server,
            min_split_size=min_split_size,
            piece_length=piece_length,
            allow_piece_length_change=allow_piece_length_change,
            continue_download=continue_download,
            max_tries=max_tries,
            retry_wait=retry_wait,
            conditional_get=conditional_get,
            remote_time=remote_time,
        )
    elif tool == "urllib":
        return download_file_from_url_urllib(url=url, save_path=path, file_name=save_name, progress=progress)
    return None


def download_file(
    url: str | Sequence[str],
    path: Path | None = None,
    save_name: str | None = None,
    tool: DownloadToolType | None = "requests",
    progress: bool = True,
    split: int = DEFAULT_SPLIT,
    max_connection_per_server: int = DEFAULT_MAX_CONNECTION_PER_SERVER,
    min_split_size: int = DEFAULT_MIN_SPLIT_SIZE,
    piece_length: int = DEFAULT_PIECE_LENGTH,
    allow_piece_length_change: bool = False,
    continue_download: bool = False,
    max_tries: int = 5,
    retry_wait: int = 0,
    conditional_get: bool = False,
    remote_time: bool = True,
) -> Path:
    """下载文件工具

    Args:
        url (str | Sequence[str]):
            文件下载链接或同一文件的镜像链接列表
        path (Path | None):
            文件下载路径
        save_name (str | None):
            文件保存名称
        tool (DownloadToolType | None):
            下载工具
        progress (bool):
            是否启用下载进度条
        split (int):
            aria2 风格的单文件最大分割数
        max_connection_per_server (int):
            aria2 风格的单服务器最大连接数
        min_split_size (int):
            aria2 风格的最小切分大小
        piece_length (int):
            aria2 风格的 piece 大小
        allow_piece_length_change (bool):
            piece_length 与已有控制文件不一致时, 是否允许转换已完成 bitfield
        continue_download (bool):
            没有匹配控制文件时, 是否从已有文件推断断点续传进度
        max_tries (int):
            requests 下载器单个分片的最大尝试次数
        retry_wait (int):
            HTTP 503 重试前等待秒数
        conditional_get (bool):
            已有本地文件时是否发送 If-Modified-Since, 远端返回 304 时复用本地文件
        remote_time (bool):
            下载完成后是否把本地文件 mtime 设置为远端 Last-Modified

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
        split=split,
        max_connection_per_server=max_connection_per_server,
        min_split_size=min_split_size,
        piece_length=piece_length,
        allow_piece_length_change=allow_piece_length_change,
        continue_download=continue_download,
        max_tries=max_tries,
        retry_wait=retry_wait,
        conditional_get=conditional_get,
        remote_time=remote_time,
    )
