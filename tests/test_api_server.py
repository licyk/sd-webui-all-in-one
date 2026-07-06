import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from sd_webui_all_in_one.api_server import ApiClient, ApiClientError, ApiMethodSpec, create_api_server
from sd_webui_all_in_one.api_server import registry
from sd_webui_all_in_one.api_server import server as api_server_module
from sd_webui_all_in_one.api_server.adapters import webui as webui_adapters


def _request(url, method="GET", data=None, token=""):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _request_raw(url, method="GET", data=None, token=""):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
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
        _, payload = _request(f"{base_url}/api/v1/tasks/{task_id}")
        task = payload["result"]
        if task["status"] == status:
            return task
        time.sleep(0.02)
    raise AssertionError(f"task did not reach {status}")


def test_api_server_loads_default_business_methods():
    server = create_api_server(port=0)
    try:
        catalog = server.method_catalog()
        assert "version.branches" in catalog["methods"]
        assert "snapshot.read" in catalog["methods"]
        assert "version.update" in catalog["tasks"]
        assert "snapshot.create" in catalog["tasks"]
        assert catalog["metadata"]["snapshot.create"]["kind"] == "task"
    finally:
        server.server_close()


def test_api_server_health_methods_and_empty_task_method_registry():
    server, thread, base_url = _start_server()

    try:
        status, payload = _request(f"{base_url}/health")
        assert status == 200
        assert payload == {"ok": True, "result": {"status": "ok"}}

        status, payload = _request(f"{base_url}/api/v1/methods")
        assert status == 200
        assert payload["ok"] is True
        assert payload["result"]["methods"] == []
        assert payload["result"]["tasks"] == []
        assert payload["result"]["metadata"] == {}
        assert "invalid_request" in payload["result"]["error_codes"]
        assert "running" in payload["result"]["task_statuses"]

        status, payload = _request_error(f"{base_url}/api/v1/call", method="POST", data={"method": "missing", "params": {}})
        assert status == 404
        assert payload["ok"] is False
        assert payload["error"]["code"] == "method_not_found"
    finally:
        _stop_server(server, thread)


def test_api_server_sync_method_registry_call():
    def echo(params):
        return {"received": params}

    server, thread, base_url = _start_server(
        methods={
            "demo.echo": ApiMethodSpec(
                name="demo.echo",
                handler=echo,
                kind="sync",
                description="Echo parameters",
                params_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
            )
        }
    )

    try:
        _, payload = _request(f"{base_url}/api/v1/methods")
        result = payload["result"]
        assert result["methods"] == ["demo.echo"]
        assert result["tasks"] == []
        assert result["metadata"]["demo.echo"]["description"] == "Echo parameters"
        assert result["metadata"]["demo.echo"]["params_schema"]["properties"]["value"]["type"] == "integer"

        status, payload = _request(f"{base_url}/api/v1/call", method="POST", data={"method": "demo.echo", "params": {"value": 1}})
        assert status == 200
        assert payload == {"ok": True, "result": {"received": {"value": 1}}}
    finally:
        _stop_server(server, thread)


def test_api_server_task_lifecycle_progress_logs_and_cancel():
    release = threading.Event()

    def wait_task(params, context):
        context.log(f"starting {params['name']}")
        context.set_progress(10, "started")
        while not release.wait(0.02):
            context.check_canceled()
        context.set_progress(100, "done")
        return {"done": True}

    server, thread, base_url = _start_server(task_methods={"demo.wait": wait_task})

    try:
        status, payload = _request(f"{base_url}/api/v1/tasks", method="POST", data={"method": "demo.wait", "params": {"name": "job"}})
        assert status == 202
        task_id = payload["result"]["id"]
        assert payload["result"]["method"] == "demo.wait"

        deadline = time.time() + 5
        while time.time() < deadline:
            _, payload = _request(f"{base_url}/api/v1/tasks/{task_id}/logs")
            if payload["result"]["logs"]:
                break
            time.sleep(0.02)
        assert payload["result"]["logs"][0]["message"] == "starting job"

        _, payload = _request(f"{base_url}/api/v1/tasks")
        assert payload["result"]["tasks"][0]["id"] == task_id

        _, payload = _request(f"{base_url}/api/v1/tasks/{task_id}/cancel", method="POST")
        assert payload["ok"] is True
        assert payload["result"]["canceled"] is True

        task = _wait_for_task(base_url, task_id, "canceled")
        assert task["error"]["code"] == "task_canceled"
    finally:
        release.set()
        _stop_server(server, thread)


