"""文件下载工具包"""

from sd_webui_all_in_one.downloader.types import (
    DownloadToolType,
    DOWNLOAD_TOOL_TYPE_LIST,
    DEFAULT_USER_AGENT,
)
from sd_webui_all_in_one.downloader.multi_thread import MultiThreadDownloader
from sd_webui_all_in_one.downloader.aria2_server import Aria2RpcServer
from sd_webui_all_in_one.downloader.aria2_downloader import aria2
from sd_webui_all_in_one.downloader.requests_downloader import download_file_from_url
from sd_webui_all_in_one.downloader.urllib_downloader import download_file_from_url_urllib
from sd_webui_all_in_one.downloader.hash_utils import compare_sha256
from sd_webui_all_in_one.downloader.downloader import (
    download_file,
    download_executer,
)
from sd_webui_all_in_one.downloader.archive_downloader import download_archive_and_unpack

__all__ = [
    # 类型和常量
    "DownloadToolType",
    "DOWNLOAD_TOOL_TYPE_LIST",
    "DEFAULT_USER_AGENT",
    # 类
    "MultiThreadDownloader",
    "Aria2RpcServer",
    # 下载函数
    "aria2",
    "download_file_from_url",
    "download_file_from_url_urllib",
    "download_file",
    "download_executer",
    "download_archive_and_unpack",
    # 工具函数
    "compare_sha256",
]
