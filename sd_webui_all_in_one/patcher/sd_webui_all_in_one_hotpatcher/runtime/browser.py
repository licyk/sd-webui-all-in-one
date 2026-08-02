"""由宿主控制的标准库浏览器拦截。"""

from __future__ import annotations

import functools
import sys
import warnings
from types import ModuleType
from typing import Any, Literal

from ..hook import install_import_hook, register_hook
from ..state import HotpatcherState, get_default_state
from .interfaces import RuntimeEventSink, emit_runtime_event

BrowserMode = Literal["host", "suppress", "passthrough"]
_BROWSER_MODES = {"host", "suppress", "passthrough"}


class ManagedBrowser:
    """向运行时主机发送浏览器请求。"""

    def __init__(self, client: RuntimeEventSink | Any):
        self.client = client

    def open(self, url: str) -> None:
        """请求运行时主机打开网址。

        Args:
            url (str): 要打开的网址。
        """
        emit_runtime_event(self.client, "browser.open", {"url": url})


def patch_webbrowser(
    client: RuntimeEventSink | ManagedBrowser | Any | None,
    *,
    mode: BrowserMode = "host",
    state: HotpatcherState | None = None,
) -> None:
    """配置对 :mod:`webbrowser` 模块级打开函数的拦截。

    ``host`` 和 ``suppress`` 会安装一个幂等包装器；``host`` 在客户端可用时
    发送一次事件，两种模式都会在不打开系统浏览器的情况下报告成功。
    ``passthrough`` 不修改尚未打补丁的进程，并让已有包装器调用原函数。

    Args:
        client (RuntimeEventSink | ManagedBrowser | Any | None): 运行时事件客户端。
        mode (BrowserMode): 浏览器打开处理模式。
        state (HotpatcherState | None): 可选热补丁状态。

    Raises:
        ValueError: 浏览器处理模式无效时抛出。
    """

    if mode not in _BROWSER_MODES:
        raise ValueError(f"unsupported browser mode: {mode}")
    active_state = state or get_default_state()
    active_state.browser_patch_mode = mode
    active_state.browser_runtime_client = client

    if mode == "passthrough" and not active_state.browser_patch_registered:
        return
    if mode == "host" and client is None:
        diagnostic = "browser host mode has no runtime client; browser opening remains suppressed"
        active_state.browser_diagnostics.append(diagnostic)
        del active_state.browser_diagnostics[:-100]
        warnings.warn(diagnostic, RuntimeWarning, stacklevel=2)

    install_import_hook(state=active_state)

    def hook_open(func: Any, module: ModuleType):
        del module
        if getattr(func, "__sd_webui_aio_browser_state__", None) is active_state:
            return func

        @functools.wraps(func)
        def wrapper(url: str, *args: Any, **kwargs: Any):
            current_mode = active_state.browser_patch_mode
            if current_mode == "passthrough":
                return func(url, *args, **kwargs)
            if current_mode == "host":
                current_client = active_state.browser_runtime_client
                if current_client is not None:
                    browser = current_client if isinstance(current_client, ManagedBrowser) else ManagedBrowser(current_client)
                    try:
                        browser.open(url)
                    except Exception as exc:
                        active_state.browser_diagnostics.append(f"browser host event failed; opening remained suppressed: {exc}")
                        del active_state.browser_diagnostics[:-100]
            return True

        wrapper.__sd_webui_aio_browser_state__ = active_state
        return wrapper

    if not active_state.browser_patch_registered:
        register_hook("webbrowser", "open", hook_open, state=active_state)
        active_state.browser_patch_registered = True

    module = sys.modules.get("webbrowser")
    if module is not None and hasattr(module, "open"):
        module.open = hook_open(module.open, module)


def is_webbrowser_patch_registered(*, state: HotpatcherState | None = None) -> bool:
    """判断当前进程是否已安装浏览器包装器。

    Args:
        state (HotpatcherState | None): 可选热补丁状态。

    Returns:
        bool: 已安装浏览器包装器时返回 ``True``。
    """

    return (state or get_default_state()).browser_patch_registered


def is_webbrowser_patch_active(*, state: HotpatcherState | None = None) -> bool:
    """判断已安装的包装器当前是否抑制浏览器打开。

    Args:
        state (HotpatcherState | None): 可选热补丁状态。

    Returns:
        bool: 当前正在抑制浏览器打开时返回 ``True``。
    """

    active_state = state or get_default_state()
    return active_state.browser_patch_registered and active_state.browser_patch_mode in {
        "host",
        "suppress",
    }
