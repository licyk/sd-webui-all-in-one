"""压缩包下载工具"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from sd_webui_all_in_one.file_operations.archive_manager import extract_archive
from sd_webui_all_in_one.downloader.downloader import download_file
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


def download_archive_and_unpack(
    url: str,
    local_dir: Path,
    name: str | None = None,
) -> None:
    """下载压缩包并解压到指定路径

    Args:
        url (str):
            压缩包下载链接, 压缩包支持的格式: .zip, .7z, .rar, .tar, .tar.Z, .tar.lz, .tar.lzma, .tar.bz2, .tar.7z, .tar.gz, .tar.xz, .tar.zst
        local_dir (Path):
            下载路径
        name (str | None):
            下载文件保存的名称, 为`None`时从`url`解析文件名

    Raises:
        RuntimeError:
            下载并解压压缩包时发生错误时
    """
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        if name is None:
            parts = urlparse(url)
            name = os.path.basename(parts.path)

        try:
            origin_file_path = download_file(
                url=url,
                path=path,
                save_name=name,
            )
            logger.info("解压 %s 到 %s 中", name, local_dir)
            extract_archive(
                archive_path=origin_file_path,
                extract_to=local_dir,
            )
            logger.info("%s 解压完成, 路径: %s", name, local_dir)
        except Exception as e:
            logger.error("解压 %s 时发生错误: %s", name, e)
            raise RuntimeError(f"下载 {name} 并解压压缩包时发生错误: {e}") from e
