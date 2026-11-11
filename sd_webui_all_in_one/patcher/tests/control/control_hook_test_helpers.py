"""import hook 控制平面测试的共享工具。"""

import importlib
import sys
import textwrap
from contextlib import contextmanager

from sd_webui_all_in_one_hotpatcher import get_default_state, monkey_zoo, uninstall_import_hook

MODULE_PREFIX = "hpc_"


@contextmanager
def clean_hook_state():
    """在测试前后重置 import hook、补丁注册表、句柄注册表、严格模式和测试模块。

    Yields:
        None: 测试执行期间。
    """

    state = get_default_state()
    strict_mode = state.strict_mode
    uninstall_import_hook()
    monkey_zoo.clear()
    state.strict_mode = False
    before_path = list(sys.path)
    before_handles = dict(state.patch_handles)
    before_sets = dict(state.patch_sets)
    try:
        yield
    finally:
        uninstall_import_hook()
        monkey_zoo.clear()
        state.strict_mode = strict_mode
        sys.path[:] = before_path
        state.patch_handles.clear()
        state.patch_handles.update(before_handles)
        state.patch_sets.clear()
        state.patch_sets.update(before_sets)
        for name in list(sys.modules):
            if name.startswith(MODULE_PREFIX):
                sys.modules.pop(name, None)
        importlib.invalidate_caches()


def write_module(directory, name, source):
    """写入测试模块并刷新导入缓存。

    Args:
        directory: 模块目录。
        name: 模块名。
        source: 模块源码, 会自动去除缩进。

    Returns:
        Path: 模块文件路径。
    """

    path = directory / f"{name}.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    importlib.invalidate_caches()
    return path


def forget_module(name):
    """从 ``sys.modules`` 移除模块, 以便重新导入。

    Args:
        name: 模块名。
    """

    sys.modules.pop(name, None)
    importlib.invalidate_caches()
