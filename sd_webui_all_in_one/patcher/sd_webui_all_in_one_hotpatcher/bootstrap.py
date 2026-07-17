"""环境变量驱动的启动配置工具"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .exceptions import capture_exception
from .state import HotpatcherState, get_default_state

if TYPE_CHECKING:
    from .runtime.client import RuntimeClient
    from .runtime.desktop_broker import DesktopBrokerClient
    from .runtime.interfaces import RuntimeCommandHandler

_BOOTSTRAPPED_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_BOOTSTRAPPED"


@dataclass
class BootstrapState:
    """
    启动配置结果

    Attributes:
        stack_shadower_installed (bool):
            是否已安装栈隐藏 finder
        import_hook_installed (bool):
            是否已安装 import hook
        runtime_client (RuntimeClient | DesktopBrokerClient | None):
            已连接的运行时客户端, 未连接时为 None
        config (dict[str, Any]):
            从环境变量或宿主拉取到的配置
        error_capture (Any):
            已安装的错误捕获器, 未启用时为 None
        log_capture (Any):
            已安装的日志采集器, 未启用时为 None
        service_control_channel (Any):
            已安装的 services 控制通道, 未启用时为 None
        service_apply_result (dict[str, Any] | None):
            bootstrap 自动应用 services 配置的结果
        transport_mode (str):
            集中解析后的 transport mode
        transport_status (dict[str, Any] | None):
            selected transport 的初始状态快照
        transport_diagnostics (list[str]):
            bootstrap transport 初始化诊断
    """

    stack_shadower_installed: bool
    import_hook_installed: bool
    runtime_client: RuntimeClient | DesktopBrokerClient | None
    config: dict[str, Any]
    error_capture: Any
    log_capture: Any
    service_control_channel: Any
    service_apply_result: dict[str, Any] | None
    transport_mode: str
    transport_status: dict[str, Any] | None
    transport_diagnostics: list[str]


def configure_from_env(*, state: HotpatcherState | None = None) -> BootstrapState:
    """
    根据环境变量安装可选热补丁能力

    会按顺序尝试安装栈隐藏、import hook、运行时客户端、配置加载和日志采集。
    所有开关均使用 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*`` 前缀。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        BootstrapState:
            启动配置结果
    """

    active_state = state or get_default_state()
    os.environ[_BOOTSTRAPPED_ENV] = "1"

    from .runtime.transport_mode import TransportMode, resolve_transport_mode

    transport_mode = resolve_transport_mode()
    active_state.bootstrap_transport_mode = transport_mode.value
    active_state.bootstrap_transport_diagnostics.clear()

    from .stack_shadow import configure_stack_shadower_from_env, is_stack_shadower_installed

    configure_stack_shadower_from_env(state=active_state)

    if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK") == "1":
        from .hook import install_import_hook

        install_import_hook(state=active_state)

    active_state.bootstrap_runtime_client = None
    legacy_client: RuntimeClient | None = None
    desktop_client: DesktopBrokerClient | None = None
    if transport_mode is TransportMode.LEGACY:
        legacy_client = initialize_legacy_runtime(state=active_state)
    else:
        try:
            desktop_client = initialize_desktop_broker_runtime(
                state=active_state,
                start=False,
                command_handler=lambda command_type, payload: _handle_desktop_command(
                    command_type,
                    payload,
                    state=active_state,
                ),
            )
        except Exception as exc:
            # 显式桌面模式仍只使用桌面传输；下方应用配置时仍可安装本地浏览器抑制。
            active_state.bootstrap_transport_diagnostics.append(f"desktop_broker initialization failed: {type(exc).__name__}: {exc}")
            del active_state.bootstrap_transport_diagnostics[:-100]
            capture_exception(state=active_state)

    runtime_client = legacy_client if transport_mode is TransportMode.LEGACY else desktop_client

    try:
        from .runtime.config import load_config

        active_state.bootstrap_runtime_config = load_config(client=legacy_client)
        from .services import set_current_config

        active_state.bootstrap_runtime_config = set_current_config(active_state.bootstrap_runtime_config, state=active_state)
    except Exception:
        capture_exception(state=active_state)
        active_state.bootstrap_runtime_config = {}

    active_state.bootstrap_service_apply_result = None
    if _services_apply_on_bootstrap(active_state.bootstrap_runtime_config):
        try:
            from .services import apply_config

            active_state.bootstrap_service_apply_result = apply_config(
                active_state.bootstrap_runtime_config,
                runtime_client=runtime_client,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)
            active_state.bootstrap_service_apply_result = {
                "applied": [],
                "warnings": [],
                "errors": [{"feature": "services", "code": "bootstrap_failed"}],
            }

    active_state.bootstrap_error_capture = None
    active_state.bootstrap_log_capture = None
    if runtime_client is not None:
        try:
            from .runtime.errors import configure_error_capture_from_env

            active_state.bootstrap_error_capture = configure_error_capture_from_env(
                runtime_client,
                active_state.bootstrap_runtime_config,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)

        try:
            from .runtime.logs import configure_log_capture_from_env

            active_state.bootstrap_log_capture = configure_log_capture_from_env(
                runtime_client,
                active_state.bootstrap_runtime_config,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)

    active_state.bootstrap_service_control_channel = None
    if transport_mode is TransportMode.LEGACY and legacy_client is not None and os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES") == "1":
        try:
            from .services import install_service_control_channel

            active_state.bootstrap_service_control_channel = install_service_control_channel(
                legacy_client,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)

    from .hook import is_import_hook_installed

    if transport_mode is TransportMode.DESKTOP_BROKER and desktop_client is not None:
        desktop_client.start()

    runtime_status = runtime_client.status() if runtime_client is not None else None

    return BootstrapState(
        stack_shadower_installed=is_stack_shadower_installed(state=active_state),
        import_hook_installed=is_import_hook_installed(state=active_state),
        runtime_client=runtime_client,
        config=active_state.bootstrap_runtime_config,
        error_capture=active_state.bootstrap_error_capture,
        log_capture=active_state.bootstrap_log_capture,
        service_control_channel=active_state.bootstrap_service_control_channel,
        service_apply_result=active_state.bootstrap_service_apply_result,
        transport_mode=active_state.bootstrap_transport_mode,
        transport_status=runtime_status,
        transport_diagnostics=list(active_state.bootstrap_transport_diagnostics),
    )


def initialize_legacy_runtime(*, state: HotpatcherState | None = None) -> RuntimeClient | None:
    """设置旧版标志时初始化现有 TCP JSONL 客户端。

    Args:
        state (HotpatcherState | None): 可选热补丁状态。

    Returns:
        RuntimeClient | None: 已连接的旧版运行时客户端；未启用时返回 ``None``。
    """

    active_state = state or get_default_state()
    if not _runtime_enabled_from_env():
        active_state.bootstrap_runtime_client = None
        return None
    from .runtime.client import RuntimeClient

    active_state.bootstrap_runtime_client = RuntimeClient.connect_from_env(required=False)
    return active_state.bootstrap_runtime_client


def initialize_desktop_broker_runtime(
    *,
    state: HotpatcherState | None = None,
    command_handler: RuntimeCommandHandler | None = None,
    start: bool = True,
) -> DesktopBrokerClient:
    """仅初始化独立的 HTTP 桌面代理客户端。

    Args:
        state (HotpatcherState | None): 可选热补丁状态。
        command_handler (RuntimeCommandHandler | None): 桌面命令处理器。
        start (bool): 是否立即启动客户端。

    Returns:
        DesktopBrokerClient: 桌面代理客户端。
    """

    active_state = state or get_default_state()
    from .runtime.desktop_broker import DesktopBrokerClient

    client = DesktopBrokerClient.from_env(command_handler=command_handler)
    active_state.bootstrap_runtime_client = client
    if start:
        client.start()
    return client


def _handle_desktop_command(
    command_type: str,
    payload: dict[str, Any],
    *,
    state: HotpatcherState,
) -> dict[str, Any]:
    """将带版本的桌面命令接口映射到现有纯服务。"""

    from .runtime.desktop_broker import DesktopBrokerCommandError

    if command_type != "config.apply":
        raise DesktopBrokerCommandError(
            "unknown_command",
            f"unsupported desktop broker command: {command_type}",
        )
    config = payload.get("config")
    if not isinstance(config, dict):
        raise DesktopBrokerCommandError(
            "invalid_command_payload",
            "config.apply payload.config must be an object",
        )
    from .services import apply_config

    return {
        "applyResult": apply_config(
            config,
            runtime_client=state.bootstrap_runtime_client,
            state=state,
        )
    }


def get_runtime_client(*, state: HotpatcherState | None = None) -> RuntimeClient | DesktopBrokerClient | None:
    """
    获取最近一次 bootstrap 创建的运行时客户端

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        RuntimeClient | DesktopBrokerClient | None:
            运行时客户端对象, 未连接时为 None
    """

    return (state or get_default_state()).bootstrap_runtime_client


def get_runtime_config(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    获取最近一次 bootstrap 加载的配置

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            配置对象副本
    """

    return copy.deepcopy((state or get_default_state()).bootstrap_runtime_config)


