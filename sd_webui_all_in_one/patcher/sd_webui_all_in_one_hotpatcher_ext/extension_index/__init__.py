"""扩展索引镜像补丁"""

from __future__ import annotations

import functools
from types import CodeType, ModuleType
from typing import Any

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

__all__ = [
    "A1111_EXTENSION_INDEX_URLS",
    "COMFYUI_MANAGER_MIRROR_PREFIX",
    "COMFYUI_MANAGER_RAW_PREFIX",
    "apply_from_config",
    "patch_extension_index_a1111",
    "patch_extension_index_comfyui_manager",
]

A1111_EXTENSION_INDEX_URLS = (
    "https://raw.githubusercontent.com/wiki/AUTOMATIC1111/stable-diffusion-webui/Extensions-index.md",
    "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json",
    # "https://vladmandic.github.io/sd-data/pages/extensions.json",
)

COMFYUI_MANAGER_RAW_PREFIX = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/"
COMFYUI_MANAGER_MIRROR_PREFIX = "https://ghfast.top/https://raw.githubusercontent.com//ltdrdata/ComfyUI-Manager/main/"
COMFYUI_MANAGER_MODULES = ("ComfyUI-Manager", "ComfyUI-Manager-main")


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
    destination_prefix: str = COMFYUI_MANAGER_MIRROR_PREFIX,
    *,
    source_prefix: str = COMFYUI_MANAGER_RAW_PREFIX,
) -> None:
    """
    重写 ComfyUI-Manager 资源 URL 前缀

    Args:
        destination_prefix (str):
            目标镜像前缀
        source_prefix (str):
            需要替换的原始前缀
    """

    install_import_hook()

    def patch_default_urls(code_object) -> None:
        for cache_update in code_object.co_consts.operate(
            lambda const: isinstance(const, CodeType) and const.co_name == "default_cache_update",
            only_first=True,
        ):
            for get_cache in cache_update.co_consts.operate(
                lambda const: isinstance(const, CodeType) and const.co_name == "get_cache",
                only_first=True,
            ):
                _replace_prefixed_string_constants_in_code(get_cache, source_prefix, destination_prefix)

    def patch_get_data(func: Any, module: ModuleType):
        @functools.wraps(func)
        def wrapper(uri, *args, **kwargs):
            if isinstance(uri, str) and uri.startswith(source_prefix):
                uri = uri.replace(source_prefix, destination_prefix, 1)
            return func(uri, *args, **kwargs)

        return wrapper

    for module_name in COMFYUI_MANAGER_MODULES:
        with monkey_zoo(module_name) as monkey:
            monkey.patch_function("get_data", patch_get_data)
            monkey.patch_bytecode(patch_default_urls)


def apply_from_config(config: dict[str, Any] | None) -> None:
    """
    根据配置应用扩展索引补丁

    支持以下配置形式:

    ``{"extension_index_url": "https://mirror/index.json"}``
        启用 A1111 扩展索引替换。

    ``{"a1111_url": "https://mirror/index.json"}``
        ``extension_index_url`` 的别名。

    ``{"comfyui_manager": true}``
        启用 ComfyUI-Manager 默认镜像。

    ``{"comfyui_manager": {"destination_prefix": "...", "source_prefix": "..."}}``
        使用自定义前缀启用 ComfyUI-Manager 替换。

    Args:
        config (dict[str, Any] | None):
            扩展配置
    """

    if not config:
        return

    a1111_url = config.get("extension_index_url") or config.get("a1111_url")
    if a1111_url:
        patch_extension_index_a1111(str(a1111_url))

    comfyui_config = config.get("comfyui_manager")
    if comfyui_config:
        if isinstance(comfyui_config, dict):
            patch_extension_index_comfyui_manager(
                str(comfyui_config.get("destination_prefix", COMFYUI_MANAGER_MIRROR_PREFIX)),
                source_prefix=str(comfyui_config.get("source_prefix", COMFYUI_MANAGER_RAW_PREFIX)),
            )
        else:
            patch_extension_index_comfyui_manager()


def _replace_string_constants_in_code(code_object: Any, replacements: dict[str, str]) -> None:
    _replace_string_constants_in_tuple(code_object.co_consts, replacements)


def _replace_string_constants_in_tuple(constants: Any, replacements: dict[str, str]) -> None:
    constants.replace(
        lambda const: isinstance(const, str) and const in replacements,
        lambda const: replacements[const],
    )
    for nested_code in constants.operate(lambda const: isinstance(const, CodeType)):
        _replace_string_constants_in_code(nested_code, replacements)
    for nested_tuple in constants.operate(lambda const: isinstance(const, tuple)):
        _replace_string_constants_in_tuple(nested_tuple, replacements)


def _replace_prefixed_string_constants_in_code(
    code_object: Any,
    source_prefix: str,
    destination_prefix: str,
) -> None:
    _replace_prefixed_string_constants_in_tuple(code_object.co_consts, source_prefix, destination_prefix)


def _replace_prefixed_string_constants_in_tuple(
    constants: Any,
    source_prefix: str,
    destination_prefix: str,
) -> None:
    constants.replace(
        lambda const: isinstance(const, str) and const.startswith(source_prefix),
        lambda const: const.replace(source_prefix, destination_prefix, 1),
    )
    for nested_code in constants.operate(lambda const: isinstance(const, CodeType)):
        _replace_prefixed_string_constants_in_code(nested_code, source_prefix, destination_prefix)
    for nested_tuple in constants.operate(lambda const: isinstance(const, tuple)):
        _replace_prefixed_string_constants_in_tuple(nested_tuple, source_prefix, destination_prefix)
