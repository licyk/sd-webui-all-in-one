import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from sd_webui_all_in_one.api_server import ApiClient, ApiClientError, ApiMethodSpec, create_api_server
from sd_webui_all_in_one.api_server import server as api_server_module


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
    server = create_api_server(port=0, **kwargs)
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