def test_api_server_task_success_result():
    def complete_task(params, context):
        context.log("done")
        context.set_progress(100, "complete")
        return {"value": params["value"]}

    server, thread, base_url = _start_server(task_methods={"demo.complete": complete_task})

    try:
        _, payload = _request(f"{base_url}/api/v1/tasks", method="POST", data={"method": "demo.complete", "params": {"value": 7}})
        task_id = payload["result"]["id"]

        task = _wait_for_task(base_url, task_id, "succeeded")
        assert task["result"] == {"value": 7}
        assert task["progress"] == 100
        assert task["progress_message"] == "complete"
    finally:
        _stop_server(server, thread)


def test_api_server_head_options_and_unsupported_methods():
    server, thread, base_url = _start_server()

    try:
        status, headers, body = _request_raw(f"{base_url}/health", method="HEAD")
        assert status == 200
        assert headers["Allow"] == "GET,HEAD,POST,OPTIONS"
        assert body == b""

        status, headers, body = _request_raw(f"{base_url}/api/v1/methods", method="OPTIONS")
        assert status == 204
        assert headers["Allow"] == "GET,HEAD,POST,OPTIONS"
        assert headers["Access-Control-Allow-Methods"] == "GET,HEAD,POST,OPTIONS"
        assert body == b""

        status, headers, body = _request_error_raw(f"{base_url}/api/v1/methods", method="PUT", data={})
        assert status == 405
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        payload = json.loads(body.decode("utf-8"))
        assert payload["ok"] is False
        assert payload["error"]["code"] == "method_not_allowed"
    finally:
        _stop_server(server, thread)


def test_api_server_token_and_request_validation():
    server, thread, base_url = _start_server(token="secret")

    try:
        status, payload = _request_error(f"{base_url}/api/v1/methods")
        assert status == 401
        assert payload["error"]["code"] == "unauthorized"

        status, payload = _request(f"{base_url}/api/v1/methods", token="secret")
        assert status == 200
        assert payload["ok"] is True
        assert payload["result"]["methods"] == []
        assert payload["result"]["tasks"] == []

        status, payload = _request_error(f"{base_url}/api/v1/call", method="POST", data={"params": {}}, token="secret")
        assert status == 400
        assert payload["error"]["code"] == "invalid_request"
    finally:
        _stop_server(server, thread)


def test_api_request_handler_logs_access_status(monkeypatch):
    messages = []

    class FakeLogger:
        def info(self, message, *args):
            messages.append(message % args)

    handler = object.__new__(api_server_module.ApiRequestHandler)
    handler.client_address = ("127.0.0.1", 43210)
    handler.command = "GET"
    handler.path = "/health"
    handler.request_version = "HTTP/1.1"
    monkeypatch.setattr(api_server_module, "logger", FakeLogger())

    handler.log_request(200)

    assert messages == ['API 127.0.0.1:43210 - "GET /health HTTP/1.1" 200']


def test_api_server_rejects_invalid_registered_method_names():
    with pytest.raises(ValueError, match="Invalid API method name"):
        create_api_server(port=0, methods={"bad-name": lambda _params: None})


def test_api_client_wraps_api_protocol():
    def echo(params):
        return {"received": params}

    def complete_task(params, context):
        context.log("done")
        return {"value": params["value"]}

    server, thread, base_url = _start_server(methods={"demo.echo": echo}, task_methods={"demo.complete": complete_task})
    client = ApiClient(base_url=base_url, timeout=5)

    try:
        assert client.health() == {"status": "ok"}
        catalog = client.methods()
        assert catalog["methods"] == ["demo.echo"]
        assert catalog["tasks"] == ["demo.complete"]
        assert client.call("demo.echo", {"value": 3}) == {"received": {"value": 3}}

        task = client.create_task("demo.complete", {"value": 9})
        task_id = task["id"]
        result = _wait_for_task(base_url, task_id, "succeeded")
        assert result["result"] == {"value": 9}
        assert client.get_task_logs(task_id)["logs"][0]["message"] == "done"

        with pytest.raises(ApiClientError) as exc:
            client.call("demo.missing", {})
        assert exc.value.code == "method_not_found"
    finally:
        _stop_server(server, thread)


