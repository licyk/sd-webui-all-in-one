"""Host-controlled standard-library browser interception."""

from __future__ import annotations

import functools
import sys
import warnings
from types import ModuleType
from typing import Any, Literal, cast

from ..hook import install_import_hook, register_hook
from ..state import HotpatcherState, get_default_state
from .client import RuntimeClient

BrowserMode = Literal["host", "suppress", "passthrough"]
_BROWSER_MODES = {"host", "suppress", "passthrough"}


class ManagedBrowser:
    """Send browser requests to the runtime host."""

    def __init__(self, client: RuntimeClient):
        self.client = client

    def open(self, url: str) -> None:
        self.client.event("browser.open", {"url": url})


def patch_webbrowser(
    client: RuntimeClient | ManagedBrowser | None,
    *,
    mode: BrowserMode = "host",
    state: HotpatcherState | None = None,
) -> None:
    """Configure interception of :mod:`webbrowser` module-level opens.

    ``host`` and ``suppress`` install one idempotent wrapper. ``host`` emits a
    single event when a client is available; both modes always report success
    without opening an operating-system browser. ``passthrough`` leaves an
    unpatched process untouched and makes an existing wrapper delegate to the
    original function.
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
                    browser = (
                        current_client
                        if isinstance(current_client, ManagedBrowser)
                        else ManagedBrowser(cast(RuntimeClient, current_client))
                    )
                    try:
                        browser.open(url)
                    except Exception as exc:
                        active_state.browser_diagnostics.append(
                            f"browser host event failed; opening remained suppressed: {exc}"
                        )
                        del active_state.browser_diagnostics[:-100]
            return True

        wrapper.__sd_webui_aio_browser_state__ = active_state  # type: ignore[attr-defined]
        return wrapper

    if not active_state.browser_patch_registered:
        register_hook("webbrowser", "open", hook_open, state=active_state)
        active_state.browser_patch_registered = True

    module = sys.modules.get("webbrowser")
    if module is not None and hasattr(module, "open"):
        module.open = hook_open(module.open, module)  # type: ignore[attr-defined]


def is_webbrowser_patch_registered(*, state: HotpatcherState | None = None) -> bool:
    """Return whether this process has installed the browser wrapper."""

    return (state or get_default_state()).browser_patch_registered


def is_webbrowser_patch_active(*, state: HotpatcherState | None = None) -> bool:
    """Return whether the installed wrapper currently suppresses browser opens."""

    active_state = state or get_default_state()
    return active_state.browser_patch_registered and active_state.browser_patch_mode in {
        "host",
        "suppress",
    }
