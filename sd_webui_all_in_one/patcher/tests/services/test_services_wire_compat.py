"""Hotpatcher services JSON 请求响应结构兼容性测试

冻结 ``handle_request_json`` 对 7 种 ``services.*`` 请求和错误响应的 envelope 结构, 只断言 key 与错误码, 不断言易变的运行时值。
"""

import importlib.util
import json
import sys

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, services, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.services import clear_current_config, get_default_config, handle_request_json
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess

SUCCESS_KEYS = ["ok", "payload"]
ERROR_KEYS = ["error", "ok"]
ERROR_BODY_KEYS = ["code", "message"]
APPLY_RESULT_KEYS = ["applied", "errors", "warnings"]


def _reset(state: HotpatcherState) -> None:
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
    _reset(isolated)
    meta_path_before = list(sys.meta_path)
    spec_from_file_location_before = importlib.util.spec_from_file_location
    yield isolated
    _reset(isolated)
    assert sys.meta_path == meta_path_before
    assert importlib.util.spec_from_file_location is spec_from_file_location_before


def _request(state: HotpatcherState, message_type: str, payload: dict | None = None, *, as_text: bool = False) -> dict:
    request: dict = {"type": message_type, "payload": {} if payload is None else payload}
    response = handle_request_json(json.dumps(request) if as_text else request, state=state)
    # 响应必须可以直接写到 JSONL 通道
    assert json.loads(json.dumps(response)) == response
    return response


def _success_payload(response: dict) -> dict:
    assert sorted(response) == SUCCESS_KEYS
    assert response["ok"] is True
    assert isinstance(response["payload"], dict)
    return response["payload"]


def _error_body(response: dict) -> dict:
    assert sorted(response) == ERROR_KEYS
    assert response["ok"] is False
    assert sorted(response["error"]) == ERROR_BODY_KEYS
    assert isinstance(response["error"]["message"], str)
    return response["error"]


def test_catalog_get_response_shape(state):
    payload = _success_payload(_request(state, "services.catalog.get", as_text=True))

    assert list(payload) == ["catalog"]
    assert list(payload["catalog"]) == ["features", "registered_patches"]
    assert sorted(payload["catalog"]["registered_patches"]) == ["aliases", "modules"]
    for feature in payload["catalog"]["features"].values():
        assert {"title", "description", "settings", "default", "active"} <= set(feature)


def test_defaults_get_response_shape(state):
    payload = _success_payload(_request(state, "services.defaults.get"))

    assert list(payload) == ["config"]
    assert payload["config"] == get_default_config()


def test_config_current_response_shape(state):
    payload = _success_payload(_request(state, "services.config.current"))

    assert list(payload) == ["config"]
    assert payload["config"] == get_default_config()


def test_config_normalize_response_shape(state):
    payload = _success_payload(_request(state, "services.config.normalize", {"config": {"extensions": {"uv_pip": {"enabled": True}}}}))

    assert list(payload) == ["config"]
    assert sorted(payload["config"]) == sorted(get_default_config())
    assert payload["config"]["extensions"]["uv_pip"] == {"enabled": True, "symlink": False}


def test_config_load_response_shape(state, tmp_path):
    config_file = tmp_path / "wire_compat.json"
    config_file.write_text(json.dumps({"core": {"import_hook": {"enabled": False}}}), encoding="utf-8")

    payload = _success_payload(_request(state, "services.config.load", {"path": str(config_file), "write_back": False}))

    assert list(payload) == ["config"]
    assert payload["config"]["core"]["import_hook"] == {"enabled": False}
    assert json.loads(config_file.read_text(encoding="utf-8")) == {"core": {"import_hook": {"enabled": False}}}


def test_config_save_response_shape(state, tmp_path):
    config_file = tmp_path / "nested" / "wire_compat.json"

    payload = _success_payload(_request(state, "services.config.save", {"path": str(config_file), "config": {"services": {"apply_on_bootstrap": False}}}))

    assert list(payload) == ["config"]
    assert payload["config"]["services"] == {**get_default_config()["services"], "apply_on_bootstrap": False}
    assert json.loads(config_file.read_text(encoding="utf-8")) == payload["config"]


def test_config_apply_response_shape(state):
    config = {"runtime": {"errors": {"enabled": True}}}

    payload = _success_payload(_request(state, "services.config.apply", {"config": config}))

    assert list(payload) == ["result"]
    result = payload["result"]
    assert sorted(result) == APPLY_RESULT_KEYS
    assert all(isinstance(result[key], list) for key in APPLY_RESULT_KEYS)
    assert result["applied"][:2] == ["core.import_hook", "core.stack_shadow"]
    assert all(isinstance(feature, str) for feature in result["applied"])
    assert result["errors"] == []
    assert result["warnings"] == [{"feature": "runtime.errors", "message": "runtime_client is required to enable errors"}]


def test_config_apply_error_entry_shape(state, monkeypatch):
    def broken_install_import_hook(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(services, "install_import_hook", broken_install_import_hook)

    payload = _success_payload(_request(state, "services.config.apply", {"config": {}}))

    assert payload["result"]["errors"] == [{"feature": "core.import_hook", "code": "RuntimeError", "message": "boom"}]
    assert "core.import_hook" not in payload["result"]["applied"]


def test_unknown_request_error_envelope(state):
    error = _error_body(_request(state, "services.unknown"))

    assert error == {"code": "unknown_request", "message": "unknown services request: services.unknown"}


def test_non_object_payload_error_envelope(state):
    response = handle_request_json({"type": "services.defaults.get", "payload": []}, state=state)

    assert _error_body(response) == {"code": "invalid_request", "message": "payload must be an object"}


def test_invalid_json_error_envelope(state):
    response = handle_request_json("{not json", state=state)

    assert _error_body(response)["code"] == "invalid_json"


@pytest.mark.parametrize(
    "raw",
    [
        [],
        {"payload": {}},
        {"type": "services.config.load", "payload": {}},
        {"type": "services.config.normalize", "payload": {"config": []}},
    ],
)
def test_request_failed_error_envelope(state, raw):
    response = handle_request_json(raw, state=state)

    assert _error_body(response)["code"] == "request_failed"
