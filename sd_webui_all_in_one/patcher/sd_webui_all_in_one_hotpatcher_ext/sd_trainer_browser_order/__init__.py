"""SD Trainer Next 浏览器打开顺序热补丁。"""

from __future__ import annotations

import functools
import inspect
import os
import socket
import sys
import threading
import time
from types import ModuleType
from typing import Any, Callable
from urllib.parse import urlsplit

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo
from sd_webui_all_in_one_hotpatcher.logger import get_hotpatcher_logger

__all__ = [
    "DEFAULT_MAIN_WAIT_TIMEOUT",
    "DEFAULT_MONITOR_DELAY",
    "TARGET_FUNCTION",
    "TARGET_MODULE",
    "BrowserRequest",
    "apply_from_config",
    "is_sd_trainer_browser_order_patch_registered",
    "is_sd_trainer_next_application",
    "order_browser_requests",
    "patch_sd_trainer_browser_order",
    "replay_browser_requests",
]

TARGET_MODULE = "mikazuki.app.application"
TARGET_FUNCTION = "app_startup"
DEFAULT_MONITOR_DELAY = 1.0
DEFAULT_MAIN_WAIT_TIMEOUT = 30.0
_PATCH_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_sd_trainer_browser_order_patch"
_WRAPPER_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_sd_trainer_browser_order_wrapper"
# 只有 SD Trainer Next 分支同时具备这些成员; 原版 lora-scripts 只有一个主界面, 不需要调整顺序
_NEXT_FINGERPRINT_ATTRS = ("webbrowser", "_resolve_browser", "train_monitor_browser_url")
_WILDCARD_HOSTS = {"0.0.0.0", "::", ""}

logger = get_hotpatcher_logger(__name__)

_monitor_delay = DEFAULT_MONITOR_DELAY


