"""补丁系统业务控制服务"""

from __future__ import annotations

import copy
import errno
import json
import logging
import math
import socket
import threading
from pathlib import Path
from collections.abc import Callable
from typing import Any, cast

from .control.commands import run_after_send
from .control.features import (
    BUILTIN_FEATURES,
    FeatureContext,
    apply_feature_configs,
    attach_feature_state,
    build_default_config,
    build_setting_schema,
    get_feature_registry,
    warn_disabled_but_active,
)
from .hook import install_import_hook, is_import_hook_installed, monkey_zoo
from .runtime.client import RuntimeClient
from .runtime.interfaces import RuntimeEventSink
from .runtime.errors import (
    DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES,
    install_error_capture,
    is_error_capture_installed,
    uninstall_error_capture,
)
from .runtime.logs import (
    DEFAULT_FD_CAPTURE,
    DEFAULT_HOOK_CHECK_INTERVAL,
    DEFAULT_HOOK_POLICY,
    DEFAULT_LOGGER_EXCLUDE,
    DEFAULT_MAX_CHARS,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_STREAMS,
    install_log_capture,
    uninstall_log_capture,
)
from .runtime.protocol import RuntimeProtocolError, decode_message, encode_message
from .state import HotpatcherState, get_default_state
from .stack_shadow import (
    DEFAULT_FILENAME_TEMPLATE,
    install_stack_shadower,
    is_stack_shadower_installed,
)

_MISSING = object()
_LOGGER = logging.getLogger(__name__)
SERVICE_CONTROL_DIAGNOSTIC_LIMIT = 100
DEFAULT_SERVICE_CONTROL_TIMEOUT = 5.0


def _service_control_timeout(name: str, value: float) -> float:
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return timeout


DEFAULT_CONFIG: dict[str, Any] = build_default_config(BUILTIN_FEATURES)
"""内置功能的完整默认配置, 由 ``control.features.BUILTIN_FEATURES`` 生成。运行时注册的功能见 ``get_default_config()``"""

SETTING_SCHEMA: dict[str, Any] = build_setting_schema(BUILTIN_FEATURES)
"""内置功能的设置 schema, 由 ``control.features.BUILTIN_FEATURES`` 生成。运行时注册的功能见 ``get_catalog()``"""


