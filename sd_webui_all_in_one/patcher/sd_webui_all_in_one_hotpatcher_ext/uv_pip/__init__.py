"""uv pip 命令替换补丁"""

from __future__ import annotations

import logging
import shlex
import subprocess
import sys
from collections.abc import Sequence
from functools import wraps
from typing import Any

__all__ = [
    "apply_from_config",
    "is_uv_patch_installed",
    "patch_uv_to_subprocess",
    "preprocess_command",
    "unpatch_uv_to_subprocess",
]

_ORIGINAL_RUN_ATTR = "_sd_webui_all_in_one_hotpatcher_uv_original_run"
_WRAPPER_ATTR = "_sd_webui_all_in_one_hotpatcher_uv_wrapper"
_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_uv_patch"
_BAD_PIP_FLAGS = ("--prefer-binary", "--ignore-installed", "-I")

logger = logging.getLogger(__name__)


def preprocess_command(command: list[str] | str, shell: bool) -> list[str] | str:
    """
    针对不同平台对命令进行预处理

    Args:
        command (list[str] | str):
            待执行命令
        shell (bool):
            是否使用 shell 执行命令

    Returns:
        list[str] | str:
            预处理后的命令
    """

    if sys.platform == "win32":
        return command
    if shell:
        if isinstance(command, list):
            return shlex.join(command)
        return command
    if isinstance(command, str):
        return shlex.split(command)
    return command


def patch_uv_to_subprocess(symlink: bool | None = False) -> None:
    """
    使用 ``subprocess.run()`` 执行 Pip 时替换成 uv

    该补丁会包装当前的 ``subprocess.run``。如果其它软件已经先安装了 wrapper,
    hotpatcher 会把它作为下游继续调用；如果其它软件之后替换了
    ``subprocess.run``，``unpatch_uv_to_subprocess()`` 不会覆盖那个新 wrapper。

    Args:
        symlink (bool | None):
            是否为 ``uv pip`` 添加 ``--link-mode symlink``
    """

    if is_uv_patch_installed():
        return

    original_run = subprocess.run
    logger.debug("启用 uv pip subprocess.run 补丁")

    @wraps(original_run)
    def patched_run(*args: Any, **kwargs: Any) -> Any:
        if args:
            command, *extra_args = args
        else:
            command = kwargs.pop("args", "")
            extra_args = []

        normalized = _normalize_command(command)
        if not _contains_pip_command(normalized):
            return original_run(
                preprocess_command([*normalized, *extra_args], shell=bool(kwargs.get("shell", False))),
                **kwargs,
            )

        pip_args = normalized[_pip_command_index(normalized) + 1 :]
        pip_args = [arg for arg in pip_args if arg not in _BAD_PIP_FLAGS]
        modified_command = ["uv", "pip", *pip_args]
        if symlink:
            modified_command.extend(["--link-mode", "symlink"])

        return original_run(
            preprocess_command([*modified_command, *extra_args], shell=bool(kwargs.get("shell", False))),
            **kwargs,
        )

    setattr(patched_run, _MARKER_ATTR, True)
    setattr(patched_run, _ORIGINAL_RUN_ATTR, original_run)
    setattr(subprocess, _ORIGINAL_RUN_ATTR, original_run)
    setattr(subprocess, _WRAPPER_ATTR, patched_run)
    subprocess.run = patched_run  # ty: ignore[invalid-assignment]


def unpatch_uv_to_subprocess() -> None:
    """卸载当前进程中的 uv pip ``subprocess.run`` 补丁"""

    wrapper = getattr(subprocess, _WRAPPER_ATTR, None)
    original_run = getattr(subprocess, _ORIGINAL_RUN_ATTR, None)
    if wrapper is not None and subprocess.run is wrapper and original_run is not None:
        subprocess.run = original_run

    for attr in (_WRAPPER_ATTR, _ORIGINAL_RUN_ATTR):
        if hasattr(subprocess, attr):
            delattr(subprocess, attr)


def is_uv_patch_installed() -> bool:
    """
    检查 uv pip ``subprocess.run`` 补丁是否已安装

    Returns:
        bool:
            已安装时返回 True
    """

    return bool(getattr(subprocess.run, _MARKER_ATTR, False))


def apply_from_config(config: dict[str, Any] | None) -> None:
    """
    根据配置启用 uv pip 命令替换补丁

    Args:
        config (dict[str, Any] | None):
            扩展配置
    """

    if not config:
        return
    if config.get("enabled"):
        patch_uv_to_subprocess(symlink=bool(config.get("symlink", False)))


def _normalize_command(command: str | Sequence[Any]) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return [str(arg).strip() for arg in command]


def _contains_pip_command(command: list[str]) -> bool:
    return any(_is_pip_command(arg) for arg in command)


def _pip_command_index(command: list[str]) -> int:
    for index, arg in enumerate(command):
        if _is_pip_command(arg):
            return index
    raise ValueError("pip command not found")


def _is_pip_command(arg: str) -> bool:
    normalized = arg.strip().lower().replace("\\", "/")
    name = normalized.rsplit("/", maxsplit=1)[-1]
    return name in {"pip", "pip.exe", "pip3", "pip3.exe"}
