"""功能注册表测试: 注册顺序、惰性引用、目录派生、逐功能补丁集、启用/禁用/更新与可选 reconcile。"""

import copy
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, services, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.control.features import (
    BUILTIN_FEATURES,
    ConfigCall,
    FeatureReferenceError,
    FeatureRegistry,
    FeatureSpec,
    NoArgCall,
    build_default_config,
    build_setting_schema,
    disable_feature,
    enable_feature,
    feature_set_name,
    get_feature_registry,
    get_feature_set,
    list_features,
    resolve_reference,
    update_feature,
)
from sd_webui_all_in_one_hotpatcher.runtime.errors import is_error_capture_installed, uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.services import apply_config, clear_current_config, get_catalog, get_default_config, normalize_config
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState, get_default_state
from sd_webui_all_in_one_hotpatcher_ext.comfyui_auto_port import is_comfyui_auto_port_patch_registered
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import is_uv_patch_installed, unpatch_uv_to_subprocess

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "services" / "golden"

APPLY_ORDER = [
    "services",
    "core.import_hook",
    "core.stack_shadow",
    "runtime.browser",
    "runtime.errors",
    "runtime.logs",
    "extensions.comfyui_auto_port",
    "extensions.zluda",
    "extensions.extension_index",
    "extensions.hf_endpoint_mirror",
    "extensions.uv_pip",
    "extensions.xformers_cutlass",
]
CATALOG_ORDER = [
    "services",
    "core.import_hook",
    "core.stack_shadow",
    "runtime.logs",
    "runtime.browser",
    "runtime.errors",
    "extensions.zluda",
    "extensions.comfyui_auto_port",
    "extensions.extension_index",
    "extensions.hf_endpoint_mirror",
    "extensions.xformers_cutlass",
    "extensions.uv_pip",
]
V1_DISABLED_WARNINGS = [
    {"feature": "core.import_hook", "message": "import hook is already installed and v1 services does not uninstall it"},
    {"feature": "core.stack_shadow", "message": "stack shadower is already installed and v1 services does not uninstall it"},
    {"feature": "runtime.browser", "message": "browser wrapper remains registered in passthrough mode; process restart is required to remove it"},
    {"feature": "extensions.comfyui_auto_port", "message": "ComfyUI auto-port patch remains registered; process restart is required to remove it"},
    {"feature": "extensions.uv_pip", "message": "uv pip patch is already installed and v1 services does not uninstall it"},
]
ALL_DISABLED: dict[str, Any] = {
    "core": {"import_hook": {"enabled": False}, "stack_shadow": {"enabled": False}},
    "extensions": {"comfyui_auto_port": {"enabled": False}, "xformers_cutlass": {"enabled": False}},
}


class FakeSink:
    def __init__(self):
        self.events = []

    def emit_event(self, event_type, payload=None, /):
        self.events.append((event_type, payload))
        return True


def _reset(state):
    for target in (state, None):
        clear_current_config(state=target)
        uninstall_error_capture(state=target)
        uninstall_log_capture(state=target)
        uninstall_import_hook(state=target)
        uninstall_stack_shadower(state=target)
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()


@pytest.fixture
def state():
    isolated = HotpatcherState()
    default = get_default_state()
    saved = (dict(default.patch_sets), dict(default.patch_handles), default.feature_registry, default.current_config)
    original_run = subprocess.run
    _reset(isolated)
    meta_path_before = list(sys.meta_path)
    spec_from_file_location_before = importlib.util.spec_from_file_location
    yield isolated
    _reset(isolated)
    default.patch_sets.clear()
    default.patch_sets.update(saved[0])
    default.patch_handles.clear()
    default.patch_handles.update(saved[1])
    default.feature_registry = saved[2]
    default.current_config = saved[3]
    assert subprocess.run is original_run
    assert sys.meta_path == meta_path_before
    assert importlib.util.spec_from_file_location is spec_from_file_location_before


