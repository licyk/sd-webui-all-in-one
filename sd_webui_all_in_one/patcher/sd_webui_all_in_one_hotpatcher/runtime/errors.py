"""普通 Python 异常运行时上报工具"""

from __future__ import annotations

import asyncio
import os
import platform
import sys
import threading
import traceback
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from ..exceptions import set_exception_reporter
from .client import RuntimeClient

_LOCAL_REPR_MAX_CHARS = 512
_LOCAL_FRAME_LIMIT = 40
_LOCAL_TOTAL_REPR_BUDGET = 32768
_SENSITIVE_LOCAL_NAME_PARTS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "authorization",
    "cookie",
    "session",
    "credential",
    "bearer",
)
_current_capture: ErrorCapture | None = None
_guard = threading.local()


@dataclass
class ExceptionReporter:
    """
    异常事件上报器

    Attributes:
        client (RuntimeClient):
            发送异常事件的运行时客户端
        include_locals (bool):
            是否包含脱敏后的局部变量摘要。
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

        _send_exception_event(self.client, exc_type, exc_value, exc_tb, include_locals=self.include_locals)


@dataclass
class ErrorCapture:
    """
    全局异常捕获器

    捕获后会先发送 ``error.exception`` 事件, 再调用目标进程原本安装的 hook,
    让 ComfyUI 等应用原有的控制台报错行为保持不变。
    """

    client: RuntimeClient
    include_locals: bool = False
    sys_excepthook: bool = True
    threading_excepthook: bool = True
    unraisablehook: bool = True
    asyncio: bool = True
    closed: bool = False

    def __post_init__(self) -> None:
        self._original_sys_excepthook: Any = None
        self._original_threading_excepthook: Any = None
        self._original_unraisablehook: Any = None
        self._original_asyncio_call_exception_handler: Any = None
        self._sys_wrapper: Any = None
        self._threading_wrapper: Any = None
        self._unraisable_wrapper: Any = None
        self._asyncio_wrapper: Any = None

    def install(self) -> "ErrorCapture":
        """安装已配置的全局异常 hook"""

        install_exception_reporter(self.client, include_locals=self.include_locals)

        if self.sys_excepthook:
            self._original_sys_excepthook = sys.excepthook
            self._sys_wrapper = self._handle_sys_excepthook
            sys.excepthook = self._sys_wrapper

        if self.threading_excepthook and hasattr(threading, "excepthook"):
            self._original_threading_excepthook = threading.excepthook
            self._threading_wrapper = self._handle_threading_excepthook
            threading.excepthook = self._threading_wrapper

        if self.unraisablehook and hasattr(sys, "unraisablehook"):
            self._original_unraisablehook = sys.unraisablehook
            self._unraisable_wrapper = self._handle_unraisablehook
            sys.unraisablehook = self._unraisable_wrapper

        if self.asyncio:
            self._original_asyncio_call_exception_handler = asyncio_module.BaseEventLoop.call_exception_handler
            self._asyncio_wrapper = self._make_asyncio_wrapper(self._original_asyncio_call_exception_handler)
            asyncio_module.BaseEventLoop.call_exception_handler = self._asyncio_wrapper

        return self

    def close(self) -> None:
        """卸载异常捕获 hook 并恢复原始 hook"""

        if self.closed:
            return
        self.closed = True

        if self._sys_wrapper is not None and sys.excepthook is self._sys_wrapper:
            sys.excepthook = self._original_sys_excepthook

        if (
            self._threading_wrapper is not None
            and hasattr(threading, "excepthook")
            and threading.excepthook is self._threading_wrapper
        ):
            threading.excepthook = self._original_threading_excepthook

        if self._unraisable_wrapper is not None and hasattr(sys, "unraisablehook") and sys.unraisablehook is self._unraisable_wrapper:
            sys.unraisablehook = self._original_unraisablehook

        if (
            self._asyncio_wrapper is not None
            and asyncio_module.BaseEventLoop.call_exception_handler is self._asyncio_wrapper
        ):
            asyncio_module.BaseEventLoop.call_exception_handler = self._original_asyncio_call_exception_handler

        uninstall_exception_reporter()

    def _handle_sys_excepthook(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        _send_exception_event(
            self.client,
            exc_type,
            exc_value,
            exc_tb,
            source="sys.excepthook",
            include_locals=self.include_locals,
        )
        self._call_original(self._original_sys_excepthook, exc_type, exc_value, exc_tb)

    def _handle_threading_excepthook(self, args: Any) -> None:
        thread = getattr(args, "thread", None)
        context = {
            "thread_name": getattr(thread, "name", None),
            "thread_ident": getattr(thread, "ident", None),
        }
        exc_type = getattr(args, "exc_type", BaseException)
        exc_value = getattr(args, "exc_value", None)
        exc_tb = getattr(args, "exc_traceback", None)
        if isinstance(exc_value, BaseException):
            _send_exception_event(
                self.client,
                exc_type,
                exc_value,
                exc_tb,
                source="threading.excepthook",
                context=context,
                include_locals=self.include_locals,
            )
        self._call_original(self._original_threading_excepthook, args)

    def _handle_unraisablehook(self, args: Any) -> None:
        context = {
            "err_msg": getattr(args, "err_msg", None),
            "object": _safe_repr(getattr(args, "object", None)),
        }
        exc_type = getattr(args, "exc_type", BaseException)
        exc_value = getattr(args, "exc_value", None)
        exc_tb = getattr(args, "exc_traceback", None)
        if isinstance(exc_value, BaseException):
            _send_exception_event(
                self.client,
                exc_type,
                exc_value,
                exc_tb,
                source="sys.unraisablehook",
                context=context,
                include_locals=self.include_locals,
            )
        self._call_original(self._original_unraisablehook, args)

    def _make_asyncio_wrapper(self, original: Any) -> Any:
        def call_exception_handler(loop: Any, context: dict[str, Any]) -> None:
            self._handle_asyncio_exception(context)
            return original(loop, context)

        call_exception_handler._sd_webui_all_in_one_hotpatcher_error_capture = True  # type: ignore[attr-defined]
        return call_exception_handler

    def _handle_asyncio_exception(self, context: dict[str, Any]) -> None:
        exception = context.get("exception")
        event_context = {
            "message": context.get("message"),
            "future": _safe_repr(context.get("future")) if "future" in context else None,
            "task": _safe_repr(context.get("task")) if "task" in context else None,
            "handle": _safe_repr(context.get("handle")) if "handle" in context else None,
        }
        if isinstance(exception, BaseException):
            _send_exception_event(
                self.client,
                type(exception),
                exception,
                exception.__traceback__,
                source="asyncio",
                context=event_context,
                include_locals=self.include_locals,
            )
            return

        message = str(context.get("message") or "asyncio event loop exception")
        generated = RuntimeError(message)
        _send_exception_event(
            self.client,
            type(generated),
            generated,
            generated.__traceback__,
            source="asyncio",
            context=event_context,
            include_locals=self.include_locals,
        )

    @staticmethod
    def _call_original(callback: Any, *args: Any) -> None:
        if callback is None:
            return
        callback(*args)


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
            是否包含脱敏后的局部变量摘要。

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


def install_error_capture(
    client: RuntimeClient,
    *,
    sys_excepthook: bool = True,
    threading_excepthook: bool = True,
    unraisablehook: bool = True,
    asyncio: bool = True,
    include_locals: bool = False,
) -> ErrorCapture:
    """
    安装全局 Python 运行时错误捕获

    Args:
        client (RuntimeClient):
            发送异常事件的运行时客户端
        sys_excepthook (bool):
            是否捕获主线程未处理异常
        threading_excepthook (bool):
            是否捕获线程未处理异常
        unraisablehook (bool):
            是否捕获 unraisable 异常
        asyncio (bool):
            是否捕获 asyncio event loop 异常
        include_locals (bool):
            是否包含脱敏后的局部变量摘要。

    Returns:
        ErrorCapture:
            已安装的错误捕获器
    """

    global _current_capture

    uninstall_error_capture()
    capture = ErrorCapture(
        client=client,
        include_locals=include_locals,
        sys_excepthook=sys_excepthook,
        threading_excepthook=threading_excepthook,
        unraisablehook=unraisablehook,
        asyncio=asyncio,
    ).install()
    _current_capture = capture
    return capture


def uninstall_error_capture() -> None:
    """卸载当前全局 Python 运行时错误捕获"""

    global _current_capture

    capture = _current_capture
    _current_capture = None
    if capture is not None:
        capture.close()


def is_error_capture_installed() -> bool:
    """
    检查全局错误捕获是否已安装

    Returns:
        bool:
            当前错误捕获器是否处于安装状态
    """

    return _current_capture is not None and not _current_capture.closed


def configure_error_capture_from_env(
    client: RuntimeClient,
    config: dict[str, Any] | None = None,
) -> ErrorCapture | None:
    """
    根据环境变量和配置安装错误捕获

    ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERRORS=1`` 或配置
    ``runtime.errors.enabled=true`` 时启用。
    """

    config_errors = _config_errors(config)
    enabled = _env_bool("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERRORS", default=_config_enabled(config_errors))
    if not enabled:
        uninstall_error_capture()
        return None

    return install_error_capture(
        client,
        sys_excepthook=_env_bool(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_SYS_EXCEPTHOOK",
            default=_config_bool(config_errors, "sys_excepthook", True),
        ),
        threading_excepthook=_env_bool(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_THREADING_EXCEPTHOOK",
            default=_config_bool(config_errors, "threading_excepthook", True),
        ),
        unraisablehook=_env_bool(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_UNRAISABLEHOOK",
            default=_config_bool(config_errors, "unraisablehook", True),
        ),
        asyncio=_env_bool(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_ASYNCIO",
            default=_config_bool(config_errors, "asyncio", True),
        ),
        include_locals=_env_bool(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_ERROR_INCLUDE_LOCALS",
            default=_config_bool(config_errors, "include_locals", False),
        ),
    )


def format_exception_payload(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
    *,
    source: str | None = None,
    context: dict[str, Any] | None = None,
    include_locals: bool = False,
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
    payload: dict[str, Any] = {
        "type": f"{exc_type.__module__}.{exc_type.__qualname__}",
        "name": exc_type.__name__,
        "message": str(exc_value),
        "traceback": "".join(formatted),
        "frames": _frames_from_traceback(exc_tb, include_locals=include_locals),
        "process": {
            "pid": os.getpid(),
            "executable": sys.executable,
            "python": platform.python_version(),
        },
    }
    if source is not None:
        payload["source"] = source
    if context:
        payload["context"] = _json_safe_context(context)
    return payload


def _frames_from_traceback(exc_tb: TracebackType | None, *, include_locals: bool = False) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    budget = _LocalBudget(_LOCAL_TOTAL_REPR_BUDGET)
    while exc_tb is not None:
        frame = exc_tb.tb_frame
        frame_payload = {
            "filename": frame.f_code.co_filename,
            "function": frame.f_code.co_name,
            "lineno": exc_tb.tb_lineno,
            "module": frame.f_globals.get("__name__"),
        }
        if include_locals:
            frame_payload["locals"] = _locals_from_frame(frame, budget)
        frames.append(frame_payload)
        exc_tb = exc_tb.tb_next
    return frames


def _send_exception_event(
    client: RuntimeClient,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
    *,
    source: str | None = None,
    context: dict[str, Any] | None = None,
    include_locals: bool = False,
) -> None:
    if getattr(_guard, "active", False):
        return
    _guard.active = True
    try:
        payload = format_exception_payload(
            exc_type,
            exc_value,
            exc_tb,
            source=source,
            context=context,
            include_locals=include_locals,
        )
        transport = getattr(client, "transport", None)
        if transport is not None:
            transport.event("error.exception", payload)
        else:
            client.event("error.exception", payload)
    except Exception:
        return
    finally:
        _guard.active = False


def _config_errors(config: dict[str, Any] | None) -> dict[str, Any] | bool:
    if not isinstance(config, dict):
        return {}
    runtime = config.get("runtime")
    if isinstance(runtime, dict) and "errors" in runtime:
        errors = runtime.get("errors", {})
    else:
        errors = config.get("errors", {})
    return errors if isinstance(errors, dict) else bool(errors)


def _config_enabled(config_errors: dict[str, Any] | bool) -> bool:
    if isinstance(config_errors, dict):
        return bool(config_errors.get("enabled", False))
    return bool(config_errors)


def _config_bool(config_errors: dict[str, Any] | bool, key: str, default: bool) -> bool:
    if not isinstance(config_errors, dict):
        return default
    return bool(config_errors.get(key, default))


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _json_safe_context(context: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in context.items() if value is not None}


def _json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return _safe_repr(value)


@dataclass
class _LocalBudget:
    remaining: int

    def consume(self, text: str) -> tuple[str, bool]:
        if self.remaining <= 0:
            return "", True

        if len(text) <= self.remaining:
            self.remaining -= len(text)
            return text, False

        if self.remaining <= 3:
            truncated = "." * self.remaining
        else:
            truncated = text[: self.remaining - 3] + "..."
        self.remaining = 0
        return truncated, True


def _locals_from_frame(frame: Any, budget: _LocalBudget) -> dict[str, Any]:
    locals_payload: dict[str, Any] = {}
    for index, (name, value) in enumerate(frame.f_locals.items()):
        if index >= _LOCAL_FRAME_LIMIT:
            locals_payload["__truncated__"] = {"reason": "frame_local_limit"}
            break
        if budget.remaining <= 0:
            locals_payload["__truncated__"] = {"reason": "locals_repr_budget"}
            break

        locals_payload[str(name)] = _local_value_payload(str(name), value, budget)
        if budget.remaining <= 0:
            locals_payload["__truncated__"] = {"reason": "locals_repr_budget"}
            break
    return locals_payload


def _local_value_payload(name: str, value: Any, budget: _LocalBudget) -> dict[str, Any]:
    type_name = _type_name(value)
    if _is_sensitive_local_name(name):
        return {
            "type": type_name,
            "redacted": True,
            "reason": "sensitive_name",
        }

    text, value_truncated = _safe_repr_with_truncation(value, max_chars=_LOCAL_REPR_MAX_CHARS)
    text, budget_truncated = budget.consume(text)
    return {
        "type": type_name,
        "repr": text,
        "truncated": value_truncated or budget_truncated,
    }


def _is_sensitive_local_name(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in _SENSITIVE_LOCAL_NAME_PARTS)


def _type_name(value: Any) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _safe_repr_with_truncation(value: Any, *, max_chars: int) -> tuple[str, bool]:
    try:
        text = repr(value)
    except Exception:
        return f"<unrepresentable {type(value).__name__}>", False
    if len(text) <= max_chars:
        return text, False
    if max_chars <= 3:
        return "." * max_chars, True
    return text[: max_chars - 3] + "...", True


def _safe_repr(value: Any, *, max_chars: int = 512) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


asyncio_module = asyncio
