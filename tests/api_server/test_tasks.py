"""API v2 任务生命周期测试"""

from __future__ import annotations

import threading
import time

import pytest

from sd_webui_all_in_one.api_server import ApiTaskContext
from sd_webui_all_in_one.api_server.server import ApiTaskCanceled
from tests.api_server.helpers import api_request, api_request_error, start_server, stop_server, wait_for_task


def test_task_lifecycle_progress_logs_and_cancel():
    release = threading.Event()

    def wait(name: str, context: ApiTaskContext) -> dict[str, bool]:
        context.log(f"starting {name}")
        context.set_progress(10, "started")
        while not release.wait(0.02):
            context.check_canceled()
        return {"done": True}

    server, thread, base_url = start_server(methods={"demo.wait": wait})
    try:
        status, payload = api_request(
            f"{base_url}/api/v2/tasks",
            method="POST",
            data={"method": "demo.wait", "params": {"name": "job"}},
        )
        assert status == 202
        task_id = payload["result"]["id"]

        deadline = time.time() + 2
        while time.time() < deadline:
            _, log_payload = api_request(f"{base_url}/api/v2/tasks/{task_id}/logs")
            if log_payload["result"]["logs"]:
                break
            time.sleep(0.02)
        assert log_payload["result"]["logs"][0]["message"] == "starting job"

        _, cancel_payload = api_request(f"{base_url}/api/v2/tasks/{task_id}/cancel", method="POST")
        assert cancel_payload["result"]["canceled"] is True
        result = wait_for_task(base_url, task_id, "canceled")
        assert result["progress"] == 10
        assert result["error"]["code"] == "task_canceled"
    finally:
        release.set()
        stop_server(server, thread)


def test_task_failure_and_success_results():
    def complete(value: int, context: ApiTaskContext) -> dict[str, int]:
        context.log("done")
        context.set_progress(100, "complete")
        return {"value": value}

    def fail(message: str) -> None:
        raise RuntimeError(message)

    server, thread, base_url = start_server(methods={"demo.complete": complete, "demo.fail": fail})
    try:
        status, payload = api_request(
            f"{base_url}/api/v2/tasks",
            method="POST",
            data={"method": "demo.complete", "params": {"value": 7}},
        )
        assert status == 202
        result = wait_for_task(base_url, payload["result"]["id"], "succeeded")
        assert result["result"] == {"value": 7}

        status, payload = api_request_error(
            f"{base_url}/api/v2/call",
            method="POST",
            data={"method": "demo.fail", "params": {"message": "broken"}, "wait_ms": 1000},
        )
        assert status == 500
        assert payload["error"]["code"] == "task_failed"
        assert payload["error"]["message"] == "broken"
    finally:
        stop_server(server, thread)


def test_context_cancellation_exception_is_preserved():
    class CanceledTask:
        task_id = "id"
        is_canceled = True

    context = object.__new__(ApiTaskContext)
    context._task = CanceledTask()  # type: ignore[attr-defined]
    with pytest.raises(ApiTaskCanceled):
        context.check_canceled()