@pytest.fixture
def fake_webbrowser(monkeypatch):
    from sd_webui_all_in_one_hotpatcher.runtime import browser

    module = types.ModuleType("webbrowser")
    opened = []

    def original(url, *args, **kwargs):
        opened.append(url)
        return False

    setattr(module, "open", original)
    monkeypatch.setitem(sys.modules, "webbrowser", module)
    monkeypatch.setattr(browser, "install_import_hook", lambda **_kwargs: None)
    return module, opened


def _demo_spec(calls, **overrides):
    def apply(ctx, section):
        calls.append(("apply", copy.deepcopy(section)))
        ctx.patch_set.context.set_attr(target, "value", section["level"])

    target = types.SimpleNamespace(value=0)
    fields: dict[str, Any] = {
        "key": "thirdparty.demo",
        "title": "Demo",
        "description": "第三方演示功能",
        "defaults": {"enabled": False, "level": 1},
        "settings": {
            "enabled": {"type": "bool", "title": "启用", "description": "启用演示功能。"},
            "level": {"type": "int", "title": "级别", "description": "演示级别。"},
        },
        "apply": apply,
        "is_active": lambda ctx: target.value != 0,
    }
    fields.update(overrides)
    return FeatureSpec(**fields), target


# ---------------------------------------------------------------------------
# 注册表与引用解析
# ---------------------------------------------------------------------------


def test_builtin_registry_preserves_apply_catalog_and_config_orders():
    registry = FeatureRegistry(BUILTIN_FEATURES)

    assert registry.keys() == APPLY_ORDER
    assert [spec.key for spec in registry.catalog_specs()] == CATALOG_ORDER
    assert list(build_default_config(registry)) == ["services", "core", "runtime", "extensions"]
    defaults = build_default_config(registry)
    assert list(defaults["runtime"]) == ["browser", "errors", "logs"]
    assert list(defaults["extensions"]) == ["comfyui_auto_port", "zluda", "extension_index", "hf_endpoint_mirror", "xformers_cutlass", "uv_pip"]


def test_registry_register_replace_unregister_and_conflicts():
    registry = FeatureRegistry(BUILTIN_FEATURES)
    spec, _target = _demo_spec([])
    late, _ = _demo_spec([], key="thirdparty.early", order=1)

    registry.register(spec)
    registry.register(late)
    assert registry.keys()[0] == "services"
    assert registry.keys()[1] == "thirdparty.early"
    assert registry.keys()[-1] == "thirdparty.demo"
    assert [item.key for item in registry.catalog_specs()][-2:] == ["thirdparty.demo", "thirdparty.early"]

    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec)
    replacement, _ = _demo_spec([], title="Demo 2")
    registry.register(replacement, replace=True)
    assert registry.get("thirdparty.demo") is replacement
    assert [item.key for item in registry.catalog_specs()][-2:] == ["thirdparty.demo", "thirdparty.early"]

    with pytest.raises(ValueError, match="overlap"):
        registry.register(FeatureSpec(key="services.extra", title="x", description="x"))
    with pytest.raises(ValueError, match="overlap"):
        registry.register(FeatureSpec(key="thirdparty", title="x", description="x"))
    with pytest.raises(TypeError):
        registry.register("thirdparty.other")  # ty: ignore[invalid-argument-type]
    with pytest.raises(ValueError, match="dot-separated"):
        FeatureSpec(key="bad key", title="x", description="x")

    assert registry.unregister("thirdparty.demo") is replacement
    assert registry.unregister("thirdparty.demo") is None
    assert "thirdparty.demo" not in registry
    assert len(registry) == len(BUILTIN_FEATURES) + 1


