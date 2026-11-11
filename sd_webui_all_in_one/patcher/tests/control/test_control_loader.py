"""运行时补丁加载测试: 加载/卸载/重新加载回滚/更新、文件监视器、rebind 跳过、远程加载门禁与配置声明的补丁集。"""

import copy
import hashlib
import importlib
import itertools
import json
import os
import sys
import textwrap
import threading
import types
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher import install_import_hook, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.control import (
    DYNAMIC_PACKAGE,
    PatchFileWatcher,
    RemoteLoadError,
    check_remote_load_allowed,
    get_loaded_patch,
    get_patch_set,
    list_loaded_patches,
    list_patch_sets,
    load_patch,
    reload_patch,
    start_patch_watcher,
    stop_patch_watcher,
    unload_patch,
    update_patch,
)
from sd_webui_all_in_one_hotpatcher.control.features import disable_feature, get_feature_set
from sd_webui_all_in_one_hotpatcher.control.loader import WATCH_ENV, LoadedPatch, watch_enabled_from_env
from sd_webui_all_in_one_hotpatcher.control.patchset import PatchSet
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.services import apply_config, clear_current_config, set_current_config
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

TARGET = "hpl_target"
MODULE_PREFIX = "hpl_"
QUIET_CONFIG = {
    "core": {"import_hook": {"enabled": False}, "stack_shadow": {"enabled": False}},
    "extensions": {"comfyui_auto_port": {"enabled": False}, "xformers_cutlass": {"enabled": False}},
}
# 每次写入使用递增且互不相同的 mtime, 避免同一秒内改写的源码命中过期字节码缓存。
_MTIMES = itertools.count(1_700_000_000, 10)

PATCH_V1 = """
import sys

TARGET = sys.modules["hpl_target"]
VERSION = "{version}"


def _helper():
    return VERSION


def setup(ctx):
    ctx.set_attr(TARGET, "VALUE", _helper())
    TARGET.events.append(("setup", VERSION, dict(ctx.config)))


def teardown(ctx):
    TARGET.events.append(("teardown", VERSION, TARGET.VALUE))
"""


def write_source(path, text):
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    stamp = next(_MTIMES)
    os.utime(path, (stamp, stamp))
    return path


def patch_source(version, extra=""):
    return PATCH_V1.format(version=version) + textwrap.dedent(extra)


def loaded(key, state) -> LoadedPatch:
    record = get_loaded_patch(key, state=state)
    assert record is not None, key
    return record


def registered_set(key, state) -> PatchSet:
    patch_set = get_patch_set(key, state=state)
    assert patch_set is not None, key
    return patch_set


@pytest.fixture
def target():
    module: Any = types.ModuleType(TARGET)
    module.VALUE = "original"
    module.LEVEL = 0
    module.events = []
    module.calls = 0
    sys.modules[TARGET] = module
    return module


@pytest.fixture
def state():
    isolated = HotpatcherState()
    before_path = list(sys.path)
    before_meta_path = list(sys.meta_path)
    yield isolated
    stop_patch_watcher(state=isolated)
    for name in list(isolated.loaded_patches):
        unload_patch(name, state=isolated)
    clear_current_config(state=isolated)
    uninstall_error_capture(state=isolated)
    uninstall_log_capture(state=isolated)
    uninstall_import_hook(state=isolated)
    uninstall_stack_shadower(state=isolated)
    sys.path[:] = before_path
    sys.meta_path[:] = before_meta_path
    for name in list(sys.modules):
        if name.startswith(MODULE_PREFIX) or name.startswith(f"{DYNAMIC_PACKAGE}."):
            del sys.modules[name]
    importlib.invalidate_caches()


@pytest.fixture
def module_root(tmp_path):
    root = tmp_path / "dotted"
    root.mkdir()
    sys.path.insert(0, str(root))
    importlib.invalidate_caches()
    return root


def private_modules():
    return sorted(name for name in sys.modules if name.startswith(f"{DYNAMIC_PACKAGE}."))


# ---------------------------------------------------------------------------
# 加载与卸载
# ---------------------------------------------------------------------------


