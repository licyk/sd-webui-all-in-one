"""xFormers CUTLASS CUDA compute capability 热补丁。"""

from __future__ import annotations

import logging
import sys
from importlib import metadata
from types import ModuleType
from typing import Any

from sd_webui_all_in_one.package_analyzer import PyWhlVersionComparison
from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

__all__ = [
    "TARGET_CAPABILITY",
    "apply_cutlass_cuda_capability_patch",
    "apply_from_config",
    "is_xformers_cutlass_patch_active",
    "patch_xformers_cutlass_cuda_capability",
    "should_patch_xformers_cutlass",
]

TARGET_MODULE = "xformers.ops.fmha.cutlass"
TARGET_CAPABILITY = (12, 1)
_MIN_TORCH_VERSION = "2.9.0"
_MIN_XFORMERS_VERSION = "0.0.33"
_PATCH_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_xformers_cutlass_patch"

logger = logging.getLogger(__name__)


def should_patch_xformers_cutlass() -> bool:
    """
    检查当前安装的 torch 和 xformers 版本是否满足补丁条件。

    返回:
        bool:
            torch >= 2.9.0 且 xformers >= 0.0.33 时返回 True。
    """

    try:
        torch_version = metadata.version("torch")
        xformers_version = metadata.version("xformers")
    except Exception as exc:
        logger.debug("跳过 xFormers CUTLASS 热补丁，无法获取软件包版本: %s", exc)
        return False

    try:
        return _version_at_least(torch_version, _MIN_TORCH_VERSION) and _version_at_least(xformers_version, _MIN_XFORMERS_VERSION)
    except Exception as exc:
        logger.debug(
            "跳过 xFormers CUTLASS 热补丁，版本比较失败: torch=%s xformers=%s error=%s",
            torch_version,
            xformers_version,
            exc,
        )
        return False


def patch_xformers_cutlass_cuda_capability() -> bool:
    """
    注册并立即应用 xFormers CUTLASS capability 热补丁。

    返回:
        bool:
            版本条件满足且补丁已注册时返回 True。
    """

    if not should_patch_xformers_cutlass():
        return False

    install_import_hook()
    _register_cutlass_module_patch()

    module = sys.modules.get(TARGET_MODULE)
    if module is not None:
        apply_cutlass_cuda_capability_patch(module)

    return True


def apply_cutlass_cuda_capability_patch(module: ModuleType) -> None:
    """
    设置 xFormers CUTLASS forward/backward op 的 CUDA capability 上限。

    参数:
        module (ModuleType):
            已导入的 ``xformers.ops.fmha.cutlass`` 模块。
    """

    for class_name in ("FwOp", "BwOp"):
        op_class = getattr(module, class_name, None)
        if op_class is not None:
            setattr(op_class, "CUDA_MAXIMUM_COMPUTE_CAPABILITY", TARGET_CAPABILITY)


def is_xformers_cutlass_patch_active() -> bool:
    """
    检查已导入的 CUTLASS 模块是否已经使用目标 capability。

    这个函数不会主动导入 xformers。

    返回:
        bool:
            FwOp 以及存在时的 BwOp 已经暴露 ``(12, 1)`` 时返回 True。
    """

    module = sys.modules.get(TARGET_MODULE)
    if module is None:
        return False

    fw_op = getattr(module, "FwOp", None)
    if getattr(fw_op, "CUDA_MAXIMUM_COMPUTE_CAPABILITY", None) != TARGET_CAPABILITY:
        return False

    bw_op = getattr(module, "BwOp", None)
    if bw_op is not None and getattr(bw_op, "CUDA_MAXIMUM_COMPUTE_CAPABILITY", None) != TARGET_CAPABILITY:
        return False

    return True


def apply_from_config(config: dict[str, Any] | None) -> bool:
    """
    根据扩展配置应用 xFormers CUTLASS CUDA capability 热补丁。

    参数:
        config (dict[str, Any] | None):
            扩展配置。

    返回:
        bool:
            补丁已注册时返回 True；禁用或跳过时返回 False。
    """

    if not config or not config.get("enabled"):
        return False
    return patch_xformers_cutlass_cuda_capability()


def _register_cutlass_module_patch() -> None:
    with monkey_zoo(TARGET_MODULE) as monkey:
        if any(getattr(hooker, _PATCH_MARKER_ATTR, False) for hooker, _priority in monkey.module_patches):
            return

        def patch_module(module: ModuleType) -> None:
            apply_cutlass_cuda_capability_patch(module)

        setattr(patch_module, _PATCH_MARKER_ATTR, True)
        monkey.patch_module(patch_module)


def _version_at_least(version: str, minimum: str) -> bool:
    return PyWhlVersionComparison(version).compare_versions(version, minimum, ignore_local=True) >= 0
