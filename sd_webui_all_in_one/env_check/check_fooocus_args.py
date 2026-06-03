"""检查 Fooocus 启动参数支持"""

import importlib
import multiprocessing
import sys
from pathlib import Path
from typing import Any

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


def check_fooocus_hf_mirror_arg(fooocus_path: Path, timeout: float = 10) -> bool:
    """检查 Fooocus 是否支持 --hf-mirror 启动参数

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        timeout (float):
            检查子进程超时时间, 单位为秒

    Returns:
        bool:
            支持 --hf-mirror 参数时返回 True, 否则返回 False
    """
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_check_fooocus_hf_mirror_arg_worker,
        args=(fooocus_path, child_conn),
        name="FooocusArgsCheck",
    )

    try:
        logger.debug("启动子进程检查 Fooocus --hf-mirror 参数支持")
        process.start()
        child_conn.close()
        process.join(timeout)

        if process.is_alive():
            logger.debug("检查 Fooocus --hf-mirror 参数支持超时")
            return False

        if process.exitcode not in (0, None):
            logger.debug("检查 Fooocus --hf-mirror 参数支持子进程退出码: %s", process.exitcode)

        if parent_conn.poll():
            return bool(parent_conn.recv())
    except Exception as e:
        logger.debug("通过子进程检查 Fooocus --hf-mirror 参数支持失败: %s", e)
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        parent_conn.close()
        if not child_conn.closed:
            child_conn.close()
        process.close()

    return False
