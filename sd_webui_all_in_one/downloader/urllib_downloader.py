import urllib.request
from pathlib import Path
from urllib.parse import urlparse


from sd_webui_all_in_one.downloader.hash_utils import compare_sha256
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


def download_file_from_url_urllib(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
) -> Path:
    """使用 urllib 库下载文件

    Args:
        url (str):
            下载链接
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool | None):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        re_download (bool):
            强制重新下载文件

    Returns:
        Path: 下载的文件路径

    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
    """

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    if save_path is None:
        save_path = Path.cwd()

    if not file_name:
        parts = urlparse(url)
        file_name = Path(parts.path).name

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.getheader("Content-Length", 0))
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=file_name,
                disable=not progress,
            ) as progress_bar:
                with open(temp_file, "wb") as file:
                    while True:
                        chunk = response.read(1024)
                        if not chunk:
                            break
                        file.write(chunk)
                        progress_bar.update(len(chunk))

        if hash_prefix and not compare_sha256(temp_file, hash_prefix):
            logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
            temp_file.unlink()
            raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

        temp_file.rename(cached_file)
        logger.info("'%s' 下载完成", file_name)
    else:
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
    return cached_file
