"""基于 HF_ENDPOINT 的 Hugging Face 镜像补丁"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from functools import wraps
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

__all__ = [
    "HUGGINGFACE_URL_PATTERN",
    "apply_from_config",
    "apply_mirror",
    "compare_sha256",
    "load_file_from_url",
    "patch_comfyui_wd14_tagger",
    "patch_sd_webui_load_file_from_url",
    "patch_torchhub",
    "patch_torchvision",
    "rewrite_huggingface_url",
]

HUGGINGFACE_URL_PATTERN = re.compile(
    r"^https://huggingface\.co(?P<path>/.*)$",
    flags=re.IGNORECASE,
)


def apply_mirror() -> None:
    """
    注册全部 Hugging Face 镜像补丁

    包装函数会在调用时读取 ``HF_ENDPOINT``。环境变量为空或 URL 不是
    Hugging Face 链接时, 保持原始 URL 不变。
    """

    patch_torchhub()
    patch_torchvision()
    patch_comfyui_wd14_tagger()
    patch_sd_webui_load_file_from_url()


def patch_torchhub() -> None:
    """补丁 ``torch.hub.download_url_to_file`` 的 URL 参数"""

    install_import_hook()

    with monkey_zoo("torch.hub") as monkey:

        def download_url_to_file_wrapper(func: Any, module: Any):
            @wraps(func)
            def wrapper(url, dst, *args, **kwargs):
                return func(rewrite_huggingface_url(url), dst, *args, **kwargs)

            return wrapper

        monkey.patch_function("download_url_to_file", download_url_to_file_wrapper)


def patch_torchvision() -> None:
    """补丁 ``torchvision.datasets.utils._urlretrieve`` 的 URL 参数"""

    install_import_hook()

    with monkey_zoo("torchvision.datasets.utils") as monkey:

        def urlretrieve_wrapper(func: Any, module: Any):
            @wraps(func)
            def wrapper(url, fpath, *args, **kwargs):
                return func(rewrite_huggingface_url(url), fpath, *args, **kwargs)

            return wrapper

        monkey.patch_function("_urlretrieve", urlretrieve_wrapper)


def patch_comfyui_wd14_tagger() -> None:
    """补丁 ComfyUI WD14 tagger ``download_to_file`` 的 URL 参数"""

    install_import_hook()

    with monkey_zoo("ComfyUI-WD14-Tagger.pysssss") as monkey:

        def download_to_file_wrapper(func: Any, module: Any):
            @wraps(func)
            async def wrapper(url, dst, *args, **kwargs):
                rewritten = rewrite_huggingface_url(url)
                task = asyncio.create_task(
                    asyncio.to_thread(func, rewritten, dst, *args, **kwargs)
                )
                await asyncio.sleep(0)
                await task
                return task.result()

            return wrapper

        monkey.patch_function("download_to_file", download_to_file_wrapper)


def patch_sd_webui_load_file_from_url() -> None:
    """替换 ``modules.util.load_file_from_url`` 为支持 HF_ENDPOINT 的实现"""

    install_import_hook()

    with monkey_zoo("modules.util") as monkey:

        def load_file_from_url_wrapper(func: Any, module: Any):
            return load_file_from_url

        monkey.patch_function(
            "load_file_from_url",
            load_file_from_url_wrapper,
            add_if_not_exists=True,
        )


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
        ValueError:
            hash_prefix 校验失败
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
        except Exception:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

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


def rewrite_huggingface_url(url: Any) -> Any:
    """
    使用 ``HF_ENDPOINT`` 重写 Hugging Face URL

    非字符串、非 Hugging Face URL、或未设置 ``HF_ENDPOINT`` 时原样返回。

    Args:
        url (Any):
            待处理的 URL

    Returns:
        Any:
            重写后的 URL, 或原始输入
    """

    if not isinstance(url, str):
        return url

    endpoint = _hf_endpoint()
    if endpoint is None:
        return url

    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return url
    if (parsed.hostname or "").lower() != "huggingface.co":
        return url

    endpoint_parts = urlsplit(endpoint)
    if not endpoint_parts.scheme or not endpoint_parts.netloc:
        return url

    endpoint_path = endpoint_parts.path.rstrip("/")
    path = parsed.path
    combined_path = f"{endpoint_path}{path}" if endpoint_path else path
    return urlunsplit(
        (
            endpoint_parts.scheme,
            endpoint_parts.netloc,
            combined_path,
            parsed.query,
            parsed.fragment,
        )
    )


def apply_from_config(config: dict[str, Any] | None = None) -> None:
    """
    根据配置应用镜像补丁

    ``HF_ENDPOINT`` 始终是镜像源的唯一来源。配置只控制是否注册补丁。

    Args:
        config (dict[str, Any] | None):
            扩展配置。传入 ``{"enabled": False}`` 时跳过注册。
    """

    if isinstance(config, dict) and config.get("enabled") is False:
        return
    apply_mirror()


def _hf_endpoint() -> str | None:
    endpoint = os.getenv("HF_ENDPOINT")
    if endpoint is None:
        return None
    endpoint = endpoint.strip()
    if not endpoint:
        return None
    return endpoint.rstrip("/")
