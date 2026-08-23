"""Hotpatcher 配置和运行时宿主管理"""

from __future__ import annotations

import copy
import json
import os
import queue
import socketserver
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
    ROOT_PATH,
    SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH,
)
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

if TYPE_CHECKING:
    from sd_webui_all_in_one_hotpatcher import services

HOTPATCHER_PATH = ROOT_PATH / "patcher"
DEFAULT_HOTPATCHER_CONFIG_PATH = SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH
DEFAULT_RUNTIME_HOST = "127.0.0.1"
DEFAULT_RUNTIME_PORT = 8765
HOTPATCHER_ENV_PREFIX = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_"


def ensure_hotpatcher_import_path() -> Path:
    """
    确保抽取版 hotpatcher 目录可以被导入。

    Returns:
        Path:
            hotpatcher 源码目录。
    """

    path_text = HOTPATCHER_PATH.as_posix()
    if path_text not in sys.path:
        logger.debug("将 hotpatcher 源码目录 %s 插入 sys.path 首位", path_text)
        sys.path.insert(0, path_text)
    return HOTPATCHER_PATH


def _services_module() -> "services":  # ty: ignore[invalid-type-form]
    ensure_hotpatcher_import_path()
    from sd_webui_all_in_one_hotpatcher import services

    logger.debug("加载 hotpatcher services 模块")
    return services


def get_hotpatcher_default_config() -> dict[str, Any]:
    """
    获取 hotpatcher 默认配置

    Returns:
        dict[str, Any]:
            hotpatcher services 提供的默认配置。
    """

    config = _services_module().get_default_config()
    logger.debug("获取 hotpatcher 默认配置")
    return config


def get_hotpatcher_catalog() -> dict[str, Any]:
    """
    获取 hotpatcher 功能目录

    Returns:
        dict[str, Any]:
            hotpatcher features catalog 和已注册补丁信息。
    """

    catalog = _services_module().get_catalog()
    logger.debug("获取 hotpatcher 功能目录")
    return catalog


