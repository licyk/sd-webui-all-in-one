"""SD Trainer 浏览器打开请求的排序与回放"""

from __future__ import annotations

import os
import socket
import time
from urllib.parse import urlsplit

from sd_webui_all_in_one_hotpatcher.logger import get_hotpatcher_logger

from .recording import BrowserRequest

DEFAULT_MONITOR_DELAY = 1.0
DEFAULT_MAIN_WAIT_TIMEOUT = 30.0
_WILDCARD_HOSTS = {"0.0.0.0", "::", ""}
logger = get_hotpatcher_logger(__name__)


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
