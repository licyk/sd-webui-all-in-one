"""ZLUDA 兼容性扩展补丁"""

from __future__ import annotations

import ctypes
import glob
import os
from functools import wraps
from pathlib import Path
from types import ModuleType
from typing import Any

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

__all__ = [
    "apply_from_config",
    "apply_torch_zluda_timer_hotfix",
    "apply_zluda_compat",
    "apply_zluda_library",
]


def apply_zluda_library(library_path: str | os.PathLike[str]) -> None:
    """
    在 ``torch`` 执行前加载 ZLUDA DLL

    行为对应原 ``swlpatches.zluda_companion.apply_zluda_library``, 但通过抽取后的
    ``sd_webui_all_in_one_hotpatcher`` import hook 注册。

    Args:
        library_path (str | os.PathLike[str]):
            ZLUDA DLL 所在目录
    """

    install_import_hook()
    dll_path = str(Path(library_path))

    with monkey_zoo("torch") as monkey:

        def load_zluda_module(module: ModuleType) -> None:
            if os.name != "nt":
                raise RuntimeError("ZLUDA DLL loading is only supported on Windows")

            kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
            with_load_library_flags = hasattr(kernel32, "AddDllDirectory")
            prev_error_mode = kernel32.SetErrorMode(0x0001)

            try:
                kernel32.LoadLibraryW.restype = ctypes.c_void_p
                if with_load_library_flags:
                    kernel32.LoadLibraryExW.restype = ctypes.c_void_p

                dlls = glob.glob(os.path.join(dll_path, "*.dll"))
                path_patched = False
                for dll in dlls:
                    is_loaded = False
                    if with_load_library_flags:
                        res = kernel32.LoadLibraryExW(dll, None, 0x00001100)
                        last_error = ctypes.get_last_error()
                        if res is None and last_error != 126:
                            err = ctypes.WinError(last_error)
                            err.strerror = f"{err.strerror or ''} Error loading '{dll}' or one of its dependencies."
                            raise err
                        if res is not None:
                            is_loaded = True

                    if not is_loaded:
                        if not path_patched:
                            os.environ["PATH"] = ";".join([dll_path, os.environ.get("PATH", "")])
                            path_patched = True
                        res = kernel32.LoadLibraryW(dll)
                        if res is None:
                            err = ctypes.WinError(ctypes.get_last_error())
                            err.strerror = f"{err.strerror or ''} Error loading '{dll}' or one of its dependencies."
                            raise err
            finally:
                kernel32.SetErrorMode(prev_error_mode)

        monkey.patch_premodule(load_zluda_module)


def apply_zluda_compat() -> None:
    """补丁 torch CUDA backend 标志以适配 ZLUDA"""

    install_import_hook()

    with monkey_zoo("torch") as monkey:

        def set_torch_var(module: ModuleType) -> None:
            module.backends.cudnn.enabled = False
            module.backends.cuda.enable_flash_sdp(False)
            module.backends.cuda.enable_math_sdp(True)
            module.backends.cuda.enable_mem_efficient_sdp(False)

        monkey.patch_module(set_torch_var)

    with monkey_zoo("torch.backends.cuda") as monkey:

        def always_false_fn(func: Any, module: ModuleType):
            @wraps(func)
            def always_false(enabled):
                return func(False)

            return always_false

        monkey.patch_function("enable_flash_sdp", always_false_fn)
        monkey.patch_function("enable_mem_efficient_sdp", always_false_fn)


def apply_torch_zluda_timer_hotfix() -> None:
    """补丁 ``torch.utils.cpp_extension`` 源码以修复 Windows ZLUDA timer 构建"""

    install_import_hook()

    with monkey_zoo("torch.utils.cpp_extension") as monkey:

        def zluda_patch(source: str, filename: str) -> str:
            source = source.replace(
                "HIP_HOME = _join_rocm_home('hip') if ROCM_HOME else None",
                "HIP_HOME = ROCM_HOME",
            )
            source = source.replace(
                """    elif IS_WINDOWS:
        raise""",
                """    elif IS_WINDOWS and False:
        raise""",
            )
            return source

        monkey.patch_sources(zluda_patch)


def apply_from_config(config: dict[str, Any] | None) -> None:
    """
    根据配置应用 ZLUDA 扩展补丁

    支持的配置形式:

    ``{"compat": true, "path": "C:/zluda", "torch_zluda_timer": true}``

    Args:
        config (dict[str, Any] | None):
            扩展配置
    """

    if not config:
        return

    if config.get("compat"):
        apply_zluda_compat()

    library_path = config.get("path")
    if library_path:
        apply_zluda_library(library_path)

    if config.get("torch_zluda_timer"):
        apply_torch_zluda_timer_hotfix()