class ServiceControlChannel:
    """
    services 运行时控制通道

    独立连接宿主 TCP JSONL 端口, 打开 ``channel.open: services`` 后在后台线程中
    接收 ``services.*`` 请求并写回响应。

    Attributes:
        client (RuntimeClient):
            提供 host、port、token 信息的运行时客户端
        service (PatchService):
            处理 services 请求的服务对象
        sock (socket.socket | None):
            独立控制通道套接字；尚未连接或连接失败时为 ``None``。
        closed (bool):
            控制通道是否已关闭
    """

    def __init__(
        self,
        client: RuntimeClient,
        service: "PatchService | None" = None,
        *,
        timeout: float = DEFAULT_SERVICE_CONTROL_TIMEOUT,
        connect_timeout: float | None = None,
        response_write_timeout: float | None = None,
    ) -> None:
        """
        初始化 services 控制通道

        Args:
            client (RuntimeClient):
                已连接的运行时客户端
            service (PatchService | None):
                请求处理服务。为 None 时使用默认服务。
            timeout (float):
                兼容超时设置。未单独指定时，同时作为建连和响应写入超时。
            connect_timeout (float | None):
                TCP 连接建立超时。为 None 时使用 ``timeout``。
            response_write_timeout (float | None):
                ``channel.open`` 和单次响应的写入超时。为 None 时使用
                ``timeout``。空闲读取始终保持阻塞。

        Raises:
            Exception:
                建立控制通道或创建读取器失败时重新抛出原异常。
        """

        self.client = client
        self.service = service or PatchService()
        compatibility_timeout = _service_control_timeout("timeout", timeout)
        self.connect_timeout = compatibility_timeout if connect_timeout is None else _service_control_timeout("connect_timeout", connect_timeout)
        self.response_write_timeout = compatibility_timeout if response_write_timeout is None else _service_control_timeout("response_write_timeout", response_write_timeout)
        self.write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._diagnostic_lock = threading.Lock()
        self._close_complete = threading.Event()
        self._thread_started = False
        self.diagnostics: list[dict[str, str]] = []
        self.terminal_failure: dict[str, str] | None = None
        self.closed = False
        self.sock: socket.socket | None = None
        self.reader: Any | None = None
        try:
            sock = socket.create_connection((client.host, client.port), timeout=self.connect_timeout)
            self.sock = sock
            # 此超时是建连截止时间，不是长连接命令通道的空闲策略。
            sock.settimeout(None)
            self.reader = sock.makefile("rb")
        except Exception as exc:
            self._record_diagnostic("connect", exc)
            self.closed = True
            if self.reader is not None:
                try:
                    self.reader.close()
                except Exception as close_exc:
                    self._record_diagnostic("close", close_exc)
            if self.sock is not None:
                try:
                    self.sock.close()
                except Exception as close_exc:
                    self._record_diagnostic("close", close_exc)
            self.reader = None
            self.sock = None
            self._close_complete.set()
            raise
        self.thread = threading.Thread(
            target=self._run,
            name="sd_webui_all_in_one_hotpatcher-services",
            daemon=True,
        )

    def start(self) -> "ServiceControlChannel":
        """
        发送通道握手并启动后台线程

        Returns:
            ServiceControlChannel:
                当前控制通道对象

        Raises:
            Exception:
                发送通道握手或启动后台线程失败时重新抛出原异常。
        """

        try:
            self._send(
                {
                    "type": "channel.open",
                    "channel": "services",
                    "token": self.client.token,
                }
            )
            self.thread.start()
            self._thread_started = True
        except Exception as exc:
            self._set_terminal_failure("connect", exc)
            self.close()
            raise
        return self

    def close(self) -> None:
        """关闭控制通道"""

        owns_cleanup = False
        reader = None
        sock = None
        with self._state_lock:
            if not self.closed:
                self.closed = True
                reader = self.reader
                sock = self.sock
                owns_cleanup = True

        if not owns_cleanup:
            if threading.current_thread() is not self.thread:
                self._close_complete.wait()
                if self._thread_started:
                    self.thread.join()
            return

        try:
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError as exc:
                    if exc.errno not in {errno.EBADF, errno.EINVAL, errno.ENOTCONN}:
                        self._record_diagnostic("close", exc)
                except Exception as exc:
                    self._record_diagnostic("close", exc)
            if reader is not None:
                try:
                    reader.close()
                except Exception as exc:
                    self._record_diagnostic("close", exc)
            if sock is not None:
                try:
                    sock.close()
                except Exception as exc:
                    self._record_diagnostic("close", exc)
        finally:
            self._close_complete.set()

        if threading.current_thread() is not self.thread and self._thread_started:
            self.thread.join()

    def _run(self) -> None:
        try:
            while not self.closed:
                reader = self.reader
                if reader is None:
                    return
                try:
                    line = reader.readline()
                except Exception as exc:
                    if not self.closed:
                        self._terminate("read", exc)
                    return
                if not line:
                    if not self.closed:
                        self._terminate("read", "host closed the services channel")
                    return

                try:
                    request = decode_message(line)
                except Exception as exc:
                    self._record_diagnostic("decode", exc)
                    if not self._send_error_response(_error_response("request_failed", str(exc))):
                        return
                    continue

                after_send: list[Callable[[], Any]] = []
                try:
                    response = self._handle_request(request, after_send)
                except Exception as exc:
                    self._record_diagnostic("handler", exc)
                    response = _error_response("request_failed", str(exc))
                    after_send.clear()
                if "id" in request:
                    response["id"] = request["id"]

                try:
                    self._send(response)
                except Exception as exc:
                    if not self.closed:
                        self._terminate("response", exc)
                    return
                # 响应已写出后再执行处理函数登记的后续动作 (例如切换连接), 失败只记录诊断。
                run_after_send(after_send, on_error=lambda exc: self._record_diagnostic("after_send", f"{type(exc).__name__}: {exc}"))
        finally:
            self.close()

    def _handle_request(self, request: dict[str, Any], after_send: list[Callable[[], Any]]) -> dict[str, Any]:
        """经统一命令分发处理请求; 只实现 ``handle_request_json`` 的自定义服务沿用旧调用方式。"""

        handler = getattr(self.service, "handle_control_request", None)
        if not callable(handler):
            return self.service.handle_request_json(request, runtime_client=self.client)
        token = getattr(self.client, "token", None)
        return handler(
            request,
            runtime_client=self.client,
            transport="legacy",
            token=token if isinstance(token, str) else None,
            after_send=after_send,
        )

    def _send_error_response(self, response: dict[str, Any]) -> bool:
        """在套接字健康时发送可恢复的解码或处理器错误。"""

        if self.closed:
            return False
        try:
            self._send(response)
            return True
        except Exception as exc:
            if not self.closed:
                self._terminate("response", exc)
            return False

    def _terminate(self, stage: str, error: BaseException | str) -> None:
        """记录第一个终止故障并关闭通道。"""

        self._set_terminal_failure(stage, error)
        self.close()

    def _set_terminal_failure(self, stage: str, error: BaseException | str) -> None:
        message = str(error)
        self._record_diagnostic(stage, message)
        with self._state_lock:
            if self.terminal_failure is None:
                self.terminal_failure = {"stage": stage, "message": message}

    def _record_diagnostic(self, stage: str, error: BaseException | str) -> None:
        message = str(error)
        with self._diagnostic_lock:
            self.diagnostics.append({"stage": stage, "message": message})
            del self.diagnostics[:-SERVICE_CONTROL_DIAGNOSTIC_LIMIT]
        _LOGGER.warning("services control channel %s failure: %s", stage, message)

    def _send(self, message: dict[str, Any]) -> None:
        with self.write_lock:
            with self._state_lock:
                if self.closed or self.sock is None:
                    raise RuntimeProtocolError("Services control channel is closed")
                sock = self.sock
            old_timeout = sock.gettimeout()
            operation_error: BaseException | None = None
            try:
                sock.settimeout(self.response_write_timeout)
                sock.sendall(encode_message(message))
            except BaseException as exc:
                operation_error = exc
                raise
            finally:
                try:
                    sock.settimeout(old_timeout)
                except Exception as restore_exc:
                    if operation_error is None:
                        raise
                    # 调用方会因主要写入故障终止并关闭通道。保留恢复诊断，
                    # 但不覆盖原始异常。
                    self._record_diagnostic("close", restore_exc)


