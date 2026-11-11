"""hotpatcher 进程状态容器。"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from _thread import RLock as RLockType
    from _thread import _local as ThreadLocal
    from importlib.machinery import ModuleSpec

    from .control.controller import HotpatchController
    from .control.events import PatchEventLog
    from .control.features import FeatureRegistry
    from .control.handles import PatchHandle
    from .control.loader import LoadedPatch, PatchFileWatcher
    from .control.patchset import PatchSet
    from .control.trace import HotpatchTracer
    from .hook import HookedMetaPathFinder, MonkeyZoo
    from .runtime.client import RuntimeClient
    from .runtime.connection import ConnectionManager
    from .runtime.desktop_broker import DesktopBrokerClient
    from .runtime.errors import ErrorCapture
    from .runtime.faults import FaultChannel
    from .runtime.logs import LogCapture
    from .services import ServiceControlChannel
    from .stack_shadow import StackShadowFinder

ExceptionReporterCallback = Callable[[type[BaseException], BaseException, TracebackType | None], None]

STRICT_MODE_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_STRICT"
"""启用补丁严格模式的环境变量名, 值为 ``1`` 时启用"""

TRACE_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE"
"""启用跟踪输出的环境变量名, 值为逗号分隔的标签 (``import,patch,...``) 或 ``all``"""

TRACE_FILE_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE_FILE"
"""跟踪输出文件路径的环境变量名, 未设置时写入 stderr"""


def strict_mode_from_env() -> bool:
    """
    读取严格模式环境变量。

    Returns:
        bool:
            ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_STRICT=1`` 时返回 True。
    """

    return os.getenv(STRICT_MODE_ENV) == "1"


@dataclass
class HotpatcherState:
    """
    hotpatcher 默认进程状态。

    锁约定: ``control_lock`` 只保护控制平面的内存注册表 (``patch_id_counter``、``patch_sets``、
    ``patch_handles``、``feature_registry`` 的创建、``loaded_patches``、``loading_patches``、
    ``rebind_skip_modules``、``patch_file_watcher``、``tracer``、``event_log``、``controller`` 与 ``connection_manager`` 的创建) 的读写。``event_log`` 记录事件时只使用其内部叶子锁, 从不获取 ``control_lock``。持有该锁时绝不执行 ``importlib`` 调用、用户补丁函数或
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
        feature_registry (FeatureRegistry | None):
            services 功能注册表, 首次通过 ``control.features.get_feature_registry`` 访问时创建并注册内置功能。
        strict_mode (bool):
            补丁严格模式。启用后 import 阶段补丁抛出的异常会在记录结果后继续向外抛出,
            而不是被 ``capture_exception`` 吞掉。创建状态对象时从
            ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_STRICT`` 读取初始值; 默认状态在导入本模块
            (即 bootstrap) 时创建, 之后修改环境变量不会生效, 运行时请使用 ``hook.set_strict_mode``。
        loaded_patches (dict[str, LoadedPatch]):
            ``control.loader`` 在运行时加载的补丁模块, 键为补丁名称 (跨重新加载保持不变)。
        loading_patches (set[str]):
            正在加载、卸载、重新加载或更新的补丁名称, 同名补丁的并发操作会被拒绝。
        rebind_skip_modules (dict[str, set[str]]):
            ``rebind_references`` 扫描时跳过的模块名, 值为登记该模块的补丁集 ID 集合;
            按模块名加载的补丁模块在补丁集生命周期内登记于此, 避免包装函数通过自身全局变量递归调用自己。
        patch_file_watcher (PatchFileWatcher | None):
            当前补丁文件监视器。
        tracer (HotpatchTracer | None):
            跟踪输出器, 由 ``control.trace.get_tracer``、bootstrap 或 ``install_import_hook`` (设置了
            ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE`` 时) 惰性创建。热路径只读取该字段, 为 None 时不跟踪。
        event_log (PatchEventLog | None):
            补丁事件环形缓冲区, 首次记录事件时由 ``control.events.get_event_log`` 惰性创建。
        controller (HotpatchController | None):
            统一控制门面与命令注册表, 首次通过 ``control.controller.get_controller`` 访问时创建。
        connection_manager (ConnectionManager | None):
            旧版运行时客户端的连接管理器, 由 ``runtime.connection.get_connection_manager`` 惰性创建
            (启用 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RECONNECT`` 时由 bootstrap 创建)。
        fault_channel (FaultChannel | None):
            ``runtime.faults.install_faulthandler`` 最近安装的 fault 通道, 切换连接时在新宿主上重新打开。
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
    feature_registry: "FeatureRegistry | None" = None
    strict_mode: bool = field(default_factory=strict_mode_from_env)
    loaded_patches: "dict[str, LoadedPatch]" = field(default_factory=dict)
    loading_patches: set[str] = field(default_factory=set)
    rebind_skip_modules: dict[str, set[str]] = field(default_factory=dict)
    patch_file_watcher: "PatchFileWatcher | None" = None
    tracer: "HotpatchTracer | None" = None
    event_log: "PatchEventLog | None" = None
    controller: "HotpatchController | None" = None
    connection_manager: "ConnectionManager | None" = None
    fault_channel: "FaultChannel | None" = None


_default_state = HotpatcherState()


def get_default_state() -> HotpatcherState:
    """
    获取默认 hotpatcher 进程状态。

    Returns:
        HotpatcherState:
            默认状态对象。
    """

    return _default_state
