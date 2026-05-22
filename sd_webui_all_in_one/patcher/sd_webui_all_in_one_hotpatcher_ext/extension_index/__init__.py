"""扩展索引镜像补丁"""

from __future__ import annotations

import functools
from types import CodeType, ModuleType
from typing import Any
from urllib.parse import urlsplit

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

__all__ = [
    "A1111_EXTENSION_INDEX_AUTO",
    "A1111_EXTENSION_INDEX_RAW_FILE_PATH",
    "A1111_EXTENSION_INDEX_URLS",
    "COMFYUI_MANAGER_RAW_FILE_PATH",
    "COMFYUI_MANAGER_RAW_PREFIX",
    "apply_from_config",
    "patch_extension_index_a1111",
    "patch_extension_index_comfyui_manager",
    "resolve_a1111_extension_index_url",
    "resolve_comfyui_manager_channel_prefix",
]

A1111_EXTENSION_INDEX_AUTO = "auto"
A1111_EXTENSION_INDEX_RAW_FILE_PATH = "AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
A1111_EXTENSION_INDEX_URLS = (
    "https://raw.githubusercontent.com/wiki/AUTOMATIC1111/stable-diffusion-webui/Extensions-index.md",
    "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json",
    # "https://vladmandic.github.io/sd-data/pages/extensions.json",
)

COMFYUI_MANAGER_RAW_FILE_PATH = "ltdrdata/ComfyUI-Manager/main"
COMFYUI_MANAGER_RAW_PREFIX = f"https://raw.githubusercontent.com/{COMFYUI_MANAGER_RAW_FILE_PATH}"
COMFYUI_MANAGER_CORE_MODULE = "manager_core"
COMFYUI_MANAGER_SERVER_MODULE = "manager_server"
COMFYUI_MANAGER_UTIL_MODULE = "manager_util"
GITHUB_RAW_HOST = "raw.githubusercontent.com"
GITHUB_HOST = "github.com"


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


def patch_extension_index_a1111(destination: str) -> None:
    """
    重写 A1111 / Forge / Vladmandic 扩展索引 URL

    Args:
        destination (str):
            目标镜像索引 URL
    """

    install_import_hook()

    with monkey_zoo("modules.ui_extensions") as monkey:

        def patch_extension_index_url(code_object) -> None:
            replacements = {source_url: destination for source_url in A1111_EXTENSION_INDEX_URLS}
            _replace_string_constants_in_code(code_object, replacements)

        monkey.patch_bytecode(patch_extension_index_url)


def patch_extension_index_comfyui_manager(
    destination_prefix: str | None = None,
    *,
    source_prefix: str = COMFYUI_MANAGER_RAW_PREFIX,
) -> None:
    """
    重写 ComfyUI-Manager 资源 URL 前缀

    Args:
        destination_prefix (str | None):
            目标镜像前缀。为 None 或 ``auto`` 时自动判断是否需要 GitHub raw 镜像。
        source_prefix (str):
            需要替换的原始前缀
    """

    source_prefix = _normalize_comfyui_manager_channel_prefix(source_prefix)
    destination_prefix = resolve_comfyui_manager_channel_prefix(destination_prefix)
    if destination_prefix is None:
        return

    install_import_hook()

    def patch_manager_core_module(module: ModuleType) -> None:
        module.DEFAULT_CHANNEL = destination_prefix  # ty: ignore[unresolved-attribute]
        _add_valid_channel(module, destination_prefix)

    def patch_get_channel_dict(func: Any, module: ModuleType):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            channel_dict = func(*args, **kwargs)
            if isinstance(channel_dict, dict):
                for name, url in list(channel_dict.items()):
                    mirrored_url = _replace_comfyui_manager_channel_url(
                        url,
                        source_prefix=source_prefix,
                        destination_prefix=destination_prefix,
                    )
                    if mirrored_url != url:
                        channel_dict[name] = mirrored_url
                        _add_valid_channel(module, mirrored_url)
            return channel_dict

        return wrapper

    with monkey_zoo(COMFYUI_MANAGER_CORE_MODULE) as monkey:
        monkey.patch_function("get_channel_dict", patch_get_channel_dict)
        monkey.patch_module(patch_manager_core_module)

    with monkey_zoo(COMFYUI_MANAGER_SERVER_MODULE) as monkey:

        def patch_manager_server_urls(code_object) -> None:
            replacements = {source_prefix: destination_prefix}
            _replace_string_constants_in_code(code_object, replacements)

        monkey.patch_bytecode(patch_manager_server_urls)

    def patch_manager_util_get_data(func: Any, module: ModuleType):
        @functools.wraps(func)
        async def wrapper(uri, *args, **kwargs):
            return await func(
                _replace_comfyui_manager_get_data_url(
                    uri,
                    source_prefix=source_prefix,
                    destination_prefix=destination_prefix,
                ),
                *args,
                **kwargs,
            )

        return wrapper

    with monkey_zoo(COMFYUI_MANAGER_UTIL_MODULE) as monkey:
        monkey.patch_function("get_data", patch_manager_util_get_data)


