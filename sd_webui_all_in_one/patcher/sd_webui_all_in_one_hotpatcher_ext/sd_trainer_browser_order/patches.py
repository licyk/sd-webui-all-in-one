"""SD Trainer Next 浏览器打开顺序补丁注册"""

from __future__ import annotations

import functools
import inspect
import sys
import threading
from types import ModuleType
from typing import Any

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

from .recording import BrowserRequest, _RecordingWebbrowser
from .replay import DEFAULT_MONITOR_DELAY, replay_browser_requests

TARGET_MODULE = "mikazuki.app.application"
TARGET_FUNCTION = "app_startup"
_PATCH_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_sd_trainer_browser_order_patch"
_WRAPPER_MARKER_ATTR = "_sd_webui_all_in_one_hotpatcher_sd_trainer_browser_order_wrapper"
# 只有 SD Trainer Next 分支同时具备这些成员; 原版 lora-scripts 只有一个主界面, 不需要调整顺序
_NEXT_FINGERPRINT_ATTRS = ("webbrowser", "_resolve_browser", "train_monitor_browser_url")
_monitor_delay = DEFAULT_MONITOR_DELAY


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