def test_load_file_uses_private_module_and_unload_removes_it(tmp_path, state, target):
    path = write_source(tmp_path / "fix.py", patch_source("v1"))

    report = load_patch(str(path), name="fix", config={"level": 1}, state=state)

    json.dumps(report)
    assert report["ok"] is True and report["status"] == "loaded"
    assert report["kind"] == "file"
    assert report["source"] == report["path"] == str(path.resolve())
    assert report["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert isinstance(report["loaded_at"], float)
    set_id = report["set_id"]
    assert report["module"] == f"{DYNAMIC_PACKAGE}.{set_id}"
    assert private_modules() == [report["module"]]
    assert sys.modules[DYNAMIC_PACKAGE].__path__ == []
    assert sys.modules[report["module"]].__name__ == report["module"]
    assert target.VALUE == "v1"
    assert target.events == [("setup", "v1", {"level": 1})]
    patch_set = get_patch_set("fix", state=state)
    assert patch_set is not None and patch_set.id == set_id
    assert get_loaded_patch(set_id, state=state) is get_loaded_patch("fix", state=state)
    listed = list_loaded_patches(state=state)
    assert [(item["name"], item["origin"], item["set_id"]) for item in listed] == [("fix", "api", set_id)]
    json.dumps(listed)

    unloaded = unload_patch("fix", state=state)

    json.dumps(unloaded)
    assert unloaded["ok"] is True
    assert unloaded["status"] == "reverted"
    assert unloaded["teardown"] == "ok"
    assert unloaded["set_id"] == set_id
    assert [item["status"] for item in unloaded["handles"]] == ["reverted"]
    # teardown 在撤销之前运行, 仍能看到补丁值。
    assert target.events[-1] == ("teardown", "v1", "v1")
    assert target.VALUE == "original"
    assert private_modules() == []
    assert list_loaded_patches(state=state) == []
    assert get_patch_set("fix", state=state) is None
    assert unload_patch("fix", state=state)["error"]["code"] == "not_found"


def test_load_dotted_module_runs_setup_and_unload_keeps_module(module_root, state, target):
    write_source(module_root / "hpl_dotted_basic.py", patch_source("dotted"))

    report = load_patch("hpl_dotted_basic", state=state)

    assert report["status"] == "loaded"
    assert report["name"] == "hpl_dotted_basic"
    assert report["kind"] == "module"
    assert report["module"] == "hpl_dotted_basic"
    assert report["path"] == str(module_root / "hpl_dotted_basic.py")
    assert report["sha256"] == hashlib.sha256((module_root / "hpl_dotted_basic.py").read_bytes()).hexdigest()
    assert target.VALUE == "dotted"
    assert state.rebind_skip_modules == {"hpl_dotted_basic": {report["set_id"]}}

    assert unload_patch(report["set_id"], state=state)["status"] == "reverted"
    assert target.VALUE == "original"
    assert "hpl_dotted_basic" in sys.modules
    assert state.rebind_skip_modules == {}


def test_import_runs_inside_the_new_patch_set(tmp_path, state, target):
    path = write_source(
        tmp_path / "owner.py",
        patch_source(
            "owner",
            """
            from sd_webui_all_in_one_hotpatcher.control import current_patch_context

            OWNER = current_patch_context().id


            def setup(ctx):
                TARGET.events.append(("owner", OWNER == ctx.id))
            """,
        ),
    )

    report = load_patch(path, state=state)

    assert report["status"] == "loaded"
    assert report["name"] == str(path.resolve())
    assert target.events == [("owner", True)]


def test_load_reports_validation_errors_without_side_effects(tmp_path, state, target):
    no_setup = write_source(tmp_path / "no_setup.py", "VALUE = 1\n")
    import_error = write_source(tmp_path / "import_error.py", "raise RuntimeError('boom at import')\n")
    ok = write_source(tmp_path / "ok.py", patch_source("ok"))

    missing_setup = load_patch(no_setup, state=state)
    assert missing_setup["status"] == "failed"
    assert missing_setup["error"]["code"] == "missing_setup"
    assert missing_setup["error"]["stage"] == "setup"
    assert missing_setup["set"]["status"] == "failed"
    json.dumps(missing_setup)

    raised = load_patch(import_error, state=state)
    assert raised["error"]["code"] == "import_failed"
    assert raised["error"]["stage"] == "import"
    assert raised["error"]["error_type"] == "RuntimeError"
    assert "boom at import" in raised["error"]["message"]
    assert "Traceback" in raised["error"]["traceback"]

    assert load_patch(tmp_path / "missing.py", state=state)["error"]["code"] == "not_found"
    assert load_patch(str(tmp_path), state=state)["error"]["code"] == "invalid_source"
    assert load_patch("not a module!", state=state)["error"]["code"] == "invalid_source"
    assert load_patch(42, state=state)["error"]["code"] == "invalid_source"  # ty: ignore[invalid-argument-type]
    assert load_patch(ok, name="feature:x", state=state)["error"]["code"] == "invalid_name"
    assert load_patch(ok, config=[1], state=state)["error"]["code"] == "invalid_config"  # ty: ignore[invalid-argument-type]
    assert load_patch("hpl_missing_module_xyz", state=state)["error"]["code"] == "import_failed"

    assert private_modules() == []
    assert list_loaded_patches(state=state) == []
    assert list_patch_sets(state=state) == []
    assert state.loading_patches == set()
    assert state.rebind_skip_modules == {}

    assert load_patch(ok, name="dup", state=state)["status"] == "loaded"
    assert load_patch(ok, name="dup", state=state)["error"]["code"] == "already_loaded"
    assert target.VALUE == "ok"


def test_setup_failure_is_reverted_transactionally(tmp_path, state, target, monkeypatch):
    monkeypatch.delenv("HPL_LOADER_ENV", raising=False)
    path = write_source(
        tmp_path / "broken.py",
        """
        import sys

        TARGET = sys.modules["hpl_target"]


        def setup(ctx):
            ctx.set_attr(TARGET, "VALUE", "partial")
            ctx.set_env("HPL_LOADER_ENV", "1")
            raise RuntimeError("setup exploded")
        """,
    )

    report = load_patch(path, name="broken", state=state)

    assert report["status"] == "failed"
    assert report["error"]["code"] == "setup_failed"
    assert report["error"]["error_type"] == "RuntimeError"
    assert report["set"]["status"] == "failed"
    assert [item["status"] for item in report["set"]["handles"]] == ["reverted", "reverted"]
    assert target.VALUE == "original"
    assert "HPL_LOADER_ENV" not in os.environ
    assert private_modules() == []
    assert get_loaded_patch("broken", state=state) is None
    assert get_patch_set("broken", state=state) is None


def test_teardown_failure_is_reported_but_unload_completes(tmp_path, state, target):
    path = write_source(
        tmp_path / "bad_teardown.py",
        patch_source(
            "t",
            """
            def teardown(ctx):
                raise ValueError("teardown exploded")
            """,
        ),
    )
    assert load_patch(path, name="t", state=state)["status"] == "loaded"

    report = unload_patch("t", state=state)

    assert report["ok"] is False
    assert report["status"] == "failed"
    assert report["teardown"] == "failed"
    assert report["error"]["code"] == "teardown_failed"
    assert [item["status"] for item in report["handles"]] == ["reverted"]
    assert target.VALUE == "original"
    assert get_loaded_patch("t", state=state) is None
    assert private_modules() == []


# ---------------------------------------------------------------------------
# 重新加载与回滚
# ---------------------------------------------------------------------------


def test_reload_file_executes_new_code_with_stable_name(tmp_path, state, target):
    path = write_source(tmp_path / "fix.py", patch_source("v1"))
    first = load_patch(path, name="fix", config={"a": 1}, state=state)

    write_source(path, patch_source("v2-longer"))
    report = reload_patch("fix", state=state)

    json.dumps(report)
    assert report["status"] == "reloaded" and report["ok"] is True
    assert report["name"] == "fix"
    assert report["previous_set_id"] == first["set_id"]
    assert report["set_id"] != first["set_id"]
    assert report["generation"] == 2
    assert report["unload"]["status"] == "reverted"
    assert report["module"] == f"{DYNAMIC_PACKAGE}.{report['set_id']}"
    assert private_modules() == [report["module"]]
    assert target.VALUE == "v2-longer"
    assert target.events == [("setup", "v1", {"a": 1}), ("teardown", "v1", "v1"), ("setup", "v2-longer", {"a": 1})]
    assert registered_set("fix", state).id == report["set_id"]

    reloaded_with_config = reload_patch(report["set_id"], config={"a": 2}, state=state)
    assert reloaded_with_config["status"] == "reloaded"
    assert target.events[-1] == ("setup", "v2-longer", {"a": 2})
    assert loaded("fix", state).config == {"a": 2}


@pytest.mark.parametrize(
    ("broken_extra", "stage"),
    [
        ("raise RuntimeError('new version broken at import')\n", "import"),
        (
            """
            def setup(ctx):
                ctx.set_attr(TARGET, "VALUE", "v2-partial")
                raise RuntimeError("new version broken in setup")
            """,
            "setup",
        ),
    ],
)
def test_reload_file_rolls_back_to_old_module(tmp_path, state, target, broken_extra, stage):
    path = write_source(tmp_path / "fix.py", patch_source("v1"))
    first = load_patch(path, name="fix", config={"a": 1}, state=state)
    old_module = sys.modules[first["module"]]

    write_source(path, patch_source("v2", broken_extra))
    report = reload_patch("fix", config={"a": 99}, state=state)

    json.dumps(report)
    assert report["status"] == "rolled_back"
    assert report["ok"] is False
    assert report["error"]["code"] == f"{stage}_failed"
    assert "new version broken" in report["error"]["message"]
    assert report["failed_set"]["status"] == "failed"
    assert report["rollback_error"] is None
    # 旧模块 (含模块级辅助函数) 重新应用, 使用旧配置。
    assert target.VALUE == "v1"
    assert target.events[-1] == ("setup", "v1", {"a": 1})
    record = get_loaded_patch("fix", state=state)
    assert record is not None
    assert record.status == "rolled_back"
    assert record.module is old_module
    assert record.module_name == first["module"]
    assert record.sha256 == first["sha256"]
    assert record.failed_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert record.last_error is not None and record.last_error["code"] == f"{stage}_failed"
    assert record.set_id == report["set_id"] != first["set_id"]
    assert private_modules() == [first["module"]]
    assert sys.modules[first["module"]] is old_module

    assert unload_patch("fix", state=state)["status"] == "reverted"
    assert target.VALUE == "original"
    assert private_modules() == []


def test_reload_dotted_module_rolls_back_and_restores_namespace(module_root, state, target):
    source = module_root / "hpl_dotted_reload.py"
    write_source(source, patch_source("v1"))
    first = load_patch("hpl_dotted_reload", state=state)
    module = sys.modules["hpl_dotted_reload"]

    write_source(
        source,
        patch_source(
            "v2-broken",
            """
            NEW_ONLY = True


            def setup(ctx):
                raise RuntimeError("dotted v2 broken")
            """,
        ),
    )
    report = reload_patch("hpl_dotted_reload", state=state)

    assert report["status"] == "rolled_back"
    assert report["error"]["code"] == "setup_failed"
    assert sys.modules["hpl_dotted_reload"] is module
    assert module.VERSION == "v1"
    assert not hasattr(module, "NEW_ONLY")
    assert target.VALUE == "v1"
    assert state.rebind_skip_modules == {"hpl_dotted_reload": {report["set_id"]}}
    assert first["set_id"] != report["set_id"]

    write_source(source, patch_source("v3-fixed"))
    fixed = reload_patch("hpl_dotted_reload", state=state)
    assert fixed["status"] == "reloaded"
    assert sys.modules["hpl_dotted_reload"] is module
    assert module.VERSION == "v3-fixed"
    assert target.VALUE == "v3-fixed"
    assert loaded("hpl_dotted_reload", state).status == "loaded"
    assert state.rebind_skip_modules == {"hpl_dotted_reload": {fixed["set_id"]}}


def test_reload_double_failure_reports_both_errors(tmp_path, state, target, module_root):
    flaky = """
    def setup(ctx):
        TARGET.calls += 1
        if TARGET.calls > 1:
            raise RuntimeError("old version cannot be re-applied")
        ctx.set_attr(TARGET, "VALUE", _helper())
    """
    path = write_source(tmp_path / "flaky.py", patch_source("v1", flaky))
    assert load_patch(path, name="flaky", state=state)["status"] == "loaded"
    write_source(path, "raise RuntimeError('new version broken')\n")

    report = reload_patch("flaky", state=state)

    json.dumps(report)
    assert report["status"] == "failed"
    assert report["error"]["code"] == "import_failed"
    assert "new version broken" in report["error"]["message"]
    assert report["rollback_error"]["code"] == "setup_failed"
    assert "old version cannot be re-applied" in report["rollback_error"]["message"]
    assert target.VALUE == "original"
    assert get_loaded_patch("flaky", state=state) is None
    assert get_patch_set("flaky", state=state) is None
    assert private_modules() == []
    assert state.loading_patches == set()

    target.calls = 0
    dotted = module_root / "hpl_dotted_flaky.py"
    write_source(dotted, patch_source("v1", flaky))
    assert load_patch("hpl_dotted_flaky", state=state)["status"] == "loaded"
    write_source(dotted, "raise RuntimeError('dotted new version broken')\n")
    assert reload_patch("hpl_dotted_flaky", state=state)["status"] == "failed"
    assert state.rebind_skip_modules == {}


def test_dotted_package_submodule_loads_reloads_and_rolls_back(module_root, state, target):
    package = module_root / "hpl_pkg"
    package.mkdir()
    write_source(package / "__init__.py", "PACKAGE_MARK = 'pkg'\n")
    write_source(package / "helpers.py", "def version_suffix():\n    return '-helper'\n")
    fix = package / "fix.py"
    body = """
    from .helpers import version_suffix


    def setup(ctx):
        ctx.set_attr(TARGET, "VALUE", VERSION + version_suffix())
    """
    write_source(fix, patch_source("v1", body))
    importlib.invalidate_caches()

    report = load_patch("hpl_pkg.fix", state=state)

    assert report["status"] == "loaded" and report["kind"] == "module"
    assert report["path"] == str(fix)
    assert target.VALUE == "v1-helper"
    module = sys.modules["hpl_pkg.fix"]
    assert getattr(sys.modules["hpl_pkg"], "fix") is module
    assert state.rebind_skip_modules == {"hpl_pkg.fix": {report["set_id"]}}

    write_source(fix, patch_source("v2-pkg", body))
    reloaded = reload_patch("hpl_pkg.fix", state=state)
    assert reloaded["status"] == "reloaded"
    assert target.VALUE == "v2-pkg-helper"

    write_source(fix, patch_source("v3", "from .missing_helper import nothing\n"))
    rolled_back = reload_patch("hpl_pkg.fix", state=state)
    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["error"]["code"] == "import_failed"
    assert sys.modules["hpl_pkg.fix"] is module
    assert getattr(sys.modules["hpl_pkg"], "fix") is module
    assert getattr(module, "VERSION") == "v2-pkg"
    assert target.VALUE == "v2-pkg-helper"

    assert unload_patch("hpl_pkg.fix", state=state)["status"] == "reverted"
    assert target.VALUE == "original"
    assert state.rebind_skip_modules == {}


def test_file_patch_with_import_hook_installed_reports_deregistered_and_reverted(tmp_path, module_root, state, target):
    install_import_hook(state=state)
    write_source(module_root / "hpl_lazy_target.py", "def value():\n    return 'plain'\n")
    importlib.invalidate_caches()
    source = """
    import sys

    TARGET = sys.modules["hpl_target"]


    def setup(ctx):
        with ctx.module("hpl_lazy_target") as monkey:
            monkey.patch_function("value", lambda original, module: lambda: "patched " + original())
        ctx.set_attr(TARGET, "VALUE", "live")
    """
    path = write_source(tmp_path / "hooked.py", source)

    first = load_patch(path, name="hooked", state=state)
    assert first["status"] == "loaded"
    assert [handle["status"] for handle in first["set"]["handles"]] == ["registered", "applied"]
    # 目标模块尚未导入: 函数补丁从计划中注销, 实时操作被撤销。
    unloaded = unload_patch("hooked", state=state)
    assert sorted(handle["status"] for handle in unloaded["handles"]) == ["deregistered", "reverted"]
    assert unloaded["status"] == "reverted"
    assert target.VALUE == "original"
    assert "hpl_lazy_target" not in sys.modules

    assert load_patch(path, name="hooked", state=state)["status"] == "loaded"
    lazy = importlib.import_module("hpl_lazy_target")
    assert lazy.value() == "patched plain"
    after_import = unload_patch("hooked", state=state)
    assert sorted(handle["status"] for handle in after_import["handles"]) == ["reverted", "reverted"]
    assert lazy.value() == "plain"
    assert private_modules() == []


# ---------------------------------------------------------------------------
# 更新
# ---------------------------------------------------------------------------

UPDATABLE = """
def update(ctx, config):
    if config.get("mode") == "explode":
        raise ValueError("update exploded")
    if config.get("mode") != "in_place":
        return False
    ctx.set_attr(TARGET, "LEVEL", config["level"])
    return True
"""


def test_update_in_place_and_fallback_to_reload(tmp_path, state, target):
    path = write_source(tmp_path / "upd.py", patch_source("v1", UPDATABLE))
    first = load_patch(path, name="upd", config={"mode": "in_place", "level": 1}, state=state)

    in_place = update_patch("upd", {"mode": "in_place", "level": 3}, state=state)

    json.dumps(in_place)
    assert in_place["status"] == "updated" and in_place["mode"] == "in_place"
    assert in_place["set_id"] == first["set_id"]
    assert target.LEVEL == 3
    record = get_loaded_patch("upd", state=state)
    assert record is not None and record.config == {"mode": "in_place", "level": 3}
    assert record.patch_set.context.config == {"mode": "in_place", "level": 3}

    exploded = update_patch("upd", {"mode": "explode"}, state=state)
    assert exploded["status"] == "failed"
    assert exploded["error"]["code"] == "update_failed"
    assert loaded("upd", state).set_id == first["set_id"]
    assert target.VALUE == "v1"

    fallback = update_patch("upd", {"mode": "restart"}, state=state)
    assert fallback["mode"] == "reload"
    assert fallback["status"] == "reloaded"
    assert fallback["reload"]["status"] == "reloaded"
    assert fallback["set_id"] != first["set_id"]
    # 原地更新的修改属于旧补丁集, 重新加载时一并撤销。
    assert target.LEVEL == 0
    assert target.events[-1] == ("setup", "v1", {"mode": "restart"})

    plain = write_source(tmp_path / "plain.py", patch_source("plain"))
    load_patch(plain, name="plain", state=state)
    no_update = update_patch("plain", {"x": 1}, state=state)
    assert no_update["mode"] == "reload" and no_update["status"] == "reloaded"
    assert target.events[-1] == ("setup", "plain", {"x": 1})
    assert update_patch("plain", [1], state=state)["error"]["code"] == "invalid_config"  # ty: ignore[invalid-argument-type]
    assert update_patch("nope", {}, state=state)["error"]["code"] == "not_found"


def test_concurrent_operation_on_same_patch_is_rejected(tmp_path, state, target):
    path = write_source(tmp_path / "busy.py", patch_source("v1"))
    load_patch(path, name="busy", state=state)
    state.loading_patches.add("busy")
    try:
        assert unload_patch("busy", state=state)["error"]["code"] == "busy"
        assert reload_patch("busy", state=state)["error"]["code"] == "busy"
        assert load_patch(path, name="busy", state=state)["error"]["code"] == "busy"
    finally:
        state.loading_patches.discard("busy")
    assert unload_patch("busy", state=state)["status"] == "reverted"


# ---------------------------------------------------------------------------
# rebind 跳过
# ---------------------------------------------------------------------------


def _make_greet():
    # 在函数内创建: rebind_references 会扫描所有模块命名空间, 测试模块全局变量不能持有原函数。
    def greet(name):
        return f"hello {name}"

    return greet


def test_dotted_patch_module_is_skipped_by_rebind_scan(module_root, state, target):
    target.greet = _make_greet()
    consumer: Any = types.ModuleType("hpl_consumer")
    consumer.greet = target.greet
    sys.modules["hpl_consumer"] = consumer
    write_source(
        module_root / "hpl_rebind_patch.py",
        """
        from hpl_target import greet


        def setup(ctx):
            # 包装函数通过模块全局变量 greet 调用原函数; 若本模块被 rebind 改写会无限递归。
            ctx.wrap("hpl_target:greet", lambda original: lambda name: "wrapped " + greet(name), rebind_references=True)
        """,
    )

    report = load_patch("hpl_rebind_patch", state=state)

    assert report["status"] == "loaded"
    assert state.rebind_skip_modules == {"hpl_rebind_patch": {report["set_id"]}}
    assert target.greet("x") == "wrapped hello x"
    assert consumer.greet("x") == "wrapped hello x"
    assert getattr(sys.modules["hpl_rebind_patch"], "greet")("x") == "hello x"
    handle = next(handle for handle in registered_set(report["set_id"], state).handles if handle.kind == "wrap")
    outcome = handle.last_outcome
    assert outcome is not None and outcome.detail is not None
    rebound = outcome.detail["rebound"]
    assert "hpl_consumer.greet" in rebound
    assert not any(location.startswith("hpl_rebind_patch.") for location in rebound)

    unload_patch("hpl_rebind_patch", state=state)
    assert state.rebind_skip_modules == {}
    assert target.greet("x") == "hello x"
    assert consumer.greet("x") == "hello x"


def test_file_patch_module_is_skipped_by_rebind_scan(tmp_path, state, target):
    target.greet = _make_greet()
    path = write_source(
        tmp_path / "rebind_file.py",
        """
        from hpl_target import greet


        def setup(ctx):
            ctx.wrap("hpl_target:greet", lambda original: lambda name: "file " + greet(name), rebind_references=True)
        """,
    )

    report = load_patch(path, state=state)

    assert report["status"] == "loaded"
    assert state.rebind_skip_modules == {}
    assert target.greet("y") == "file hello y"


# ---------------------------------------------------------------------------
# 文件监视器
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_watcher_reloads_after_debounce_and_retries_only_on_new_change(tmp_path, state, target):
    path = write_source(tmp_path / "watched.py", patch_source("v1"))
    load_patch(path, name="watched", state=state)
    clock = FakeClock()
    watcher = PatchFileWatcher(state=state, interval=1.0, debounce=0.5, clock=clock)

    assert watcher.poll_once() == []

    write_source(path, patch_source("v2"))
    assert watcher.poll_once() == []
    clock.advance(0.2)
    assert watcher.poll_once() == []
    clock.advance(0.4)
    [report] = watcher.poll_once()
    assert report["status"] == "reloaded"
    assert target.VALUE == "v2"
    assert watcher.reload_count == 1
    assert watcher.poll_once() == []

    write_source(path, patch_source("v3", "raise RuntimeError('v3 broken')\n"))
    assert watcher.poll_once() == []
    clock.advance(1)
    [failed] = watcher.poll_once()
    assert failed["status"] == "rolled_back"
    assert target.VALUE == "v2"
    assert watcher.failures["watched"]["status"] == "rolled_back"
    clock.advance(5)
    assert watcher.poll_once() == []
    assert watcher.reload_count == 2

    # 内容在防抖窗口内再次变化时重新计时。
    write_source(path, patch_source("v4"))
    assert watcher.poll_once() == []
    clock.advance(0.3)
    write_source(path, patch_source("v5-final"))
    assert watcher.poll_once() == []
    clock.advance(0.3)
    assert watcher.poll_once() == []
    clock.advance(0.3)
    [fixed] = watcher.poll_once()
    assert fixed["status"] == "reloaded"
    assert target.VALUE == "v5-final"
    assert "watched" not in watcher.failures


def test_watcher_without_debounce_reloads_immediately_and_never_holds_locks(tmp_path, state, target):
    path = write_source(tmp_path / "immediate.py", patch_source("v1"))
    load_patch(path, name="immediate", state=state)
    observations = []

    def reload(name, *, state):
        result = {}

        def probe():
            acquired = state.control_lock.acquire(timeout=2)
            if acquired:
                state.control_lock.release()
            result["control_lock"] = acquired

        thread = threading.Thread(target=probe)
        thread.start()
        thread.join(5)
        watcher_lock_free = watcher._lock.acquire(blocking=False)
        if watcher_lock_free:
            watcher._lock.release()
        observations.append((name, result.get("control_lock"), watcher_lock_free))
        return reload_patch(name, state=state)

    watcher = PatchFileWatcher(state=state, debounce=0, clock=FakeClock(), reload=reload)
    write_source(path, patch_source("v2"))

    [report] = watcher.poll_once()

    assert report["status"] == "reloaded"
    assert observations == [("immediate", True, True)]
    assert target.VALUE == "v2"

    path.unlink()
    assert watcher.poll_once() == []
    unload_patch("immediate", state=state)
    assert watcher.poll_once() == []


def test_watcher_thread_start_stop_and_env(tmp_path, state, monkeypatch):
    sleeps = []
    slept_twice = threading.Event()

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= 2:
            slept_twice.set()
        threading.Event().wait(0.001)

    watcher = PatchFileWatcher(state=state, interval=0.25, sleep=sleep)
    assert watcher.start() is watcher
    assert watcher.start() is watcher
    assert slept_twice.wait(5)
    assert watcher.running
    watcher.stop()
    assert not watcher.running
    assert set(sleeps) == {0.25}

    started = start_patch_watcher(interval=0.05, state=state)
    assert started.running and started.interval == 0.05
    assert start_patch_watcher(state=state) is started
    assert stop_patch_watcher(state=state) is True
    assert not started.running
    assert stop_patch_watcher(state=state) is False

    with pytest.raises(ValueError):
        PatchFileWatcher(state=state, interval=0)
    with pytest.raises(ValueError):
        PatchFileWatcher(state=state, debounce=-1)

    monkeypatch.delenv(WATCH_ENV, raising=False)
    assert watch_enabled_from_env() is False
    monkeypatch.setenv(WATCH_ENV, "1")
    assert watch_enabled_from_env() is True


# ---------------------------------------------------------------------------
# 远程加载门禁
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("control", "transport", "token", "expected"),
    [
        (None, "legacy", "token", "remote_load_disabled"),
        ({"allow_remote_load": False}, "legacy", "token", "remote_load_disabled"),
        ({"allow_remote_load": False}, "desktop", None, "remote_load_disabled"),
        ({"allow_remote_load": "true"}, "legacy", "token", "remote_load_disabled"),
        ({"allow_remote_load": 1}, "desktop", None, "remote_load_disabled"),
        ({"allow_remote_load": True}, "legacy", "", "forbidden"),
        ({"allow_remote_load": True}, "legacy", "   ", "forbidden"),
        ({"allow_remote_load": True}, "legacy", None, "forbidden"),
        ({"allow_remote_load": True}, "custom", None, "forbidden"),
        ({"allow_remote_load": True}, "legacy", "token", None),
        ({"allow_remote_load": True}, "custom", "token", None),
        ({"allow_remote_load": True}, "desktop", None, None),
        ({"allow_remote_load": True}, "desktop", "", None),
    ],
)
def test_remote_load_gate_matrix(state, control, transport, token, expected):
    if control is not None:
        set_current_config({"control": control}, state=state)

    if expected is None:
        assert check_remote_load_allowed(state=state, transport=transport, token=token) is None
        return
    with pytest.raises(RemoteLoadError) as caught:
        check_remote_load_allowed(state=state, transport=transport, token=token)
    assert caught.value.code == expected
    assert isinstance(caught.value, PermissionError)


