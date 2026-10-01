"""SD Trainer 浏览器打开请求的记录"""

from __future__ import annotations

from typing import Any, Callable


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
