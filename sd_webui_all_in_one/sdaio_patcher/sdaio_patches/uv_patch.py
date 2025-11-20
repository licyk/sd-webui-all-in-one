import sys
import copy
import shlex
import subprocess
from functools import wraps
from pathlib import Path

from sdaio_utils.logger import get_logger
from sdaio_utils.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="uv Patcher",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


BAD_FLAGS = ("--prefer-binary", "-I", "--ignore-installed")


def patch_uv_to_subprocess() -> None:
    """使用 subprocess 执行 Pip 时替换成 uv"""
    if hasattr(subprocess, "__original_run"):
        return

    logger.debug("启用 uv patch")
    try:
        subprocess.run(["uv", "-V"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        subprocess.run([Path(sys.executable).as_posix(), "-m", "pip", "install", "uv"])

    subprocess.__original_run = subprocess.run

    @wraps(subprocess.__original_run)
    def patched_run(*args, **kwargs):
        _kwargs = copy.copy(kwargs)
        if args:
            command, *_args = args
        else:
            command, _args = _kwargs.pop("args", ""), ()

        if isinstance(command, str):
            command = shlex.split(command)
        else:
            command = [arg.strip() for arg in command]

        if not isinstance(command, list) or "pip" not in command:
            return subprocess.__original_run(*args, **kwargs)

        cmd = command[command.index("pip") + 1 :]

        cmd = [arg for arg in cmd if arg not in BAD_FLAGS]

        modified_command = ["uv", "pip", *cmd]

        cmd_str = shlex.join([*modified_command, *_args])
        result = subprocess.__original_run(cmd_str, **_kwargs)
        if result.returncode != 0:
            return subprocess.__original_run(*args, **kwargs)
        return result

    subprocess.run = patched_run