class PatchService:
    """补丁系统业务控制服务对象"""

    def __init__(self, *, state: HotpatcherState | None = None) -> None:
        """初始化补丁服务对象

        Args:
            state (HotpatcherState | None):
                可选状态对象。为 None 时使用默认状态。
        """

        self.state = state or get_default_state()

    def get_catalog(self) -> dict[str, Any]:
        """
        查询补丁系统能力目录

        Returns:
            dict[str, Any]:
                当前功能目录、可调设置和已注册补丁状态
        """

        return get_catalog(state=self.state)

    def get_default_config(self) -> dict[str, Any]:
        """
        查询默认配置

        Returns:
            dict[str, Any]:
                完整默认配置副本
        """

        return get_default_config(state=self.state)

    def get_current_config(self) -> dict[str, Any]:
        """
        查询当前进程配置

        Returns:
            dict[str, Any]:
                当前进程最后加载或应用的完整配置副本
        """

        return get_current_config(state=self.state)

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        补齐配置默认值

        Args:
            config (dict[str, Any]):
                用户配置

        Returns:
            dict[str, Any]:
                补齐默认值后的配置
        """

        return normalize_config(config, state=self.state)

    def handle_request_json(
        self,
        raw: str | dict[str, Any],
        *,
        runtime_client: RuntimeEventSink | None = None,
    ) -> dict[str, Any]:
        """
        处理 services JSON 请求

        Args:
            raw (str | dict[str, Any]):
                JSON 字符串或请求对象
            runtime_client (RuntimeEventSink | None):
                可选运行时客户端

        Returns:
            dict[str, Any]:
                固定 ok/error 格式响应
        """

        return handle_request_json(raw, runtime_client=runtime_client, state=self.state)

    def handle_control_request(
        self,
        raw: str | dict[str, Any],
        *,
        runtime_client: RuntimeEventSink | None = None,
        transport: str = "legacy",
        token: str | None = None,
        after_send: list[Callable[[], Any]] | None = None,
    ) -> dict[str, Any]:
        """
        处理来自运行时通道的请求, 按来源传输执行信任边界检查

        Args:
            raw (str | dict[str, Any]):
                JSON 字符串或请求对象
            runtime_client (RuntimeEventSink | None):
                可选运行时客户端
            transport (str):
                来源传输, ``legacy`` 或 ``desktop``
            token (str | None):
                该连接使用的 token
            after_send (list[Callable[[], Any]] | None):
                接收响应后回调的列表, 由调用方在写出响应后执行。为 None 时在分发后立即执行。

        Returns:
            dict[str, Any]:
                固定 ok/error 格式响应
        """

        return handle_control_request(
            raw,
            runtime_client=runtime_client,
            state=self.state,
            transport=transport,
            token=token,
            after_send=after_send,
        )


def get_catalog(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    查询当前可用功能和已注册补丁

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON-serializable 能力目录
    """

    active_state = state or get_default_state()
    defaults = get_default_config(state=active_state)
    features = build_setting_schema(get_feature_registry(active_state))
    _attach_feature_state(features, defaults, active_state)
    return {
        "features": features,
        "registered_patches": _registered_patches(active_state),
    }