def normalize_hotpatcher_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    补齐 hotpatcher 配置默认值

    Args:
        config (dict[str, Any]):
            原始配置对象。

    Returns:
        dict[str, Any]:
            补齐默认值后的配置对象。
    """

    logger.debug("补齐 hotpatcher 配置默认值")
    return _services_module().normalize_config(config)


def _resolve_config_path(path: str | Path | None = None) -> Path:
    return Path(path).expanduser() if path is not None else DEFAULT_HOTPATCHER_CONFIG_PATH


def load_hotpatcher_config(path: str | Path | None = None, normalize: bool = True) -> dict[str, Any]:
    """
    读取 hotpatcher JSON 配置文件。

    Args:
        path (str | Path | None):
            配置文件路径。为 None 时使用默认配置路径。
        normalize (bool):
            是否补齐默认值。

    Returns:
        dict[str, Any]:
            配置对象。

    Raises:
        ValueError:
            配置文件内容不是 JSON 对象时抛出。
    """

    config_path = _resolve_config_path(path)
    logger.debug("读取 hotpatcher 配置, 路径: %s, normalize: %s", config_path, normalize)
    if normalize:
        config = _services_module().load_config_file(config_path, write_back=False)
    else:
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict):
            logger.error("hotpatcher 配置文件 %s 内容不是 JSON 对象", config_path)
            raise ValueError("hotpatcher config file must decode to an object")
    logger.debug("hotpatcher 配置加载完成, 配置键: %s", list(config.keys()))
    return config


def save_hotpatcher_config(path: str | Path | None, config: dict[str, Any]) -> None:
    """
    保存 hotpatcher JSON 配置文件

    Args:
        path (str | Path | None):
            配置文件路径。为 None 时使用默认配置路径。
        config (dict[str, Any]):
            要写出的配置对象。
    """

    config_path = _resolve_config_path(path)
    logger.info("保存 hotpatcher 配置, 路径: %s", config_path)
    _services_module().save_config_file(config_path, config)


def export_hotpatcher_default_config(path: str | Path | None = None, overwrite: bool = False) -> Path:
    """
    导出 hotpatcher 默认配置。

    Args:
        path (str | Path | None):
            输出路径。为 None 时使用默认配置路径。
        overwrite (bool):
            是否覆盖已有文件。

    Returns:
        Path:
            写出的配置文件路径。

    Raises:
        FileExistsError:
            配置文件已存在且未允许覆盖时抛出。
    """

    output_path = _resolve_config_path(path)
    if output_path.exists() and not overwrite:
        logger.warning("导出目标文件已存在且未允许覆盖, 路径: %s", output_path)
        raise FileExistsError(f"Config file already exists: {output_path}")
    logger.info("导出 hotpatcher 默认配置, 路径: %s, overwrite: %s", output_path, overwrite)
    save_hotpatcher_config(output_path, get_hotpatcher_default_config())
    return output_path


def apply_hotpatcher_config(config_or_path: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    """
    应用 hotpatcher 配置到当前进程。

    Args:
        config_or_path (dict[str, Any] | str | Path | None):
            配置对象或配置文件路径。为 None 时读取默认配置路径。

    Returns:
        dict[str, Any]:
            services.apply_config 返回的应用结果。
    """

    if isinstance(config_or_path, dict):
        config = config_or_path
        logger.debug("直接应用传入的 hotpatcher 配置对象")
    else:
        logger.debug("从路径加载 hotpatcher 配置: %s", config_or_path)
        config = load_hotpatcher_config(config_or_path, normalize=True)
    result = _services_module().apply_config(config)
    logger.info("hotpatcher 配置应用完成")
    return result


def apply_hotpatcher_launch_env(
    origin_env: dict[str, str] | None = None,
    enabled: bool = False,
    config_path: str | Path | None = None,
    port: int = DEFAULT_RUNTIME_PORT,
    enable_runtime: bool = False,
) -> dict[str, str]:
    """
    为 WebUI 启动环境注入 hotpatcher bootstrap 变量。

    Args:
        origin_env (dict[str, str] | None):
            原始环境变量。
        enabled (bool):
            是否启用 hotpatcher。关闭时会移除现有 hotpatcher 环境变量。
        config_path (str | Path | None):
            配置文件路径。为 None 时优先使用默认配置文件，不存在则注入默认配置 JSON。
        port (int):
            runtime host 端口。
        enable_runtime (bool):
            是否注入 runtime host 连接变量。默认只做本地补丁配置注入。

    Returns:
        dict[str, str]:
            注入后的环境变量。
    """

    env = origin_env.copy() if origin_env is not None else os.environ.copy()
    preserved_keys = {"SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG"}
    if enable_runtime:
        preserved_keys.update(
            {
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN",
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT",
            }
        )
    preserved = {key: value for key, value in env.items() if key in preserved_keys}
    env = remove_hotpatcher_launch_env(env)

    if not enabled:
        logger.info("hotpatcher 未启用, 已移除相关启动环境变量")
        return env

    env.update(preserved)
    env = ensure_hotpatcher_pythonpath_first(env)
    if enable_runtime:
        env.update(
            {
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "1",
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST": DEFAULT_RUNTIME_HOST,
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT": str(port),
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES": "1",
            }
        )

    if config_path is not None:
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] = "file"
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] = Path(config_path).expanduser().as_posix()
    elif DEFAULT_HOTPATCHER_CONFIG_PATH.is_file():
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] = "file"
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] = DEFAULT_HOTPATCHER_CONFIG_PATH.as_posix()
    else:
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] = "env"
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON"] = json.dumps(
            get_hotpatcher_default_config(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    config_source = env.get("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "unknown")
    config_file = env.get("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE")
    logger.info(
        "hotpatcher 启动环境注入完成, 配置来源: %s, 配置文件: %s, enable_runtime: %s",
        config_source,
        config_file,
        enable_runtime,
    )
    return env


def configure_hotpatcher_for_current_process(enabled: bool = False) -> Any:
    """
    在当前 Python 进程中根据 hotpatcher 环境变量执行 bootstrap

    InvokeAI 这类入口不会新建 Python 子进程, 因此不能依赖 sitecustomize
    在解释器启动时自动执行。

    Args:
        enabled (bool):
            是否启用当前进程 hotpatcher bootstrap。

    Returns:
        Any:
            ``bootstrap.configure_from_env()`` 返回的状态对象。未启用时返回 None。
    """

    if not enabled:
        return None
    logger.info("在当前进程执行 hotpatcher bootstrap")
    ensure_hotpatcher_import_path()
    from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

    state = configure_from_env()
    logger.debug("hotpatcher bootstrap 完成")
    return state


def remove_hotpatcher_launch_env(origin_env: dict[str, str]) -> dict[str, str]:
    """
    移除 hotpatcher 启动环境变量

    Args:
        origin_env (dict[str, str]):
            原始环境变量。

    Returns:
        dict[str, str]:
            移除 hotpatcher 前缀变量后的环境变量。
    """

    env = {key: value for key, value in origin_env.items() if not key.startswith(HOTPATCHER_ENV_PREFIX)}
    logger.debug("已移除 %d 个 hotpatcher 前缀环境变量", len(origin_env) - len(env))
    return env


def ensure_hotpatcher_pythonpath_first(origin_env: dict[str, str]) -> dict[str, str]:
    """
    确保 hotpatcher 目录位于 PYTHONPATH 第一项

    Args:
        origin_env (dict[str, str]):
            原始环境变量。

    Returns:
        dict[str, str]:
            调整 PYTHONPATH 后的环境变量。
    """

    env = origin_env.copy()
    path_text = HOTPATCHER_PATH.as_posix()
    current = env.get("PYTHONPATH", "")
    parts = [item for item in current.split(os.pathsep) if item and item != path_text]
    env["PYTHONPATH"] = os.pathsep.join([path_text, *parts])
    logger.debug("确保 hotpatcher 目录 %s 位于 PYTHONPATH 首位", path_text)
    return env


def build_hotpatcher_runtime_env(
    host: str,
    port: int,
    token: str = "",
    config_source: str = "remote",
) -> dict[str, str]:
    """
    构建让 hotpatcher 进程连接管理器 runtime host 的环境变量。

    Args:
        host (str):
            runtime host 地址。
        port (int):
            runtime host 端口。
        token (str):
            连接 token。
        config_source (str):
            配置来源。

    Returns:
        dict[str, str]:
            需要传给目标进程的环境变量。
    """

    env = {
        "PYTHONPATH": HOTPATCHER_PATH.as_posix(),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "1",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST": str(host),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT": str(port),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE": str(config_source),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK": "1",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES": "1",
    }
    if token:
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] = token
    logger.debug("构建 hotpatcher runtime 连接环境, host: %s, port: %s, config_source: %s", host, port, config_source)
    return env


def launch_hotpatcher_manager_gui(
    config_path: str | Path | None = DEFAULT_HOTPATCHER_CONFIG_PATH,
    host: str = DEFAULT_RUNTIME_HOST,
    port: int = DEFAULT_RUNTIME_PORT,
    token: str = "",
) -> None:
    """
    启动 hotpatcher 配置管理 GUI

    Args:
        config_path (str | Path | None):
            启动时加载的配置文件路径。
        host (str):
            runtime host 监听地址。
        port (int):
            runtime host 监听端口。
        token (str):
            runtime host 连接 token。

    Raises:
        RuntimeError:
            当前 Python 环境未安装 tkinter 时抛出。
        ModuleNotFoundError:
            启动 GUI 时缺少非 tkinter 模块时继续抛出。
    """

    try:
        from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui import launch_hotpatcher_manager_gui as _launch_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            logger.error("当前 Python 环境未安装 tkinter, 无法启动补丁系统配置管理 GUI")
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动补丁系统配置管理 GUI") from e
        logger.error("启动 GUI 时缺少模块: %s", e.name)
        raise e

    logger.info("启动 hotpatcher 配置管理 GUI, host: %s, port: %s", host, port)
    _launch_gui(config_path=config_path, host=host, port=port, token=token)


@dataclass(slots=True)
class RuntimeLogEntry:
    """
    runtime 日志事件

    Attributes:
        message_type (str):
            runtime 消息类型。
        payload (dict[str, Any]):
            runtime 消息载荷。
        created (float):
            记录创建时间戳。
    """

    message_type: str
    payload: dict[str, Any]
    created: float = field(default_factory=time.time)
    sequence: int = 0

    def format_line(self) -> str:
        """
        格式化为 GUI / CLI 可读日志行

        Returns:
            str:
                可直接显示的单行日志文本。
        """

        if self.message_type == "log.record":
            level = self.payload.get("level", "LOG")
            logger_name = self.payload.get("logger", "")
            message = self.payload.get("message", "")
            return f"[{level}] {logger_name}: {message}".rstrip()
        if self.message_type == "log.stream":
            stream = self.payload.get("stream", "stream")
            source = self.payload.get("source", "stream")
            text = str(self.payload.get("text", ""))
            return f"[{source}/{stream}] {text}".rstrip()
        if self.message_type == "log.dropped":
            count = self.payload.get("count", 0)
            reason = self.payload.get("reason", "")
            return f"[dropped] {count} messages dropped: {reason}".rstrip()
        return f"[{self.message_type}] {json.dumps(self.payload, ensure_ascii=False)}"


@dataclass(slots=True)
class RuntimeMessage:
    """
    runtime 原始消息记录

    Attributes:
        message (dict[str, Any]):
            原始 runtime 消息。
        address (tuple[str, int] | None):
            客户端地址。
        created (float):
            记录创建时间戳。
    """

    message: dict[str, Any]
    address: tuple[str, int] | None = None
    created: float = field(default_factory=time.time)


@dataclass(slots=True)
class RuntimeBrowserEvent:
    """运行时主机保留的已校验浏览器请求。"""

    sequence: int
    url: str
    created: float = field(default_factory=time.time)


class RemoteServiceError(RuntimeError):
    """
    远程 services channel 请求失败

    Attributes:
        code (str):
            错误代码。
        message (str):
            错误说明。
        payload (dict[str, Any]):
            远端返回的错误载荷。
    """

    def __init__(self, code: str, message: str = "", payload: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"{code}: {message}" if message else code)


class _PendingRequest:
    def __init__(self) -> None:
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)


class RuntimeServiceChannel:
    """
    连接到远端 hotpatcher services 控制通道的宿主侧对象

    Attributes:
        writer (Any):
            services channel 的写入端。
        on_close (Callable[[RuntimeServiceChannel], None] | None):
            通道关闭时的回调函数。
        closed (bool):
            通道是否已关闭。
    """

    def __init__(
        self,
        writer: Any,
        *,
        on_close: Callable[["RuntimeServiceChannel"], None] | None = None,
    ) -> None:
        self.writer = writer
        self.on_close = on_close
        self._write_lock = threading.Lock()
        self._pending: dict[str, _PendingRequest] = {}
        self._pending_lock = threading.Lock()
        self.closed = False

    def request(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        向远端 services channel 发送请求并等待响应

        Args:
            message_type (str):
                services 请求类型。
            payload (dict[str, Any] | None):
                请求载荷。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                远端响应载荷。

        Raises:
            RemoteServiceError:
                通道关闭、请求超时或远端返回错误时抛出。
        """

        message_id = uuid.uuid4().hex
        pending = _PendingRequest()
        with self._pending_lock:
            if self.closed:
                logger.warning("services channel 已关闭, 拒绝发送请求 %s", message_type)
                raise RemoteServiceError("channel_closed", "services channel is closed")
            self._pending[message_id] = pending

        logger.debug("发送 services 请求, id: %s, type: %s, timeout: %s", message_id, message_type, timeout)
        try:
            self._send(
                {
                    "id": message_id,
                    "type": message_type,
                    "payload": payload or {},
                }
            )
            try:
                response = pending.queue.get(timeout=timeout)
            except queue.Empty as exc:
                logger.error("services 请求 %s (%s) 等待响应超时", message_type, message_id)
                raise RemoteServiceError("timeout", "services request timed out") from exc

            if response.get("ok") is True:
                response_payload = response.get("payload", {})
                logger.debug("services 请求 %s (%s) 成功", message_type, message_id)
                return response_payload if isinstance(response_payload, dict) else {}

            error = response.get("error", {})
            if not isinstance(error, dict):
                error = {}
            logger.warning("services 请求 %s (%s) 远端返回错误: %s", message_type, message_id, error.get("code", "request_failed"))
            raise RemoteServiceError(
                str(error.get("code", "request_failed")),
                str(error.get("message", "")),
                error,
            )
        finally:
            with self._pending_lock:
                self._pending.pop(message_id, None)

    def handle_message(self, message: dict[str, Any]) -> bool:
        """
        处理 services channel 输入消息

        Args:
            message (dict[str, Any]):
                远端发来的 JSON 消息。

        Returns:
            bool:
                消息匹配到等待中的请求时返回 True。
        """

        message_id = message.get("id")
        if not isinstance(message_id, str):
            return False
        with self._pending_lock:
            pending = self._pending.get(message_id)
        if pending is None:
            return False
        try:
            pending.queue.put_nowait(message)
        except queue.Full:
            return False
        logger.debug("services 通道收到匹配请求 id: %s 的响应", message_id)
        return True

    def close(self) -> None:
        """
        标记通道关闭

        关闭时会触发 ``on_close`` 回调, 用于从 runtime host 中移除当前通道。
        """

        with self._pending_lock:
            if self.closed:
                return
            logger.debug("services 通道关闭")
            self.closed = True
            pending_requests = tuple(self._pending.values())
        closed_response = {
            "ok": False,
            "error": {
                "code": "channel_closed",
                "message": "services channel is closed",
            },
        }
        for pending in pending_requests:
            try:
                pending.queue.put_nowait(closed_response)
            except queue.Full:
                pass
        if self.on_close is not None:
            self.on_close(self)

    def _send(self, message: dict[str, Any]) -> None:
        data = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._write_lock:
            self.writer.write(data)
            self.writer.flush()