# ---------------------------------------------------------------------------
# 配置声明的补丁集
# ---------------------------------------------------------------------------


def control_config(patch_sets, **watch):
    config = copy.deepcopy(QUIET_CONFIG)
    config["control"] = {"patch_sets": patch_sets}
    if watch:
        config["control"]["watch"] = watch
    return config


def test_config_declared_sets_apply_with_isolation_and_idempotency(tmp_path, state, target):
    good = write_source(tmp_path / "good.py", patch_source("good"))
    bad = write_source(tmp_path / "bad.py", "def setup(ctx):\n    raise RuntimeError('bad setup')\n")
    off = write_source(tmp_path / "off.py", patch_source("off"))
    entries: list[Any] = [
        {"source": str(good), "name": "good", "config": {"n": 1}},
        "not-an-object",
        {"source": str(bad), "name": "bad"},
        {"source": str(tmp_path / "missing.py"), "name": "missing"},
        {"source": str(off), "name": "off", "enabled": False},
        {"name": "no-source"},
    ]

    result = apply_config(control_config(entries), state=state)

    json.dumps(result)
    assert "control" in result["applied"]
    errors = {(item.get("patch_set"), item["code"]) for item in result["errors"] if item["feature"] == "control"}
    assert errors == {(None, "invalid_config"), ("no-source", "invalid_config"), ("bad", "setup_failed"), ("missing", "not_found")}
    assert len([item for item in result["errors"] if item["feature"] == "control"]) == 4
    assert [item["name"] for item in list_loaded_patches(state=state)] == ["good"]
    record = get_loaded_patch("good", state=state)
    assert record is not None and record.origin == "config" and record.config == {"n": 1}
    first_set_id = record.set_id
    assert target.VALUE == "good"
    assert target.events == [("setup", "good", {"n": 1})]

    again = apply_config(control_config(entries), state=state)
    assert loaded("good", state).set_id == first_set_id
    assert target.events == [("setup", "good", {"n": 1})]
    assert {(item.get("patch_set"), item["code"]) for item in again["errors"] if item["feature"] == "control"} == errors

    entries[0]["config"] = {"n": 2}
    apply_config(control_config(entries), state=state)
    changed = get_loaded_patch("good", state=state)
    assert changed is not None and changed.set_id != first_set_id
    assert changed.config == {"n": 2}
    assert target.events[-1] == ("setup", "good", {"n": 2})

    write_source(good, patch_source("good-v2"))
    apply_config(control_config(entries), state=state)
    assert target.VALUE == "good-v2"
    assert loaded("good", state).generation == 3