def test_default_api_registry_dispatches_version_queries(monkeypatch, tmp_path):
    calls = []

    class FakeAdapter:
        def list_branches(self, webui_path, fetch=True):
            calls.append(("branches", webui_path, fetch))
            return {"branches": []}

        def list_commits(self, webui_path, limit=100):
            calls.append(("commits", webui_path, limit))
            return {"commits": []}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    assert registry.version_branches({"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"fetch": False}}) == {"branches": []}
    assert registry.version_commits({"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"limit": 5}}) == {"commits": []}
    assert calls == [("branches", tmp_path, False), ("commits", tmp_path, 5)]


def test_default_api_registry_dispatches_snapshot_task(monkeypatch, tmp_path):
    calls = []

    class FakeContext:
        def log(self, message):
            calls.append(("log", message))

        def set_progress(self, value, message):
            calls.append(("progress", value, message))

    class FakeAdapter:
        def create_snapshot(self, webui_path, include_packages=True, output_dir=None):
            calls.append(("create", webui_path, include_packages, output_dir))
            return {"path": "snapshot.json"}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    result = registry.snapshot_create(
        {"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"include_packages": False, "output_dir": str(tmp_path / "snapshots")}},
        FakeContext(),
    )

    assert result == {"path": "snapshot.json"}
    assert calls == [("log", "Creating snapshot"), ("create", tmp_path, False, tmp_path / "snapshots"), ("progress", 100, "done")]


def test_get_webui_adapter_rejects_unknown_type():
    with pytest.raises(ValueError, match="Unsupported webui_type"):
        webui_adapters.get_webui_adapter("missing")


def test_default_api_registry_includes_full_version_snapshot_extension_surface():
    server = create_api_server(port=0)
    try:
        catalog = server.method_catalog()
        assert {"version.status", "snapshot.list", "snapshot.delete", "extension.list", "extension.index", "extension.versions", "environment.dependencies", "package.versions", "launch.prepare"}.issubset(catalog["methods"])
        assert {
            "extension.set_enabled",
            "extension.install",
            "extension.install_index_item",
            "extension.update",
            "extension.update_all",
            "extension.uninstall",
            "extension.switch_branch",
            "extension.switch_commit",
            "extension.switch_registry_version",
            "invokeai.install_version",
        }.issubset(catalog["tasks"])
    finally:
        server.server_close()


def test_default_api_registry_dispatches_extension_methods(monkeypatch, tmp_path):
    calls = []

    class FakeContext:
        def log(self, message):
            calls.append(("log", message))

        def set_progress(self, value, message):
            calls.append(("progress", value, message))

    class FakeAdapter:
        def list_extensions(self, webui_path):
            calls.append(("list", webui_path))
            return {"extensions": []}

        def set_extension_enabled(self, webui_path, name, enabled):
            calls.append(("enabled", webui_path, name, enabled))
            return {"changed": True}

        def install_extension_index_item(self, webui_path, item, use_github_mirror=False, custom_github_mirror=None):
            calls.append(("install_index", webui_path, item["name"], use_github_mirror, custom_github_mirror))
            return {"installed": True}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    assert registry.extension_list({"webui_type": "sd_webui", "webui_path": str(tmp_path)}) == {"extensions": []}
    assert registry.extension_set_enabled({"webui_type": "sd_webui", "webui_path": str(tmp_path), "name": "ext", "enabled": True}, FakeContext()) == {"changed": True}
    assert registry.extension_install_index_item(
        {"webui_type": "sd_webui", "webui_path": str(tmp_path), "item": {"name": "ext", "url": "https://example.invalid/ext.git"}, "options": {"use_github_mirror": True, "custom_github_mirror": "https://mirror.example"}},
        FakeContext(),
    ) == {"installed": True}

    assert calls == [
        ("list", tmp_path),
        ("log", "Changing extension status"),
        ("enabled", tmp_path, "ext", True),
        ("progress", 100, "done"),
        ("log", "Installing extension index item"),
        ("install_index", tmp_path, "ext", True, "https://mirror.example"),
        ("progress", 100, "done"),
    ]


def test_default_api_registry_dispatches_launch_prepare(monkeypatch, tmp_path):
    calls = []

    class FakeAdapter:
        def prepare_launch(self, webui_path, options=None):
            calls.append((webui_path, options))
            return {
                "launch": {
                    "webui_path": webui_path.as_posix(),
                    "launch_script": "main.py",
                    "webui_name": "ComfyUI",
                    "launch_args": options["launch_args"],
                    "custom_env": {"HF_ENDPOINT": "https://hf.example"},
                }
            }

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    result = registry.launch_prepare(
        {
            "webui_type": "comfyui",
            "webui_path": str(tmp_path),
            "options": {"launch_args": ["--listen"]},
        }
    )

    assert result["launch"]["launch_script"] == "main.py"
    assert result["launch"]["launch_args"] == ["--listen"]
    assert calls == [(tmp_path, {"launch_args": ["--listen"]})]


def test_default_api_registry_dispatches_environment_dependencies(monkeypatch, tmp_path):
    calls = []

    class FakeAdapter:
        def check_environment_dependencies(self, webui_path):
            calls.append(webui_path)
            return {"dependencies": {"has_missing_requires": False, "has_conflict_requires": False}}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    result = registry.environment_dependencies({"webui_type": "comfyui", "webui_path": str(tmp_path)})

    assert result == {"dependencies": {"has_missing_requires": False, "has_conflict_requires": False}}
    assert calls == [tmp_path]


def test_webui_adapter_lists_and_deletes_snapshots(tmp_path):
    from sd_webui_all_in_one.base_manager.snapshot import PythonSnapshot, WebUiIdentitySnapshot, WebUiSnapshot, save_snapshot

    adapter = webui_adapters.WebUiApiAdapter("sd_webui", "Stable Diffusion WebUI", lambda _path, _include: None)
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    snapshot_path = snapshot_dir / "sample.json"
    save_snapshot(
        WebUiSnapshot(
            schema_version=1,
            created_at="2026-07-05T00:00:00Z",
            webui=WebUiIdentitySnapshot(type="sd_webui", name="Stable Diffusion WebUI", path=tmp_path),
            python=PythonSnapshot(executable="python", version="3.11", implementation="CPython", platform="linux"),
        ),
        snapshot_path,
    )

    result = adapter.list_snapshots(tmp_path, snapshot_dir=snapshot_dir)

    assert result["snapshots"][0]["path"] == snapshot_path.as_posix()
    assert result["snapshots"][0]["webui_type"] == "sd_webui"
    assert adapter.delete_snapshot(snapshot_path) == {"deleted": True, "path": snapshot_path.as_posix()}
    assert not snapshot_path.exists()


def test_default_api_registry_includes_model_and_hotpatcher_surface():
    server = create_api_server(port=0)
    try:
        catalog = server.method_catalog()
        assert {
            "version.branch_presets",
            "system.pytorch_device_type",
            "system.pytorch_library",
            "model.root",
            "model.library",
            "model.directories",
            "model.entries",
            "model.invokeai.list",
            "hotpatcher.catalog",
            "hotpatcher.runtime_status",
            "hotpatcher.runtime_logs",
        }.issubset(catalog["methods"])
        assert {
            "model.create_folder",
            "model.copy",
            "model.move",
            "model.delete",
            "model.import",
            "model.download",
            "model.invokeai.install_url",
            "hotpatcher.save_config",
            "hotpatcher.runtime_start",
            "hotpatcher.runtime_stop",
            "hotpatcher.runtime_apply_remote",
        }.issubset(catalog["tasks"])
    finally:
        server.server_close()


def test_model_api_adapter_file_operations(tmp_path):
    from sd_webui_all_in_one.api_server.adapters.model import MODEL_API_ADAPTER

    webui_path = tmp_path / "ComfyUI"
    root = webui_path / "models"
    source = tmp_path / "source.safetensors"
    source.write_text("model", encoding="utf-8")

    created = MODEL_API_ADAPTER.create_folder("comfyui", webui_path, ".", "checkpoints")
    assert created["path"].endswith("models/checkpoints")

    imported = MODEL_API_ADAPTER.import_paths("comfyui", webui_path, [source.as_posix()], "checkpoints")
    assert imported["paths"][0].endswith("models/checkpoints/source.safetensors")

    entries = MODEL_API_ADAPTER.list_entries("comfyui", webui_path, "checkpoints")
    assert entries["entries"][0]["name"] == "source.safetensors"

    copied = MODEL_API_ADAPTER.copy_entry("comfyui", webui_path, "checkpoints/source.safetensors", ".", new_name="copy.safetensors")
    assert (root / "copy.safetensors").is_file()
    assert copied["path"].endswith("models/copy.safetensors")

    moved = MODEL_API_ADAPTER.move_entry("comfyui", webui_path, "copy.safetensors", "checkpoints", new_name="moved.safetensors")
    assert moved["path"].endswith("models/checkpoints/moved.safetensors")
    assert not (root / "copy.safetensors").exists()

    deleted = MODEL_API_ADAPTER.delete_entry("comfyui", webui_path, "checkpoints/moved.safetensors")
    assert deleted == {"deleted": True}
    assert not (root / "checkpoints" / "moved.safetensors").exists()


def test_hotpatcher_api_adapter_runtime_status_and_env():
    from sd_webui_all_in_one.api_server.adapters.hotpatcher import HotpatcherApiAdapter

    adapter = HotpatcherApiAdapter()
    assert adapter.runtime_status()["running"] is False

    env = adapter.runtime_env(host="127.0.0.1", port=9876, token="secret")
    assert env["env"]["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == "9876"
    assert env["env"]["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] == "secret"

    started = adapter.start_runtime(host="127.0.0.1", port=0, token="")
    try:
        assert started["running"] is True
        assert started["address"]["port"] > 0
        assert adapter.runtime_logs()["logs"] == []
    finally:
        assert adapter.stop_runtime() == {"stopped": True}
    assert adapter.runtime_status()["running"] is False


def test_default_api_registry_dispatches_pytorch_device_type(monkeypatch):
    monkeypatch.setattr(registry, "get_available_pytorch_device_type", lambda: ["all", "cpu", "cu128"])
    monkeypatch.setattr(registry, "auto_detect_pytorch_device_category", lambda: "cuda")

    assert registry.pytorch_device_type({}) == {"types": ["all", "cpu", "cu128"]}
    assert registry.pytorch_device_type({"options": {"category": True}}) == {"category": "cuda"}


def test_default_api_registry_dispatches_pytorch_library(monkeypatch):
    monkeypatch.setattr(
        registry,
        "export_pytorch_list",
        lambda: [
            {"name": "Torch CPU", "dtype": "cpu", "supported": True},
            {"name": "Torch CUDA", "dtype": "cu128", "supported": True},
            {"name": "Torch ROCm", "dtype": "rocm6.4", "supported": False},
        ],
    )

    all_items = registry.pytorch_library({})
    cuda_items = registry.pytorch_library({"options": {"dtype": "cu128"}})
    supported_items = registry.pytorch_library({"options": {"supported": True}})

    assert all_items["count"] == 3
    assert cuda_items == {"count": 1, "items": [{"name": "Torch CUDA", "dtype": "cu128", "supported": True}]}
    assert supported_items["count"] == 2
    assert [item["name"] for item in supported_items["items"]] == ["Torch CPU", "Torch CUDA"]

    with pytest.raises(ValueError, match="options.dtype"):
        registry.pytorch_library({"options": {"dtype": 128}})


def test_default_api_registry_dispatches_model_library():
    result = registry.model_library({"webui_type": "comfyui"})

    assert result["webui_type"] == "comfyui"
    assert result["count"] == len(result["models"])
    assert result["count"] > 0
    assert result["models"][0]["name"]
    assert "comfyui" in result["models"][0]["supported_webui"]

    with pytest.raises(ValueError, match="Unsupported model library"):
        registry.model_library({"webui_type": "unknown"})


def test_default_api_registry_dispatches_branch_presets():
    sd_webui = registry.version_branch_presets({"webui_type": "sd_webui"})
    fooocus = registry.version_branch_presets({"webui_type": "fooocus"})
    sd_trainer = registry.version_branch_presets({"webui_type": "sd_trainer"})
    unsupported = registry.version_branch_presets({"webui_type": "comfyui"})

    assert sd_webui["webui_type"] == "sd_webui"
    assert sd_webui["source"] == "preset"
    assert sd_webui["supported"] is True
    assert sd_webui["types"][0] == "sd_webui_main"
    assert sd_webui["branches"][0]["dtype"] == "sd_webui_main"
    assert fooocus["supported"] is True
    assert fooocus["types"][0] == "fooocus_main"
    assert fooocus["branches"][0]["dtype"] == "fooocus_main"
    assert sd_trainer["supported"] is True
    assert sd_trainer["types"][0] == "sd_trainer_main"
    assert sd_trainer["branches"][0]["dtype"] == "sd_trainer_main"
    assert unsupported == {
        "webui_type": "comfyui",
        "source": "preset",
        "supported": False,
        "branches": [],
        "types": [],
    }
