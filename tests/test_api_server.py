import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import cast

import pytest

from sd_webui_all_in_one.api_server import ApiClient, ApiClientError, ApiMethodSpec, create_api_server
from sd_webui_all_in_one.api_server import registry
from sd_webui_all_in_one.api_server import server as api_server_module
from sd_webui_all_in_one.api_server.adapters import webui as webui_adapters
from sd_webui_all_in_one.api_server.adapters.webui import WebUiApiType
from sd_webui_all_in_one.base_manager.base import PyTorchUpdateStatus
from sd_webui_all_in_one.base_manager import version_manager
from sd_webui_all_in_one.cli_manager import auto_mirror


class _NoopTaskContext:
    """Minimal ApiTaskContext stand-in for calling task handlers directly."""

    def check_canceled(self):
        return None

    def is_canceled(self):
        return False

    def log(self, message, level="info"):
        return None

    def set_progress(self, value=None, message=""):
        return None


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
        # One registry: every method is a job listed under "methods"; "tasks" is empty.
        assert "version.branches" in catalog["methods"]
        assert "snapshot.read" in catalog["methods"]
        assert "version.update" in catalog["methods"]
        assert "snapshot.create" in catalog["methods"]
        assert "snapshot.delete" in catalog["methods"]
        assert catalog["tasks"] == []
        assert catalog["metadata"]["snapshot.create"]["kind"] == "job"
        assert catalog["metadata"]["snapshot.delete"]["kind"] == "job"
        assert catalog["metadata"]["snapshot.delete"]["params_schema"]["required"] == ["webui_type", "snapshot_path"]
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
    def echo(params, context=None):
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

    server, thread, base_url = _start_server(methods={"demo.wait": wait_task})

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

    server, thread, base_url = _start_server(methods={"demo.complete": complete_task})

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
    def echo(params, context=None):
        return {"received": params}

    def complete_task(params, context):
        context.log("done")
        return {"value": params["value"]}

    server, thread, base_url = _start_server(methods={"demo.echo": echo, "demo.complete": complete_task})
    client = ApiClient(base_url=base_url, timeout=5)

    try:
        assert client.health() == {"status": "ok"}
        catalog = client.methods()
        assert catalog["methods"] == ["demo.complete", "demo.echo"]
        assert catalog["tasks"] == []
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

        def check_updates(self, webui_path, options=None):
            calls.append(("check-updates", webui_path, options))
            return {"summary": {"has_update": False}}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    assert registry.version_branches({"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"fetch": False}}) == {"branches": []}
    assert registry.version_commits({"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"limit": 5}}) == {"commits": []}
    assert registry.version_commits({"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"limit": None}}) == {"commits": []}
    assert registry.webui_check_updates({"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"include_extensions": False}}, _NoopTaskContext()) == {"summary": {"has_update": False}}
    assert calls == [("branches", tmp_path, False), ("commits", tmp_path, 5), ("commits", tmp_path, None), ("check-updates", tmp_path, {"include_extensions": False})]


def test_default_api_registry_dispatches_snapshot_task(monkeypatch, tmp_path):
    calls = []

    class FakeContext:
        def check_canceled(self):
            calls.append(("check-canceled",))

        def log(self, message):
            calls.append(("log", message))

        def set_progress(self, value, message):
            calls.append(("progress", value, message))

    class FakeAdapter:
        def create_snapshot(self, webui_path, include_packages=True, output_dir=None):
            calls.append(("create", webui_path, include_packages, output_dir))
            return {"path": "snapshot.json"}

        def delete_snapshot(self, snapshot_path):
            calls.append(("delete", snapshot_path))
            return {"deleted": True, "path": snapshot_path.as_posix()}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    result = registry.snapshot_create(
        {"webui_type": "sd_webui", "webui_path": str(tmp_path), "options": {"include_packages": False, "output_dir": str(tmp_path / "snapshots")}},
        FakeContext(),
    )

    assert result == {"path": "snapshot.json"}
    delete_result = registry.snapshot_delete(
        {"webui_type": "sd_webui", "snapshot_path": str(tmp_path / "snapshots" / "sample.json")},
        FakeContext(),
    )

    assert delete_result == {"deleted": True, "path": (tmp_path / "snapshots" / "sample.json").as_posix()}
    assert calls == [
        ("log", "Creating snapshot"),
        ("create", tmp_path, False, tmp_path / "snapshots"),
        ("progress", 100, "done"),
        ("check-canceled",),
        ("log", "Deleting WebUI snapshot"),
        ("delete", tmp_path / "snapshots" / "sample.json"),
        ("progress", 100, "done"),
    ]


def test_snapshot_delete_honors_cancellation_before_mutation(monkeypatch, tmp_path):
    class CanceledContext:
        def check_canceled(self):
            raise api_server_module.ApiTaskCanceled("canceled before delete")

        def log(self, _message):
            raise AssertionError("canceled deletion must not log or mutate")

    class FakeAdapter:
        def delete_snapshot(self, _snapshot_path):
            raise AssertionError("canceled deletion must not reach the adapter")

    monkeypatch.setattr(registry, "get_webui_adapter", lambda _webui_type: FakeAdapter())

    with pytest.raises(api_server_module.ApiTaskCanceled, match="before delete"):
        registry.snapshot_delete(
            {"webui_type": "sd_webui", "snapshot_path": str(tmp_path / "sample.json")},
            CanceledContext(),
        )


def test_get_webui_adapter_rejects_unknown_type():
    with pytest.raises(ValueError, match="Unsupported webui_type"):
        webui_adapters.get_webui_adapter(cast(WebUiApiType, "missing"))


def test_webui_adapter_check_updates_returns_structured_summary(tmp_path):
    update_status = version_manager.WebUiUpdateStatus(
        webui_type="sd_webui",
        name="Stable Diffusion WebUI",
        path=tmp_path,
        kernel=version_manager.RepositoryUpdateStatus(name="repo", path=tmp_path, is_git_repo=True, has_update=True, behind=1),
        pytorch=PyTorchUpdateStatus(True, "2.7.0+cu128", "cu128", "2.8.0+cu128", "Torch CUDA", True),
        extensions=[
            version_manager.ExtensionUpdateStatus(
                name="demo-ext",
                path=tmp_path / "extensions" / "demo-ext",
                enabled=True,
                source_type="git",
                is_git_repo=True,
                has_update=True,
                behind=2,
            )
        ],
        extensions_supported=True,
        summary=version_manager.WebUiUpdateSummary(True, True, True, 1, 1, 0, 0),
        errors=[],
    )
    adapter = webui_adapters.WebUiApiAdapter(
        "sd_webui",
        "Stable Diffusion WebUI",
        lambda _path, _include_packages: None,
        lambda _path, _options: update_status,
    )

    result = adapter.check_updates(tmp_path, options={"fetch": False})

    assert result["kernel"]["has_update"] is True
    assert result["extensions"][0]["name"] == "demo-ext"
    assert result["extensions"][0]["behind"] == 2
    assert result["summary"] == {
        "has_update": True,
        "kernel_has_update": True,
        "pytorch_has_update": True,
        "extension_update_count": 1,
        "checked_extension_count": 1,
        "skipped_count": 0,
        "error_count": 0,
    }


def test_default_api_registry_includes_full_version_snapshot_extension_surface():
    server = create_api_server(port=0)
    try:
        catalog = server.method_catalog()
        # One registry: reads and mutations alike are listed under "methods".
        assert catalog["tasks"] == []
        assert {
            "version.status",
            "snapshot.list",
            "extension.list",
            "extension.commits",
            "environment.dependencies",
            "environment.pytorch_version",
            "launch.prepare",
            "system.proxy",
            "webui.check_updates",
            "extension.index",
            "extension.versions",
            "package.versions",
            "launch.arguments.catalog",
            "snapshot.delete",
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
        }.issubset(catalog["methods"])
        assert catalog["metadata"]["extension.commits"]["params_schema"]["required"] == ["webui_type", "webui_path", "name"]
    finally:
        server.server_close()


def test_launch_argument_catalog_api_success_and_typed_failure_envelopes(tmp_path):
    (tmp_path / "comfy").mkdir()
    (tmp_path / "comfy" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "comfy" / "cli_args.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\n",
        encoding="utf-8",
    )
    server = create_api_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, payload = _request(
            f"{base_url}/api/v1/tasks",
            method="POST",
            data={
                "method": "launch.arguments.catalog",
                "params": {"webui_type": "comfyui", "webui_path": str(tmp_path)},
            },
        )
        assert status == 202
        task = _wait_for_task(base_url, payload["result"]["id"], "succeeded")
        assert task["result"]["catalog"]["arguments"][0]["name"] == "help"

        status, payload = _request(
            f"{base_url}/api/v1/tasks",
            method="POST",
            data={
                "method": "launch.arguments.catalog",
                "params": {"webui_type": "unknown", "webui_path": str(tmp_path)},
            },
        )
        assert status == 202
        task = _wait_for_task(base_url, payload["result"]["id"], "failed")
        assert task["error"]["code"] == "task_failed"
        assert "Unsupported webui_type" in task["error"]["message"]
    finally:
        _stop_server(server, thread)


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


def test_extension_commits_resolves_name_and_forwards_none_limit(monkeypatch, tmp_path):
    extension_path = tmp_path / "extensions" / "demo"
    calls = []

    class FakeAdapter:
        def list_extensions(self, webui_path):
            calls.append(("list", webui_path))
            return {"extensions": [{"name": "demo", "path": str(extension_path)}]}

        def list_commits(self, path, limit=100):
            calls.append(("commits", path, limit))
            return {"commits": [{"commit": "full-id"}]}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda webui_type: FakeAdapter())

    result = registry.extension_commits(
        {
            "webui_type": "sd_webui",
            "webui_path": str(tmp_path),
            "name": "demo",
            "options": {"limit": None},
        }
    )

    assert result == {"commits": [{"commit": "full-id"}]}
    assert calls == [("list", tmp_path), ("commits", extension_path, None)]


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


def test_launch_prepare_delegates_automatic_mirror_rewriting_to_python(monkeypatch, tmp_path):
    calls = []
    received = []

    class FakeAdapter:
        def prepare_launch(self, webui_path, options=None):
            calls.append(options)
            return {"launch": {}}

    monkeypatch.setattr(registry, "get_webui_adapter", lambda _webui_type: FakeAdapter())
    def rewrite(namespace):
        received.append(dict(vars(namespace)))
        return registry.Namespace(**{**vars(namespace), "use_pypi_mirror": True,
            "use_github_mirror": True, "use_hf_mirror": True,
            "custom_github_mirror": None, "custom_hf_mirror": None})
    monkeypatch.setattr(registry, "apply_auto_mirror", rewrite)
    registry.launch_prepare({
        "webui_type": "comfyui", "webui_path": str(tmp_path),
        "options": {"automatic_mirror": True, "launch_args": ["--listen"],
                    "use_pypi_mirror": False, "use_github_mirror": False,
                    "custom_github_mirror": "https://configured.example",
                    "use_hf_mirror": False, "custom_hf_mirror": "https://hf.example"},
    })
    assert received == [{"auto_mirror": True, "launch_args": ["--listen"],
                         "use_pypi_mirror": False, "use_github_mirror": False,
                         "custom_github_mirror": "https://configured.example",
                         "use_hf_mirror": False, "custom_hf_mirror": "https://hf.example"}]
    assert calls == [{"launch_args": ["--listen"], "use_pypi_mirror": True, "use_github_mirror": True,
                      "use_hf_mirror": True, "custom_github_mirror": None,
                      "custom_hf_mirror": None}]


def test_api_mirror_processing_overwrites_automatic_and_preserves_manual(monkeypatch):
    configured = {"automatic_mirror": True, "keep": "value", "use_pypi_mirror": True,
                  "use_github_mirror": True, "custom_github_mirror": "https://github.example",
                  "use_hf_mirror": True, "custom_hf_mirror": "https://hf.example",
                  "source": "modelscope"}
    monkeypatch.setattr(auto_mirror, "network_gfw_test", lambda: True)
    automatic = registry._resolved_mirror_options(
        {"options": configured},
        ("use_pypi_mirror", "use_github_mirror", "custom_github_mirror",
         "use_hf_mirror", "custom_hf_mirror", "source"),
    )
    assert automatic == {"keep": "value", "use_pypi_mirror": False,
                         "use_github_mirror": False, "custom_github_mirror": None,
                         "use_hf_mirror": False, "custom_hf_mirror": None,
                         "source": "huggingface"}
    configured["automatic_mirror"] = False
    assert registry._resolved_mirror_options({"options": configured}, tuple(configured)) == {
        key: value for key, value in configured.items() if key != "automatic_mirror"
    }


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


def test_default_api_registry_dispatches_environment_pytorch_version(monkeypatch):
    monkeypatch.setattr(registry, "check_torch_version_status", lambda: {"status": "compatible", "is_compatible": True})

    result = registry.environment_pytorch_version({})

    assert result == {"pytorch": {"status": "compatible", "is_compatible": True}}


def test_default_api_registry_dispatches_system_proxy(monkeypatch):
    calls = []
    monkeypatch.setattr(registry, "get_system_proxy_address", lambda: "http://127.0.0.1:7890")
    monkeypatch.setattr(registry, "test_proxy_connectivity", lambda address, timeout=5: calls.append((address, timeout)) or True)

    result = registry.system_proxy({"options": {"test_connectivity": True, "timeout": 2}})

    assert result == {
        "address": "http://127.0.0.1:7890",
        "detected": True,
        "connectivity_tested": True,
        "connectivity": True,
    }
    assert calls == [("http://127.0.0.1:7890", 2)]


def test_system_proxy_reports_only_executed_connectivity_checks(monkeypatch):
    calls = []
    monkeypatch.setattr(registry, "test_proxy_connectivity", lambda *args, **kwargs: calls.append((args, kwargs)) or False)
    monkeypatch.setattr(registry, "get_system_proxy_address", lambda: "http://127.0.0.1:7890")
    assert registry.system_proxy({}) == {
        "address": "http://127.0.0.1:7890",
        "detected": True,
        "connectivity_tested": False,
        "connectivity": None,
    }
    monkeypatch.setattr(registry, "get_system_proxy_address", lambda: None)
    assert registry.system_proxy({"options": {"test_connectivity": True}}) == {
        "address": None,
        "detected": False,
        "connectivity_tested": False,
        "connectivity": None,
    }
    assert calls == []


def test_system_proxy_reports_executed_unreachable_connectivity(monkeypatch):
    monkeypatch.setattr(registry, "get_system_proxy_address", lambda: "http://127.0.0.1:7890")
    monkeypatch.setattr(registry, "test_proxy_connectivity", lambda _address, timeout=5: False)
    assert registry.system_proxy({"options": {"test_connectivity": True, "timeout": 3}}) == {
        "address": "http://127.0.0.1:7890",
        "detected": True,
        "connectivity_tested": True,
        "connectivity": False,
    }


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"test_connectivity": 1}, "must be a boolean"),
        ({"timeout": True}, "must be an integer"),
        ({"timeout": 1.5}, "must be an integer"),
        ({"timeout": 0}, "between 1 and 30"),
        ({"timeout": 31}, "between 1 and 30"),
    ],
)
def test_system_proxy_rejects_invalid_connectivity_options(options, message):
    with pytest.raises(ValueError, match=message):
        registry.system_proxy({"options": options})


def test_system_proxy_set_and_clear_are_validated_and_idempotent(monkeypatch):
    calls = []
    monkeypatch.setattr(registry, "set_proxy", lambda address: calls.append(("set", address)))
    monkeypatch.setattr(registry, "clean_proxy", lambda: calls.append(("clear", None)))
    expected_set = {"enabled": True, "address": "socks5://127.0.0.1:1080"}
    assert registry.system_proxy_set({"address": expected_set["address"]}) == expected_set
    assert registry.system_proxy_set({"address": expected_set["address"]}) == expected_set
    expected_clear = {"enabled": False, "address": None}
    assert registry.system_proxy_clear({}) == expected_clear
    assert registry.system_proxy_clear({}) == expected_clear
    assert calls == [
        ("set", expected_set["address"]),
        ("set", expected_set["address"]),
        ("clear", None),
        ("clear", None),
    ]
    for address in ["missing-port", "http://host", "ftp://host:21", "http://bad\0host:80"]:
        with pytest.raises(ValueError):
            registry.system_proxy_set({"address": address})


def test_system_proxy_mutations_update_only_uppercase_proxy_environment(monkeypatch):
    for key in ["HTTP_PROXY", "HTTPS_PROXY"]:
        monkeypatch.delenv(key, raising=False)
    expected = "http://127.0.0.1:7890"
    assert registry.system_proxy_set({"address": expected}) == {
        "enabled": True,
        "address": expected,
    }
    assert os.environ["HTTP_PROXY"] == expected
    assert os.environ["HTTPS_PROXY"] == expected
    assert registry.system_proxy_clear({}) == {"enabled": False, "address": None}
    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ


def test_default_api_registry_exposes_proxy_mutation_schemas():
    methods = registry.get_default_methods()
    assert methods["system.proxy"].params_schema["properties"]["options"]["properties"] == {
        "test_connectivity": {"type": "boolean"},
        "timeout": {"type": "integer", "minimum": 1, "maximum": 30},
    }
    assert methods["system.proxy.set"].kind == "job"
    assert methods["system.proxy.set"].params_schema["required"] == ["address"]
    assert methods["system.proxy.clear"].kind == "job"
    assert methods["system.proxy.clear"].params_schema == {"type": "object", "properties": {}}


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
        # One registry: reads and mutations alike are listed under "methods".
        assert catalog["tasks"] == []
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
            "hotpatcher.runtime_browser_events",
            "hotpatcher.runtime_ensure",
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
        }.issubset(catalog["methods"])
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


def test_hotpatcher_api_adapter_starts_stopped():
    from sd_webui_all_in_one.api_server.adapters.hotpatcher import HotpatcherApiAdapter

    adapter = HotpatcherApiAdapter()
    assert adapter.runtime_status()["running"] is False


def test_hotpatcher_public_browser_event_api_and_adapter_runtime_contract(monkeypatch):
    from sd_webui_all_in_one.api_server.adapters.hotpatcher import HotpatcherApiAdapter

    adapter = HotpatcherApiAdapter()
    monkeypatch.setattr(registry, "HOTPATCHER_API_ADAPTER", adapter)
    ensured = registry.hotpatcher_runtime_ensure(
        {
            "config": {"runtime": {"browser": {"enabled": True, "mode": "host"}}},
            "options": {"host": "127.0.0.1", "port": 0, "token": "secret"},
        }
    )
    try:
        assert adapter._runtime_host is not None
        adapter._runtime_host._record_message(
            {"type": "browser.open", "payload": {"url": "http://localhost:7860"}},
            None,
        )
        result = registry.hotpatcher_runtime_browser_events(
            {"options": {"since_cursor": ensured["browser_next_cursor"], "limit": 100}}
        )
        assert set(result) == {
            "runtime_identity",
            "events",
            "start_cursor",
            "next_cursor",
            "truncated",
        }
        assert set(result["events"][0]) == {"sequence", "url", "created"}
        assert result["events"][0]["url"] == "http://localhost:7860"
    finally:
        adapter.stop_runtime()

    env = adapter.runtime_env(host="127.0.0.1", port=9876, token="secret")
    assert env["env"]["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT"] == "9876"
    assert env["env"]["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] == "secret"

    started = adapter.start_runtime(host="127.0.0.1", port=0, token="secret")
    try:
        assert started["running"] is True
        assert started["address"]["port"] > 0
        assert isinstance(started["runtime_identity"], str)
        assert adapter.runtime_logs() == {
            "logs": [],
            "start_cursor": 0,
            "next_cursor": 0,
            "truncated": False,
        }
        assert adapter._runtime_host is not None
        adapter._runtime_host._record_message(
            {"type": "browser.open", "payload": {"url": "http://127.0.0.1:8188/path?q=1#ui"}},
            None,
        )
        events = adapter.runtime_browser_events(since_cursor=0, limit=100)
        assert events["runtime_identity"] == started["runtime_identity"]
        assert events["start_cursor"] == 0
        assert events["next_cursor"] == 1
        assert events["truncated"] is False
        assert events["events"][0]["sequence"] == 0
        assert events["events"][0]["url"] == "http://127.0.0.1:8188/path?q=1#ui"
        assert isinstance(events["events"][0]["created"], float)

        ensured = adapter.ensure_runtime(
            host="127.0.0.1",
            port=0,
            token="replacement-must-not-win",
            config={"runtime": {"browser": {"enabled": True, "mode": "host"}}},
        )
        assert ensured["reused"] is True
        assert ensured["browser_next_cursor"] == 1
        assert ensured["runtime_identity"] == started["runtime_identity"]
        assert ensured["env"]["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] == "secret"
        assert adapter._runtime_config["runtime"]["browser"] == {"enabled": True, "mode": "host"}

        with pytest.raises(ValueError, match="since_cursor"):
            adapter.runtime_browser_events(since_cursor=-1)
        with pytest.raises(ValueError, match="limit"):
            adapter.runtime_browser_events(limit=201)
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
