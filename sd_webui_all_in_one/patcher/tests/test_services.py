import json
import socket
import threading

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env
from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message
from sd_webui_all_in_one_hotpatcher.services import (
    apply_config,
    clear_current_config,
    get_catalog,
    get_current_config,
    get_default_config,
    handle_request_json,
    install_service_control_channel,
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


class ServicesHost:
    def __init__(self):
        self.messages = []
        self.responses = []
        self.response_ready = threading.Event()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self.host, self.port = self._sock.getsockname()
        self._sock.listen()

    def __enter__(self):
        self._thread.start()
        self._ready.wait(timeout=2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop.set()
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                pass
        except Exception:
            pass
        self._thread.join(timeout=2)
        self._sock.close()

    def _run(self):
        self._ready.set()
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        with conn:
            file = conn.makefile("rb")
            first_line = file.readline()
            if not first_line:
                return
            first_message = json.loads(first_line.decode("utf-8"))
            self.messages.append(first_message)
            if first_message.get("type") != "channel.open":
                return
            conn.sendall(
                encode_message(
                    {
                        "id": "svc-1",
                        "type": "services.defaults.get",
                        "payload": {},
                    }
                )
            )
            response_line = file.readline()
            if not response_line:
                return
            self.responses.append(json.loads(response_line.decode("utf-8")))
            self.response_ready.set()


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
    assert defaults["runtime"]["logs"]["hook_policy"] == "cooperative"
    assert defaults["runtime"]["logs"]["hook_check_interval"] == 1
    assert defaults["runtime"]["logs"]["fd_capture"] == "0"
    assert {"zluda", "extension_index", "hf_endpoint_mirror", "uv_pip"} <= set(defaults["extensions"])
    assert defaults["extensions"]["extension_index"]["webui"]["enabled"] is False
    assert defaults["extensions"]["extension_index"]["webui"]["url"] == "auto"
    assert defaults["extensions"]["extension_index"]["comfyui_manager"]["enabled"] is False
    assert defaults["extensions"]["extension_index"]["comfyui_manager"]["url"] == "auto"
    assert defaults["extensions"]["uv_pip"]["enabled"] is False


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
    assert normalized["extensions"]["zluda"]["enabled"] is False


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
    assert "uv_pip" in written["extensions"]
    assert "core" in written


def test_load_config_file_rejects_non_object(tmp_path):
    config_file = tmp_path / "bad.json"
    config_file.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="object"):
        load_config_file(config_file)


def test_apply_config_enables_core_and_extension_patches(monkeypatch):
    calls = []

    def fake_zluda(config):
        calls.append(("zluda", config["compat"]))

    def fake_extension_index(config):
        calls.append(("extension_index", config["comfyui_manager"]["enabled"]))

    def fake_hf_endpoint(config):
        calls.append(("hf_endpoint_mirror", config["enabled"]))

    def fake_uv_pip(config):
        calls.append(("uv_pip", config["symlink"]))

    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.zluda.apply_from_config", fake_zluda)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.extension_index.apply_from_config", fake_extension_index)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror.apply_from_config", fake_hf_endpoint)
    monkeypatch.setattr("sd_webui_all_in_one_hotpatcher_ext.uv_pip.apply_from_config", fake_uv_pip)

    result = apply_config(
        {
            "core": {
                "import_hook": {"enabled": True},
                "stack_shadow": {"enabled": True, "prefixes": "svc_hidden"},
            },
            "extensions": {
                "zluda": {"enabled": True, "compat": True},
                "extension_index": {"comfyui_manager": {"enabled": True}},
                "hf_endpoint_mirror": {"enabled": True},
                "uv_pip": {"enabled": True, "symlink": True},
            },
        }
    )

    assert "core.import_hook" in result["applied"]
    assert "core.stack_shadow" in result["applied"]
    assert ("zluda", True) in calls
    assert ("extension_index", True) in calls
    assert ("hf_endpoint_mirror", True) in calls
    assert ("uv_pip", True) in calls
    assert result["errors"] == []


def test_apply_config_warns_when_logs_enabled_without_runtime_client():
    result = apply_config({"runtime": {"logs": {"enabled": True}}})

    assert result["warnings"] == [
        {
            "feature": "runtime.logs",
            "message": "runtime_client is required to enable logs",
        }
    ]


def test_apply_config_warns_when_errors_enabled_without_runtime_client():
    result = apply_config({"runtime": {"errors": {"enabled": True}}})

    assert result["warnings"] == [
        {
            "feature": "runtime.errors",
            "message": "runtime_client is required to enable errors",
        }
    ]


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
    extension_index_settings = features["extensions.extension_index"]["settings"]
    assert extension_index_settings["webui.enabled"]["type"] == "bool"
    assert extension_index_settings["webui.enabled"]["default"] is False
    assert extension_index_settings["webui.url"]["type"] == "str"
    assert extension_index_settings["webui.url"]["default"] == "auto"
    assert extension_index_settings["comfyui_manager.enabled"]["type"] == "bool"
    assert extension_index_settings["comfyui_manager.enabled"]["default"] is False
    assert extension_index_settings["comfyui_manager.url"]["type"] == "str"
    assert extension_index_settings["comfyui_manager.url"]["default"] == "auto"


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


def test_service_control_channel_handles_host_request():
    with ServicesHost() as host:
        with RuntimeClient.connect(host.host, host.port, token="svc-token") as client:
            channel = install_service_control_channel(client)
            assert host.response_ready.wait(timeout=2)
            channel.close()

        assert any(message.get("type") == "channel.open" and message.get("channel") == "services" for message in host.messages)
        response = host.responses[0]
        assert response["id"] == "svc-1"
        assert response["ok"] is True
        assert "config" in response["payload"]


def test_bootstrap_applies_services_config_and_opens_control_channel(monkeypatch):
    with ServicesHost() as host:
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME", "1")
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST", host.host)
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT", str(host.port))
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
        monkeypatch.setenv(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
            '{"services":{"apply_on_bootstrap":true},"core":{"import_hook":{"enabled":true}}}',
        )
        monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES", "1")

        state = configure_from_env()
        try:
            assert state.service_apply_result is not None
            assert "core.import_hook" in state.service_apply_result["applied"]
            assert state.service_control_channel is not None
            assert host.response_ready.wait(timeout=2)
        finally:
            if state.service_control_channel is not None:
                state.service_control_channel.close()
            if state.runtime_client is not None:
                state.runtime_client.close()


def test_bootstrap_records_loaded_config_without_apply(monkeypatch):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "env")
    monkeypatch.setenv(
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON",
        '{"services":{"apply_on_bootstrap":false},"runtime":{"errors":{"enabled":false,"asyncio":false}}}',
    )

    state = configure_from_env()
    current = handle_request_json({"type": "services.config.current", "payload": {}})

    assert state.service_apply_result is None
    assert current["ok"] is True
    assert current["payload"]["config"]["services"]["apply_on_bootstrap"] is False
    assert current["payload"]["config"]["runtime"]["errors"]["asyncio"] is False