def get_default_config(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    获取完整默认配置

    由状态对象的功能注册表生成, 包含运行时注册的第三方功能。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            新建的默认配置
    """

    return build_default_config(get_feature_registry(state or get_default_state()))


def get_current_config(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    获取当前进程最后加载或应用的完整配置

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            当前进程配置副本。尚未记录时返回默认配置。
    """

    active_state = state or get_default_state()
    with active_state.current_config_lock:
        if active_state.current_config is None:
            return get_default_config(state=active_state)
        return copy.deepcopy(active_state.current_config)


def set_current_config(config: dict[str, Any], *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    更新当前进程配置快照

    Args:
        config (dict[str, Any]):
            用户配置或完整配置
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            规范化后的当前配置副本
    """

    active_state = state or get_default_state()
    normalized = normalize_config(config, state=active_state)
    with active_state.current_config_lock:
        active_state.current_config = copy.deepcopy(normalized)
    return copy.deepcopy(normalized)


def clear_current_config(*, state: HotpatcherState | None = None) -> None:
    """清除当前进程配置快照, 下一次查询将返回默认配置

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    active_state = state or get_default_state()
    with active_state.current_config_lock:
        active_state.current_config = None


def normalize_config(config: dict[str, Any], *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    深度补齐默认配置

    用户配置中已有值保持不变。只有当用户值和默认值都是 dict 时才递归合并。

    Args:
        config (dict[str, Any]):
            用户配置
        state (HotpatcherState | None):
            提供功能注册表的状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            补齐默认值后的配置

    Raises:
        ValueError:
            配置顶层不是 object
    """

    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    normalized = _merge_defaults(copy.deepcopy(config), get_default_config(state=state))
    browser = _section(_section(normalized, "runtime"), "browser")
    if not isinstance(browser.get("enabled"), bool):
        raise ValueError("runtime.browser.enabled must be a boolean")
    mode = browser.get("mode")
    if mode not in {"host", "suppress", "passthrough"}:
        raise ValueError(f"unknown runtime.browser.mode: {mode!r}")
    return normalized


def load_config_file(path: str | Path, write_back: bool = True) -> dict[str, Any]:
    """
    读取并规范化 JSON 配置文件

    Args:
        path (str | Path):
            JSON 配置文件路径
        write_back (bool):
            是否把补齐后的配置写回文件

    Returns:
        dict[str, Any]:
            规范化后的配置

    Raises:
        ValueError:
            JSON 顶层不是 object
    """

    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError("config file must decode to an object")

    normalized = normalize_config(loaded)
    if write_back:
        save_config_file(config_path, normalized)
    return normalized


def save_config_file(path: str | Path, config: dict[str, Any]) -> None:
    """
    保存规范化后的 JSON 配置文件

    Args:
        path (str | Path):
            JSON 配置文件路径
        config (dict[str, Any]):
            待保存配置
    """

    config_path = Path(path).expanduser()
    normalized = normalize_config(config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
        file.write("\n")


def apply_config(
    config: dict[str, Any],
    *,
    runtime_client: RuntimeEventSink | None = None,
    state: HotpatcherState | None = None,
    reconcile: bool | None = None,
) -> dict[str, Any]:
    """
    按配置启用补丁系统功能

    按功能注册表的顺序应用, 每个启用的功能在自己的补丁集 ``feature:<key>`` 中应用; 重复应用
    复用同一个补丁集并再次调用功能入口 (扩展自身负责去重)。默认保持 v1 语义: ``enabled=false``
    只表示不再注册, 已生效的补丁保留并产生告警。

    Args:
        config (dict[str, Any]):
            用户配置或完整配置
        runtime_client (RuntimeEventSink | None):
            可选运行时客户端, 用于启用日志采集
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        reconcile (bool | None):
            是否撤销之前已应用、现在被禁用的功能。为 None 时读取 ``services.reconcile_disabled``;
            显式传入时优先于配置。启用时结果额外包含 ``reconciled`` 列表。

    Returns:
        dict[str, Any]:
            ``applied``、``warnings``、``errors`` 结果对象
    """

    active_state = state or get_default_state()
    normalized = normalize_config(config, state=active_state)
    result: dict[str, Any] = {"applied": [], "warnings": [], "errors": []}
    set_current_config(normalized, state=active_state)
    if reconcile is None:
        reconcile = bool(_section(normalized, "services").get("reconcile_disabled", False))

    _apply_features(normalized, result, runtime_client, active_state, reconcile=reconcile)
    _warn_disabled_but_active(normalized, result, active_state)
    return result


def handle_request_json(
    raw: str | dict[str, Any],
    *,
    runtime_client: RuntimeEventSink | None = None,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    处理 services JSON 请求

    Args:
        raw (str | dict[str, Any]):
            JSON 字符串或请求对象
        runtime_client (RuntimeEventSink | None):
            可选运行时客户端
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            固定 ok/error 格式响应
    """

    return handle_control_request(raw, runtime_client=runtime_client, state=state, transport="inprocess")


def handle_control_request(
    raw: str | dict[str, Any],
    *,
    runtime_client: RuntimeEventSink | None = None,
    state: HotpatcherState | None = None,
    transport: str = "inprocess",
    token: str | None = None,
    after_send: list[Callable[[], Any]] | None = None,
) -> dict[str, Any]:
    """
    解码请求并交给统一命令注册表分发

    ``services.*`` 请求的响应与 v1 完全一致; 同一入口也接受 ``hotpatch.*`` 控制命令。请求本身无法解码时返回
    ``invalid_json`` / ``request_failed``, 载荷不是 object 时返回 ``invalid_request``, 未知类型返回 ``unknown_request``。

    Args:
        raw (str | dict[str, Any]):
            JSON 字符串或请求对象
        runtime_client (RuntimeEventSink | None):
            可选运行时客户端, 原样传给命令处理函数
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        transport (str):
            来源传输: ``inprocess`` / ``legacy`` / ``desktop``
        token (str | None):
            该连接使用的 token
        after_send (list[Callable[[], Any]] | None):
            接收响应后回调的列表, 由调用方在写出响应后执行。为 None 时在分发后立即执行。

    Returns:
        dict[str, Any]:
            固定 ok/error 格式响应
    """

    active_state = state or get_default_state()
    try:
        request = _decode_request(raw)
    except json.JSONDecodeError as exc:
        return _error_response("invalid_json", str(exc))
    except (ValueError, TypeError) as exc:
        return _error_response("request_failed", str(exc))
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        return _error_response("invalid_request", "payload must be an object")

    from .control.controller import get_controller

    callbacks: list[Callable[[], Any]] = [] if after_send is None else after_send
    response = get_controller(active_state).dispatch(
        request["type"],
        payload,
        transport=transport,
        token=token,
        runtime_client=runtime_client,
        after_send=callbacks,
    )
    if after_send is None:
        run_after_send(callbacks)
    return response


def install_service_control_channel(
    client: RuntimeClient,
    service: PatchService | None = None,
    *,
    state: HotpatcherState | None = None,
) -> ServiceControlChannel:
    """
    安装 services runtime 控制通道

    Args:
        client (RuntimeClient):
            已连接的运行时客户端
        service (PatchService | None):
            可选服务对象
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        ServiceControlChannel:
            已启动的控制通道
    """

    return ServiceControlChannel(client, service or PatchService(state=state)).start()


def _apply_features(
    config: dict[str, Any],
    result: dict[str, Any],
    runtime_client: RuntimeEventSink | None,
    state: HotpatcherState,
    *,
    reconcile: bool = False,
) -> None:
    apply_feature_configs(config, result, runtime_client=runtime_client, state=state, reconcile=reconcile)


def _warn_disabled_but_active(config: dict[str, Any], result: dict[str, Any], state: HotpatcherState) -> None:
    warn_disabled_but_active(config, result, state=state)


def _attach_feature_state(features: dict[str, Any], defaults: dict[str, Any], state: HotpatcherState) -> None:
    attach_feature_state(features, defaults, state=state)
    _attach_setting_defaults(features)


# 内置 core / runtime 功能的行为, 由 ``control.features.BUILTIN_FEATURES`` 以
# ``"sd_webui_all_in_one_hotpatcher.services:<name>"`` 引用并在调用时解析, 因此对本模块属性的替换立即生效。


def _feature_apply_import_hook(ctx: FeatureContext, section: dict[str, Any]) -> None:
    del section
    install_import_hook(state=ctx.state)


def _feature_import_hook_active(ctx: FeatureContext) -> bool:
    return is_import_hook_installed(state=ctx.state)


def _feature_apply_stack_shadow(ctx: FeatureContext, section: dict[str, Any]) -> None:
    install_stack_shadower(
        _normalize_string_list(section.get("prefixes", [])),
        filename_template=str(section.get("filename_template", DEFAULT_FILENAME_TEMPLATE)),
        include_source_loaders=bool(section.get("include_source_loaders", True)),
        state=ctx.state,
    )


def _feature_stack_shadow_active(ctx: FeatureContext) -> bool:
    return is_stack_shadower_installed(state=ctx.state)


def _feature_apply_browser(ctx: FeatureContext, section: dict[str, Any]) -> None:
    from .runtime.browser import BrowserMode, patch_webbrowser

    mode = cast(BrowserMode, str(section.get("mode", "host")))
    try:
        patch_webbrowser(ctx.runtime_client, mode=mode, state=ctx.state)
    finally:
        if mode == "host" and ctx.runtime_client is None:
            ctx.warn("runtime client is unavailable; browser opening is suppressed without host events")


def _feature_update_browser(ctx: FeatureContext, old_section: dict[str, Any], new_section: dict[str, Any]) -> bool:
    # 包装器按 state 上的模式分派, 切换模式即可原地生效。
    del old_section
    _feature_apply_browser(ctx, new_section)
    return True


def _feature_browser_disabled(ctx: FeatureContext, section: dict[str, Any]) -> None:
    from .runtime.browser import is_webbrowser_patch_registered, patch_webbrowser

    del section
    if is_webbrowser_patch_registered(state=ctx.state):
        patch_webbrowser(None, mode="passthrough", state=ctx.state)


def _feature_revert_browser(ctx: FeatureContext) -> None:
    from .runtime.browser import patch_webbrowser

    patch_set = ctx.patch_set
    if patch_set is not None and any(handle.stage == "function" and handle.target == "webbrowser:open" for handle in patch_set.handles):
        # 功能补丁集已撤销 webbrowser.open 的 import 阶段注册, 重新启用时需要再次注册。
        ctx.state.browser_patch_registered = False
    patch_webbrowser(None, mode="passthrough", state=ctx.state)


def _feature_browser_active(ctx: FeatureContext) -> bool:
    from .runtime.browser import is_webbrowser_patch_active

    return is_webbrowser_patch_active(state=ctx.state)


def _feature_browser_registered(ctx: FeatureContext) -> bool:
    from .runtime.browser import is_webbrowser_patch_registered

    return is_webbrowser_patch_registered(state=ctx.state)


def _feature_apply_errors(ctx: FeatureContext, section: dict[str, Any]) -> None:
    caught_exceptions = _section(section, "caught_exceptions")
    install_error_capture(
        ctx.runtime_client,
        sys_excepthook=bool(section.get("sys_excepthook", True)),
        threading_excepthook=bool(section.get("threading_excepthook", True)),
        unraisablehook=bool(section.get("unraisablehook", True)),
        asyncio=bool(section.get("asyncio", True)),
        include_locals=bool(section.get("include_locals", False)),
        caught_exceptions_enabled=bool(caught_exceptions.get("enabled", False)),
        caught_exceptions_threading=bool(caught_exceptions.get("threading", True)),
        caught_exception_module_prefixes=_normalize_string_list(caught_exceptions.get("module_prefixes", [])),
        caught_exception_exclude_module_prefixes=_normalize_string_list(caught_exceptions.get("exclude_module_prefixes", DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES)),
        caught_exception_max_events_per_second=int(caught_exceptions.get("max_events_per_second", 20)),
        state=ctx.state,
    )


def _feature_errors_active(ctx: FeatureContext) -> bool:
    return is_error_capture_installed(state=ctx.state)


def _feature_errors_disabled(ctx: FeatureContext, section: dict[str, Any]) -> None:
    del section
    uninstall_error_capture(state=ctx.state)


def _feature_revert_errors(ctx: FeatureContext) -> None:
    uninstall_error_capture(state=ctx.state)


def _feature_apply_logs(ctx: FeatureContext, section: dict[str, Any]) -> None:
    install_log_capture(
        ctx.runtime_client,
        capture_logging=bool(section.get("logging", True)),
        streams=_normalize_string_list(section.get("streams", DEFAULT_STREAMS)),
        subprocess_mode=str(section.get("subprocess", "safe")),
        policy=str(section.get("policy", "bounded")),
        max_chars=int(section.get("max_chars", DEFAULT_MAX_CHARS)),
        queue_size=int(section.get("queue_size", DEFAULT_QUEUE_SIZE)),
        logger_include=_normalize_string_list(section.get("logger_include", [])),
        logger_exclude=_normalize_string_list(section.get("logger_exclude", DEFAULT_LOGGER_EXCLUDE)),
        hook_policy=str(section.get("hook_policy", DEFAULT_HOOK_POLICY)),
        hook_check_interval=int(section.get("hook_check_interval", DEFAULT_HOOK_CHECK_INTERVAL)),
        fd_capture=str(section.get("fd_capture", DEFAULT_FD_CAPTURE)),
        state=ctx.state,
    )


def _feature_revert_logs(ctx: FeatureContext) -> None:
    uninstall_log_capture(state=ctx.state)


def _attach_setting_defaults(features: dict[str, Any]) -> None:
    for feature in features.values():
        if not isinstance(feature, dict):
            continue
        feature_default = feature.get("default", {})
        if not isinstance(feature_default, dict):
            continue
        settings = feature.get("settings", {})
        if not isinstance(settings, dict):
            continue
        for setting_name, metadata in settings.items():
            if not isinstance(metadata, dict):
                continue
            setting_default = _get_value_by_path(feature_default, setting_name, _MISSING)
            if setting_default is _MISSING:
                continue
            metadata["default"] = copy.deepcopy(setting_default)


def _registered_patches(state: HotpatcherState) -> dict[str, Any]:
    modules: dict[str, Any] = {}
    zoo = state.monkey_zoo or monkey_zoo
    for name, monkey in sorted(zoo.monkeys.items()):
        modules[name] = {
            "premodule": len(monkey.premodule_patches),
            "module": len(monkey.module_patches),
            "function": len(monkey.function_patches),
            "source": len(monkey.source_patches),
            "ast": len(monkey.ast_patches),
            "bytecode": len(monkey.bytecode_patches),
            "output_prohibition": len(monkey.output_prohibition),
            "import_injection": len(monkey.import_injections),
        }
    return {
        "modules": modules,
        "aliases": dict(sorted(zoo.aliases_fallback.items())),
    }


def _merge_defaults(config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    for key, default_value in defaults.items():
        if key not in config:
            config[key] = copy.deepcopy(default_value)
            continue
        current_value = config[key]
        if isinstance(current_value, dict) and isinstance(default_value, dict):
            _merge_defaults(current_value, default_value)
    return config


def _decode_request(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("request must be an object")
    if not isinstance(raw.get("type"), str):
        raise ValueError("request type is required")
    return raw


def _payload_config(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("payload.config must be an object")
    return config


def _payload_path(payload: dict[str, Any]) -> str:
    path = payload.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("payload.path must be a non-empty string")
    return path


def _get_value_by_path(config: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = config
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _section(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key, {})
    return value if isinstance(value, dict) else {}


def _normalize_string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _success_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "payload": payload}


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