def test_resolve_reference_is_lazy_and_reports_clear_errors(monkeypatch):
    import json as json_module

    assert resolve_reference("json:dumps") is json_module.dumps
    assert resolve_reference(len) is len
    sentinel = object()
    monkeypatch.setattr(json_module, "dumps", lambda value: sentinel)
    assert ConfigCall("json:dumps")(None, {}) is sentinel  # ty: ignore[invalid-argument-type]
    assert NoArgCall("os:getpid")(None) > 0  # ty: ignore[invalid-argument-type]

    with pytest.raises(FeatureReferenceError, match="expected 'package.module:callable'"):
        resolve_reference("json.dumps")
    with pytest.raises(FeatureReferenceError, match="module 'hp_features_missing_module' could not be imported"):
        resolve_reference("hp_features_missing_module:apply")
    with pytest.raises(FeatureReferenceError, match="attribute 'missing' not found"):
        resolve_reference("json:missing")
    with pytest.raises(FeatureReferenceError, match="not callable"):
        resolve_reference("json:__name__")
    with pytest.raises(FeatureReferenceError):
        resolve_reference(42)  # ty: ignore[invalid-argument-type]


def test_builtin_specs_hold_unresolved_extension_references():
    references = []
    for spec in BUILTIN_FEATURES:
        for value in (spec.apply, spec.is_active, spec.is_registered, spec.revert, spec.update, spec.on_disabled):
            if isinstance(value, (ConfigCall, NoArgCall)):
                value = value.reference
            if value is not None:
                assert isinstance(value, str), spec.key
                references.append(value)
    assert "sd_webui_all_in_one_hotpatcher_ext.uv_pip:apply_from_config" in references
    assert "sd_webui_all_in_one_hotpatcher_ext.uv_pip:unpatch_uv_to_subprocess" in references
    assert "sd_webui_all_in_one_hotpatcher.services:_feature_apply_import_hook" in references
    for reference in references:
        assert callable(resolve_reference(reference)), reference


def test_enable_feature_reports_unresolvable_reference(state):
    registry = get_feature_registry(state)
    registry.register(FeatureSpec(key="thirdparty.broken", title="Broken", description="x", defaults={"enabled": False}, apply="hp_features_missing_module:apply"))

    report = enable_feature("thirdparty.broken", state=state)

    assert report["ok"] is False
    assert report["status"] == "failed"
    assert report["errors"][0]["code"] == "FeatureReferenceError"
    assert "hp_features_missing_module" in report["errors"][0]["message"]
    json.dumps(report)

    result = apply_config({"thirdparty": {"broken": {"enabled": True}}}, state=state)
    assert "thirdparty.broken" not in result["applied"]
    assert result["errors"][0]["feature"] == "thirdparty.broken"
    assert result["errors"][0]["code"] == "FeatureReferenceError"


# ---------------------------------------------------------------------------
# 目录派生
# ---------------------------------------------------------------------------


def test_derived_constants_match_golden_files():
    default_text = json.dumps(build_default_config(BUILTIN_FEATURES), ensure_ascii=False, indent=2) + "\n"
    assert default_text == (GOLDEN_DIR / "default_config.json").read_text(encoding="utf-8")
    assert services.DEFAULT_CONFIG == build_default_config(BUILTIN_FEATURES)
    assert get_default_config(state=HotpatcherState()) == services.DEFAULT_CONFIG

    catalog = json.loads((GOLDEN_DIR / "catalog_static.json").read_text(encoding="utf-8"))["features"]
    schema = build_setting_schema(BUILTIN_FEATURES)
    assert services.SETTING_SCHEMA == schema
    assert list(schema) == list(catalog)
    for key, feature in schema.items():
        assert feature["title"] == catalog[key]["title"]
        assert feature["description"] == catalog[key]["description"]
        assert list(feature["settings"]) == list(catalog[key]["settings"])
        for setting, metadata in feature["settings"].items():
            assert {name: value for name, value in catalog[key]["settings"][setting].items() if name != "default"} == metadata


