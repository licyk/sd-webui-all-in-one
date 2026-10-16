"""API v2 HTTP 协议, 鉴权与客户端测试"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

import pytest

from sd_webui_all_in_one.api_server import ApiClient, ApiClientError, ApiTaskContext
from tests.api_server.helpers import api_request, api_request_error, start_server, stop_server, wait_for_task


def _request_raw(url, method="GET", data=None, token=""):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, dict(response.headers), response.read()


def _request_error_raw(url, method="GET", data=None, token=""):
    try:
        _request_raw(url, method=method, data=data, token=token)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    raise AssertionError("request unexpectedly succeeded")


def test_v1_routes_are_removed():
    server, thread, base_url = start_server()
    try:
        status, payload = api_request_error(f"{base_url}/api/v1/methods")
        assert status == 404
        assert payload["error"]["code"] == "not_found"
    finally:
        stop_server(server, thread)


def test_health_discovery_auth_and_http_protocol():
    server, thread, base_url = start_server(token="secret")
    try:
        status, payload = api_request(f"{base_url}/health")
        assert status == 200
        assert payload == {"ok": True, "result": {"status": "ok"}}

        status, payload = api_request_error(f"{base_url}/api/v2/methods")
        assert status == 401
        assert payload["error"]["code"] == "unauthorized"

        status, payload = api_request(f"{base_url}/api/v2/methods", token="secret")
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
        stop_server(server, thread)


def test_status_reports_process_tasks_and_workers_and_requires_auth():
    release = threading.Event()

    def wait(context: ApiTaskContext) -> dict[str, bool]:
        while not release.wait(0.02):
            context.check_canceled()
        return {"done": True}

    server, thread, base_url = start_server(token="secret", methods={"demo.wait": wait})
    try:
        status, payload = api_request_error(f"{base_url}/api/v2/status")
        assert status == 401
        assert payload["error"]["code"] == "unauthorized"

        status, payload = api_request(f"{base_url}/api/v2/status", token="secret")
        assert status == 200
        idle = payload["result"]
        assert idle["status"] == "ok"
        assert idle["pid"] == os.getpid()
        assert idle["uptime"] >= 0
        assert idle["started_at"] <= time.time()
        assert idle["tasks"] == {"pending": 0, "running": 0, "succeeded": 0, "failed": 0, "canceled": 0}
        assert idle["workers"] == {"max": 8, "busy": 0}

        _, payload = api_request(
            f"{base_url}/api/v2/tasks",
            method="POST",
            data={"method": "demo.wait", "params": {}},
            token="secret",
        )
        task_id = payload["result"]["id"]
        deadline = time.time() + 5
        while True:
            _, payload = api_request(f"{base_url}/api/v2/status", token="secret")
            if payload["result"]["tasks"]["running"] == 1:
                break
            assert time.time() < deadline, "task did not start"
            time.sleep(0.02)
        assert payload["result"]["workers"]["busy"] == 1

        release.set()
        deadline = time.time() + 5
        while True:
            _, task = api_request(f"{base_url}/api/v2/tasks/{task_id}", token="secret")
            if task["result"]["status"] == "succeeded":
                break
            assert time.time() < deadline, "task did not finish"
            time.sleep(0.02)
        _, payload = api_request(f"{base_url}/api/v2/status", token="secret")
        assert payload["result"]["tasks"]["running"] == 0
        assert payload["result"]["tasks"]["succeeded"] == 1
        assert payload["result"]["workers"]["busy"] == 0
    finally:
        release.set()
        stop_server(server, thread)


def test_status_blocks_while_the_task_manager_is_wedged():
    server, thread, base_url = start_server()
    try:
        with server.task_manager._lock:
            request = urllib.request.Request(f"{base_url}/api/v2/status")
            with pytest.raises(OSError):
                urllib.request.urlopen(request, timeout=0.5)
            status, payload = api_request(f"{base_url}/health")
            assert status == 200
            assert payload["result"] == {"status": "ok"}
    finally:
        stop_server(server, thread)


def test_api_client_uses_v2_protocol():
    def echo(value: int) -> dict[str, int]:
        return {"value": value}

    server, thread, base_url = start_server(methods={"demo.echo": echo})
    client = ApiClient(base_url=base_url, timeout=5)
    try:
        assert client.health() == {"status": "ok"}
        assert client.status()["workers"]["max"] == 8
        assert client.methods()["methods"] == ["demo.echo"]
        assert client.get_method("demo.echo")["parameters"][0]["type"] == "integer"
        assert client.call("demo.echo", {"value": 3}) == {"value": 3}
        task = client.create_task("demo.echo", {"value": 9})
        assert wait_for_task(base_url, task["id"], "succeeded")["result"] == {"value": 9}
        with pytest.raises(ApiClientError) as exc:
            client.call("demo.missing", {})
        assert exc.value.code == "method_not_found"
    finally:
        stop_server(server, thread)
