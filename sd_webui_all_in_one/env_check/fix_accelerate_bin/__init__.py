"""修复 accelerate 命令模块"""

from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.fix_accelerate_bin.fixer import (
    check_accelerate_bin,
)

__all__ = [
    "logger",
    "check_accelerate_bin",
]
