"""API v2 反射注册、调用和任务协议测试。"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from sd_webui_all_in_one.api_server import ApiClient, ApiClientError, ApiMethodSpec, ApiTaskContext, create_api_server
from sd_webui_all_in_one.api_server import server as api_server_module
from sd_webui_all_in_one.api_server.registry import get_default_methods
from sd_webui_all_in_one.api_server.server import ApiTaskCanceled


def _request(url, method="GET", data=None, token=""):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _request_raw(url, method="GET", data=None, token=""):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, dict(response.headers), response.read()


def _request_error(url, method="GET", data=None, token=""):
    try:
        _request(url, method=method, data=data, token=token)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    raise AssertionError("request unexpectedly succeeded")


def _request_error_raw(url, method="GET", data=None, token=""):
    try:
        _request_raw(url, method=method, data=data, token=token)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    raise AssertionError("request unexpectedly succeeded")


def _start_server(**kwargs):
    server = create_api_server(port=0, include_default_methods=False, **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_address[1]}"


def _stop_server(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _wait_for_task(base_url, task_id, status):
    deadline = time.time() + 5
    while time.time() < deadline:
        _, payload = _request(f"{base_url}/api/v2/tasks/{task_id}")
        task = payload["result"]
        if task["status"] == status:
            return task
        time.sleep(0.02)
    raise AssertionError(f"task did not reach {status}")


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
    assert "fooocus.version.branch_presets" in methods
    assert "sd_trainer.version.branch_presets" in methods
    assert "invokeai.model.list" in methods
    assert "system.proxy.get" in methods

    server = create_api_server(port=0)
    try:
        details = server.method_details("comfyui.version.branches")
        assert details is not None
        assert details["target"].endswith("version_manager.list_branches")
        assert details["params_schema"]["required"] == ["path"]
        parameters = {item["name"]: item for item in details["parameters"]}
        assert parameters["path"]["type"] == "string"
        assert parameters["path"]["schema"]["format"] == "path"
        assert parameters["fetch"]["type"] == "boolean"
        assert parameters["fetch"]["default"] is True
        pytorch_details = server.method_details("comfyui.pytorch.catalog")
        assert pytorch_details is not None
        assert pytorch_details["parameters"] == []
        extension_details = server.method_details("comfyui.extension.install_index_item")
        assert extension_details is not None
        extension_parameters = {item["name"]: item for item in extension_details["parameters"]}
        item_schema = extension_parameters["item"]["schema"]
        assert item_schema["required"] == ["name", "url"]
        assert item_schema["additionalProperties"] is False
        update_details = server.method_details("comfyui.extension.update")
        assert update_details is not None
        assert update_details["target"].endswith("version_manager.update_repository")
        restore_details = server.method_details("comfyui.snapshot.restore")
        assert restore_details is not None
        assert restore_details["target"].endswith("snapshot_restore.restore_webui_snapshot")
        assert {item["name"] for item in restore_details["parameters"]} == {"snapshot_path", "webui_path", "options"}
        model_details = server.method_details("comfyui.model.copy")
        assert model_details is not None
        assert model_details["target"].endswith("model_manager.FileModelManager.copy_entry")
        assert [item["name"] for item in model_details["parameters"]] == [
            "webui_path",
            "source_relative_path",
            "target_dir_relative_path",
            "new_name",
            "overwrite",
        ]
    finally:
        server.server_close()


def test_v1_routes_are_removed():
    server, thread, base_url = _start_server()
    try:
        status, payload = _request_error(f"{base_url}/api/v1/methods")
        assert status == 404
        assert payload["error"]["code"] == "not_found"
    finally:
        _stop_server(server, thread)


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
    server, thread, base_url = _start_server(methods={"demo.configure": _configure})
    try:
        status, payload = _request(f"{base_url}/api/v2/methods/demo.configure")
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
        _stop_server(server, thread)


def test_real_callable_is_invoked_with_converted_flat_parameters():
    server, thread, base_url = _start_server(methods={"demo.configure": _configure})
    try:
        status, payload = _request(
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
        _stop_server(server, thread)


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
    server, thread, base_url = _start_server(methods={"demo.configure": _configure})
    try:
        status, payload = _request_error(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": "demo.configure", "params": params},
        )
        assert status == 400
        assert payload["error"]["code"] == "invalid_request"
        assert message in payload["error"]["message"]
        assert server.task_manager.snapshots() == []
    finally:
        _stop_server(server, thread)


def test_bound_arguments_are_hidden_and_passed_to_target():
    calls = []

    def inspect_variant(webui_type: str, webui_path: Path, limit: int = 100) -> dict[str, object]:
        calls.append((webui_type, webui_path, limit))
        return {"type": webui_type, "path": webui_path, "limit": limit}

    method_name = "comfyui.demo.inspect"
    spec = ApiMethodSpec(handler=inspect_variant, bound_arguments={"webui_type": "comfyui"})
    server, thread, base_url = _start_server(methods={method_name: spec})
    try:
        details = server.method_details(method_name)
        assert details is not None
        assert [item["name"] for item in details["parameters"]] == ["webui_path", "limit"]
        _, payload = _request(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": method_name, "params": {"webui_path": "/tmp/demo", "limit": 5}},
        )
        assert payload["result"] == {"type": "comfyui", "path": "/tmp/demo", "limit": 5}
        assert calls == [("comfyui", Path("/tmp/demo"), 5)]
    finally:
        _stop_server(server, thread)


def test_task_lifecycle_progress_logs_and_cancel():
    release = threading.Event()

    def wait(name: str, context: ApiTaskContext) -> dict[str, bool]:
        context.log(f"starting {name}")
        context.set_progress(10, "started")
        while not release.wait(0.02):
            context.check_canceled()
        return {"done": True}

    server, thread, base_url = _start_server(methods={"demo.wait": wait})
    try:
        status, payload = _request(
            f"{base_url}/api/v2/tasks",
            method="POST",
            data={"method": "demo.wait", "params": {"name": "job"}},
        )
        assert status == 202
        task_id = payload["result"]["id"]

        deadline = time.time() + 2
        while time.time() < deadline:
            _, log_payload = _request(f"{base_url}/api/v2/tasks/{task_id}/logs")
            if log_payload["result"]["logs"]:
                break
            time.sleep(0.02)
        assert log_payload["result"]["logs"][0]["message"] == "starting job"

        _, cancel_payload = _request(f"{base_url}/api/v2/tasks/{task_id}/cancel", method="POST")
        assert cancel_payload["result"]["canceled"] is True
        result = _wait_for_task(base_url, task_id, "canceled")
        assert result["progress"] == 10
        assert result["error"]["code"] == "task_canceled"
    finally:
        release.set()
        _stop_server(server, thread)


def test_task_failure_and_success_results():
    def complete(value: int, context: ApiTaskContext) -> dict[str, int]:
        context.log("done")
        context.set_progress(100, "complete")
        return {"value": value}

    def fail(message: str) -> None:
        raise RuntimeError(message)

    server, thread, base_url = _start_server(methods={"demo.complete": complete, "demo.fail": fail})
    try:
        status, payload = _request(
            f"{base_url}/api/v2/tasks",
            method="POST",
            data={"method": "demo.complete", "params": {"value": 7}},
        )
        assert status == 202
        result = _wait_for_task(base_url, payload["result"]["id"], "succeeded")
        assert result["result"] == {"value": 7}

        status, payload = _request_error(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": "demo.fail", "params": {"message": "broken"}, "wait_ms": 1000},
        )
        assert status == 500
        assert payload["error"]["code"] == "task_failed"
        assert payload["error"]["message"] == "broken"
    finally:
        _stop_server(server, thread)


def test_health_discovery_auth_and_http_protocol():
    server, thread, base_url = _start_server(token="secret")
    try:
        status, payload = _request(f"{base_url}/health")
        assert status == 200
        assert payload == {"ok": True, "result": {"status": "ok"}}

        status, payload = _request_error(f"{base_url}/api/v2/methods")
        assert status == 401
        assert payload["error"]["code"] == "unauthorized"

        status, payload = _request(f"{base_url}/api/v2/methods", token="secret")
        assert status == 200
        assert payload["result"]["methods"] == []
        assert payload["result"]["metadata"] == {}

        status, headers, body = _request_raw(f"{base_url}/api/v2/methods", method="OPTIONS")
        assert status == 204
        assert headers["Access-Control-Allow-Methods"] == "GET,HEAD,POST,OPTIONS"
        assert body == b""

        status, headers, body = _request_error_raw(f"{base_url}/api/v2/methods", method="PUT", token="secret")
        assert status == 405
        assert headers["Allow"] == "GET,HEAD,POST,OPTIONS"
        assert json.loads(body)["error"]["code"] == "method_not_allowed"
    finally:
        _stop_server(server, thread)


def test_api_client_uses_v2_protocol():
    def echo(value: int) -> dict[str, int]:
        return {"value": value}

    server, thread, base_url = _start_server(methods={"demo.echo": echo})
    client = ApiClient(base_url=base_url, timeout=5)
    try:
        assert client.health() == {"status": "ok"}
        assert client.methods()["methods"] == ["demo.echo"]
        assert client.get_method("demo.echo")["parameters"][0]["type"] == "integer"
        assert client.call("demo.echo", {"value": 3}) == {"value": 3}
        task = client.create_task("demo.echo", {"value": 9})
        assert _wait_for_task(base_url, task["id"], "succeeded")["result"] == {"value": 9}
        with pytest.raises(ApiClientError) as exc:
            client.call("demo.missing", {})
        assert exc.value.code == "method_not_found"
    finally:
        _stop_server(server, thread)


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


def test_context_cancellation_exception_is_preserved():
    class CanceledTask:
        task_id = "id"
        is_canceled = True

    context = object.__new__(ApiTaskContext)
    context._task = CanceledTask()  # type: ignore[attr-defined]
    with pytest.raises(ApiTaskCanceled):
        context.check_canceled()
