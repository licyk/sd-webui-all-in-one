"""控制平面并发测试: 控制线程加载/卸载补丁集与主线程导入并行、并发导入与 explain、同一功能的并发启用/禁用。"""

import importlib
import sys
import textwrap
import threading
import time
import types
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher import install_import_hook, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.control import DYNAMIC_PACKAGE, unload_patch
from sd_webui_all_in_one_hotpatcher.control.commands import CommandError
from sd_webui_all_in_one_hotpatcher.control.controller import get_controller
from sd_webui_all_in_one_hotpatcher.control.features import FeatureSpec, get_feature_registry, get_feature_set
from sd_webui_all_in_one_hotpatcher.hook import MonkeySourceFileLoader
from sd_webui_all_in_one_hotpatcher.services import clear_current_config
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

MODULE_PREFIX = "hpccon_"
JOIN_TIMEOUT = 60

GREET_SOURCE = """
def greet(name):
    return f"hello {name}"
"""

PATCH_SOURCE = """
def _upper(func, module):
    def wrapper(name):
        return func(name).upper()

    return wrapper


def setup(ctx):
    with ctx.module("{module}") as monkey:
        monkey.patch_function("greet", _upper)
"""


@pytest.fixture
def state(tmp_path):
    isolated = HotpatcherState()
    before_path = list(sys.path)
    before_meta_path = list(sys.meta_path)
    sys.path.insert(0, str(tmp_path))
    install_import_hook(state=isolated)
    yield isolated
    for name in list(isolated.loaded_patches):
        unload_patch(name, state=isolated)
    uninstall_import_hook(state=isolated)
    clear_current_config(state=isolated)
    sys.path[:] = before_path
    sys.meta_path[:] = before_meta_path
    for name in list(sys.modules):
        if name.startswith(MODULE_PREFIX) or name.startswith(f"{DYNAMIC_PACKAGE}."):
            del sys.modules[name]
    importlib.invalidate_caches()


def _write(path, source):
    path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
    importlib.invalidate_caches()
    return path


def _join_all(threads):
    deadline = time.monotonic() + JOIN_TIMEOUT
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    stuck = [thread.name for thread in threads if thread.is_alive()]
    assert stuck == [], f"threads did not finish (possible deadlock): {stuck}"


def test_control_thread_loads_and_unloads_while_main_thread_imports(state, tmp_path):
    module_name = "hpccon_loop_target"
    _write(tmp_path / f"{module_name}.py", GREET_SOURCE)
    patch_file = _write(tmp_path / "hpccon_loop_patch.py", PATCH_SOURCE.format(module=module_name))
    controller = get_controller(state)
    stop = threading.Event()
    errors: list[BaseException] = []
    cycles = []

    def control_loop():
        try:
            for _ in range(25):
                controller.load_patch(str(patch_file), name="hpccon-loop")
                controller.unload_patch("hpccon-loop")
                cycles.append(1)
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)
        finally:
            stop.set()

    control = threading.Thread(target=control_loop, name="hpccon-control", daemon=True)
    control.start()
    results = set()
    imports = 0
    deadline = time.monotonic() + JOIN_TIMEOUT
    while (not stop.is_set() or imports < 5) and time.monotonic() < deadline:
        sys.modules.pop(module_name, None)
        module = importlib.import_module(module_name)
        results.add(module.greet("ada"))
        imports += 1
    _join_all([control])

    assert errors == []
    assert len(cycles) == 25
    assert results <= {"hello ada", "HELLO ADA"}
    # 一致的最终状态: 没有残留的补丁、补丁集、句柄或进行中的操作; 重新导入得到未打补丁的模块。
    assert state.loaded_patches == {}
    assert state.loading_patches == set()
    assert all(patch_set.name != "hpccon-loop" for patch_set in state.patch_sets.values())
    assert all(handle.target.split(":")[0] != module_name for handle in state.patch_handles.values())
    zoo = state.monkey_zoo
    assert zoo is not None
    monkey = zoo.monkeys.get(module_name)
    assert monkey is None or monkey.function_patches == []
    sys.modules.pop(module_name, None)
    assert importlib.import_module(module_name).greet("ada") == "hello ada"