def test_third_party_feature_appears_in_config_catalog_normalize_and_apply(state):
    calls = []
    spec, target = _demo_spec(calls)
    get_feature_registry(state).register(spec)

    defaults = get_default_config(state=state)
    assert list(defaults)[-1] == "thirdparty"
    assert defaults["thirdparty"] == {"demo": {"enabled": False, "level": 1}}
    assert "thirdparty" not in get_default_config(state=HotpatcherState())

    features = get_catalog(state=state)["features"]
    assert list(features)[-1] == "thirdparty.demo"
    assert features["thirdparty.demo"]["default"] == {"enabled": False, "level": 1}
    assert features["thirdparty.demo"]["settings"]["level"]["default"] == 1
    assert features["thirdparty.demo"]["active"] is False

    assert normalize_config({}, state=state)["thirdparty"]["demo"] == {"enabled": False, "level": 1}

    result = apply_config({"thirdparty": {"demo": {"enabled": True, "level": 3}}}, state=state)
    assert result["applied"][-1] == "thirdparty.demo"
    assert result["errors"] == []
    assert calls == [("apply", {"enabled": True, "level": 3})]
    assert target.value == 3
    assert get_catalog(state=state)["features"]["thirdparty.demo"]["active"] is True
    patch_set = get_feature_set("thirdparty.demo", state=state)
    assert patch_set is not None and patch_set.name == feature_set_name("thirdparty.demo")
    assert [handle.owner for handle in patch_set.handles] == [patch_set.id]

    report = disable_feature("thirdparty.demo", state=state)
    assert report["status"] == "reverted"
    assert target.value == 0
    assert get_feature_set("thirdparty.demo", state=state) is None


def test_third_party_feature_on_default_state_reaches_module_level_api(state):
    calls = []
    spec, _target = _demo_spec(calls)
    registry = get_feature_registry()
    registry.register(spec)
    try:
        assert get_default_config()["thirdparty"]["demo"]["level"] == 1
        assert normalize_config({})["thirdparty"]["demo"]["enabled"] is False
        assert "thirdparty.demo" in get_catalog()["features"]
        assert services.PatchService().get_default_config()["thirdparty"]["demo"]["level"] == 1
    finally:
        registry.unregister("thirdparty.demo")
    assert "thirdparty" not in get_default_config()


