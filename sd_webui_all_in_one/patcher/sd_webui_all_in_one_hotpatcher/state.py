"""hotpatcher 进程状态容器。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from _thread import RLock as RLockType
    from _thread import _local as ThreadLocal
    from importlib.machinery import ModuleSpec

    from .hook import HookedMetaPathFinder, MonkeyZoo
    from .runtime.client import RuntimeClient
    from .runtime.errors import ErrorCapture
    from .runtime.logs import LogCapture
    from .services import ServiceControlChannel
    from .stack_shadow import StackShadowFinder

ExceptionReporterCallback = Callable[[type[BaseException], BaseException, TracebackType | None], None]


@dataclass
class HotpatcherState:
    """
    hotpatcher 默认进程状态。

    属性:
        monkey_zoo (MonkeyZoo | None):
            import hook 使用的补丁注册表。
        import_hook_finder (HookedMetaPathFinder | None):
            当前 import hook finder。
        import_hook_wrapped_spec_from_file_location (Callable[..., ModuleSpec | None] | None):
            被包装前的 ``importlib.util.spec_from_file_location``。
        stack_shadow_finder (StackShadowFinder | None):
            当前栈隐藏 finder。
        exception_reporter (ExceptionReporterCallback | None):
            ``capture_exception`` 使用的异常上报器。
        current_config (dict[str, Any] | None):
            services 最近一次规范化配置。
        current_config_lock (RLockType):
            services 配置快照锁。
        bootstrap_runtime_client (RuntimeClient | None):
            最近一次 bootstrap 创建的 runtime client。
        bootstrap_runtime_config (dict[str, Any]):
            最近一次 bootstrap 加载的配置。
        bootstrap_error_capture (ErrorCapture | None):
            最近一次 bootstrap 安装的错误捕获器。
        bootstrap_log_capture (LogCapture | None):
            最近一次 bootstrap 安装的日志采集器。
        bootstrap_service_control_channel (ServiceControlChannel | None):
            最近一次 bootstrap 安装的 services 控制通道。
        bootstrap_service_apply_result (dict[str, Any] | None):
            最近一次 bootstrap 自动应用 services 配置的结果。
        error_capture (ErrorCapture | None):
            当前错误捕获器。
        error_guard (ThreadLocal):
            错误事件发送递归保护。
        log_capture (LogCapture | None):
            当前日志采集器。
        log_guard (ThreadLocal):
            日志事件发送递归保护。
    """

    monkey_zoo: "MonkeyZoo | None" = None
    import_hook_finder: "HookedMetaPathFinder | None" = None
    import_hook_wrapped_spec_from_file_location: "Callable[..., ModuleSpec | None] | None" = None
    stack_shadow_finder: "StackShadowFinder | None" = None
    exception_reporter: ExceptionReporterCallback | None = None
    current_config: dict[str, Any] | None = None
    current_config_lock: "RLockType" = field(default_factory=threading.RLock)
    bootstrap_runtime_client: "RuntimeClient | None" = None
    bootstrap_runtime_config: dict[str, Any] = field(default_factory=dict)
    bootstrap_error_capture: "ErrorCapture | None" = None
    bootstrap_log_capture: "LogCapture | None" = None
    bootstrap_service_control_channel: "ServiceControlChannel | None" = None
    bootstrap_service_apply_result: dict[str, Any] | None = None
    error_capture: "ErrorCapture | None" = None
    error_guard: "ThreadLocal" = field(default_factory=threading.local)
    log_capture: "LogCapture | None" = None
    log_guard: "ThreadLocal" = field(default_factory=threading.local)


_default_state = HotpatcherState()


def get_default_state() -> HotpatcherState:
    """
    获取默认 hotpatcher 进程状态。

    返回:
        HotpatcherState:
            默认状态对象。
    """

    return _default_state
