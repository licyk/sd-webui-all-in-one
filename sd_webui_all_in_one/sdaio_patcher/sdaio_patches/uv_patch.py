"""uv 补丁, 将调用 subprocess.run() 时执行的 Pip 命令替换成 uv"""

import shlex
import sys
import subprocess
from functools import wraps

from sdaio_utils.logger import get_logger
from sdaio_utils.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="uv Patcher",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def preprocess_command(command: list[str] | str, shell: bool) -> list[str] | str:
    """针对不同平台对命令进行预处理

    Args:
        command (list[str] | str): 原始命令
        shell (bool): 是否调用 Shell
    Returns:
        (list[str] | str): 处理后的命令
    """
    if sys.platform == "win32":
        # Windows
        # 字符串命令和列表命令都可行
        return command
    else:
        # Linux / MacOS
        if shell:
            # 使用字符串命令
            if isinstance(command, list):
                return shlex.join(command)
            return command
        # 使用列表命令
        if isinstance(command, str):
            return shlex.split(command)
        return command


def patch_uv_to_subprocess(symlink: bool | None = False) -> None:
    """使用 subprocess 执行 Pip 时替换成 uv"""
    if hasattr(subprocess, "__original_run"):
        return

    logger.debug("启用 uv patch")
    subprocess.__original_run = subprocess.run  # pylint: disable=protected-access

    @wraps(subprocess.__original_run)  # pylint: disable=protected-access
    def patched_run(*args, **kwargs):
        if args:
            command, *_args = args
        else:
            command, _args = kwargs.pop("args", ""), ()

        if isinstance(command, str):
            command = shlex.split(command)
        else:
            command = [arg.strip() for arg in command]

        assert isinstance(command, list)

        if "pip" not in command:
            return subprocess.__original_run(preprocess_command([*command, *_args], shell=kwargs.get("shell", False)), **kwargs)  # pylint: disable=protected-access

        cmd = command[command.index("pip") + 1 :]

        bad_flags = ("--prefer-binary", "--ignore-installed", "-I")
        cmd = [arg for arg in cmd if arg not in bad_flags]

        modified_command: list[str] = ["uv", "pip", *cmd]

        if symlink:
            modified_command.extend(["--link-mode", "symlink"])

        command = preprocess_command(
            command=[*modified_command, *_args],
            shell=kwargs.get("shell", False),
        )

        return subprocess.__original_run(command, **kwargs)  # pylint: disable=protected-access

    subprocess.run = patched_run
