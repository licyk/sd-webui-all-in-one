"""热补丁内部异常上报工具"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from typing import Any

from .state import HotpatcherState, get_default_state

ExceptionReporter = Callable[[type[BaseException], BaseException, Any], None]


def set_exception_reporter(reporter: ExceptionReporter | None, *, state: HotpatcherState | None = None) -> None:
    """
    设置进程级异常上报器

    Args:
        reporter (ExceptionReporter | None):
            ``capture_exception`` 捕获异常后调用的上报函数。
            传入 None 时清除当前上报器。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    active_state = state or get_default_state()
    active_state.exception_reporter = reporter


def capture_exception(
    exc: BaseException | None = None,
    /,
    *,
    state: HotpatcherState | None = None,
    **_: Any,
) -> None:
    """
    捕获并打印异常

    用于补丁执行链内部, 确保某个补丁失败时不会直接打断目标模块导入。

    Args:
        exc (BaseException | None):
            要上报的异常对象。为 None 时读取当前异常上下文。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        **_:
            兼容调用方传入的额外上下文
    """

    active_state = state or get_default_state()
    if exc is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is None or exc_value is None:
            return
        traceback.print_exception(exc_type, exc_value, exc_tb)
        _report_exception(active_state, exc_type, exc_value, exc_tb)
        return

    traceback.print_exception(type(exc), exc, exc.__traceback__)
    _report_exception(active_state, type(exc), exc, exc.__traceback__)


def _report_exception(
    state: HotpatcherState,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> None:
    if state.exception_reporter is None:
        return
    try:
        state.exception_reporter(exc_type, exc_value, exc_tb)
    except Exception:
        traceback.print_exc()
