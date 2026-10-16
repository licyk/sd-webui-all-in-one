"""Hotpatcher 服务配置, 目录与请求处理测试"""

import json

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.services import (
    apply_config,
    clear_current_config,
    get_catalog,
    get_current_config,
    get_default_config,
    handle_request_json,
    load_config_file,
    normalize_config,
)
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess


@pytest.fixture(autouse=True)
def clean_service_state():
    clear_current_config()
    uninstall_error_capture()
    uninstall_log_capture()
    uninstall_import_hook()
    uninstall_stack_shadower()
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()
    yield
    clear_current_config()
    uninstall_error_capture()
    uninstall_log_capture()
    uninstall_import_hook()
    uninstall_stack_shadower()
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()


def test_default_config_is_json_serializable_and_contains_features():
    defaults = get_default_config()

    assert json.loads(json.dumps(defaults)) == defaults
    assert "import_hook" in defaults["core"]
    assert "stack_shadow" in defaults["core"]
    assert "errors" in defaults["runtime"]
    assert "logs" in defaults["runtime"]
    assert defaults["runtime"]["errors"]["enabled"] is False
    assert defaults["runtime"]["errors"]["sys_excepthook"] is True
    assert defaults["runtime"]["errors"]["threading_excepthook"] is True
    assert defaults["runtime"]["errors"]["unraisablehook"] is True
    assert defaults["runtime"]["errors"]["asyncio"] is True
    assert defaults["runtime"]["errors"]["include_locals"] is False
    assert defaults["runtime"]["errors"]["caught_exceptions"]["enabled"] is False
    assert defaults["runtime"]["errors"]["caught_exceptions"]["threading"] is True
    assert defaults["runtime"]["errors"]["caught_exceptions"]["module_prefixes"] == []
    assert defaults["runtime"]["errors"]["caught_exceptions"]["exclude_module_prefixes"] == [
        "sd_webui_all_in_one_hotpatcher",
        "sd_webui_all_in_one_hotpatcher_ext",
    ]
    assert defaults["runtime"]["errors"]["caught_exceptions"]["max_events_per_second"] == 20
    assert defaults["runtime"]["logs"]["hook_policy"] == "cooperative"
    assert defaults["runtime"]["logs"]["hook_check_interval"] == 1
    assert defaults["runtime"]["logs"]["fd_capture"] == "0"
    assert {"zluda", "extension_index", "hf_endpoint_mirror", "xformers_cutlass", "uv_pip"} <= set(defaults["extensions"])
    assert defaults["extensions"]["extension_index"]["webui"]["enabled"] is False
    assert defaults["extensions"]["extension_index"]["webui"]["url"] == "auto"
    assert defaults["extensions"]["extension_index"]["comfyui_manager"]["enabled"] is False
    assert defaults["extensions"]["extension_index"]["comfyui_manager"]["url"] == "auto"
    assert defaults["extensions"]["xformers_cutlass"]["enabled"] is True
    assert defaults["extensions"]["uv_pip"]["enabled"] is False
    assert defaults["runtime"]["browser"] == {"enabled": False, "mode": "host"}


def test_normalize_config_deep_merges_without_overwriting_user_values():
    normalized = normalize_config(
        {
            "runtime": {
                "logs": {
                    "enabled": True,
                    "streams": "stdout",
                }
            }
        }
    )

    assert normalized["runtime"]["logs"]["enabled"] is True
    assert normalized["runtime"]["logs"]["streams"] == "stdout"
    assert normalized["runtime"]["logs"]["policy"] == "bounded"
    assert normalized["runtime"]["errors"]["enabled"] is False
    assert normalized["runtime"]["errors"]["caught_exceptions"]["enabled"] is False
    assert normalized["runtime"]["browser"] == {"enabled": False, "mode": "host"}
    assert normalized["extensions"]["zluda"]["enabled"] is False


def test_browser_config_rejects_unknown_modes_and_non_boolean_enablement():
    with pytest.raises(ValueError, match="runtime.browser.mode"):
        normalize_config({"runtime": {"browser": {"mode": "external"}}})
    with pytest.raises(ValueError, match="runtime.browser.enabled"):
        normalize_config({"runtime": {"browser": {"enabled": "yes"}}})


def test_current_config_defaults_and_updates_after_apply():
    current = get_current_config()
    assert current == get_default_config()

    result = apply_config(
        {
            "runtime": {
                "errors": {
                    "enabled": False,
                    "asyncio": False,
                }
            },
            "extensions": {
                "extension_index": {
                    "webui": {
                        "enabled": True,
                        "url": "auto",
                    }
                }
            },
        }
    )

    assert result["errors"] == []
    current = get_current_config()
    assert current["runtime"]["errors"]["asyncio"] is False
    assert current["extensions"]["extension_index"]["webui"]["enabled"] is True
    assert current["extensions"]["extension_index"]["webui"]["url"] == "auto"


def test_load_config_file_writes_missing_defaults(tmp_path):
    config_file = tmp_path / "hotpatcher.json"
    config_file.write_text(json.dumps({"extensions": {"hf_endpoint_mirror": {"enabled": True}}}), encoding="utf-8")

    loaded = load_config_file(config_file, write_back=True)
    written = json.loads(config_file.read_text(encoding="utf-8"))

    assert loaded["extensions"]["hf_endpoint_mirror"]["enabled"] is True
    assert written["extensions"]["hf_endpoint_mirror"]["enabled"] is True
    assert "zluda" in written["extensions"]
    assert "xformers_cutlass" in written["extensions"]
    assert "uv_pip" in written["extensions"]
    assert "core" in written


