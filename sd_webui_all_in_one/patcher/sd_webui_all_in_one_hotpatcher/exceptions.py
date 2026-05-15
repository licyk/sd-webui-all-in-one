"""热补丁内部异常上报工具"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from typing import Any

ExceptionReporter = Callable[[type[BaseException], BaseException, Any], None]

_exception_reporter: ExceptionReporter | None = None


def set_exception_reporter(reporter: ExceptionReporter | None) -> None:
    """
    设置进程级异常上报器

    Args:
        reporter (ExceptionReporter | None):
            ``capture_exception`` 捕获异常后调用的上报函数。
            传入 None 时清除当前上报器。
    """

    global _exception_reporter
    _exception_reporter = reporter


def capture_exception(exc: BaseException | None = None, /, **_: Any) -> None:
    """
    捕获并打印异常

    用于补丁执行链内部, 确保某个补丁失败时不会直接打断目标模块导入。

    Args:
        exc (BaseException | None):
            要上报的异常对象。为 None 时读取当前异常上下文。
        **_:
            兼容调用方传入的额外上下文
    """

    if exc is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value is None:
            return
        traceback.print_exception(exc_type, exc_value, exc_tb)
        _report_exception(exc_type, exc_value, exc_tb)
        return

    traceback.print_exception(type(exc), exc, exc.__traceback__)
    _report_exception(type(exc), exc, exc.__traceback__)


def _report_exception(exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
    if _exception_reporter is None:
        return
    try:
        _exception_reporter(exc_type, exc_value, exc_tb)
    except Exception:
        traceback.print_exc()
