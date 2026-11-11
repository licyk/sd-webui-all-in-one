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

    from .control.handles import PatchHandle
    from .control.patchset import PatchSet
    from .hook import HookedMetaPathFinder, MonkeyZoo
    from .runtime.client import RuntimeClient
    from .runtime.desktop_broker import DesktopBrokerClient
    from .runtime.errors import ErrorCapture
    from .runtime.logs import LogCapture
    from .services import ServiceControlChannel
    from .stack_shadow import StackShadowFinder

ExceptionReporterCallback = Callable[[type[BaseException], BaseException, TracebackType | None], None]


@dataclass
class HotpatcherState:
    """
    hotpatcher 默认进程状态。

    锁约定: ``control_lock`` 只保护控制平面的内存注册表 (``patch_id_counter``、``patch_sets``、
    ``patch_handles``) 的读写。持有该锁时绝不执行 ``importlib`` 调用、用户补丁函数或
    ``setup`` 回调、socket/HTTP I/O; 调用方应在锁内计算、在锁外执行。这样控制线程不会在
    持有 ``control_lock`` 时等待模块导入锁, 避免与正在导入并读取补丁计划的主线程死锁。

    Attributes:
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
        bootstrap_runtime_client (RuntimeClient | DesktopBrokerClient | None):
            最近一次启动流程选择的旧版或桌面运行时客户端。
        bootstrap_transport_mode (str):
            最近一次集中解析的 transport mode。
        bootstrap_transport_diagnostics (list[str]):
            transport 初始化阶段的 bounded diagnostic 摘要。
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
        browser_patch_registered (bool):
            浏览器打开补丁是否已经安装。
        browser_patch_mode (str):
            浏览器打开补丁的当前模式。
        browser_runtime_client (Any):
            浏览器打开补丁使用的运行时客户端。
        browser_diagnostics (list[str]):
            浏览器打开补丁的诊断信息。
        control_lock (RLockType):
            控制平面注册表锁, 使用约定见类说明。
        patch_id_counter (int):
            补丁句柄和补丁集共用的 ID 计数器。
        patch_sets (dict[str, PatchSet]):
            已注册补丁集, 键为补丁集 ID。
        patch_handles (dict[str, PatchHandle]):
            已注册补丁句柄, 键为句柄 ID。
    """

    monkey_zoo: "MonkeyZoo | None" = None
    import_hook_finder: "HookedMetaPathFinder | None" = None
    import_hook_wrapped_spec_from_file_location: "Callable[..., ModuleSpec | None] | None" = None
    stack_shadow_finder: "StackShadowFinder | None" = None
    exception_reporter: ExceptionReporterCallback | None = None
    current_config: dict[str, Any] | None = None
    current_config_lock: "RLockType" = field(default_factory=threading.RLock)
    bootstrap_runtime_client: "RuntimeClient | DesktopBrokerClient | None" = None
    bootstrap_transport_mode: str = "legacy"
    bootstrap_transport_diagnostics: list[str] = field(default_factory=list)
    bootstrap_runtime_config: dict[str, Any] = field(default_factory=dict)
    bootstrap_error_capture: "ErrorCapture | None" = None
    bootstrap_log_capture: "LogCapture | None" = None
    bootstrap_service_control_channel: "ServiceControlChannel | None" = None
    bootstrap_service_apply_result: dict[str, Any] | None = None
    error_capture: "ErrorCapture | None" = None
    error_guard: "ThreadLocal" = field(default_factory=threading.local)
    log_capture: "LogCapture | None" = None
    log_guard: "ThreadLocal" = field(default_factory=threading.local)
    browser_patch_registered: bool = False
    browser_patch_mode: str = "passthrough"
    browser_runtime_client: Any = None
    browser_diagnostics: list[str] = field(default_factory=list)
    control_lock: "RLockType" = field(default_factory=threading.RLock)
    patch_id_counter: int = 0
    patch_sets: "dict[str, PatchSet]" = field(default_factory=dict)
    patch_handles: "dict[str, PatchHandle]" = field(default_factory=dict)


_default_state = HotpatcherState()


def get_default_state() -> HotpatcherState:
    """
    获取默认 hotpatcher 进程状态。

    Returns:
        HotpatcherState:
            默认状态对象。
    """

    return _default_state
