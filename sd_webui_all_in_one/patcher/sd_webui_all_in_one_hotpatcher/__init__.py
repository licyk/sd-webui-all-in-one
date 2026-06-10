"""可复用的 import 阶段热补丁工具"""

from .hook import (
    Monkey,
    MonkeyZoo,
    install_import_hook,
    is_import_hook_installed,
    monkey_zoo,
    register_customize_hook,
    register_hook,
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

__all__ = [
    "CodeWrapper",
    "HotpatcherState",
    "Monkey",
    "MonkeyZoo",
    "TupleWrapper",
    "configure_stack_shadower_from_env",
    "get_default_state",
    "get_hotpatcher_logger",
    "install_import_hook",
    "install_stack_shadower",
    "is_import_hook_installed",
    "is_stack_shadower_installed",
    "monkey_zoo",
    "register_customize_hook",
    "register_hook",
    "uninstall_import_hook",
    "uninstall_stack_shadower",
]
