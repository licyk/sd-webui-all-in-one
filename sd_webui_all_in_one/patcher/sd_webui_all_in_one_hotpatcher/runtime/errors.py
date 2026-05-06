"""普通 Python 异常运行时上报工具"""

from __future__ import annotations

import os
import platform
import sys
import traceback
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from ..exceptions import set_exception_reporter
from .client import RuntimeClient


@dataclass
class ExceptionReporter:
    """
    异常事件上报器

    Attributes:
        client (RuntimeClient):
            发送异常事件的运行时客户端
        include_locals (bool):
            是否包含局部变量。当前载荷格式暂未使用该字段。
    """

    client: RuntimeClient
    include_locals: bool = False

    def report(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        发送异常事件

        Args:
            exc_type (type[BaseException]):
                异常类型
            exc_value (BaseException):
                异常值
            exc_tb (TracebackType | None):
                异常 traceback
        """

        self.client.event("error.exception", format_exception_payload(exc_type, exc_value, exc_tb))


def install_exception_reporter(
    client: RuntimeClient,
    *,
    include_locals: bool = False,
) -> ExceptionReporter:
    """
    安装进程级异常上报器

    Args:
        client (RuntimeClient):
            发送异常事件的运行时客户端
        include_locals (bool):
            是否包含局部变量。当前版本暂不序列化局部变量。

    Returns:
        ExceptionReporter:
            已安装的异常上报器
    """

    reporter = ExceptionReporter(client=client, include_locals=include_locals)
    set_exception_reporter(reporter.report)
    return reporter


def uninstall_exception_reporter() -> None:
    """卸载进程级异常上报器"""

    set_exception_reporter(None)


def format_exception_payload(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> dict[str, Any]:
    """
    格式化异常事件载荷

    Args:
        exc_type (type[BaseException]):
            异常类型
        exc_value (BaseException):
            异常值
        exc_tb (TracebackType | None):
            异常 traceback

    Returns:
        dict[str, Any]:
            可 JSON 序列化的异常载荷
    """

    formatted = traceback.format_exception(exc_type, exc_value, exc_tb)
    return {
        "type": f"{exc_type.__module__}.{exc_type.__qualname__}",
        "name": exc_type.__name__,
        "message": str(exc_value),
        "traceback": "".join(formatted),
        "frames": _frames_from_traceback(exc_tb),
        "process": {
            "pid": os.getpid(),
            "executable": sys.executable,
            "python": platform.python_version(),
        },
    }


def _frames_from_traceback(exc_tb: TracebackType | None) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    while exc_tb is not None:
        frame = exc_tb.tb_frame
        frames.append(
            {
                "filename": frame.f_code.co_filename,
                "function": frame.f_code.co_name,
                "lineno": exc_tb.tb_lineno,
                "module": frame.f_globals.get("__name__"),
            }
        )
        exc_tb = exc_tb.tb_next
    return frames
