"""Implementation grouped from the former ``version_gui.py`` module."""

from __future__ import annotations

import queue
import threading
import traceback
import tkinter as tk
from dataclasses import dataclass
from tkinter import (
    messagebox,
)
from typing import (
    Any,
    Callable,
    Generic,
    TYPE_CHECKING,
)

from .theme import T


if TYPE_CHECKING:

    class GuiActionsMixinContext(tk.Misc):
        """Static context for action mixins assembled by an application."""

        def __getattr__(self, name: str) -> Any:
            raise AttributeError(name)

else:

    class GuiActionsMixinContext:
        """Runtime-neutral base shared by GUI action mixins."""

        def __getattr__(self, name: str) -> Any:
            raise AttributeError(name)


@dataclass(slots=True)
class BackgroundResult(Generic[T]):
    """
    后台任务结果

    Attributes:
        callback (Callable[[T], object] | None):
            任务成功回调
        error_callback (Callable[[BaseException], object] | None):
            任务失败回调
        value (T | None):
            任务返回值
        error (BaseException | None):
            任务异常
        traceback_text (str | None):
            异常追踪信息
        message (str):
            任务状态文本
    """

    callback: Callable[[T], object] | None
    error_callback: Callable[[BaseException], object] | None
    value: T | None = None
    error: BaseException | None = None
    traceback_text: str | None = None
    message: str = ""


class BackgroundTaskMixin:
    """
    Tkinter 后台任务辅助类

    将耗时任务放入后台线程执行, 并通过队列把结果投递回 Tk 主线程,
    避免 Git、网络和文件操作阻塞界面。
    """

    def __init__(
        self,
    ) -> None:
        self._task_queue: queue.Queue[BackgroundResult[Any]] = queue.Queue()
        self._busy_count = 0

    def _install_task_poller(
        self,
        root: tk.Misc,
    ) -> None:
        """
        安装后台任务轮询器

        Args:
            root (tk.Misc):
                用于调度 after 回调的 Tk 组件
        """
        root.after(100, self._poll_tasks)

    def run_background(
        self,
        message: str,
        func: Callable[[], T],
        callback: Callable[[T], object] | None = None,
        error_callback: Callable[[BaseException], object] | None = None,
    ) -> None:
        """
        在线程中执行任务并把结果投递回主线程

        Args:
            message (str):
                任务状态文本
            func (Callable[[], T]):
                后台执行函数
            callback (Callable[[T], object] | None):
                成功回调
            error_callback (Callable[[BaseException], object] | None):
                失败回调
        """
        self._busy_count += 1
        self.set_status(message)
        self.set_busy_state(True)

        def _target() -> None:
            try:
                value = func()
                self._task_queue.put(BackgroundResult(callback=callback, error_callback=error_callback, value=value, message=message))
            except BaseException as e:  # pylint: disable=broad-exception-caught
                self._task_queue.put(
                    BackgroundResult(
                        callback=callback,
                        error_callback=error_callback,
                        error=e,
                        traceback_text=traceback.format_exc(),
                        message=message,
                    )
                )

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

    def run_two_phase_refresh(
        self,
        message: str,
        fast_func: Callable[[], T],
        full_func: Callable[[], T],
        callback: Callable[[T], object] | None = None,
    ) -> None:
        """
        两段式刷新 Git 列表

        先执行 fast_func(应使用 fetch=False, 仅读取本地已知引用) 快速渲染列表,
        再在后台执行 full_func(应使用 fetch=True, 拉取远程引用), 完成后再次调用
        callback 刷新列表, 避免提交或分支列表同步阻塞在网络拉取上。

        Args:
            message (str):
                第一阶段任务状态文本
            fast_func (Callable[[], T]):
                快速阶段执行函数, 应使用 fetch=False
            full_func (Callable[[], T]):
                后台刷新阶段执行函数, 应使用 fetch=True
            callback (Callable[[T], object] | None):
                成功回调, 快速阶段与后台刷新阶段都会调用
        """

        def _fast_done(value: T) -> None:
            if callback is not None:
                callback(value)
            self.run_background(
                "联网刷新列表中...",
                full_func,
                callback,
                error_callback=lambda exc: self.set_status(f"联网刷新失败, 保留当前列表: {exc}"),
            )

        self.run_background(message, fast_func, _fast_done)

    def _poll_tasks(
        self,
    ) -> None:
        while True:
            try:
                result = self._task_queue.get_nowait()
            except queue.Empty:
                break
            self._busy_count = max(0, self._busy_count - 1)
            if result.error is not None:
                if result.error_callback is not None:
                    result.error_callback(result.error)
                else:
                    messagebox.showerror("操作失败", f"{result.error}\n\n{result.traceback_text or ''}".strip())
            elif result.callback is not None:
                result.callback(result.value)
            if self._busy_count == 0:
                self.set_status("就绪")
                self.set_busy_state(False)
        self.after(100, self._poll_tasks)  # ty: ignore[unresolved-attribute]

    def set_status(
        self,
        message: str,
    ) -> None:
        """
        设置状态栏文本

        Args:
            message (str):
                状态文本

        Raises:
            NotImplementedError:
                子类未实现状态栏更新逻辑时抛出。
        """
        raise NotImplementedError

    def set_busy_state(
        self,
        busy: bool,
    ) -> None:
        """
        更新忙碌状态

        Args:
            busy (bool):
                是否处于忙碌状态
        """
