"""hotpatcher 进程状态容器。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HotpatcherState:
    """
    hotpatcher 默认进程状态。

    Attributes:
        monkey_zoo (Any):
            import hook 使用的补丁注册表。
        import_hook_finder (Any):
            当前 import hook finder。
        import_hook_wrapped_spec_from_file_location (Callable[..., Any] | None):
            被包装前的 ``importlib.util.spec_from_file_location``。
        stack_shadow_finder (Any):
            当前栈隐藏 finder。
        exception_reporter (Callable[..., Any] | None):
            ``capture_exception`` 使用的异常上报器。
        current_config (dict[str, Any] | None):
            services 最近一次规范化配置。
        current_config_lock (Any):
            services 配置快照锁。
        bootstrap_runtime_client (Any):
            最近一次 bootstrap 创建的 runtime client。
        bootstrap_runtime_config (dict[str, Any]):
            最近一次 bootstrap 加载的配置。
        bootstrap_error_capture (Any):
            最近一次 bootstrap 安装的错误捕获器。
        bootstrap_log_capture (Any):
            最近一次 bootstrap 安装的日志采集器。
        bootstrap_service_control_channel (Any):
            最近一次 bootstrap 安装的 services 控制通道。
        bootstrap_service_apply_result (dict[str, Any] | None):
            最近一次 bootstrap 自动应用 services 配置的结果。
        error_capture (Any):
            当前错误捕获器。
        error_guard (Any):
            错误事件发送递归保护。
        log_capture (Any):
            当前日志采集器。
        log_guard (Any):
            日志事件发送递归保护。
    """

    monkey_zoo: Any = None
    import_hook_finder: Any = None
    import_hook_wrapped_spec_from_file_location: Callable[..., Any] | None = None
    stack_shadow_finder: Any = None
    exception_reporter: Callable[..., Any] | None = None
    current_config: dict[str, Any] | None = None
    current_config_lock: Any = field(default_factory=threading.RLock)
    bootstrap_runtime_client: Any = None
    bootstrap_runtime_config: dict[str, Any] = field(default_factory=dict)
    bootstrap_error_capture: Any = None
    bootstrap_log_capture: Any = None
    bootstrap_service_control_channel: Any = None
    bootstrap_service_apply_result: dict[str, Any] | None = None
    error_capture: Any = None
    error_guard: Any = field(default_factory=threading.local)
    log_capture: Any = None
    log_guard: Any = field(default_factory=threading.local)


_default_state = HotpatcherState()


def get_default_state() -> HotpatcherState:
    """
    获取默认 hotpatcher 进程状态。

    Returns:
        HotpatcherState:
            默认状态对象。
    """

    return _default_state
