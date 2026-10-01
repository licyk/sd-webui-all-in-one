"""扩展索引镜像地址解析"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from .constants import (
    A1111_EXTENSION_INDEX_AUTO,
    A1111_EXTENSION_INDEX_RAW_FILE_PATH,
    COMFYUI_MANAGER_RAW_FILE_PATH,
    GITHUB_HOST,
    GITHUB_RAW_HOST,
)


def resolve_a1111_extension_index_url(value: str) -> str | None:
    """
    解析 A1111 / Forge / Vladmandic 扩展索引目标 URL

    Args:
        value (str):
            普通目标 URL, 或 ``auto``。

    Returns:
        str | None:
            需要写入的目标 URL。为 None 时表示保持原始 URL。
    """

    value = value.strip()
    if not value:
        return None
    if value.lower() != A1111_EXTENSION_INDEX_AUTO:
        return value

    return _resolve_github_raw_auto_mirror(A1111_EXTENSION_INDEX_RAW_FILE_PATH)


def resolve_comfyui_manager_channel_prefix(value: str | None = None) -> str | None:
    """
    解析 ComfyUI-Manager channel 目标前缀

    Args:
        value (str | None):
            普通目标 URL, ``auto`` 或 None。None 等价于 ``auto``。

    Returns:
        str | None:
            需要写入的目标 channel 前缀。为 None 时表示保持原始 URL。
    """

    value = A1111_EXTENSION_INDEX_AUTO if value is None else value.strip()
    if not value:
        return None
    if value.lower() != A1111_EXTENSION_INDEX_AUTO:
        return _normalize_comfyui_manager_channel_prefix(value)

    resolved = _resolve_github_raw_auto_mirror(COMFYUI_MANAGER_RAW_FILE_PATH)
    return _normalize_comfyui_manager_channel_prefix(resolved) if resolved is not None else None


def _github_direct_accessible() -> bool:
    from sd_webui_all_in_one.utils import network_gfw_test

    return network_gfw_test()


def _apply_github_raw_file_mirror(raw_file_path: str) -> str | None:
    from sd_webui_all_in_one.base_manager.base import apply_github_raw_file_mirror

    return apply_github_raw_file_mirror(raw_file_path=raw_file_path)


def _resolve_github_raw_auto_mirror(raw_file_path: str) -> str | None:
    if _github_direct_accessible():
        return None
    return _apply_github_raw_file_mirror(raw_file_path)


def _normalize_comfyui_manager_channel_prefix(prefix: str) -> str:
    return prefix.rstrip("/")


def _replace_comfyui_manager_channel_url(
    url: Any,
    *,
    source_prefix: str,
    destination_prefix: str,
) -> Any:
    if not isinstance(url, str):
        return url
    if url == source_prefix:
        return destination_prefix
    if url.startswith(source_prefix + "/"):
        return destination_prefix + url[len(source_prefix) :]
    return url


def _replace_comfyui_manager_get_data_url(
    url: Any,
    *,
    source_prefix: str,
    destination_prefix: str,
) -> Any:
    mirrored_url = _replace_comfyui_manager_channel_url(
        url,
        source_prefix=source_prefix,
        destination_prefix=destination_prefix,
    )
    if mirrored_url != url:
        return mirrored_url

    raw_file = _split_github_raw_file_url(url)
    if raw_file is None:
        return url

    raw_file_path, suffix = raw_file
    mirrored_url = _mirror_github_raw_file_url(
        raw_file_path,
        source_prefix=source_prefix,
        destination_prefix=destination_prefix,
    )
    return (mirrored_url + suffix) if mirrored_url is not None else url


def _mirror_github_raw_file_url(
    raw_file_path: str,
    *,
    source_prefix: str,
    destination_prefix: str,
) -> str | None:
    mirror_prefix = _derive_github_raw_mirror_prefix(
        source_prefix=source_prefix,
        destination_prefix=destination_prefix,
    )
    if mirror_prefix is not None:
        return f"{mirror_prefix}/{raw_file_path}"
    return _apply_github_raw_file_mirror(raw_file_path)


def _derive_github_raw_mirror_prefix(
    *,
    source_prefix: str,
    destination_prefix: str,
) -> str | None:
    source_raw_file = _split_github_raw_file_url(source_prefix)
    if source_raw_file is None:
        return None

    source_raw_file_path, _ = source_raw_file
    expected_suffix = "/" + source_raw_file_path
    if not destination_prefix.endswith(expected_suffix):
        return None

    mirror_prefix = destination_prefix[: -len(expected_suffix)].rstrip("/")
    return mirror_prefix or None


def _split_github_raw_file_url(url: Any) -> tuple[str, str] | None:
    if not isinstance(url, str):
        return None

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    raw_file_path: str | None = None
    if host == GITHUB_RAW_HOST and len(path_parts) >= 3:
        raw_file_path = "/".join(path_parts)
    elif host == GITHUB_HOST and len(path_parts) >= 4 and path_parts[2] in {"raw", "blob"}:
        raw_file_path = "/".join([path_parts[0], path_parts[1], *path_parts[3:]])

    if raw_file_path is None:
        return None

    suffix = ""
    if parsed.query:
        suffix += "?" + parsed.query
    if parsed.fragment:
        suffix += "#" + parsed.fragment
    return raw_file_path, suffix
