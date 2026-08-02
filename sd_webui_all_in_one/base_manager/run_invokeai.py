"""InvokeAI 启动器"""

from __future__ import annotations

import copy
import socket
import threading
import time
import traceback
import webbrowser
from typing import Any

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def _parser_has_option(parser: Any, option: str) -> bool:
    """判断 argparse parser 是否已有指定命令行选项"""
    option_actions = getattr(parser, "_option_string_actions", None)
    if isinstance(option_actions, dict):
        return option in option_actions

    for action in getattr(parser, "_actions", []):
        if option in getattr(action, "option_strings", []):
            return True
    return False


def _add_disable_auto_launch_arg(parser: Any) -> None:
    """为 InvokeAI 参数解析器补充禁止自动打开浏览器的参数"""
    if _parser_has_option(parser, "--disable-auto-launch"):
        return
    parser.add_argument("--disable-auto-launch", action="store_true", help="禁止自动启动浏览器打开 InvokeAI 界面")


def _open_browser_later(url: str) -> None:
    """延迟打开浏览器"""

    def _open_browser() -> None:
        time.sleep(2)
        logger.info("通过浏览器打开 InvokeAI 访问地址 '%s' 中", url)
        logger.info("如果需要禁用自动打开浏览器, 可通过 --disable-auto-launch 参数禁用该功能")
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.warning("打开浏览器时发生错误: %s", e)

    threading.Thread(target=_open_browser, daemon=True).start()


def main() -> None:
    """启动 InvokeAI"""
    import uvicorn
    import invokeai.frontend.cli.arg_parser  # ty: ignore[unresolved-import]
    from invokeai.frontend.cli.arg_parser import _parser, InvokeAIArgs  # ty: ignore[unresolved-import]
    from invokeai.app.run_app import run_app  # ty: ignore[unresolved-import]

    original_parser = copy.deepcopy(_parser)
    original_uvicorn_serve = uvicorn.Server.serve

    run_successful = False
    try:
        _add_disable_auto_launch_arg(_parser)
        args = InvokeAIArgs.parse_args()

        async def _patched_serve(
            self: uvicorn.Server,
            sockets: list[socket.socket] | None = None,
        ) -> None:
            host = self.config.host
            port = self.config.port
            url = f"http://{host}:{port}"
            logger.debug("获取到的 InvokeAI 访问地址: %s", url)
            if not getattr(args, "disable_auto_launch", False):
                _open_browser_later(url)
            return await original_uvicorn_serve(self, sockets)

        uvicorn.Server.serve = _patched_serve
        run_app()
        run_successful = True
    except KeyboardInterrupt:
        logger.debug("捕获到 Ctrl + C 中断信号")
        run_successful = True
    except Exception as e:
        traceback.print_exc()
        logger.error("运行时发生 %s 错误: %s", type(e).__name__, e)
    finally:
        logger.debug("清理 Monkey patches")
        uvicorn.Server.serve = original_uvicorn_serve
        invokeai.frontend.cli.arg_parser._parser = original_parser  # pylint: disable=protected-access
        InvokeAIArgs.args = None
        InvokeAIArgs.did_parse = False

        if not run_successful:
            logger.warning("检测到异常, 尝试使用原始配置重新启动")
            run_app()


if __name__ == "__main__":
    main()