def test_config_declared_sets_reconcile_and_disable(tmp_path, state, target):
    first = write_source(tmp_path / "first.py", patch_source("first"))
    second = write_source(tmp_path / "second.py", "import sys\n\n\ndef setup(ctx):\n    ctx.set_attr(sys.modules['hpl_target'], 'LEVEL', 7)\n")
    api = write_source(tmp_path / "api.py", "def setup(ctx):\n    pass\n")
    load_patch(api, name="api", state=state)
    entries: list[dict[str, Any]] = [{"source": str(first), "name": "first"}, {"source": str(second), "name": "second"}]
    apply_config(control_config(entries), state=state)
    assert target.VALUE == "first" and target.LEVEL == 7

    entries[1]["enabled"] = False
    kept = apply_config(control_config(entries), state=state)
    assert get_loaded_patch("second", state=state) is not None
    assert any("'second' is disabled but remains loaded" in item["message"] for item in kept["warnings"])
    assert "reconciled" not in kept

    reconciled = apply_config(control_config(entries[:1]), state=state, reconcile=True)
    assert get_loaded_patch("second", state=state) is None
    assert target.LEVEL == 0
    assert [(item["name"], item["status"]) for item in reconciled["reconciled"]] == [("second", "reverted")]
    assert get_loaded_patch("api", state=state) is not None

    report = disable_feature("control", state=state)
    assert report["ok"] is True
    assert report["status"] == "reverted"
    assert not [item for item in report["warnings"] if item["feature"] == "control"]
    assert get_loaded_patch("first", state=state) is None
    assert target.VALUE == "original"
    assert get_loaded_patch("api", state=state) is not None