def apply_from_config(config: dict[str, Any] | None) -> None:
    """
    根据配置应用扩展索引补丁

    支持以下配置形式:

    ``{"webui": {"enabled": true, "url": "https://mirror/index.json"}}``
        启用 A1111 扩展索引替换。

    ``{"webui": {"enabled": true, "url": "auto"}}``
        自动检测网络, 需要时使用可用 GitHub raw 镜像。

    ``{"comfyui_manager": {"enabled": true, "url": "auto"}}``
        自动检测网络, 需要时使用可用 GitHub raw 镜像。

    ``{"comfyui_manager": {"enabled": true, "url": "https://mirror/channel"}}``
        使用自定义 ComfyUI-Manager channel 前缀。

    ``{"comfyui_manager": {"enabled": true, "url": "...", "source_prefix": "..."}}``
        使用自定义前缀启用 ComfyUI-Manager 替换。未设置 ``url`` 时按 ``auto`` 处理。

    Args:
        config (dict[str, Any] | None):
            扩展配置
    """

    if not config:
        return

    webui_config = config.get("webui")
    if isinstance(webui_config, dict) and webui_config.get("enabled"):
        resolved_extension_index_url = resolve_a1111_extension_index_url(str(webui_config.get("url") or A1111_EXTENSION_INDEX_AUTO))
        if resolved_extension_index_url:
            patch_extension_index_a1111(resolved_extension_index_url)

    comfyui_config = config.get("comfyui_manager")
    if isinstance(comfyui_config, dict) and comfyui_config.get("enabled"):
        patch_extension_index_comfyui_manager(
            str(comfyui_config.get("url") or A1111_EXTENSION_INDEX_AUTO),
            source_prefix=str(comfyui_config.get("source_prefix", COMFYUI_MANAGER_RAW_PREFIX)),
        )


def _replace_string_constants_in_code(code_object: Any, replacements: dict[str, str]) -> None:
    _replace_string_constants_in_tuple(code_object.co_consts, replacements)


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


def _add_valid_channel(module: ModuleType, url: str) -> None:
    valid_channels = getattr(module, "valid_channels", None)
    if hasattr(valid_channels, "add"):
        valid_channels.add(url)


def _replace_string_constants_in_tuple(constants: Any, replacements: dict[str, str]) -> None:
    constants.replace(
        lambda const: isinstance(const, str) and const in replacements,
        lambda const: replacements[const],
    )
    for nested_code in constants.operate(lambda const: isinstance(const, CodeType)):
        _replace_string_constants_in_code(nested_code, replacements)
    for nested_tuple in constants.operate(lambda const: isinstance(const, tuple)):
        _replace_string_constants_in_tuple(nested_tuple, replacements)
