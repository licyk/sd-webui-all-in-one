"""API v2 方法反射注册与参数转换测试"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from sd_webui_all_in_one.api_server import ApiMethodSpec, create_api_server
from sd_webui_all_in_one.api_server import server as api_server_module
from sd_webui_all_in_one.api_server.registry import get_default_methods
from sd_webui_all_in_one.base_manager.base import mirrors as base_mirrors
from tests.api_server.helpers import api_request, api_request_error, start_server, stop_server


def test_default_registry_uses_namespaced_real_callables():
    methods = get_default_methods()
    assert "version.branches" not in methods
    assert "webui.check_updates" not in methods
    assert "comfyui.version.branches" in methods
    assert "sd_webui.version.branches" in methods
    assert "comfyui.extension.list" in methods
    assert "comfyui.extension.branches" in methods
    assert "comfyui.extension.commits" in methods
    assert "sd_webui.extension.list" in methods
    assert "sd_webui.version.branch_presets" in methods
    assert all(
        f"{webui_type}.environment.collect" in methods
        for webui_type in ("sd_webui", "comfyui", "fooocus", "invokeai", "sd_trainer", "sd_scripts", "qwen_tts_webui", "rvc_next_webui", "mizuoto_tts_webui")
    )
    assert "fooocus.version.branch_presets" in methods
    assert "sd_trainer.version.branch_presets" in methods
    assert "invokeai.model.list" in methods
    assert "system.proxy.get" in methods
    assert "environment.managed_env_vars" in methods
    assert "mirror.resolve" in methods
    assert "hotpatcher.catalog" in methods
    assert "hotpatcher.default_config" in methods
    assert "hotpatcher.normalize_config" in methods
    assert "hotpatcher.apply_config" in methods
    assert "hotpatcher.runtime_status" not in methods
    assert "hotpatcher.runtime_start" not in methods
    assert "hotpatcher.runtime_apply_remote" not in methods
    assert "comfyui.pytorch.reinstall" not in methods
    assert "comfyui.model.install_library" not in methods
    assert "comfyui.pytorch.resolve_selection" not in methods
    assert "comfyui.model.resolve_library_install" not in methods
    assert all("adapters.webui" not in getattr(spec, "handler", spec).__module__ for spec in methods.values())

    server = create_api_server(port=0)
    try:
        for method_name, target_name in {
            "hotpatcher.catalog": "hotpatcher_manager.config.get_hotpatcher_catalog",
            "hotpatcher.default_config": "hotpatcher_manager.config.get_hotpatcher_default_config",
            "hotpatcher.normalize_config": "hotpatcher_manager.config.normalize_hotpatcher_config",
            "hotpatcher.apply_config": "hotpatcher_manager.config.apply_hotpatcher_config",
        }.items():
            hotpatcher_details = server.method_details(method_name)
            assert hotpatcher_details is not None
            assert hotpatcher_details["target"].endswith(target_name)

        details = server.method_details("comfyui.version.branches")
        assert details is not None
        assert details["target"].endswith("version_manager.repository.list_branches")
        assert details["params_schema"]["required"] == ["path"]
        parameters = {item["name"]: item for item in details["parameters"]}
        assert parameters["path"]["type"] == "string"
        assert parameters["path"]["schema"]["format"] == "path"
        assert parameters["fetch"]["type"] == "boolean"
        assert parameters["fetch"]["default"] is True
        pytorch_details = server.method_details("comfyui.pytorch.catalog")
        assert pytorch_details is not None
        assert pytorch_details["target"].endswith("library_catalog.pytorch_catalog")
        assert pytorch_details["parameters"] == []
        model_library_details = server.method_details("comfyui.model.library")
        assert model_library_details is not None
        assert model_library_details["target"].endswith("library_catalog.model_library_catalog")
        extension_details = server.method_details("comfyui.extension.install_index_item")
        assert extension_details is not None
        assert extension_details["target"].endswith("comfyui_base.extensions.index.install_comfyui_extension_index_item")
        extension_parameters = {item["name"]: item for item in extension_details["parameters"]}
        item_schema = extension_parameters["item"]["schema"]
        assert item_schema["required"] == ["name", "url"]
        assert item_schema["additionalProperties"] is False
        snapshot_details = server.method_details("comfyui.snapshot.create")
        assert snapshot_details is not None
        assert snapshot_details["target"].endswith("snapshot.storage.create_webui_snapshot")
        assert [item["name"] for item in snapshot_details["parameters"]] == [
            "webui_path",
            "include_packages",
            "snapshot_dir",
        ]
        environment_details = server.method_details("comfyui.environment.collect")
        assert environment_details is not None
        assert environment_details["target"].endswith("comfyui_base.reporting.get_comfyui_environment_info")
        assert [item["name"] for item in environment_details["parameters"]] == ["comfyui_path", "include_packages"]
        update_details = server.method_details("comfyui.extension.update")
        assert update_details is not None
        assert update_details["target"].endswith("version_manager.repository.update_repository")
        restore_details = server.method_details("comfyui.snapshot.restore")
        assert restore_details is not None
        assert restore_details["target"].endswith("snapshot_restore.service.restore_webui_snapshot")
        assert {item["name"] for item in restore_details["parameters"]} == {"snapshot_path", "webui_path", "options"}
        model_details = server.method_details("comfyui.model.copy")
        assert model_details is not None
        assert model_details["target"].endswith("model_manager.files.FileModelManager.copy_entry")
        assert [item["name"] for item in model_details["parameters"]] == [
            "webui_path",
            "source_relative_path",
            "target_dir_relative_path",
            "new_name",
            "overwrite",
        ]
        rename_details = server.method_details("comfyui.model.rename")
        assert rename_details is not None
        assert rename_details["target"].endswith("model_manager.files.FileModelManager.rename_entry")
        assert [item["name"] for item in rename_details["parameters"]] == [
            "webui_path",
            "source_relative_path",
            "new_name",
            "overwrite",
        ]
    finally:
        server.server_close()


@dataclass
class DemoOptions:
    enabled: bool = True
    labels: list[str] | None = None


def _configure(
    name: str,
    limit: int = 10,
    target: str | None = None,
    mode: Literal["safe", "fast"] = "safe",
    options: DemoOptions = DemoOptions(),
) -> dict[str, object]:
    """配置演示方法。

    Args:
        name (str): 配置名称。
        limit (int): 最大数量。
        target (str | None): 可选目标。
        mode (Literal): 执行模式。
        options (DemoOptions): 嵌套选项。
    """
    return {"name": name, "limit": limit, "target": target, "mode": mode, "options": options}


def test_method_details_are_generated_from_real_signature():
    server, thread, base_url = start_server(methods={"demo.configure": _configure})
    try:
        status, payload = api_request(f"{base_url}/api/v2/methods/demo.configure")
        assert status == 200
        details = payload["result"]
        assert details["target"].endswith("._configure")
        assert details["description"] == "配置演示方法。"
        parameters = {item["name"]: item for item in details["parameters"]}
        assert parameters["name"]["required"] is True
        assert parameters["name"]["description"] == "配置名称。"
        assert parameters["limit"]["type"] == "integer"
        assert parameters["limit"]["default"] == 10
        assert parameters["target"]["type"] == ["string", "null"]
        assert parameters["target"]["default"] is None
        assert parameters["mode"]["schema"]["enum"] == ["safe", "fast"]
        option_schema = parameters["options"]["schema"]
        assert option_schema["properties"]["enabled"]["default"] is True
        assert option_schema["properties"]["labels"]["anyOf"] == [
            {"type": "array", "items": {"type": "string"}},
            {"type": "null"},
        ]
    finally:
        stop_server(server, thread)


def test_managed_env_vars_method_returns_grouped_environment(tmp_path):
    methods = get_default_methods()
    server, thread, base_url = start_server(methods={"environment.managed_env_vars": methods["environment.managed_env_vars"]})
    try:
        status, payload = api_request(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": "environment.managed_env_vars", "params": {"cache_path": tmp_path.as_posix()}},
        )
        assert status == 200
        result = payload["result"]
        assert set(result) == {"defaults", "overrides"}
        assert result["defaults"]["HF_HOME"] == (tmp_path / "huggingface").as_posix()
        assert result["overrides"]["PIP_TIMEOUT"] == "30"
        assert "UV_PYTHON" not in result["overrides"]
    finally:
        stop_server(server, thread)


def test_real_callable_is_invoked_with_converted_flat_parameters():
    server, thread, base_url = start_server(methods={"demo.configure": _configure})
    try:
        status, payload = api_request(
            f"{base_url}/api/v2/call",
            method="POST",
            data={
                "method": "demo.configure",
                "params": {
                    "name": "demo",
                    "target": None,
                    "mode": "fast",
                    "options": {"enabled": False, "labels": ["one"]},
                },
            },
        )
        assert status == 200
        assert payload["result"] == {
            "name": "demo",
            "limit": 10,
            "target": None,
            "mode": "fast",
            "options": {"enabled": False, "labels": ["one"]},
        }
    finally:
        stop_server(server, thread)


def test_mirror_resolve_method_is_invoked(monkeypatch):
    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: False)
    server, thread, base_url = start_server(methods=get_default_methods())
    try:
        status, payload = api_request(
            f"{base_url}/api/v2/call",
            method="POST",
            data={
                "method": "mirror.resolve",
                "params": {
                    "auto_mirror": True,
                    "use_pypi_mirror": False,
                    "use_github_mirror": False,
                    "custom_github_mirror": "https://github.example",
                    "use_hf_mirror": False,
                    "custom_hf_mirror": None,
                    "model_download_resource_type": "huggingface",
                },
            },
        )
        assert status == 200
        assert payload["result"] == {
            "use_pypi_mirror": True,
            "use_github_mirror": True,
            "custom_github_mirror": None,
            "use_hf_mirror": True,
            "custom_hf_mirror": None,
            "model_download_resource_type": "modelscope",
        }
    finally:
        stop_server(server, thread)


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({}, "Missing required parameter: name"),
        ({"name": "demo", "limit": True}, "must be an integer"),
        ({"name": "demo", "mode": "turbo"}, "must be one of"),
        ({"name": "demo", "unknown": 1}, "Unexpected parameter"),
        ({"name": "demo", "options": {"unknown": True}}, "Unexpected field"),
    ],
)
def test_invalid_parameters_are_rejected_before_task_creation(params, message):
    server, thread, base_url = start_server(methods={"demo.configure": _configure})
    try:
        status, payload = api_request_error(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": "demo.configure", "params": params},
        )
        assert status == 400
        assert payload["error"]["code"] == "invalid_request"
        assert message in payload["error"]["message"]
        assert server.task_manager.snapshots() == []
    finally:
        stop_server(server, thread)


def test_bound_arguments_are_hidden_and_passed_to_target():
    calls = []

    def inspect_variant(webui_type: str, webui_path: Path, limit: int = 100) -> dict[str, object]:
        calls.append((webui_type, webui_path, limit))
        return {"type": webui_type, "path": webui_path, "limit": limit}

    method_name = "comfyui.demo.inspect"
    spec = ApiMethodSpec(handler=inspect_variant, bound_arguments={"webui_type": "comfyui"})
    server, thread, base_url = start_server(methods={method_name: spec})
    try:
        details = server.method_details(method_name)
        assert details is not None
        assert [item["name"] for item in details["parameters"]] == ["webui_path", "limit"]
        _, payload = api_request(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": method_name, "params": {"webui_path": "/tmp/demo", "limit": 5}},
        )
        assert payload["result"] == {"type": "comfyui", "path": "/tmp/demo", "limit": 5}
        assert calls == [("comfyui", Path("/tmp/demo"), 5)]
    finally:
        stop_server(server, thread)


def test_invalid_method_registration_is_rejected_before_listener_creation(monkeypatch):
    monkeypatch.setattr(api_server_module.ThreadingHTTPServer, "server_bind", lambda self: None)
    monkeypatch.setattr(api_server_module.ThreadingHTTPServer, "server_activate", lambda self: None)
    with pytest.raises(ValueError, match="Invalid API method name"):
        create_api_server(port=0, methods={"bad-name": lambda value: value}, include_default_methods=False)


def test_missing_annotations_are_rejected():
    def untyped(value):
        return value

    with pytest.raises(TypeError, match="must have a type annotation"):
        create_api_server(port=0, methods={"demo.untyped": untyped}, include_default_methods=False)