def test_concurrent_imports_with_explain_always_get_wrapped_specs(state, tmp_path):
    module_name = "hpccon_parallel_target"
    _write(tmp_path / f"{module_name}.py", GREET_SOURCE)
    patch_file = _write(tmp_path / "hpccon_parallel_patch.py", PATCH_SOURCE.format(module=module_name))
    controller = get_controller(state)
    controller.load_patch(str(patch_file), name="hpccon-parallel")

    for _ in range(15):
        sys.modules.pop(module_name, None)
        barrier = threading.Barrier(3)
        observed: list[tuple[Any, str]] = []
        explained: list[dict[str, Any]] = []
        errors: list[BaseException] = []

        def do_import():
            try:
                barrier.wait(10)
                module = importlib.import_module(module_name)
                spec = module.__spec__
                observed.append((spec.loader if spec is not None else None, module.greet("ada")))
            except BaseException as exc:  # pragma: no cover - reported below
                errors.append(exc)

        def do_explain():
            try:
                barrier.wait(10)
                for _ in range(5):
                    explained.append(controller.inspect.explain(module_name))
            except BaseException as exc:  # pragma: no cover - reported below
                errors.append(exc)

        threads = [threading.Thread(target=do_import, daemon=True), threading.Thread(target=do_import, daemon=True), threading.Thread(target=do_explain, daemon=True)]
        for thread in threads:
            thread.start()
        _join_all(threads)

        assert errors == []
        assert len(observed) == 2
        for loader, greeting in observed:
            assert isinstance(loader, MonkeySourceFileLoader)
            assert greeting == "HELLO ADA"
        assert len(explained) == 5
        assert all(item["registered"] is True for item in explained)


def _register_blocking_feature(state, gate):
    module: Any = types.ModuleType("hpccon_feature_target")
    module.VALUE = "original"
    sys.modules["hpccon_feature_target"] = module

    def apply(ctx, section):
        gate(section)
        ctx.patch_set.context.set_attr(module, "VALUE", section["value"])

    get_feature_registry(state).register(FeatureSpec(key="thirdparty.concurrent", title="C", description="x", defaults={"enabled": False, "value": "patched"}, apply=apply))
    return module


def test_concurrent_disable_during_enable_on_same_key_is_busy(state):
    entered = threading.Event()
    release = threading.Event()

    def gate(section):
        if section.get("value") == "slow":
            entered.set()
            assert release.wait(JOIN_TIMEOUT)

    module = _register_blocking_feature(state, gate)
    controller = get_controller(state)
    outcome: dict[str, Any] = {}

    def slow_enable():
        try:
            outcome["enable"] = controller.features.enable("thirdparty.concurrent", {"value": "slow"})
        except BaseException as exc:  # pragma: no cover - reported below
            outcome["enable"] = exc

    worker = threading.Thread(target=slow_enable, daemon=True)
    worker.start()
    assert entered.wait(JOIN_TIMEOUT)
    try:
        with pytest.raises(CommandError) as exc_info:
            controller.features.disable("thirdparty.concurrent")
        envelope = controller.call("hotpatch.features.update", {"key": "thirdparty.concurrent", "config": {"value": "other"}})
    finally:
        release.set()
    _join_all([worker])

    assert exc_info.value.code == "busy"
    assert envelope["ok"] is False and envelope["error"]["code"] == "busy"
    assert isinstance(outcome["enable"], dict) and outcome["enable"]["status"] == "applied"
    assert module.VALUE == "slow"
    # 锁按功能键区分, 其他键不受影响; 未知功能键不创建锁。
    with controller.operation_lock("feature:thirdparty.other", timeout=0):
        pass
    assert controller.call("hotpatch.features.disable", {"key": "thirdparty.unknown"})["error"]["code"] == "not_found"
    assert "feature:thirdparty.unknown" not in controller._operation_locks

    assert controller.features.disable("thirdparty.concurrent")["status"] == "reverted"
    assert module.VALUE == "original"
    assert get_feature_set("thirdparty.concurrent", state=state) is None


def test_hammering_enable_and_disable_keeps_feature_state_consistent(state):
    module = _register_blocking_feature(state, lambda section: time.sleep(0.001))
    controller = get_controller(state)
    codes: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(4)

    def hammer(index):
        barrier.wait(10)
        for step in range(20):
            if (index + step) % 2:
                envelope = controller.call("hotpatch.features.enable", {"key": "thirdparty.concurrent", "config": {"value": f"v{index}"}})
            else:
                envelope = controller.call("hotpatch.features.disable", {"key": "thirdparty.concurrent"})
            with lock:
                codes.append("ok" if envelope["ok"] else envelope["error"]["code"])

    threads = [threading.Thread(target=hammer, args=(index,), daemon=True) for index in range(4)]
    for thread in threads:
        thread.start()
    _join_all(threads)

    assert set(codes) <= {"ok", "busy"}
    assert "ok" in codes
    feature_sets = [patch_set for patch_set in state.patch_sets.values() if patch_set.name == "feature:thirdparty.concurrent"]
    assert len(feature_sets) <= 1
    assert all(not patch_set.closed for patch_set in feature_sets)
    controller.features.disable("thirdparty.concurrent")
    assert module.VALUE == "original"
    assert get_feature_set("thirdparty.concurrent", state=state) is None
    assert [handle for handle in state.patch_handles.values() if handle.target.startswith("hpccon_feature_target")] == []