def test_load_config_file_rejects_non_object(tmp_path):
    config_file = tmp_path / "bad.json"
    config_file.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="object"):
        load_config_file(config_file)


def test_catalog_reports_registered_patches():
    with monkey_zoo("svc_target") as monkey:
        monkey.patch_module(lambda module: None)

    catalog = get_catalog()
    features = catalog["features"]

    assert "services" in features
    assert "core.import_hook" in features
    assert catalog["registered_patches"]["modules"]["svc_target"]["module"] == 1
    for feature in features.values():
        assert feature["title"]
        assert feature["description"]
        assert "default" in feature
        assert "active" in feature
        for setting in feature["settings"].values():
            assert setting["type"]
            assert setting["title"]
            assert setting["description"]
            assert "default" in setting

    error_settings = features["runtime.errors"]["settings"]
    assert error_settings["enabled"]["type"] == "bool"
    assert error_settings["enabled"]["default"] is False
    assert error_settings["sys_excepthook"]["default"] is True
    assert error_settings["threading_excepthook"]["default"] is True
    assert error_settings["unraisablehook"]["default"] is True
    assert error_settings["asyncio"]["default"] is True
    assert error_settings["include_locals"]["default"] is False
    assert error_settings["caught_exceptions.enabled"]["default"] is False
    assert error_settings["caught_exceptions.threading"]["default"] is True
    assert error_settings["caught_exceptions.module_prefixes"]["default"] == []
    assert error_settings["caught_exceptions.exclude_module_prefixes"]["default"] == [
        "sd_webui_all_in_one_hotpatcher",
        "sd_webui_all_in_one_hotpatcher_ext",
    ]
    assert error_settings["caught_exceptions.max_events_per_second"]["default"] == 20
    subprocess_setting = features["runtime.logs"]["settings"]["subprocess"]
    assert subprocess_setting["type"] == "choice"
    assert subprocess_setting["choices"] == ["0", "safe", "force"]
    assert subprocess_setting["default"] == "safe"
    hook_policy_setting = features["runtime.logs"]["settings"]["hook_policy"]
    assert hook_policy_setting["type"] == "choice"
    assert hook_policy_setting["choices"] == ["cooperative", "warn", "reapply"]
    assert hook_policy_setting["default"] == "cooperative"
    fd_capture_setting = features["runtime.logs"]["settings"]["fd_capture"]
    assert fd_capture_setting["type"] == "choice"
    assert fd_capture_setting["choices"] == ["0", "fallback", "force"]
    assert fd_capture_setting["default"] == "0"
    browser_feature = features["runtime.browser"]
    assert browser_feature["settings"]["enabled"]["default"] is False
    assert browser_feature["settings"]["mode"]["choices"] == ["host", "suppress", "passthrough"]
    assert browser_feature["registered"] is False
    extension_index_settings = features["extensions.extension_index"]["settings"]
    comfyui_auto_port_settings = features["extensions.comfyui_auto_port"]["settings"]
    assert comfyui_auto_port_settings["enabled"]["type"] == "bool"
    assert comfyui_auto_port_settings["enabled"]["default"] is True
    assert extension_index_settings["webui.enabled"]["type"] == "bool"
    assert extension_index_settings["webui.enabled"]["default"] is False
    assert extension_index_settings["webui.url"]["type"] == "str"
    assert extension_index_settings["webui.url"]["default"] == "auto"
    assert extension_index_settings["comfyui_manager.enabled"]["type"] == "bool"
    assert extension_index_settings["comfyui_manager.enabled"]["default"] is False
    assert extension_index_settings["comfyui_manager.url"]["type"] == "str"
    assert extension_index_settings["comfyui_manager.url"]["default"] == "auto"
    xformers_cutlass_settings = features["extensions.xformers_cutlass"]["settings"]
    assert xformers_cutlass_settings["enabled"]["type"] == "bool"
    assert xformers_cutlass_settings["enabled"]["default"] is True


def test_handle_request_json_supports_services_requests(tmp_path):
    config_file = tmp_path / "service.json"
    config_file.write_text(json.dumps({"core": {"import_hook": {"enabled": True}}}), encoding="utf-8")

    defaults = handle_request_json({"type": "services.defaults.get", "payload": {}})
    current = handle_request_json({"type": "services.config.current", "payload": {}})
    normalized = handle_request_json(
        {
            "type": "services.config.normalize",
            "payload": {"config": {"extensions": {"hf_endpoint_mirror": {"enabled": True}}}},
        }
    )
    loaded = handle_request_json(
        {
            "type": "services.config.load",
            "payload": {"path": str(config_file), "write_back": False},
        }
    )
    unknown = handle_request_json({"type": "services.unknown", "payload": {}})

    assert defaults["ok"] is True
    assert current["ok"] is True
    assert current["payload"]["config"] == get_default_config()
    assert normalized["payload"]["config"]["extensions"]["hf_endpoint_mirror"]["enabled"] is True
    assert loaded["payload"]["config"]["core"]["import_hook"]["enabled"] is True
    assert unknown["ok"] is False
    assert unknown["error"]["code"] == "unknown_request"


def test_handle_request_json_current_returns_last_applied_config():
    applied = handle_request_json(
        {
            "type": "services.config.apply",
            "payload": {
                "config": {
                    "runtime": {
                        "errors": {
                            "enabled": False,
                            "sys_excepthook": False,
                        }
                    }
                }
            },
        }
    )
    current = handle_request_json({"type": "services.config.current", "payload": {}})

    assert applied["ok"] is True
    assert current["ok"] is True
    assert current["payload"]["config"]["runtime"]["errors"]["sys_excepthook"] is False
    assert current["payload"]["config"]["runtime"]["logs"]["enabled"] is False