def test_reconcile_keeps_listed_sets_whose_entry_failed_and_rejects_duplicates(tmp_path, state, target):
    kept = write_source(tmp_path / "kept.py", patch_source("kept"))
    entries: list[dict[str, Any]] = [{"source": str(kept)}, {"source": str(kept), "name": "twin"}]
    apply_config(control_config(entries), state=state)
    name = str(kept.resolve())
    assert loaded(name, state).origin == "config"

    # 源文件暂时缺失、配置非法、名称重复: 条目报错, 但 reconcile 不卸载仍在列表中的补丁集。
    kept.rename(tmp_path / "moved.py")
    entries[1]["config"] = "not-an-object"
    entries.append({"source": str(tmp_path / "moved.py"), "name": "twin"})
    result = apply_config(control_config(entries), state=state, reconcile=True)

    codes = sorted((item.get("patch_set"), item["code"]) for item in result["errors"] if item["feature"] == "control")
    assert codes == [(name, "not_found"), ("twin", "duplicate_name"), ("twin", "invalid_config")]
    assert result["reconciled"] == []
    assert loaded(name, state).set_id
    assert loaded("twin", state).set_id
    assert target.VALUE == "kept"


def test_empty_control_section_leaves_apply_result_unchanged(state):
    result = apply_config(copy.deepcopy(QUIET_CONFIG), state=state)

    assert "control" not in result["applied"]
    assert not [item for item in result["errors"] if item["feature"] == "control"]
    assert not [item for item in result["warnings"] if item["feature"] == "control"]
    assert get_feature_set("control", state=state) is None
    assert state.patch_file_watcher is None


def test_config_watch_starts_and_reconcile_stops_watcher(state, monkeypatch):
    monkeypatch.delenv(WATCH_ENV, raising=False)

    result = apply_config(control_config([], enabled=True, interval=0.5), state=state)

    assert "control" in result["applied"]
    watcher = state.patch_file_watcher
    assert watcher is not None and watcher.running and watcher.interval == 0.5

    invalid = apply_config(control_config([], enabled=True, interval="soon"), state=state)
    assert any("watch interval" in item["message"] for item in invalid["warnings"])
    assert state.patch_file_watcher is watcher and watcher.interval == 1.0

    apply_config(control_config([], enabled=False), state=state)
    assert watcher.running
    apply_config(control_config([], enabled=False), state=state, reconcile=True)
    assert not watcher.running
    assert state.patch_file_watcher is None

    monkeypatch.setenv(WATCH_ENV, "1")
    apply_config(control_config([]), state=state)
    assert state.patch_file_watcher is not None and state.patch_file_watcher.running
