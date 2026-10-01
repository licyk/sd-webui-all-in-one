"""Fooocus 启动参数检查子进程"""

import importlib
import sys
from pathlib import Path
from typing import Any

from sd_webui_all_in_one.env_check.shared import logger


def _fooocus_parser_has_arg(parser: Any, option_name: str) -> bool:
    option_string_actions = getattr(parser, "_option_string_actions", None)
    if isinstance(option_string_actions, dict):
        return option_name in option_string_actions

    actions = getattr(parser, "_actions", None)
    if actions is None:
        return False

    return any(option_name in getattr(action, "option_strings", ()) for action in actions)


def _check_fooocus_hf_mirror_arg_worker(fooocus_path: Path, conn: Any) -> None:
    sys.path.insert(0, fooocus_path.as_posix())

    try:
        args_parser = importlib.import_module("ldm_patched.modules.args_parser")
        parser = getattr(args_parser, "parser", None)
        conn.send(_fooocus_parser_has_arg(parser, "--hf-mirror"))
    except Exception as e:
        logger.debug("检查 Fooocus --hf-mirror 参数支持时发生错误: %s", e)
        conn.send(False)
    finally:
        conn.close()
