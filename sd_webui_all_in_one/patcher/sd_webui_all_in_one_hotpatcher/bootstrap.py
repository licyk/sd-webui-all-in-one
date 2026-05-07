"""环境变量驱动的启动配置工具"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .exceptions import capture_exception

_runtime_client: Any = None
_runtime_config: dict[str, Any] = {}
_error_capture: Any = None
_log_capture: Any = None
_service_control_channel: Any = None
_service_apply_result: dict[str, Any] | None = None
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


def configure_from_env() -> BootstrapState:
    """
    根据环境变量安装可选热补丁能力

    会按顺序尝试安装栈隐藏、import hook、运行时客户端、配置加载和日志采集。
    所有开关均使用 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*`` 前缀。

    Returns:
        BootstrapState:
            启动配置结果
    """

    global _runtime_client, _runtime_config, _error_capture, _log_capture, _service_control_channel, _service_apply_result

    os.environ[_BOOTSTRAPPED_ENV] = "1"

    from .stack_shadow import configure_stack_shadower_from_env, is_stack_shadower_installed

    configure_stack_shadower_from_env()

    if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK") == "1":
        from .hook import install_import_hook

        install_import_hook()

    _runtime_client = None
    if _runtime_enabled_from_env():
        from .runtime.client import RuntimeClient

        _runtime_client = RuntimeClient.connect_from_env(required=False)

    try:
        from .runtime.config import load_config

        _runtime_config = load_config(client=_runtime_client)
        from .services import set_current_config

        _runtime_config = set_current_config(_runtime_config)
    except Exception:
        capture_exception()
        _runtime_config = {}

    _service_apply_result = None
    if _services_apply_on_bootstrap(_runtime_config):
        try:
            from .services import apply_config

            _service_apply_result = apply_config(_runtime_config, runtime_client=_runtime_client)
        except Exception:
            capture_exception()
            _service_apply_result = {
                "applied": [],
                "warnings": [],
                "errors": [{"feature": "services", "code": "bootstrap_failed"}],
            }

    _error_capture = None
    _log_capture = None
    if _runtime_client is not None:
        try:
            from .runtime.errors import configure_error_capture_from_env

            _error_capture = configure_error_capture_from_env(_runtime_client, _runtime_config)
        except Exception:
            capture_exception()

        try:
            from .runtime.logs import configure_log_capture_from_env

            _log_capture = configure_log_capture_from_env(_runtime_client, _runtime_config)
        except Exception:
            capture_exception()

    _service_control_channel = None
    if _runtime_client is not None and os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES") == "1":
        try:
            from .services import install_service_control_channel

            _service_control_channel = install_service_control_channel(_runtime_client)
        except Exception:
            capture_exception()

    from .hook import is_import_hook_installed

    return BootstrapState(
        stack_shadower_installed=is_stack_shadower_installed(),
        import_hook_installed=is_import_hook_installed(),
        runtime_client=_runtime_client,
        config=_runtime_config,
        error_capture=_error_capture,
        log_capture=_log_capture,
        service_control_channel=_service_control_channel,
        service_apply_result=_service_apply_result,
    )


def get_runtime_client() -> Any:
    """
    获取最近一次 bootstrap 创建的运行时客户端

    Returns:
        Any:
            运行时客户端对象, 未连接时为 None
    """

    return _runtime_client


def get_runtime_config() -> dict[str, Any]:
    """
    获取最近一次 bootstrap 加载的配置

    Returns:
        dict[str, Any]:
            配置对象副本
    """

    return dict(_runtime_config)


def get_log_capture() -> Any:
    """
    获取最近一次 bootstrap 安装的日志采集器

    Returns:
        Any:
            日志采集器对象, 未启用时为 None
    """

    return _log_capture


def get_error_capture() -> Any:
    """
    获取最近一次 bootstrap 安装的错误捕获器

    Returns:
        Any:
            错误捕获器, 未启用时为 None
    """

    return _error_capture


def get_service_control_channel() -> Any:
    """
    获取最近一次 bootstrap 安装的 services 控制通道

    Returns:
        Any:
            services 控制通道对象, 未启用时为 None
    """

    return _service_control_channel


def get_service_apply_result() -> dict[str, Any] | None:
    """
    获取最近一次 bootstrap 自动应用 services 配置的结果

    Returns:
        dict[str, Any] | None:
            自动应用结果, 未执行时为 None
    """

    return _service_apply_result


def _runtime_enabled_from_env() -> bool:
    return os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME") == "1"


def _services_apply_on_bootstrap(config: dict[str, Any]) -> bool:
    services = config.get("services")
    if not isinstance(services, dict):
        return False
    return bool(services.get("apply_on_bootstrap"))
