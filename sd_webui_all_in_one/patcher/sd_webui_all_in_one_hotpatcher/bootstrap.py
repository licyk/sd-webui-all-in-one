"""环境变量驱动的启动配置工具"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from typing import Any

from .exceptions import capture_exception
from .state import HotpatcherState, get_default_state

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
        runtime_client (Any):
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
    """

    stack_shadower_installed: bool
    import_hook_installed: bool
    runtime_client: Any
    config: dict[str, Any]
    error_capture: Any
    log_capture: Any
    service_control_channel: Any
    service_apply_result: dict[str, Any] | None


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

    from .stack_shadow import configure_stack_shadower_from_env, is_stack_shadower_installed

    configure_stack_shadower_from_env(state=active_state)

    if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK") == "1":
        from .hook import install_import_hook

        install_import_hook(state=active_state)

    active_state.bootstrap_runtime_client = None
    if _runtime_enabled_from_env():
        from .runtime.client import RuntimeClient

        active_state.bootstrap_runtime_client = RuntimeClient.connect_from_env(required=False)

    try:
        from .runtime.config import load_config

        active_state.bootstrap_runtime_config = load_config(client=active_state.bootstrap_runtime_client)
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
                runtime_client=active_state.bootstrap_runtime_client,
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
    if active_state.bootstrap_runtime_client is not None:
        try:
            from .runtime.errors import configure_error_capture_from_env

            active_state.bootstrap_error_capture = configure_error_capture_from_env(
                active_state.bootstrap_runtime_client,
                active_state.bootstrap_runtime_config,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)

        try:
            from .runtime.logs import configure_log_capture_from_env

            active_state.bootstrap_log_capture = configure_log_capture_from_env(
                active_state.bootstrap_runtime_client,
                active_state.bootstrap_runtime_config,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)

    active_state.bootstrap_service_control_channel = None
    if active_state.bootstrap_runtime_client is not None and os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES") == "1":
        try:
            from .services import install_service_control_channel

            active_state.bootstrap_service_control_channel = install_service_control_channel(
                active_state.bootstrap_runtime_client,
                state=active_state,
            )
        except Exception:
            capture_exception(state=active_state)

    from .hook import is_import_hook_installed

    return BootstrapState(
        stack_shadower_installed=is_stack_shadower_installed(state=active_state),
        import_hook_installed=is_import_hook_installed(state=active_state),
        runtime_client=active_state.bootstrap_runtime_client,
        config=active_state.bootstrap_runtime_config,
        error_capture=active_state.bootstrap_error_capture,
        log_capture=active_state.bootstrap_log_capture,
        service_control_channel=active_state.bootstrap_service_control_channel,
        service_apply_result=active_state.bootstrap_service_apply_result,
    )


def get_runtime_client(*, state: HotpatcherState | None = None) -> Any:
    """
    获取最近一次 bootstrap 创建的运行时客户端

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        Any:
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
    if not isinstance(services, dict):
        return False
    return bool(services.get("apply_on_bootstrap"))
