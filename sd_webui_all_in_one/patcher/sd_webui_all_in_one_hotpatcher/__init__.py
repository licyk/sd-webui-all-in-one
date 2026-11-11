"""可复用的 import 阶段热补丁工具

``hotpatch`` (默认状态的 ``HotpatchController``) 通过模块级 ``__getattr__`` 惰性提供: 导入本包或安装 import hook
不会加载 ``control`` 子包, 首次访问 ``hotpatch`` 时才导入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .hook import (
    Monkey,
    MonkeyZoo,
    PostExecLoader,
    install_import_hook,
    is_import_hook_installed,
    is_strict_mode,
    monkey_zoo,
    register_customize_hook,
    register_hook,
    set_strict_mode,
    uninstall_import_hook,
)
from .logger import get_hotpatcher_logger
from .mutable import CodeWrapper, TupleWrapper
from .state import HotpatcherState, get_default_state
from .stack_shadow import (
    configure_stack_shadower_from_env,
    install_stack_shadower,
    is_stack_shadower_installed,
    uninstall_stack_shadower,
)

if TYPE_CHECKING:
    from .control.controller import HotpatchController

    hotpatch: HotpatchController

__all__ = [
    "CodeWrapper",
    "HotpatcherState",
    "Monkey",
    "MonkeyZoo",
    "PostExecLoader",
    "TupleWrapper",
    "configure_stack_shadower_from_env",
    "get_default_state",
    "get_hotpatcher_logger",
    "hotpatch",
    "install_import_hook",
    "install_stack_shadower",
    "is_import_hook_installed",
    "is_stack_shadower_installed",
    "is_strict_mode",
    "monkey_zoo",
    "register_customize_hook",
    "register_hook",
    "set_strict_mode",
    "uninstall_import_hook",
    "uninstall_stack_shadower",
]


def __getattr__(name: str) -> Any:
    """
    惰性提供 ``hotpatch`` 控制门面。

    Args:
        name (str):
            属性名。

    Returns:
        Any:
            ``name`` 为 ``hotpatch`` 时返回默认状态的控制器。

    Raises:
        AttributeError:
            其他未知属性。
    """

    if name == "hotpatch":
        from .control.controller import get_controller

        return get_controller()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
