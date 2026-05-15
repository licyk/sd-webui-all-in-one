"""宿主管理浏览器工具"""

from __future__ import annotations

import functools
import sys
from types import ModuleType
from typing import Any

from ..hook import install_import_hook, monkey_zoo
from .client import RuntimeClient


class ManagedBrowser:
    """
    通过宿主打开 URL 的浏览器代理

    Attributes:
        client (RuntimeClient):
            发送 ``browser.open`` 事件的运行时客户端
    """

    def __init__(self, client: RuntimeClient):
        self.client = client

    def open(self, url: str) -> None:
        """
        请求宿主打开 URL

        Args:
            url (str):
                需要打开的 URL
        """

        self.client.event("browser.open", {"url": url})


def patch_webbrowser(client: RuntimeClient | ManagedBrowser) -> None:
    """
    补丁标准库 ``webbrowser.open``

    将后续 ``webbrowser.open`` 调用转成 ``browser.open`` 运行时事件。

    Args:
        client (RuntimeClient | ManagedBrowser):
            运行时客户端或已创建的浏览器代理
    """

    browser = client if isinstance(client, ManagedBrowser) else ManagedBrowser(client)
    install_import_hook()

    def hook_open(func: Any, module: ModuleType):
        @functools.wraps(func)
        def wrapper(url: str, *args: Any, **kwargs: Any):
            browser.open(url)
            return True

        return wrapper

    with monkey_zoo("webbrowser") as monkey:
        monkey.patch_function("open", hook_open)

    module = sys.modules.get("webbrowser")
    if module is not None and hasattr(module, "open"):
        module.open = hook_open(module.open, module)  # ty: ignore[unresolved-attribute]
