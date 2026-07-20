"""标准库 API 客户端。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "canceled"})


class ApiClientError(RuntimeError):
    """API 客户端错误。"""

    def __init__(self, code: str, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


class ApiClient:
    """SD WebUI All In One API 客户端。"""

    def __init__(self, base_url: str = "http://127.0.0.1:8765", token: str = "", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        """检查 API 服务健康状态。

        Returns:
            dict[str, Any]: 健康检查结果。
        """
        return self.request("GET", "/health")

    def methods(self) -> dict[str, Any]:
        """获取 API 方法目录。

        Returns:
            dict[str, Any]: 方法目录和元数据。
        """
        return self.request("GET", "/api/v1/methods")

    def call(self, method: str, params: dict[str, Any] | None = None, wait_ms: float | None = None) -> Any:
        """调用 API 方法作业，等待其完成并返回结果。

        提交作业后，服务在内联预算内完成则单次往返返回结果；否则返回句柄，客户端
        轮询至完成。无论快慢，方法执行时长都与单次请求超时解耦。

        Args:
            method (str): API 方法名。
            params (dict[str, Any] | None): API 方法参数。
            wait_ms (float | None): 服务端内联等待毫秒数，None 使用服务默认值。

        Returns:
            Any: 作业成功时的结果。

        Raises:
            ApiClientError: 作业失败或被取消。
        """
        body: dict[str, Any] = {"method": method, "params": params or {}}
        if wait_ms is not None:
            body["wait_ms"] = wait_ms
        status, result = self._request_status("POST", "/api/v1/call", body)
        # 200 carries the inline result directly; 202 carries a handle to poll.
        if status == 202:
            return self._await_result(result)
        return result

    def create_task(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """提交异步作业并立即返回其句柄快照（不等待完成）。

        Args:
            method (str): 方法名。
            params (dict[str, Any] | None): 方法参数。

        Returns:
            dict[str, Any]: 已创建作业的状态快照。
        """
        return self.request("POST", "/api/v1/tasks", {"method": method, "params": params or {}})

    def _await_result(self, snapshot: dict[str, Any], poll_interval: float = 0.05, poll_timeout: float = 600.0) -> Any:
        """轮询作业快照至终态并返回结果。

        Args:
            snapshot (dict[str, Any]): 提交返回的作业快照。
            poll_interval (float): 轮询间隔秒数。
            poll_timeout (float): 轮询总超时秒数。

        Returns:
            Any: 作业成功结果。

        Raises:
            ApiClientError: 作业失败、被取消或轮询超时。
        """
        deadline = time.monotonic() + poll_timeout
        while snapshot.get("status") not in _TERMINAL_STATUSES:
            if time.monotonic() > deadline:
                raise ApiClientError("task_timeout", "Timed out awaiting API job", snapshot)
            time.sleep(poll_interval)
            snapshot = self.get_task(str(snapshot.get("id")))
        status = snapshot.get("status")
        if status == "succeeded":
            return snapshot.get("result")
        error = snapshot.get("error") or {}
        code = "task_canceled" if status == "canceled" else str(error.get("code", "task_failed"))
        message = str(error.get("message") or f"API job {status}")
        raise ApiClientError(code, message, snapshot)

    def list_tasks(self) -> dict[str, Any]:
        """列出后台任务。

        Returns:
            dict[str, Any]: 后台任务列表。
        """
        return self.request("GET", "/api/v1/tasks")

    def get_task(self, task_id: str) -> dict[str, Any]:
        """获取任务状态。

        Args:
            task_id (str): 任务 ID。

        Returns:
            dict[str, Any]: 任务状态快照。
        """
        return self.request("GET", f"/api/v1/tasks/{task_id}")

    def get_task_logs(self, task_id: str) -> dict[str, Any]:
        """获取任务日志。

        Args:
            task_id (str): 任务 ID。

        Returns:
            dict[str, Any]: 任务日志列表。
        """
        return self.request("GET", f"/api/v1/tasks/{task_id}/logs")

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        """请求取消任务。

        Args:
            task_id (str): 任务 ID。

        Returns:
            dict[str, Any]: 取消请求结果。
        """
        return self.request("POST", f"/api/v1/tasks/{task_id}/cancel")

    def request(self, http_method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        """发送原始 API 请求并返回 result。

        Args:
            http_method (str): HTTP 方法。
            path (str): API 路径。
            payload (dict[str, Any] | None): JSON 请求体。

        Returns:
            Any: API 响应的 result 字段。

        Raises:
            ApiClientError: API 返回错误响应或响应格式无效。
            urllib.error.HTTPError: HTTP 请求失败且响应不是标准 API 错误格式。
        """
        return self._request_status(http_method, path, payload)[1]

    def _request_status(self, http_method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
        """发送请求并返回 (HTTP 状态码, result)。

        Args:
            http_method (str): HTTP 方法。
            path (str): API 路径。
            payload (dict[str, Any] | None): JSON 请求体。

        Returns:
            tuple[int, Any]: HTTP 状态码与响应 result 字段。

        Raises:
            ApiClientError: API 返回错误响应或响应格式无效。
            urllib.error.HTTPError: HTTP 请求失败且响应不是标准 API 错误格式。
        """
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=http_method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, self._decode_response(response.read())
        except urllib.error.HTTPError as exc:
            try:
                self._decode_response(exc.read())
            except ApiClientError as api_exc:
                raise api_exc from exc
            raise exc

    def _decode_response(self, body: bytes) -> Any:
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ApiClientError("invalid_response", "API response must be a JSON object", {"response": data})
        if data.get("ok") is True:
            return data.get("result")
        error = data.get("error")
        if not isinstance(error, dict):
            error = {}
        raise ApiClientError(
            str(error.get("code", "request_failed")),
            str(error.get("message", "API request failed")),
            data,
        )