def test_failed_handles_are_surfaced_in_apply_and_enable_reports(state):
    def apply(ctx, section):
        ctx.patch_set.context.wrap("hp_features_missing_module:function", lambda original: original)

    get_feature_registry(state).register(FeatureSpec(key="thirdparty.tolerant", title="T", description="x", defaults={"enabled": False}, apply=apply))

    result = apply_config({"thirdparty": {"tolerant": {"enabled": True}}}, state=state)
    assert "thirdparty.tolerant" in result["applied"]
    assert [error["code"] for error in result["errors"]] == ["patch_failed"]
    assert "hp_features_missing_module" in result["errors"][0]["message"]

    disable_feature("thirdparty.tolerant", state=state)
    report = enable_feature("thirdparty.tolerant", state=state)
    assert report["ok"] is False
    assert report["status"] == "failed"
    assert report["set"]["status"] == "open"
    failed = [handle for handle in report["set"]["handles"] if handle["status"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["error_type"]
    json.dumps(report)


# ---------------------------------------------------------------------------
# 逐功能补丁集与扩展
# ---------------------------------------------------------------------------


def test_disable_uv_pip_restores_subprocess_run(state):
    original_run = subprocess.run

    report = enable_feature("extensions.uv_pip", state=state)
    assert report["ok"] is True
    assert report["status"] == "applied"
    assert subprocess.run is not original_run
    assert is_uv_patch_installed()

    report = disable_feature("extensions.uv_pip", state=state)
    assert report["ok"] is True
    assert report["status"] == "reverted"
    assert report["revert"] == {"status": "reverted"}
    assert subprocess.run is original_run
    assert not is_uv_patch_installed()
    json.dumps(report)


def test_comfyui_auto_port_disable_then_enable_registers_again(state):
    first = enable_feature("extensions.comfyui_auto_port", state=state)
    assert first["status"] == "applied"
    assert is_comfyui_auto_port_patch_registered()
    patch_set = get_feature_set("extensions.comfyui_auto_port", state=state)
    assert patch_set is not None
    assert [handle["target"] for handle in first["set"]["handles"]] == ["comfy.cli_args"]

    # 重复应用复用同一个补丁集, 扩展自身的标记阻止重复注册。
    apply_config({}, state=state)
    apply_config({}, state=state)
    assert get_feature_set("extensions.comfyui_auto_port", state=state) is patch_set
    monkey = monkey_zoo["comfy.cli_args"]
    assert monkey is not None
    assert len(monkey.module_patches) == 1

    report = disable_feature("extensions.comfyui_auto_port", state=state)
    assert report["status"] == "deregistered"
    assert [handle["status"] for handle in report["set"]["handles"]] == ["deregistered"]
    assert not is_comfyui_auto_port_patch_registered()

    second = enable_feature("extensions.comfyui_auto_port", state=state)
    assert second["status"] == "applied"
    assert is_comfyui_auto_port_patch_registered()
    assert get_feature_set("extensions.comfyui_auto_port", state=state) is not patch_set


@pytest.mark.parametrize(
    ("key", "config", "modules"),
    [
        (
            "extensions.extension_index",
            {
                "webui": {"enabled": True, "url": "https://mirror.invalid/index.json"},
                "comfyui_manager": {"enabled": True, "url": "https://mirror.invalid/channel"},
            },
            {"modules.ui_extensions", "manager_core", "manager_server", "manager_util"},
        ),
        ("extensions.hf_endpoint_mirror", {"enabled": True}, {"torch.hub", "torchvision.datasets.utils"}),
    ],
)
def test_unmodified_extension_registrations_are_owned_and_deregistered(state, key, config, modules):
    report = enable_feature(key, config, state=state)

    assert report["ok"] is True, report
    patch_set = get_feature_set(key, state=state)
    assert patch_set is not None and patch_set.name == f"feature:{key}"
    owned = {handle.id: handle for handle in patch_set.handles}
    assert owned
    monkeys = [monkey_zoo[name] for name in modules]
    zoo_handles = [handle for monkey in monkeys if monkey is not None for handle in monkey.handles()]
    assert len([monkey for monkey in monkeys if monkey is not None]) == len(modules)
    assert zoo_handles
    assert all(handle.owner == patch_set.id and handle.id in owned for handle in zoo_handles)

    report = disable_feature(key, state=state)
    assert report["status"] == "deregistered"
    assert {handle["status"] for handle in report["set"]["handles"]} == {"deregistered"}
    assert all(monkey_zoo[name] is None for name in modules)


def test_update_feature_restarts_without_update_hook_and_keeps_state_on_invalid_config(state, fake_webbrowser):
    enable_feature("extensions.uv_pip", state=state)
    patched = subprocess.run

    report = update_feature("extensions.uv_pip", {"symlink": True}, state=state)
    assert report["mode"] == "restart"
    assert report["ok"] is True
    assert report["disable"]["status"] == "reverted"
    assert report["enable"]["status"] == "applied"
    assert subprocess.run is not patched and is_uv_patch_installed()
    restarted = get_feature_set("extensions.uv_pip", state=state)
    assert restarted is not None and restarted.context.config["symlink"] is True

    enable_feature("runtime.browser", {"mode": "suppress"}, state=state)
    invalid = update_feature("runtime.browser", {"mode": "bogus"}, state=state)
    assert invalid["ok"] is False
    assert invalid["errors"][0]["code"] == "invalid_config"
    assert state.browser_patch_mode == "suppress"
    assert get_feature_set("runtime.browser", state=state) is not None

    report = update_feature("extensions.uv_pip", {"enabled": False}, state=state)
    assert report["mode"] == "disable"
    assert not is_uv_patch_installed()


# ---------------------------------------------------------------------------
# reconcile (D5)
# ---------------------------------------------------------------------------


def test_reconcile_is_off_by_default_and_keeps_v1_warnings(state, fake_webbrowser):
    apply_config(
        {"runtime": {"browser": {"enabled": True, "mode": "suppress"}}, "extensions": {"uv_pip": {"enabled": True}}},
        state=state,
    )
    assert is_uv_patch_installed()

    result = apply_config(ALL_DISABLED, state=state)

    assert list(result) == ["applied", "warnings", "errors"]
    assert result["warnings"] == V1_DISABLED_WARNINGS
    assert is_uv_patch_installed()
    assert get_feature_set("extensions.uv_pip", state=state) is not None
    assert state.browser_patch_mode == "passthrough"


@pytest.mark.parametrize("use_config_key", [False, True])
def test_reconcile_disables_previously_applied_features(state, use_config_key, fake_webbrowser):
    module, opened = fake_webbrowser
    original_run = subprocess.run
    apply_config(
        {"runtime": {"browser": {"enabled": True, "mode": "suppress"}}, "extensions": {"uv_pip": {"enabled": True}}},
        state=state,
    )
    assert getattr(module, "open")("http://suppressed") is True

    config = copy.deepcopy(ALL_DISABLED)
    if use_config_key:
        config["services"] = {"reconcile_disabled": True}
        result = apply_config(config, state=state)
    else:
        result = apply_config(config, state=state, reconcile=True)

    reconciled = {report["key"]: report for report in result["reconciled"]}
    assert set(reconciled) == {"core.import_hook", "core.stack_shadow", "runtime.browser", "extensions.comfyui_auto_port", "extensions.uv_pip"}
    assert reconciled["extensions.uv_pip"]["status"] == "reverted"
    assert reconciled["runtime.browser"]["status"] == "reverted"
    assert reconciled["extensions.comfyui_auto_port"]["status"] == "deregistered"
    assert reconciled["core.import_hook"]["status"] == "requires_restart"
    assert subprocess.run is original_run
    assert not is_comfyui_auto_port_patch_registered()
    assert state.browser_patch_registered is False
    assert getattr(module, "open")("http://opened") is False
    assert opened == ["http://opened"]
    assert [warning["feature"] for warning in result["warnings"]] == ["core.import_hook", "core.stack_shadow"]
    json.dumps(result)


def test_explicit_reconcile_false_overrides_config_key(state):
    apply_config({"extensions": {"uv_pip": {"enabled": True}}}, state=state)

    result = apply_config({"services": {"reconcile_disabled": True}}, state=state, reconcile=False)

    assert "reconciled" not in result
    assert is_uv_patch_installed()


# ---------------------------------------------------------------------------
# 运行时功能
# ---------------------------------------------------------------------------


def test_runtime_errors_and_logs_disable_use_uninstall_paths(state):
    sink = FakeSink()

    missing = enable_feature("runtime.errors", state=state)
    assert missing["errors"][0]["code"] == "runtime_client_required"

    report = enable_feature("runtime.errors", runtime_client=sink, state=state)
    assert report["status"] == "applied"
    assert is_error_capture_installed(state=state)
    rejected = update_feature("runtime.errors", {"include_locals": True}, state=state)
    assert rejected["errors"][0]["code"] == "runtime_client_required"
    assert is_error_capture_installed(state=state)
    report = disable_feature("runtime.errors", state=state)
    assert report["status"] == "reverted"
    assert not is_error_capture_installed(state=state)

    report = enable_feature("runtime.logs", {"streams": [], "subprocess": "0", "logging": False}, runtime_client=sink, state=state)
    assert report["status"] == "applied"
    capture = state.log_capture
    assert capture is not None and not capture.closed
    report = disable_feature("runtime.logs", state=state)
    assert report["status"] == "reverted"
    assert state.log_capture is None
    assert capture.closed


def test_runtime_browser_disable_switches_to_passthrough_and_can_reenable(state, fake_webbrowser):
    module, opened = fake_webbrowser

    report = enable_feature("runtime.browser", {"mode": "suppress"}, state=state)
    assert report["status"] == "applied"
    assert [handle["target"] for handle in report["set"]["handles"]] == ["webbrowser:open"]
    assert getattr(module, "open")("http://a") is True

    update = update_feature("runtime.browser", {"mode": "host"}, runtime_client=FakeSink(), state=state)
    assert update["mode"] == "in_place"
    assert state.browser_patch_mode == "host"

    report = disable_feature("runtime.browser", state=state)
    assert report["status"] == "reverted"
    assert report["warnings"] == []
    assert state.browser_patch_registered is False
    assert getattr(module, "open")("http://b") is False
    assert opened == ["http://b"]

    report = enable_feature("runtime.browser", {"mode": "suppress"}, state=state)
    assert report["status"] == "applied"
    assert state.browser_patch_registered is True
    assert getattr(module, "open")("http://c") is True
    assert opened == ["http://b"]


def test_core_feature_disable_reports_requires_restart(state):
    apply_config({}, state=state)

    report = disable_feature("core.import_hook", state=state)

    assert report["status"] == "requires_restart"
    assert report["warnings"] == [V1_DISABLED_WARNINGS[0]]


def test_feature_operations_validate_keys_and_list_features(state):
    assert disable_feature("missing.feature", state=state)["errors"][0]["code"] == "unknown_feature"
    assert enable_feature("services", state=state)["errors"][0]["code"] == "not_applicable"
    assert update_feature("extensions.uv_pip", "bad", state=state)["errors"][0]["code"] == "invalid_config"  # ty: ignore[invalid-argument-type]
    assert disable_feature("extensions.zluda", state=state)["status"] == "not_applied"

    enable_feature("extensions.uv_pip", state=state)
    listing = list_features(state=state)
    json.dumps(listing)
    items = {item["key"]: item for item in listing["features"]}
    assert [item["key"] for item in listing["features"]] == APPLY_ORDER
    assert items["extensions.uv_pip"]["applied"] is True
    assert items["extensions.uv_pip"]["active"] is True
    assert items["extensions.uv_pip"]["builtin"] is True
    assert items["services"]["configurable_only"] is True
    assert items["runtime.browser"]["registered"] is False
    assert items["extensions.zluda"]["set"] is None


def test_xformers_cutlass_disable_then_enable_registers_again(state, monkeypatch):
    from sd_webui_all_in_one_hotpatcher_ext.xformers_cutlass import patches as xformers_patches

    monkeypatch.setattr(xformers_patches, "should_patch_xformers_cutlass", lambda: True)

    def registered():
        monkey = monkey_zoo[xformers_patches.TARGET_MODULE]
        return monkey is not None and len(monkey.module_patches) == 1

    first = enable_feature("extensions.xformers_cutlass", state=state)
    assert first["status"] == "applied"
    assert registered()
    apply_config({}, state=state)
    assert registered()

    report = disable_feature("extensions.xformers_cutlass", state=state)
    assert report["status"] == "deregistered"
    assert monkey_zoo[xformers_patches.TARGET_MODULE] is None

    second = enable_feature("extensions.xformers_cutlass", state=state)
    assert second["status"] == "applied"
    assert registered()


def test_unremovable_effect_reports_requires_restart(state):
    installed = []

    def revert(ctx):
        # 例如 sys.addaudithook 安装的审计 hook 无法移除。
        return "requires_restart"

    get_feature_registry(state).register(
        FeatureSpec(
            key="thirdparty.audit",
            title="Audit",
            description="x",
            defaults={"enabled": False},
            apply=lambda ctx, section: installed.append(section),
            revert=revert,
        )
    )
    enable_feature("thirdparty.audit", state=state)

    report = disable_feature("thirdparty.audit", state=state)

    assert installed
    assert report["status"] == "requires_restart"
    assert report["revert"] == {"status": "requires_restart"}
