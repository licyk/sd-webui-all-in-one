"""ComfyUI 默认端口自动避让热补丁。"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo
from sd_webui_all_in_one_hotpatcher.logger import get_hotpatcher_logger

__all__ = [
    "TARGET_MODULE",
    "adjust_comfyui_default_port",
    "apply_from_config",
    "is_comfyui_auto_port_patch_registered",
    "patch_comfyui_auto_port",
]

TARGET_MODULE = "comfy.cli_args"
_PATCH_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_comfyui_auto_port_patch"

logger = get_hotpatcher_logger(__name__)


def adjust_comfyui_default_port(module: ModuleType) -> bool:
    """在 ComfyUI 使用 parser 默认端口时选择可用端口。

    Args:
        module (ModuleType):
            已导入的 ``comfy.cli_args`` 模块。

    Returns:
        bool:
            找到 ComfyUI 参数对象并确认其正在使用默认端口时返回 True。
    """

    args = getattr(module, "args", None)
    parser = getattr(module, "parser", None)
    if args is None or parser is None or not hasattr(args, "port"):
        return False

    default_port = parser.get_default("port")
    if not isinstance(default_port, int) or args.port != default_port:
        return False

    from sd_webui_all_in_one.utils import find_port

    available_port = find_port(default_port)
    if available_port != default_port:
        logger.info("ComfyUI 默认端口 %s 已被占用，自动改用端口 %s", default_port, available_port)
    args.port = available_port
    return True


def patch_comfyui_auto_port() -> None:
    """注册 ComfyUI 默认端口自动避让补丁，并处理已导入模块。"""

    install_import_hook()
    _register_comfyui_cli_args_patch()

    module = sys.modules.get(TARGET_MODULE)
    if module is not None:
        adjust_comfyui_default_port(module)


def is_comfyui_auto_port_patch_registered() -> bool:
    """检查 ComfyUI 默认端口补丁是否已经注册。

    Returns:
        bool:
            补丁已经注册时返回 True。
    """

    monkey = monkey_zoo[TARGET_MODULE]
    if monkey is None:
        return False
    return any(getattr(hooker, _PATCH_MARKER_ATTR, False) for hooker, _priority in monkey.module_patches)


def apply_from_config(config: dict[str, Any] | None) -> None:
    """根据扩展配置注册 ComfyUI 默认端口自动避让补丁。

    Args:
        config (dict[str, Any] | None):
            扩展配置。
    """

    if config and config.get("enabled"):
        patch_comfyui_auto_port()


def _register_comfyui_cli_args_patch() -> None:
    with monkey_zoo(TARGET_MODULE) as monkey:
        if any(getattr(hooker, _PATCH_MARKER_ATTR, False) for hooker, _priority in monkey.module_patches):
            return

        def patch_module(module: ModuleType) -> None:
            adjust_comfyui_default_port(module)

        setattr(patch_module, _PATCH_MARKER_ATTR, True)
        monkey.patch_module(patch_module)