class BrowserRequest:
    """一次被延后的浏览器打开请求。

    Attributes:
        url (str):
            要打开的网址。
        opener (Callable[[], Callable[..., Any]]):
            回放时用来取得真实打开函数的回调。
        args (tuple[Any, ...]):
            原调用的位置参数。
        kwargs (dict[str, Any]):
            原调用的关键字参数。
    """

    def __init__(
        self,
        url: str,
        opener: Callable[[], Callable[..., Any]],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """初始化浏览器打开请求。

        Args:
            url (str):
                要打开的网址。
            opener (Callable[[], Callable[..., Any]]):
                回放时用来取得真实打开函数的回调。
            args (tuple[Any, ...]):
                原调用的位置参数。
            kwargs (dict[str, Any] | None):
                原调用的关键字参数。
        """

        self.url = url
        self.opener = opener
        self.args = args
        self.kwargs = kwargs or {}

    def open(self) -> Any:
        """用真实打开函数执行这次请求。

        Returns:
            Any:
                真实打开函数的返回值。
        """

        return self.opener()(self.url, *self.args, **self.kwargs)


class _RecordingController:
    """记录 ``webbrowser.get()`` 返回的控制器上的打开请求。"""

    def __init__(self, controller: Any, requests: list[BrowserRequest]) -> None:
        self._controller = controller
        self._requests = requests

    def open(self, url: str, *args: Any, **kwargs: Any) -> bool:
        self._requests.append(BrowserRequest(url, lambda: self._controller.open, args, kwargs))
        return True

    def __getattr__(self, name: str) -> Any:
        return getattr(self._controller, name)


class _RecordingWebbrowser:
    """在 ``app_startup`` 执行期间替代目标模块里的 ``webbrowser`` 全局变量。"""

    def __init__(self, real: Any, requests: list[BrowserRequest]) -> None:
        self._real = real
        self._requests = requests

    def open(self, url: str, *args: Any, **kwargs: Any) -> bool:
        # 回放时再取 open, 这样 runtime.browser 等后装的包装器仍然生效
        self._requests.append(BrowserRequest(url, lambda: self._real.open, args, kwargs))
        return True

    def get(self, *args: Any, **kwargs: Any) -> _RecordingController:
        return _RecordingController(self._real.get(*args, **kwargs), self._requests)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def is_sd_trainer_next_application(module: ModuleType) -> bool:
    """判断目标模块是否来自带训练监控界面的 SD Trainer Next 分支。

    Args:
        module (ModuleType):
            已导入的 ``mikazuki.app.application`` 模块。

    Returns:
        bool:
            模块具备 Next 分支的浏览器打开结构时返回 True。
    """

    return all(hasattr(module, name) for name in _NEXT_FINGERPRINT_ATTRS) and inspect.iscoroutinefunction(getattr(module, TARGET_FUNCTION, None))


def order_browser_requests(requests: list[BrowserRequest], main_port: int | None = None) -> list[BrowserRequest]:
    """把主界面的打开请求排到最前面, 其余请求保持原有顺序。

    Args:
        requests (list[BrowserRequest]):
            按调用顺序记录的打开请求。
        main_port (int | None):
            主界面端口。为 None 时读取 ``MIKAZUKI_PORT``; 无法识别时把第一个请求视为主界面。

    Returns:
        list[BrowserRequest]:
            主界面在前的打开请求列表。
    """

    if main_port is None:
        main_port = _env_port("MIKAZUKI_PORT")
    if main_port is None:
        return list(requests)
    main = [request for request in requests if _url_port(request.url) == main_port]
    if not main:
        return list(requests)
    return [*main, *(request for request in requests if _url_port(request.url) != main_port)]


def replay_browser_requests(
    requests: list[BrowserRequest],
    *,
    monitor_delay: float = DEFAULT_MONITOR_DELAY,
    main_wait_timeout: float = DEFAULT_MAIN_WAIT_TIMEOUT,
    main_port: int | None = None,
) -> None:
    """按“主界面优先”的顺序打开被延后的网址。

    先等待主界面端口可以连接再打开主界面, 间隔 ``monitor_delay`` 秒后再打开其余网址。

    Args:
        requests (list[BrowserRequest]):
            按调用顺序记录的打开请求。
        monitor_delay (float):
            打开主界面后, 打开其余网址前等待的秒数。
        main_wait_timeout (float):
            等待主界面端口就绪的最长秒数。超时后仍会打开主界面。
        main_port (int | None):
            主界面端口。为 None 时读取 ``MIKAZUKI_PORT``。
    """

    ordered = order_browser_requests(requests, main_port)
    if not ordered:
        return

    first, rest = ordered[0], ordered[1:]
    endpoint = _url_endpoint(first.url)
    if endpoint is not None and not _wait_for_tcp_port(*endpoint, timeout=main_wait_timeout):
        logger.warning("SD Trainer 主界面 %s 在 %s 秒内未就绪, 仍尝试打开浏览器", first.url, main_wait_timeout)
    _open_request(first)

    if rest and monitor_delay > 0:
        time.sleep(monitor_delay)
    for request in rest:
        _open_request(request)


def patch_sd_trainer_browser_order(monitor_delay: float = DEFAULT_MONITOR_DELAY) -> None:
    """注册 SD Trainer Next 浏览器打开顺序补丁, 并处理已导入模块。

    Args:
        monitor_delay (float):
            打开主界面后, 打开训练监控界面前等待的秒数。
    """

    global _monitor_delay
    _monitor_delay = max(0.0, float(monitor_delay))

    install_import_hook()
    _register_app_startup_patch()

    module = sys.modules.get(TARGET_MODULE)
    if module is not None and TARGET_FUNCTION in module.__dict__:
        replacement = _hook_app_startup(module.__dict__[TARGET_FUNCTION], module)
        if replacement is not None:
            module.__dict__[TARGET_FUNCTION] = replacement


def is_sd_trainer_browser_order_patch_registered() -> bool:
    """检查 SD Trainer 浏览器打开顺序补丁是否已经注册。

    Returns:
        bool:
            补丁已经注册时返回 True。
    """

    monkey = monkey_zoo[TARGET_MODULE]
    if monkey is None:
        return False
    return any(getattr(hooker, _PATCH_MARKER_ATTR, False) for _name, hooker, _priority, _add in monkey.function_patches)


def apply_from_config(config: dict[str, Any] | None) -> None:
    """根据扩展配置注册 SD Trainer 浏览器打开顺序补丁。

    Args:
        config (dict[str, Any] | None):
            扩展配置。
    """

    if config and config.get("enabled"):
        patch_sd_trainer_browser_order(_coerce_delay(config.get("monitor_delay", DEFAULT_MONITOR_DELAY)))


def _register_app_startup_patch() -> None:
    with monkey_zoo(TARGET_MODULE) as monkey:
        if any(getattr(hooker, _PATCH_MARKER_ATTR, False) for _name, hooker, _priority, _add in monkey.function_patches):
            return

        def patch_app_startup(func: Any, module: ModuleType) -> Any:
            return _hook_app_startup(func, module)

        setattr(patch_app_startup, _PATCH_MARKER_ATTR, True)
        monkey.patch_function(TARGET_FUNCTION, patch_app_startup)


def _hook_app_startup(func: Any, module: ModuleType) -> Any:
    if getattr(func, _WRAPPER_MARKER_ATTR, False) or not is_sd_trainer_next_application(module):
        return None

    @functools.wraps(func)
    async def app_startup(*args: Any, **kwargs: Any) -> Any:
        real = module.__dict__.get("webbrowser")
        if real is None or isinstance(real, _RecordingWebbrowser):
            return await func(*args, **kwargs)

        requests: list[BrowserRequest] = []
        module.__dict__["webbrowser"] = _RecordingWebbrowser(real, requests)
        try:
            return await func(*args, **kwargs)
        finally:
            module.__dict__["webbrowser"] = real
            if requests:
                _start_replay(requests)

    setattr(app_startup, _WRAPPER_MARKER_ATTR, True)
    return app_startup


def _start_replay(requests: list[BrowserRequest]) -> threading.Thread:
    # 主界面端口要等 app_startup 返回后才会被 uvicorn 监听, 所以必须在后台线程里等待
    thread = threading.Thread(
        target=replay_browser_requests,
        args=(requests,),
        kwargs={"monitor_delay": _monitor_delay},
        name="sd_webui_all_in_one_hotpatcher-sd-trainer-browser",
        daemon=True,
    )
    thread.start()
    return thread


def _open_request(request: BrowserRequest) -> None:
    try:
        request.open()
    except Exception as exc:
        logger.warning("打开浏览器失败: %s (%s: %s)", request.url, type(exc).__name__, exc)


def _wait_for_tcp_port(host: str, port: int, timeout: float, interval: float = 0.2) -> bool:
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval)


def _url_endpoint(url: str) -> tuple[str, int] | None:
    port = _url_port(url)
    if port is None:
        return None
    host = urlsplit(url).hostname or ""
    return ("127.0.0.1" if host in _WILDCARD_HOSTS else host, port)


def _url_port(url: str) -> int | None:
    try:
        return urlsplit(url).port
    except ValueError:
        return None


def _env_port(name: str) -> int | None:
    try:
        return int(os.environ.get(name, ""))
    except ValueError:
        return None


def _coerce_delay(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return DEFAULT_MONITOR_DELAY
