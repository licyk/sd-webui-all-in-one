"""SSH 密钥生成工具"""

import shlex
import subprocess
from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def gen_ssh_key(path: Path) -> bool:
    """生成 SSH 密钥

    Args:
        path (Path):
            生成 SSH 密钥的路径

    Returns:
        bool: 生成成功时返回 True，失败时返回 False
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        arg_string = f'ssh-keygen -t rsa -b 4096 -N "" -q -f {path.as_posix()}'
        args = shlex.split(arg_string)
        subprocess.run(args, check=True)
        path.chmod(0o600)
        logger.info("SSH 密钥生成成功: %s", path)
        return True
    except Exception as e:
        logger.error("生成 SSH 密钥失败: %s", e)
        return False