def get_log_capture(*, state: HotpatcherState | None = None) -> Any:
    """
    获取最近一次 bootstrap 安装的日志采集器

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        Any:
            日志采集器对象, 未启用时为 None
    """

    return (state or get_default_state()).bootstrap_log_capture


def get_error_capture(*, state: HotpatcherState | None = None) -> Any:
    """
    获取最近一次 bootstrap 安装的错误捕获器

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        Any:
            错误捕获器, 未启用时为 None
    """

    return (state or get_default_state()).bootstrap_error_capture


def get_service_control_channel(*, state: HotpatcherState | None = None) -> Any:
    """
    获取最近一次 bootstrap 安装的 services 控制通道

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        Any:
            services 控制通道对象, 未启用时为 None
    """

    return (state or get_default_state()).bootstrap_service_control_channel


def get_service_apply_result(*, state: HotpatcherState | None = None) -> dict[str, Any] | None:
    """
    获取最近一次 bootstrap 自动应用 services 配置的结果

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any] | None:
            自动应用结果, 未执行时为 None
    """

    return (state or get_default_state()).bootstrap_service_apply_result


def _runtime_enabled_from_env() -> bool:
    return os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME") == "1"


def _services_apply_on_bootstrap(config: dict[str, Any]) -> bool:
    services = config.get("services")
    configured = isinstance(services, dict) and bool(services.get("apply_on_bootstrap"))
    runtime = config.get("runtime")
    browser = runtime.get("browser") if isinstance(runtime, dict) else None
    browser_required = isinstance(browser, dict) and browser.get("enabled") is True
    return configured or browser_required
