"""支持 HF_ENDPOINT 的文件下载实现"""

from __future__ import annotations

import hashlib
import os
from urllib.parse import urlsplit

from .urls import rewrite_huggingface_url


def load_file_from_url(
    url: str,
    *,
    model_dir: str,
    progress: bool = True,
    file_name: str | None = None,
    hash_prefix: str | None = None,
    re_download: bool = False,
) -> str:
    """
    下载文件到模型目录

    会在下载前通过 ``HF_ENDPOINT`` 重写 Hugging Face URL, 并在下载完成后按需校验
    sha256 前缀。

    Args:
        url (str):
            下载 URL
        model_dir (str):
            模型保存目录
        progress (bool):
            是否显示 tqdm 进度条
        file_name (str | None):
            保存文件名。为 None 时从 URL path 提取。
        hash_prefix (str | None):
            sha256 前缀校验值
        re_download (bool):
            是否强制重新下载已存在文件

    Returns:
        str:
            下载后文件的绝对路径

    Raises:
        Exception:
            文件下载失败时抛出。
    """

    import requests
    from tqdm import tqdm

    if not file_name:
        parts = urlsplit(url)
        file_name = os.path.basename(parts.path)

    rewritten_url = rewrite_huggingface_url(url)
    cached_file = os.path.abspath(os.path.join(model_dir, file_name))

    if re_download or not os.path.exists(cached_file):
        os.makedirs(model_dir, exist_ok=True)
        temp_file = os.path.join(model_dir, f"{file_name}.tmp")
        if os.path.exists(temp_file):
            os.remove(temp_file)

        print(f'\nDownloading: "{rewritten_url}" to {cached_file}')
        response = requests.get(rewritten_url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))

        try:
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=file_name,
                disable=not progress,
            ) as progress_bar:
                with open(temp_file, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            progress_bar.update(len(chunk))

            if hash_prefix and not compare_sha256(temp_file, hash_prefix):
                print(f"Hash mismatch for {temp_file}. Deleting the temporary file.")
                os.remove(temp_file)
                raise ValueError(f"File hash does not match the expected hash prefix {hash_prefix}!")

            os.replace(temp_file, cached_file)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise e

    return cached_file


def compare_sha256(file_path: str, hash_prefix: str) -> bool:
    """
    检查文件 sha256 是否匹配指定前缀

    Args:
        file_path (str):
            文件路径
        hash_prefix (str):
            sha256 十六进制前缀

    Returns:
        bool:
            文件 sha256 以前缀开头时返回 True
    """

    hash_sha256 = hashlib.sha256()
    block_size = 1024 * 1024

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(block_size), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest().startswith(hash_prefix.strip().lower())