class _RuntimeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class HotpatcherRuntimeHost:
    """
    hotpatcher runtime 宿主。

    该对象监听 TCP JSONL 端口, 接收补丁进程主动连接、配置请求、日志事件和
    services 控制通道。

    Attributes:
        host (str):
            runtime host 监听地址。
        port (int):
            runtime host 监听端口。
        token (str):
            连接 token。
        messages (list[RuntimeMessage]):
            已接收的 runtime 原始消息。
        log_entries (list[RuntimeLogEntry]):
            已接收的 runtime 日志事件。
        log_queue (queue.Queue[RuntimeLogEntry]):
            供 GUI / CLI 消费的日志队列。
    """

    def __init__(
        self,
        host: str = DEFAULT_RUNTIME_HOST,
        port: int = DEFAULT_RUNTIME_PORT,
        *,
        token: str = "",
        get_config: Callable[[], dict[str, Any]] | None = None,
        on_message: Callable[[RuntimeMessage], None] | None = None,
        on_log: Callable[[RuntimeLogEntry], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        confirm_file_operation: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.token = token
        self.get_config = get_config or get_hotpatcher_default_config
        self.on_message = on_message
        self.on_log = on_log
        self.on_status = on_status
        self.confirm_file_operation = confirm_file_operation
        self.messages: list[RuntimeMessage] = []
        self.log_entries: list[RuntimeLogEntry] = []
        self.browser_events: list[RuntimeBrowserEvent] = []
        self.browser_diagnostics: list[str] = []
        self.log_queue: queue.Queue[RuntimeLogEntry] = queue.Queue()
        self._lock = threading.Lock()
        self._server: _RuntimeServer | None = None
        self._thread: threading.Thread | None = None
        self._service_channel: RuntimeServiceChannel | None = None
        self._next_log_sequence = 0
        self._log_retention = 2000
        self._next_browser_sequence = 0
        self._browser_retention = 256
        self.runtime_identity = uuid.uuid4().hex

    @property
    def server_address(self) -> tuple[str, int]:
        """
        获取实际监听地址

        Returns:
            tuple[str, int]:
                runtime host 实际监听的 host 和 port。
        """

        if self._server is None:
            return (self.host, self.port)
        host, port = self._server.server_address[:2]
        return (str(host), int(port))

    @property
    def service_channel_available(self) -> bool:
        """
        判断是否已连接远端 services 控制通道

        Returns:
            bool:
                services 控制通道可用时返回 True。
        """

        channel = self._service_channel
        return channel is not None and not channel.closed

    @property
    def browser_next_cursor(self) -> int:
        """返回用于启动基线的下一个单调递增浏览器序号。

        Returns:
            int: 下一个浏览器事件游标。
        """

        with self._lock:
            return self._next_browser_sequence

    def start(self) -> "HotpatcherRuntimeHost":
        """
        启动 runtime host

        Returns:
            HotpatcherRuntimeHost:
                当前 runtime host 实例。
        """

        if self._server is not None:
            return self

        logger.info("启动 hotpatcher runtime host, host: %s, port: %s", self.host, self.port)
        with self._lock:
            self.browser_events.clear()
            self.browser_diagnostics.clear()
            self._next_browser_sequence = 0
            self.runtime_identity = uuid.uuid4().hex

        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:  # noqa: D401
                outer._handle_client(self)

        self._server = _RuntimeServer((self.host, self.port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="sd-webui-all-in-one-hotpatcher-runtime-host",
            daemon=True,
        )
        self._thread.start()
        self._emit_status(f"runtime host listening on {self.server_address[0]}:{self.server_address[1]}")
        return self

    def stop(self) -> None:
        """
        停止 runtime host

        会关闭当前 services channel、停止 TCP server 并等待后台线程退出。
        """

        if self._service_channel is not None:
            self._service_channel.close()
            self._service_channel = None
        server = self._server
        self._server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("hotpatcher runtime host 已停止")
        self._emit_status("runtime host stopped")

    def request_services(
        self,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        向已连接补丁进程的 services channel 发送请求

        Args:
            message_type (str):
                services 请求类型。
            payload (dict[str, Any] | None):
                请求载荷。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                远端响应载荷。

        Raises:
            RemoteServiceError:
                services channel 未连接或请求失败时抛出。
        """

        channel = self._service_channel
        if channel is None or channel.closed:
            logger.warning("services channel 未连接, 无法发送请求 %s", message_type)
            raise RemoteServiceError("channel_unavailable", "services channel is not connected")
        return channel.request(message_type, payload, timeout=timeout)

    def apply_remote_config(
        self,
        config: dict[str, Any],
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        通过 services channel 应用远端配置

        Args:
            config (dict[str, Any]):
                要应用到远端进程的 hotpatcher 配置。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                远端 services.apply_config 的结果。

        Raises:
            RemoteServiceError:
                services channel 未连接或请求失败时抛出。
        """

        logger.debug("通过 services channel 应用远端 hotpatcher 配置")
        payload = self.request_services(
            "services.config.apply",
            {"config": config},
            timeout=timeout,
        )
        result = payload.get("result", {})
        logger.debug("远端配置应用结果: %s", list(result.keys()))
        return result if isinstance(result, dict) else {}

    def close(self) -> None:
        """
        关闭 runtime host

        该方法等价于调用 ``stop()``。
        """

        self.stop()

    def __enter__(self) -> "HotpatcherRuntimeHost":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def _handle_client(self, handler: socketserver.StreamRequestHandler) -> None:
        address = self._client_address(handler)
        first_line = handler.rfile.readline()
        if not first_line:
            return
        try:
            first_message = self._decode(first_line)
        except Exception as exc:
            logger.warning("来自 %s 的非法 runtime 消息: %s", address, exc)
            self._emit_status(f"invalid runtime message from {address}: {exc}")
            return

        if not self._check_token(first_message):
            logger.warning("来自 %s 的 runtime token 校验失败", address)
            self._emit_status(f"runtime token rejected from {address}")
            return

        logger.debug("收到来自 %s 的首条 runtime 消息, type: %s", address, first_message.get("type"))
        self._record_message(first_message, address)
        if first_message.get("type") == "channel.open":
            self._handle_channel(handler, first_message, address)
            return

        for raw_line in handler.rfile:
            try:
                message = self._decode(raw_line)
            except Exception as exc:
                logger.warning("来自 %s 的非法 runtime 消息: %s", address, exc)
                self._emit_status(f"invalid runtime message from {address}: {exc}")
                continue
            self._record_message(message, address)
            self._handle_main_message(handler, message)

    def _handle_channel(
        self,
        handler: socketserver.StreamRequestHandler,
        message: dict[str, Any],
        address: tuple[str, int] | None,
    ) -> None:
        channel_name = message.get("channel")
        if channel_name == "services":
            channel = RuntimeServiceChannel(handler.wfile, on_close=self._remove_service_channel)
            self._service_channel = channel
            logger.info("services channel 已连接, 来源: %s", address)
            self._emit_status(f"services channel connected from {address}")
            try:
                for raw_line in handler.rfile:
                    try:
                        incoming = self._decode(raw_line)
                    except Exception as exc:
                        logger.warning("来自 %s 的非法 services 消息: %s", address, exc)
                        self._emit_status(f"invalid services message from {address}: {exc}")
                        continue
                    self._record_message(incoming, address)
                    channel.handle_message(incoming)
            finally:
                channel.close()
                logger.info("services channel 已断开, 来源: %s", address)
                self._emit_status("services channel disconnected")
            return

        if channel_name == "fault":
            logger.debug("fault channel 已连接, 来源: %s", address)
            self._emit_status(f"fault channel connected from {address}")
            for raw_line in handler.rfile:
                payload = {"stream": "fault", "text": raw_line.decode("utf-8", errors="replace"), "source": "fault"}
                self._record_log(RuntimeLogEntry("log.stream", payload))

    def _handle_main_message(
        self,
        handler: socketserver.StreamRequestHandler,
        message: dict[str, Any],
    ) -> None:
        message_type = str(message.get("type", ""))
        message_id = message.get("id")
        logger.debug("处理 runtime 消息, id: %s, type: %s", message_id, message_type)
        if message_type.startswith("log."):
            self._record_log(RuntimeLogEntry(message_type, dict(message.get("payload", {}) if isinstance(message.get("payload"), dict) else {})))

        if message_id is None:
            return

        if message_type == "config.get":
            logger.debug("响应 config.get 请求, id: %s", message_id)
            self._send_response(handler, message_id, {"config": self._safe_config()})
            return

        if message_type.startswith("file."):
            if self.confirm_file_operation is not None and self.confirm_file_operation(message_type, self._payload(message)):
                logger.debug("响应 file 请求 %s, id: %s, 已接受", message_type, message_id)
                self._send_response(handler, message_id, {"accepted": True})
            else:
                logger.warning("file 操作 %s (id: %s) 被拒绝", message_type, message_id)
                self._send_error(handler, message_id, "cancelled", "file operation cancelled")
            return

        self._send_response(handler, message_id, {"accepted": True})

    def _record_message(self, message: dict[str, Any], address: tuple[str, int] | None) -> None:
        entry = RuntimeMessage(copy.deepcopy(message), address=address)
        with self._lock:
            self.messages.append(entry)
        if message.get("type") == "browser.open":
            payload = message.get("payload")
            url = payload.get("url") if isinstance(payload, dict) else None
            if isinstance(url, str):
                self._record_browser_event(url)
            else:
                diagnostic = "rejected malformed browser.open runtime event"
                logger.warning("拒绝格式错误的 browser.open 消息, 来源: %s", address)
                with self._lock:
                    self.browser_diagnostics.append(diagnostic)
                    del self.browser_diagnostics[:-100]
                self._emit_status(diagnostic)
        if self.on_message is not None:
            self.on_message(entry)

    def _record_browser_event(self, url: str) -> None:
        with self._lock:
            event = RuntimeBrowserEvent(
                sequence=self._next_browser_sequence,
                url=url,
            )
            self._next_browser_sequence += 1
            self.browser_events.append(event)
            overflow = len(self.browser_events) - self._browser_retention
            if overflow > 0:
                del self.browser_events[:overflow]
        logger.debug("记录浏览器事件, sequence: %s, url: %s", event.sequence, url)

    def read_browser_events(self, since_cursor: int = 0, limit: int = 100) -> dict[str, Any]:
        """读取已校验浏览器事件的有界单调切片。

        Args:
            since_cursor (int): 起始游标。
            limit (int): 最多返回的事件数量。

        Returns:
            dict[str, Any]: 浏览器事件切片及游标信息。
        """

        bounded_limit = max(1, min(int(limit), 200))
        requested = max(0, int(since_cursor))
        with self._lock:
            first_cursor = (
                self.browser_events[0].sequence
                if self.browser_events
                else self._next_browser_sequence
            )
            start_cursor = max(requested, first_cursor)
            selected = [
                event
                for event in self.browser_events
                if event.sequence >= start_cursor
            ][:bounded_limit]
            next_cursor = selected[-1].sequence + 1 if selected else start_cursor
            logger.debug("读取浏览器事件, since_cursor: %s, limit: %s, 返回 %s 条", requested, bounded_limit, len(selected))
            return {
                "runtime_identity": self.runtime_identity,
                "events": [
                    {
                        "sequence": event.sequence,
                        "url": event.url,
                        "created": event.created,
                    }
                    for event in selected
                ],
                "start_cursor": start_cursor,
                "next_cursor": next_cursor,
                "truncated": requested < first_cursor,
            }

    def _record_log(self, entry: RuntimeLogEntry) -> None:
        with self._lock:
            entry.sequence = self._next_log_sequence
            self._next_log_sequence += 1
            self.log_entries.append(entry)
            overflow = len(self.log_entries) - self._log_retention
            if overflow > 0:
                del self.log_entries[:overflow]
        self.log_queue.put(entry)
        if self.on_log is not None:
            self.on_log(entry)

    def read_logs(self, since_cursor: int = 0, limit: int = 200) -> dict[str, Any]:
        """读取已保留运行时日志的有界单调切片。

        Args:
            since_cursor (int): 起始游标。
            limit (int): 最多返回的日志数量。

        Returns:
            dict[str, Any]: 运行时日志切片及游标信息。
        """

        bounded_limit = max(1, min(int(limit), 1000))
        requested = max(0, int(since_cursor))
        with self._lock:
            first_cursor = self.log_entries[0].sequence if self.log_entries else self._next_log_sequence
            start_cursor = max(requested, first_cursor)
            selected = [item for item in self.log_entries if item.sequence >= start_cursor][:bounded_limit]
            next_cursor = selected[-1].sequence + 1 if selected else start_cursor
            logger.debug("读取 runtime 日志, since_cursor: %s, limit: %s, 返回 %s 条", requested, bounded_limit, len(selected))
            return {
                "logs": [
                    {
                        "sequence": item.sequence,
                        "message_type": item.message_type,
                        "payload": item.payload,
                        "created": item.created,
                        "line": item.format_line(),
                    }
                    for item in selected
                ],
                "start_cursor": start_cursor,
                "next_cursor": next_cursor,
                "truncated": requested < first_cursor,
            }

    def _safe_config(self) -> dict[str, Any]:
        try:
            config = self.get_config()
        except Exception:
            logger.exception("获取 hotpatcher 配置失败, 返回空配置")
            config = {}
        return config if isinstance(config, dict) else {}

    def _remove_service_channel(self, channel: RuntimeServiceChannel) -> None:
        if self._service_channel is channel:
            logger.debug("移除已断开的 services channel")
            self._service_channel = None

    def _check_token(self, message: dict[str, Any]) -> bool:
        if not self.token:
            return True
        return str(message.get("token", "")) == self.token

    def _emit_status(self, message: str) -> None:
        if self.on_status is not None:
            self.on_status(message)

    @staticmethod
    def _client_address(handler: socketserver.StreamRequestHandler) -> tuple[str, int] | None:
        address = getattr(handler, "client_address", None)
        if isinstance(address, tuple) and len(address) >= 2:
            return (str(address[0]), int(address[1]))
        return None

    @staticmethod
    def _payload(message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", {})
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _decode(line: bytes) -> dict[str, Any]:
        message = json.loads(line.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("runtime message must be an object")
        return message

    @staticmethod
    def _send_response(
        handler: socketserver.StreamRequestHandler,
        message_id: Any,
        payload: dict[str, Any],
    ) -> None:
        HotpatcherRuntimeHost._send(handler, {"id": message_id, "ok": True, "payload": payload})

    @staticmethod
    def _send_error(
        handler: socketserver.StreamRequestHandler,
        message_id: Any,
        code: str,
        message: str,
    ) -> None:
        HotpatcherRuntimeHost._send(handler, {"id": message_id, "ok": False, "error": {"code": code, "message": message}})

    @staticmethod
    def _send(handler: socketserver.StreamRequestHandler, message: dict[str, Any]) -> None:
        data = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        handler.wfile.write(data)
        handler.wfile.flush()


def wait_for_runtime_log(
    host: HotpatcherRuntimeHost,
    predicate: Callable[[RuntimeLogEntry], bool],
    timeout: float = 2.0,
) -> RuntimeLogEntry | None:
    """
    等待符合条件的 runtime 日志

    Args:
        host (HotpatcherRuntimeHost):
            runtime host 实例。
        predicate (Callable[[RuntimeLogEntry], bool]):
            日志匹配函数。
        timeout (float):
            等待超时时间。

    Returns:
        RuntimeLogEntry | None:
            匹配到的日志事件。超时时返回 None。
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        with host._lock:  # pylint: disable=protected-access
            for entry in host.log_entries:
                if predicate(entry):
                    logger.debug("等待到符合条件的 runtime 日志")
                    return entry
        time.sleep(0.02)
    logger.debug("等待 runtime 日志超时")
    return None


def wait_for_service_channel(host: HotpatcherRuntimeHost, timeout: float = 2.0) -> bool:
    """
    等待 services channel 连接

    Args:
        host (HotpatcherRuntimeHost):
            runtime host 实例。
        timeout (float):
            等待超时时间。

    Returns:
        bool:
            services channel 在超时前连接时返回 True。
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        if host.service_channel_available:
            logger.debug("services channel 已连接")
            return True
        time.sleep(0.02)
    logger.debug("等待 services channel 连接超时")
    return False
