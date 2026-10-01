"""扩展索引镜像补丁注册"""

from __future__ import annotations

import functools
from types import CodeType, ModuleType
from typing import Any

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

from .constants import (
    A1111_EXTENSION_INDEX_URLS,
    COMFYUI_MANAGER_CORE_MODULE,
    COMFYUI_MANAGER_RAW_PREFIX,
    COMFYUI_MANAGER_SERVER_MODULE,
    COMFYUI_MANAGER_UTIL_MODULE,
)
from .mirror import (
    _normalize_comfyui_manager_channel_prefix,
    _replace_comfyui_manager_channel_url,
    _replace_comfyui_manager_get_data_url,
    resolve_comfyui_manager_channel_prefix,
)


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


def _replace_string_constants_in_code(code_object: Any, replacements: dict[str, str]) -> None:
    _replace_string_constants_in_tuple(code_object.co_consts, replacements)


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
