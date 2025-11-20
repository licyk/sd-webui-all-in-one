import shlex
import subprocess
from functools import wraps

from sdaio_utils.logger import get_logger
from sdaio_utils.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="uv Patcher",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def patch_uv_to_subprocess(symlink: bool | None = False) -> None:
    """使用 subprocess 执行 Pip 时替换成 uv"""
    if hasattr(subprocess, "__original_run"):
        return

    logger.debug("启用 uv patch")
    subprocess.__original_run = subprocess.run

    @wraps(subprocess.__original_run)
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
            return subprocess.__original_run([*command, *_args], **kwargs)

        cmd = command[command.index("pip") + 1 :]

        bad_flags = ("--prefer-binary", "--ignore-installed", "-I")
        cmd = [arg for arg in cmd if arg not in bad_flags]

        modified_command: list[str] = ["uv", "pip", *cmd]

        if symlink:
            modified_command.extend(["--link-mode", "symlink"])

        if kwargs.get("shell", False):
            logger.debug("使用命令字符串")
            command = shlex.join([*modified_command, *_args])
        else:
            logger.debug("使用命令列表")
            command = [*modified_command, *_args]

        logger.debug("处理后的命令: %s", command)
        return subprocess.__original_run(command, **kwargs)

    subprocess.run = patched_run
